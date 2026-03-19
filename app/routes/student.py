from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import select

from app.extensions import db
from app.models import Book, Transaction


student_bp = Blueprint("student", __name__)


@student_bp.route("/dashboard")
@login_required
def dashboard():
    if current_user.is_admin:
        return redirect(url_for("admin.dashboard"))

    books = Book.query.all()
    txns = Transaction.query.filter_by(student_id=current_user.student_id).all()
    return render_template(
        "student_dashboard.html",
        student=current_user,
        books=books,
        txns=txns,
    )


@student_bp.route("/request_book", methods=["POST"])
@login_required
def request_book():
    if current_user.is_admin:
        return "Unauthorized"

    book_id = request.form["book_id"]
    book = Book.query.get(book_id)
    if not book or book.issued_copies >= book.total_copies:
        flash("Book not available.", "danger")
        return redirect(url_for("student.dashboard"))

    existing_txn = db.session.execute(
        select(Transaction)
        .where(Transaction.student_id == current_user.student_id)
        .where(Transaction.book_id == book_id)
        .where(Transaction.status.in_(["requested", "issued", "return_requested"]))
    ).scalar_one_or_none()
    if existing_txn:
        flash("You already have an active request or issue for this book.", "warning")
        return redirect(url_for("student.dashboard"))

    new_txn = Transaction(
        student_id=current_user.student_id,
        book_id=book_id,
        status="requested",
        due_date=request.form["due_date"],
        issue_date=None,
        barcode=None,
    )
    db.session.add(new_txn)
    db.session.commit()
    flash("Book request submitted. Await admin approval.", "info")
    return redirect(url_for("student.dashboard"))


@student_bp.route("/request_return/<int:txn_id>", methods=["POST"])
@login_required
def request_return(txn_id):
    if current_user.is_admin:
        return "Unauthorized"

    txn = Transaction.query.get(txn_id)
    if txn and txn.student_id == current_user.student_id and txn.status == "issued":
        txn.status = "return_requested"
        db.session.commit()
        flash("Return request submitted. Await admin barcode verification.", "info")

    return redirect(url_for("student.dashboard"))
