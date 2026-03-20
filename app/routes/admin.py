import csv
from datetime import date
from io import StringIO

from flask import Blueprint, Response, abort, flash, redirect, render_template, request, url_for
from flask_login import login_required
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError

from app.authz import admin_required
from app.extensions import db
from app.models import Book, Student, Transaction
from app.services.barcode_service import generate_barcode
from app.services.email_service import send_email
from app.services.reminder_service import (
    get_overdue_transactions,
    send_overdue_reminder_for_transaction,
    send_overdue_reminders,
)
from app.services.upload_service import save_uploaded_image


admin_bp = Blueprint("admin", __name__)
SEMESTER_OPTIONS = ["1st", "2nd", "3rd", "4th", "5th", "6th", "7th", "8th"]


def build_report_query(status="", department="", usn="", date_from=None, date_to=None):
    report_query = (
        Transaction.query.join(Student, Transaction.student_id == Student.student_id)
        .join(Book, Transaction.book_id == Book.book_id)
        .filter(Student.is_admin.is_(False))
    )
    if status:
        if status == "overdue":
            report_query = report_query.filter(
                Transaction.status == "issued",
                Transaction.due_date.is_not(None),
                Transaction.due_date < date.today(),
            )
        else:
            report_query = report_query.filter(Transaction.status == status)
    if department:
        report_query = report_query.filter(Student.department == department)
    if usn:
        report_query = report_query.filter(Student.usn.ilike(f"%{usn}%"))
    if date_from:
        report_query = report_query.filter(
            (Transaction.issue_date.is_not(None) & (Transaction.issue_date >= date_from))
            | (Transaction.due_date.is_not(None) & (Transaction.due_date >= date_from))
            | (Transaction.returned_at.is_not(None) & (Transaction.returned_at >= date_from))
        )
    if date_to:
        report_query = report_query.filter(
            (Transaction.issue_date.is_not(None) & (Transaction.issue_date <= date_to))
            | (Transaction.due_date.is_not(None) & (Transaction.due_date <= date_to))
            | (Transaction.returned_at.is_not(None) & (Transaction.returned_at <= date_to))
        )
    return report_query


def get_student_departments():
    return [
        row[0]
        for row in db.session.query(Student.department)
        .filter(Student.approved.is_(True), Student.is_admin.is_(False))
        .distinct()
        .order_by(Student.department)
        .all()
    ]


def get_student_sections():
    return [
        row[0]
        for row in db.session.query(Student.section)
        .filter(Student.approved.is_(True), Student.is_admin.is_(False))
        .distinct()
        .order_by(Student.section)
        .all()
        if row[0]
    ]


def format_export_date(value):
    if not value:
        return ""
    return value.strftime("%d-%m-%y")


@admin_bp.route("/admin_dashboard")
@login_required
@admin_required
def dashboard():
    student_department = request.args.get("student_department", default="", type=str).strip()
    books = Book.query.order_by(Book.title.asc()).all()
    students = Student.query.filter_by(approved=False).order_by(Student.usn.asc(), Student.student_id.asc()).all()
    issue_requests = (
        Transaction.query.filter_by(status="requested")
        .order_by(Transaction.txn_id.desc())
        .all()
    )
    return_requests = (
        Transaction.query.filter_by(status="return_requested")
        .order_by(Transaction.txn_id.desc())
        .all()
    )
    overdue_transactions = get_overdue_transactions(include_already_reminded=True)
    approved_students_query = Student.query.filter_by(approved=True, is_admin=False)
    if student_department:
        approved_students_query = approved_students_query.filter(Student.department == student_department)
    approved_students = approved_students_query.order_by(Student.usn.asc(), Student.name.asc()).all()
    student_departments = get_student_departments()
    student_summaries = []
    for student in approved_students:
        total_books = len(student.transactions)
        pending_books = sum(1 for txn in student.transactions if txn.status in {"requested", "issued", "return_requested"})
        returned_books = sum(1 for txn in student.transactions if txn.status == "returned")
        student_summaries.append(
            {
                "student": student,
                "total_books": total_books,
                "pending_books": pending_books,
                "returned_books": returned_books,
            }
        )
    return render_template(
        "admin_dashboard.html",
        books=books,
        pending_students=students,
        issue_requests=issue_requests,
        return_requests=return_requests,
        overdue_transactions=overdue_transactions,
        approved_students=student_summaries,
        student_departments=student_departments,
        student_department=student_department,
        today=date.today(),
    )


