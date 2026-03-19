from app.extensions import db


class Transaction(db.Model):
    __tablename__ = "transactions"

    txn_id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(
        db.Integer,
        db.ForeignKey("students.student_id"),
        nullable=False,
    )
    book_id = db.Column(
        db.Integer,
        db.ForeignKey("books.book_id"),
        nullable=False,
    )
    status = db.Column(db.String(50), default="requested", nullable=False)
    issue_date = db.Column(db.Date)
    due_date = db.Column(db.Date)
    returned_at = db.Column("return_date", db.Date)
    barcode = db.Column(db.String(100), unique=True)

    student = db.relationship("Student", back_populates="transactions")
    book = db.relationship("Book", back_populates="transactions")
