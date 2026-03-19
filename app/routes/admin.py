from datetime import date

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.authz import admin_required
from app.extensions import db
from app.models import Book, Student, Transaction
from app.services.barcode_service import generate_barcode
from app.services.email_service import send_email


admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/admin_dashboard")
@login_required
@admin_required
def dashboard():
    books = Book.query.all()
    students = Student.query.filter_by(approved=False).all()
    issue_requests = Transaction.query.filter_by(status="requested").all()
    return_requests = Transaction.query.filter_by(status="return_requested").all()
    return render_template(
        "admin_dashboard.html",
        books=books,
        pending_students=students,
        issue_requests=issue_requests,
        return_requests=return_requests,
    )


@admin_bp.route("/approve_student/<int:student_id>", methods=["POST"])
@login_required
@admin_required
def approve_student(student_id):
    student = Student.query.get(student_id)
    if student:
        student.approved = True
        db.session.commit()
        flash("Student approved successfully.", "success")
        send_email(
            student.email,
            "ShelfMate Registration Approved",
            (
                f"Hello {student.name},\n\nYour registration has been approved. "
                "You can now log in.\n\nShelfMate Library"
            ),
        )

    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/add_book", methods=["GET", "POST"])
@login_required
@admin_required
def add_book():
    if request.method == "POST":
        try:
            total_copies = int(request.form["total_copies"])
        except (TypeError, ValueError):
            flash("Total copies must be a positive integer.", "danger")
            return redirect(url_for("admin.add_book"))

        if total_copies <= 0:
            flash("Total copies must be a positive integer.", "danger")
            return redirect(url_for("admin.add_book"))

        new_book = Book(
            book_id=request.form["book_id"],
            title=request.form["title"],
            author=request.form["author"],
            department=request.form["department"],
            subject=request.form["subject"],
            total_copies=total_copies,
            issued_copies=0,
        )
        db.session.add(new_book)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("Book ID already exists. Please use a unique book ID.", "danger")
            return redirect(url_for("admin.add_book"))
        flash("Book added successfully.", "success")
        return redirect(url_for("admin.view_books"))

    return render_template("add_book.html")


@admin_bp.route("/view_books")
@login_required
@admin_required
def view_books():
    books = Book.query.all()
    return render_template("view_books.html", books=books)


@admin_bp.route("/approve_request/<int:txn_id>", methods=["POST"])
@login_required
@admin_required
def approve_request(txn_id):
    try:
        txn = db.session.execute(
            select(Transaction)
            .where(Transaction.txn_id == txn_id)
            .with_for_update()
        ).scalar_one_or_none()
        if not txn or txn.status != "requested":
            flash("This request is no longer available for approval.", "warning")
            return redirect(url_for("admin.dashboard"))

        book = db.session.execute(
            select(Book)
            .where(Book.book_id == txn.book_id)
            .with_for_update()
        ).scalar_one()
        student = txn.student

        if book.available_copies <= 0:
            flash("No copies available!", "danger")
            return redirect(url_for("admin.dashboard"))

        book.issued_copies += 1
        txn.status = "issued"
        txn.issue_date = date.today()
        txn.barcode = generate_barcode(
            book.book_id,
            student.student_id,
            barcode_exists=lambda barcode: db.session.execute(
                select(Transaction).where(Transaction.barcode == barcode)
            ).scalar_one_or_none()
            is not None,
        )
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash("The request could not be approved. Please try again.", "danger")
        return redirect(url_for("admin.dashboard"))

    flash(f"Book issued successfully! Barcode: {txn.barcode}", "success")
    send_email(
        student.email,
        "Book Request Approved",
        (
            f"Hello {student.name},\n\nYour request for '{book.title}' has been "
            "approved. Please collect your book.\n\nShelfMate Library"
        ),
    )

    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/confirm_return/<int:txn_id>", methods=["POST"])
@login_required
@admin_required
def confirm_return(txn_id):
    txn = Transaction.query.get(txn_id)
    if txn and txn.status == "return_requested":
        txn.status = "returned"
        txn.returned_at = date.today()
        if txn.book.issued_copies > 0:
            txn.book.issued_copies -= 1
        db.session.commit()
        flash("Book return confirmed via barcode scan.", "success")
        send_email(
            txn.student.email,
            "Book Return Confirmed",
            (
                f"Hello {txn.student.name},\n\nYour return for '{txn.book.title}' has "
                "been confirmed. Thank you!\n\nShelfMate Library"
            ),
        )

    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/view_transactions")
@login_required
@admin_required
def view_transactions():
    txns = Transaction.query.all()
    if not txns:
        flash("No transactions found.", "info")
    return render_template("view_transactions.html", txns=txns)


@admin_bp.route("/scan_lookup", methods=["GET", "POST"])
@login_required
@admin_required
def scan_lookup():
    if request.method == "POST":
        txn = Transaction.query.filter_by(barcode=request.form["barcode"]).first()
        if txn and txn.status == "return_requested":
            return render_template(
                "barcode_detail.html",
                txn=txn,
                book=txn.book,
                student=txn.student,
            )

        flash("No pending return found for this barcode.", "warning")

    return render_template("scan_lookup.html")
