from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_, select

from app.extensions import db
from app.models import Book, Transaction


student_bp = Blueprint("student", __name__)


@student_bp.route("/dashboard")
@login_required
def dashboard():
    if current_user.is_admin:
        return redirect(url_for("admin.dashboard"))

    page = request.args.get("page", default=1, type=int)
    search = request.args.get("search", default="", type=str).strip()
    department = request.args.get("department", default="", type=str).strip()
    sort = request.args.get("sort", default="title", type=str)

    books_query = Book.query
    if search:
        like_term = f"%{search}%"
        books_query = books_query.filter(
            or_(
                Book.title.ilike(like_term),
                Book.author.ilike(like_term),
                Book.subject.ilike(like_term),
            )
        )
    if department:
        books_query = books_query.filter(Book.department == department)

    sort_options = {
        "title": Book.title.asc(),
        "author": Book.author.asc(),
        "subject": Book.subject.asc(),
        "department": Book.department.asc(),
        "availability": Book.issued_copies.asc(),
    }
    books_query = books_query.order_by(sort_options.get(sort, Book.title.asc()))

    books_pagination = books_query.paginate(page=page, per_page=5, error_out=False)
    txns = (
        Transaction.query.filter_by(student_id=current_user.student_id)
        .order_by(Transaction.txn_id.desc())
        .all()
    )
    departments = [row[0] for row in db.session.query(Book.department).distinct().order_by(Book.department).all()]

    return render_template(
        "student_dashboard.html",
        student=current_user,
        books=books_pagination.items,
        books_pagination=books_pagination,
        search=search,
        department=department,
        sort=sort,
        departments=departments,
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
        admin_note=None,
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
