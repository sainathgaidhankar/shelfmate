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
    academic_status = db.Column(db.String(20), default="active")
    completion_year = db.Column(db.Integer)
    profile_image = db.Column(db.String(255))
    contact = db.Column(db.String(20))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(200))
    approved = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, default=False)

    transactions = db.relationship("Transaction", back_populates="student")
    update_requests = db.relationship(
        "StudentUpdateRequest",
        back_populates="student",
        cascade="all, delete-orphan",
        order_by="desc(StudentUpdateRequest.request_id)",
    )

    @property
    def academic_label(self):
        if self.academic_status == "completed":
            return f"Completed {self.completion_year}" if self.completion_year else "Completed"
        return self.semester or "-"

    @property
    def image_path(self):
        return self.profile_image or "images/default-student.svg"

    def get_id(self):
        return str(self.student_id)
