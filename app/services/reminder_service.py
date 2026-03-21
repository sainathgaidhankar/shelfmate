from datetime import date

from app.extensions import db
from app.models import Transaction
from app.services.email_service import send_email


def get_overdue_transactions(include_already_reminded=False):
    overdue_query = Transaction.query.filter(
        Transaction.status == "issued",
        Transaction.due_date.is_not(None),
        Transaction.due_date < date.today(),
    )
    if not include_already_reminded:
        overdue_query = overdue_query.filter(
            (Transaction.reminder_sent_at.is_(None)) | (Transaction.reminder_sent_at < date.today())
        )
    return overdue_query.order_by(Transaction.due_date.asc(), Transaction.txn_id.desc()).all()


def send_overdue_reminder_for_transaction(txn):
    sent = send_email(
        txn.student.email,
        "ShelfMate Overdue Book Reminder",
        (
            f"Hello {txn.student.name},\n\nThis is a reminder that '{txn.book.title}' by {txn.book.author} "
            f"was due on {txn.due_date}.\nPlease return the book to the library as soon as possible."
            f"\n\nShelfMate Library"
        ),
    )
    if sent:
        txn.reminder_sent_at = date.today()
    return sent


def send_overdue_reminders(transactions):
    sent_count = 0
    for txn in transactions:
        if send_overdue_reminder_for_transaction(txn):
            sent_count += 1
    if sent_count:
        db.session.commit()
    return sent_count
