from datetime import datetime
from uuid import uuid4

from app.extensions import db


class UploadedImage(db.Model):
    __tablename__ = "uploaded_images"

    image_id = db.Column(db.String(32), primary_key=True, default=lambda: uuid4().hex)
    filename = db.Column(db.String(255), nullable=False)
    content_type = db.Column(db.String(100), nullable=False)
    data = db.Column(db.LargeBinary, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
