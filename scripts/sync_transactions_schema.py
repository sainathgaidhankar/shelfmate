from pathlib import Path
import sys

from sqlalchemy import inspect, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app
from app.extensions import db


def has_index(inspector, table_name, index_name):
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def main():
    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)
        columns = {column["name"] for column in inspector.get_columns("transactions")}
        student_columns = {column["name"] for column in inspector.get_columns("students")}

        if "semester" not in student_columns:
            db.session.execute(
                text("ALTER TABLE students ADD COLUMN semester VARCHAR(20) NULL AFTER section")
            )

        if "due_date" not in columns:
            db.session.execute(text("ALTER TABLE transactions ADD COLUMN due_date DATE NULL AFTER issue_date"))
            db.session.execute(text("UPDATE transactions SET due_date = return_date WHERE due_date IS NULL"))
        if "admin_note" not in columns:
            db.session.execute(text("ALTER TABLE transactions ADD COLUMN admin_note VARCHAR(255) NULL AFTER barcode"))
        if "reminder_sent_at" not in columns:
            db.session.execute(text("ALTER TABLE transactions ADD COLUMN reminder_sent_at DATE NULL AFTER admin_note"))

        db.session.execute(
            text("ALTER TABLE transactions MODIFY student_id INT NOT NULL")
        )
        db.session.execute(
            text("ALTER TABLE transactions MODIFY book_id INT NOT NULL")
        )
        db.session.execute(
            text(
                "ALTER TABLE transactions MODIFY status VARCHAR(50) NOT NULL DEFAULT 'requested'"
            )
        )

        if not has_index(inspector, "transactions", "uq_transactions_barcode"):
            db.session.execute(
                text("ALTER TABLE transactions ADD CONSTRAINT uq_transactions_barcode UNIQUE (barcode)")
            )

        db.session.commit()


if __name__ == "__main__":
    main()
