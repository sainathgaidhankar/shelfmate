from datetime import datetime

from app.extensions import db


class StudentUpdateRequest(db.Model):
    __tablename__ = "student_update_requests"

    request_id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.student_id"), nullable=False)
    requested_contact = db.Column(db.String(20))
    requested_section = db.Column(db.String(10))
    requested_profile_image = db.Column(db.String(255))
    status = db.Column(db.String(20), nullable=False, default="pending")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime)
    admin_note = db.Column(db.String(255))

    student = db.relationship("Student", back_populates="update_requests")
