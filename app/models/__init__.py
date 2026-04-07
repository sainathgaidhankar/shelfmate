from app.extensions import db
from app.models.book import Book
from app.models.student import Student
from app.models.student_update_request import StudentUpdateRequest
from app.models.transaction import Transaction
from app.models.uploaded_image import UploadedImage

__all__ = ["Book", "Student", "StudentUpdateRequest", "Transaction", "UploadedImage", "db"]