@admin_bp.route("/approve_student/<int:student_id>", methods=["POST"])
@login_required
@admin_required
def approve_student(student_id):
    student = Student.query.get(student_id)
    if student:
        student.approved = True
        student.is_admin = bool(student.is_admin)
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


@admin_bp.route("/reject_student/<int:student_id>", methods=["POST"])
@login_required
@admin_required
def reject_student(student_id):
    student = Student.query.get(student_id)
    if not student:
        abort(404)

    reason = request.form.get("reason", "").strip() or "Registration details did not meet verification requirements."
    db.session.delete(student)
    db.session.commit()
    flash("Student registration rejected.", "warning")
    send_email(
        student.email,
        "ShelfMate Registration Update",
        (
            f"Hello {student.name},\n\nYour registration request was not approved.\n"
            f"Reason: {reason}\n\nShelfMate Library"
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

        try:
            cover_image = save_uploaded_image(
                request.files.get("cover_image"),
                "BOOK_UPLOAD_FOLDER",
                "book",
            )
        except ValueError as exc:
            flash(str(exc), "danger")
            return redirect(url_for("admin.add_book"))

        new_book = Book(
            book_id=request.form["book_id"],
            title=request.form["title"],
            author=request.form["author"],
            department=request.form["department"],
            subject=request.form["subject"],
            cover_image=cover_image,
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

    books_pagination = books_query.paginate(page=page, per_page=10, error_out=False)
    departments = [row[0] for row in db.session.query(Book.department).distinct().order_by(Book.department).all()]
    return render_template(
        "view_books.html",
        books=books_pagination.items,
        books_pagination=books_pagination,
        search=search,
        department=department,
        sort=sort,
        departments=departments,
    )


@admin_bp.route("/student_lookup")
@login_required
@admin_required
def student_lookup():
    department = request.args.get("department", default="", type=str).strip()
    semester = request.args.get("semester", default="", type=str).strip()
    usn = request.args.get("usn", default="", type=str).strip()
    selected_student_id = request.args.get("student_id", default=0, type=int)

    student_query = Student.query.filter_by(approved=True, is_admin=False)
    if department:
        student_query = student_query.filter(Student.department == department)
    if semester:
        student_query = student_query.filter(Student.semester == semester)
    if usn:
        student_query = student_query.filter(Student.usn.ilike(f"%{usn}%"))

    filtered_students = student_query.order_by(Student.usn.asc(), Student.name.asc()).all()
    filtered_student_summaries = [
        {
            "student": student,
            "issued_books": sum(1 for txn in student.transactions if txn.status == "issued"),
            "pending_books": sum(1 for txn in student.transactions if txn.status in {"requested", "return_requested"}),
        }
        for student in filtered_students
    ]
    selected_student = None
    if selected_student_id:
        selected_student = next(
            (student for student in filtered_students if student.student_id == selected_student_id),
            None,
        )
        if not selected_student:
            flash("The selected student does not match the current filters.", "warning")
    elif usn and len(filtered_students) == 1:
        selected_student = filtered_students[0]
    elif usn and not filtered_students:
        flash("No approved student found for the given filters and USN.", "warning")

    student_summary = None
    student_transactions = []
    active_transactions = []
    available_books = []
    if selected_student:
        student_transactions = (
            Transaction.query.filter_by(student_id=selected_student.student_id)
            .order_by(Transaction.txn_id.desc())
            .all()
        )
        active_transactions = [
            txn for txn in student_transactions if txn.status in {"requested", "issued", "return_requested"}
        ]
        student_summary = {
            "total_books": len(student_transactions),
            "issued_books": sum(1 for txn in student_transactions if txn.status == "issued"),
            "pending_returns": sum(1 for txn in student_transactions if txn.status == "return_requested"),
            "requested_books": sum(1 for txn in student_transactions if txn.status == "requested"),
            "returned_books": sum(1 for txn in student_transactions if txn.status == "returned"),
        }
        available_books = (
            Book.query.filter(Book.total_copies > Book.issued_copies)
            .order_by(Book.title.asc())
            .all()
        )

    departments = get_student_departments()
    return render_template(
        "admin_student_lookup.html",
        department=department,
        semester=semester,
        usn=usn,
        departments=departments,
        semester_options=SEMESTER_OPTIONS,
        filtered_students=filtered_student_summaries,
        selected_student=selected_student,
        student_summary=student_summary,
        active_transactions=active_transactions,
        student_transactions=student_transactions,
        available_books=available_books,
    )


@admin_bp.route("/academic_updates", methods=["GET", "POST"])
@login_required
@admin_required
def academic_updates():
    department = request.values.get("department", default="", type=str).strip()
    section = request.values.get("section", default="", type=str).strip()
    current_semester = request.values.get("current_semester", default="", type=str).strip()
    academic_status = request.values.get("academic_status", default="active", type=str).strip() or "active"
    target_semester = request.values.get("target_semester", default="", type=str).strip()
    completion_year = request.values.get("completion_year", default="", type=str).strip()

    student_query = Student.query.filter_by(approved=True, is_admin=False).filter(Student.academic_status == academic_status)
    if department:
        student_query = student_query.filter(Student.department == department)
    if section:
        student_query = student_query.filter(Student.section == section)
    if current_semester:
        student_query = student_query.filter(Student.semester == current_semester)

    matched_students = student_query.order_by(Student.usn.asc(), Student.name.asc()).all()

    if request.method == "POST":
        if not matched_students:
            flash("No approved students matched the selected academic filters.", "warning")
            return redirect(
                url_for(
                    "admin.academic_updates",
                    department=department,
                    section=section,
                    current_semester=current_semester,
                    academic_status=academic_status,
                )
            )
        action = request.form.get("action", "").strip()
        if action == "promote":
            if not target_semester:
                flash("Choose the semester you want to assign before applying the promotion.", "warning")
                return redirect(
                    url_for(
                        "admin.academic_updates",
                        department=department,
                        section=section,
                        current_semester=current_semester,
                        academic_status=academic_status,
                    )
                )
            if current_semester and current_semester == target_semester:
                flash("Current semester and target semester cannot be the same.", "warning")
                return redirect(
                    url_for(
                        "admin.academic_updates",
                        department=department,
                        section=section,
                        current_semester=current_semester,
                        academic_status=academic_status,
                    )
                )
            for student in matched_students:
                student.semester = target_semester
                student.academic_status = "active"
                student.completion_year = None
            db.session.commit()
            flash(f"Updated {len(matched_students)} student record(s) to semester {target_semester}.", "success")
            return redirect(
                url_for(
                    "admin.academic_updates",
                    department=department,
                    section=section,
                    current_semester=target_semester,
                    academic_status="active",
                )
            )
        if action == "complete":
            if current_semester != "8th":
                flash("Only 8th semester batches should be marked as completed.", "warning")
                return redirect(
                    url_for(
                        "admin.academic_updates",
                        department=department,
                        section=section,
                        current_semester=current_semester,
                        academic_status=academic_status,
                    )
                )
            try:
                completion_year_value = int(completion_year)
            except (TypeError, ValueError):
                flash("Enter a valid completion year before marking students as completed.", "warning")
                return redirect(
                    url_for(
                        "admin.academic_updates",
                        department=department,
                        section=section,
                        current_semester=current_semester,
                        academic_status=academic_status,
                    )
                )
            for student in matched_students:
                student.academic_status = "completed"
                student.completion_year = completion_year_value
            db.session.commit()
            flash(f"Marked {len(matched_students)} student record(s) as completed in {completion_year_value}.", "success")
            return redirect(
                url_for(
                    "admin.academic_updates",
                    department=department,
                    section=section,
                    academic_status="completed",
                )
            )
        flash("Choose a valid academic update action.", "warning")
        return redirect(
            url_for(
                "admin.academic_updates",
                department=department,
                section=section,
                current_semester=current_semester,
                academic_status=academic_status,
            )
        )

    return render_template(
        "academic_updates.html",
        departments=get_student_departments(),
        sections=get_student_sections(),
        semester_options=SEMESTER_OPTIONS,
        department=department,
        section=section,
        current_semester=current_semester,
        academic_status=academic_status,
        target_semester=target_semester,
        completion_year=completion_year,
        matched_students=matched_students,
    )


@admin_bp.route("/student_lookup/<int:student_id>/issue_book", methods=["POST"])
@login_required
@admin_required
def direct_issue_book(student_id):
    selected_student = Student.query.filter_by(student_id=student_id, approved=True, is_admin=False).first_or_404()
    redirect_args = {
        "department": request.form.get("department", "").strip(),
        "semester": request.form.get("semester", "").strip(),
        "usn": request.form.get("usn", "").strip(),
        "student_id": student_id,
    }

    book_id = request.form.get("book_id", type=int)
    due_date = request.form.get("due_date", "").strip()
    if not book_id or not due_date:
        flash("Select a book and due date before issuing.", "warning")
        return redirect(url_for("admin.student_lookup", **redirect_args))

    book = Book.query.get(book_id)
    if not book or book.available_copies <= 0:
        flash("This book is not currently available for direct issue.", "danger")
        return redirect(url_for("admin.student_lookup", **redirect_args))

    existing_txn = db.session.execute(
        select(Transaction)
        .where(Transaction.student_id == selected_student.student_id)
        .where(Transaction.book_id == book_id)
        .where(Transaction.status.in_(["requested", "issued", "return_requested"]))
    ).scalar_one_or_none()
    if existing_txn:
        flash("This student already has an active request or issued copy for the selected book.", "warning")
        return redirect(url_for("admin.student_lookup", **redirect_args))

    direct_txn = Transaction(
        student_id=selected_student.student_id,
        book_id=book_id,
        status="issued",
        issue_date=date.today(),
        due_date=due_date,
        barcode=generate_barcode(
            book.book_id,
            selected_student.student_id,
            barcode_exists=lambda barcode: db.session.execute(
                select(Transaction).where(Transaction.barcode == barcode)
            ).scalar_one_or_none()
            is not None,
        ),
        admin_note="Direct issue by admin",
    )
    book.issued_copies += 1
    db.session.add(direct_txn)
    db.session.commit()

    flash(f"Book issued directly to {selected_student.name}. Barcode: {direct_txn.barcode}", "success")
    send_email(
        selected_student.email,
        "Book Issued From ShelfMate",
        (
            f"Hello {selected_student.name},\n\n'{book.title}' has been issued to your account directly by the library."
            f"\nDue date: {due_date}\nBarcode: {direct_txn.barcode}\n\nShelfMate Library"
        ),
    )
    return redirect(url_for("admin.student_lookup", **redirect_args))


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


@admin_bp.route("/reject_request/<int:txn_id>", methods=["POST"])
@login_required
@admin_required
def reject_request(txn_id):
    txn = Transaction.query.get(txn_id)
    if not txn or txn.status != "requested":
        flash("This request is no longer available.", "warning")
        return redirect(url_for("admin.dashboard"))

    reason = request.form.get("reason", "").strip() or "The request could not be approved."
    txn.status = "rejected"
    txn.admin_note = reason
    db.session.commit()
    flash("Book request rejected.", "warning")
    send_email(
        txn.student.email,
        "Book Request Update",
        (
            f"Hello {txn.student.name},\n\nYour request for '{txn.book.title}' was not approved.\n"
            f"Reason: {reason}\n\nShelfMate Library"
        ),
    )
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/confirm_return/<int:txn_id>", methods=["POST"])
@login_required
@admin_required
def confirm_return(txn_id):
    txn = Transaction.query.get(txn_id)
    if txn and txn.status in {"issued", "return_requested"}:
        txn.status = "returned"
        txn.returned_at = date.today()
        if txn.book.issued_copies > 0:
            txn.book.issued_copies -= 1
        db.session.commit()
        flash("Book return confirmed.", "success")
        send_email(
            txn.student.email,
            "Book Return Confirmed",
            (
                f"Hello {txn.student.name},\n\nYour return for '{txn.book.title}' has "
                "been confirmed. Thank you!\n\nShelfMate Library"
            ),
        )

    source = request.form.get("source", "").strip()
    if source == "lookup":
        return redirect(
            url_for(
                "admin.student_lookup",
                department=request.form.get("department", "").strip(),
                semester=request.form.get("semester", "").strip(),
                usn=request.form.get("usn", "").strip(),
                student_id=request.form.get("student_id", type=int),
            )
        )
    if source == "barcode":
        return redirect(url_for("admin.scan_lookup"))
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/send_overdue_reminder/<int:txn_id>", methods=["POST"])
@login_required
@admin_required
def send_overdue_reminder(txn_id):
    txn = Transaction.query.get_or_404(txn_id)
    if txn.status != "issued" or not txn.due_date or txn.due_date >= date.today():
        flash("This transaction is not currently overdue.", "warning")
        return redirect(url_for("admin.dashboard"))
    if txn.reminder_sent_at == date.today():
        flash(f"Reminder already sent to {txn.student.name} today.", "info")
        return redirect(url_for("admin.dashboard"))

    send_overdue_reminder_for_transaction(txn)
    db.session.commit()
    flash(f"Reminder email sent to {txn.student.name}.", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/send_all_overdue_reminders", methods=["POST"])
@login_required
@admin_required
def send_all_overdue_reminders():
    sent_count = send_overdue_reminders(get_overdue_transactions())
    flash(f"Reminder emails sent for {sent_count} overdue book(s).", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/view_transactions")
@login_required
@admin_required
def view_transactions():
    txns = Transaction.query.order_by(Transaction.txn_id.desc()).all()
    if not txns:
        flash("No transactions found.", "info")
    return render_template("view_transactions.html", txns=txns)


@admin_bp.route("/reports")
@login_required
@admin_required
def reports():
    status = request.args.get("status", default="", type=str).strip()
    department = request.args.get("department", default="", type=str).strip()
    usn = request.args.get("usn", default="", type=str).strip()
    date_from = request.args.get("date_from", default=None, type=date.fromisoformat)
    date_to = request.args.get("date_to", default=None, type=date.fromisoformat)

    report_query = build_report_query(status=status, department=department, usn=usn, date_from=date_from, date_to=date_to)
    transactions = report_query.order_by(Transaction.txn_id.desc()).all()
    departments = get_student_departments()
    summary = {
        "total": len(transactions),
        "issued": sum(1 for txn in transactions if txn.status == "issued"),
        "overdue": sum(1 for txn in transactions if txn.is_overdue),
        "returned": sum(1 for txn in transactions if txn.status == "returned"),
        "requested": sum(1 for txn in transactions if txn.status == "requested"),
    }
    return render_template(
        "reports.html",
        transactions=transactions,
        departments=departments,
        status=status,
        department=department,
        usn=usn,
        date_from=date_from.isoformat() if date_from else "",
        date_to=date_to.isoformat() if date_to else "",
        summary=summary,
    )


@admin_bp.route("/reports/export")
@login_required
@admin_required
def export_reports():
    status = request.args.get("status", default="", type=str).strip()
    department = request.args.get("department", default="", type=str).strip()
    usn = request.args.get("usn", default="", type=str).strip()
    date_from = request.args.get("date_from", default=None, type=date.fromisoformat)
    date_to = request.args.get("date_to", default=None, type=date.fromisoformat)

    transactions = (
        build_report_query(status=status, department=department, usn=usn, date_from=date_from, date_to=date_to)
        .order_by(Transaction.txn_id.desc())
        .all()
    )

    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "Transaction ID",
            "Status",
            "Student Name",
            "USN",
            "Department",
            "Academic",
            "Book ID",
            "Book Title",
            "Author",
            "Issued On",
            "Due On",
            "Returned On",
            "Barcode",
            "Overdue",
            "Reminder Sent",
            "Admin Note",
        ]
    )
    for txn in transactions:
        writer.writerow(
            [
                txn.txn_id,
                txn.status,
                txn.student.name,
                txn.student.usn,
                txn.student.department,
                txn.student.academic_label,
                txn.book.book_id,
                txn.book.title,
                txn.book.author,
                format_export_date(txn.issue_date),
                format_export_date(txn.due_date),
                format_export_date(txn.returned_at),
                txn.barcode or "",
                "Yes" if txn.is_overdue else "No",
                format_export_date(txn.reminder_sent_at),
                txn.admin_note or "",
            ]
        )

    filename = f"shelfmate-report-{date.today().isoformat()}.csv"
    return Response(
        buffer.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@admin_bp.route("/scan_lookup", methods=["GET", "POST"])
@login_required
@admin_required
def scan_lookup():
    if request.method == "POST":
        txn = Transaction.query.filter_by(barcode=request.form["barcode"]).first()
        if txn:
            return render_template(
                "barcode_detail.html",
                txn=txn,
                book=txn.book,
                student=txn.student,
            )

        flash("No transaction found for this barcode.", "warning")

    return render_template("scan_lookup.html")
