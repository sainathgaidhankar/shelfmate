from app.extensions import db


class Book(db.Model):
    __tablename__ = "books"

    book_id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    author = db.Column(db.String(100))
    department = db.Column(db.String(50))
    subject = db.Column(db.String(50))
    total_copies = db.Column(db.Integer)
    issued_copies = db.Column(db.Integer, default=0)

    transactions = db.relationship("Transaction", back_populates="book")

    @property
    def available_copies(self):
        total = int(getattr(self, "total_copies", 0) or 0)
        issued = int(getattr(self, "issued_copies", 0) or 0)
        return max(0, total - issued)
