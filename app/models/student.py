from flask_login import UserMixin

from app.extensions import db


class Student(UserMixin, db.Model):
    __tablename__ = "students"

    student_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    usn = db.Column(db.String(50))
    department = db.Column(db.String(50))
    section = db.Column(db.String(10))
    semester = db.Column(db.String(20))
    contact = db.Column(db.String(20))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(200))
    approved = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, default=False)

    transactions = db.relationship("Transaction", back_populates="student")

    def get_id(self):
        return str(self.student_id)
