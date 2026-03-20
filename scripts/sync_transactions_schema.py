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
        book_columns = {column["name"] for column in inspector.get_columns("books")}
        has_update_requests_table = inspector.has_table("student_update_requests")

        if "semester" not in student_columns:
            db.session.execute(
                text("ALTER TABLE students ADD COLUMN semester VARCHAR(20) NULL AFTER section")
            )
        if "academic_status" not in student_columns:
            db.session.execute(
                text("ALTER TABLE students ADD COLUMN academic_status VARCHAR(20) NULL DEFAULT 'active' AFTER semester")
            )
            db.session.execute(
                text("UPDATE students SET academic_status = 'active' WHERE academic_status IS NULL")
            )
        if "completion_year" not in student_columns:
            db.session.execute(
                text("ALTER TABLE students ADD COLUMN completion_year INT NULL AFTER academic_status")
            )
        if "profile_image" not in student_columns:
            db.session.execute(
                text("ALTER TABLE students ADD COLUMN profile_image VARCHAR(255) NULL AFTER completion_year")
            )
        if "cover_image" not in book_columns:
            db.session.execute(
                text("ALTER TABLE books ADD COLUMN cover_image VARCHAR(255) NULL AFTER subject")
            )

        if not has_update_requests_table:
            db.session.execute(
                text(
                    """
                    CREATE TABLE student_update_requests (
                        request_id INT AUTO_INCREMENT PRIMARY KEY,
                        student_id INT NOT NULL,
                        requested_contact VARCHAR(20) NULL,
                        requested_section VARCHAR(10) NULL,
                        requested_profile_image VARCHAR(255) NULL,
                        status VARCHAR(20) NOT NULL DEFAULT 'pending',
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        reviewed_at DATETIME NULL,
                        admin_note VARCHAR(255) NULL,
                        CONSTRAINT fk_student_update_requests_student
                            FOREIGN KEY (student_id) REFERENCES students(student_id)
                            ON DELETE CASCADE
                    )
                    """
                )
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
