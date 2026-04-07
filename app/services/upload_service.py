from pathlib import Path
from uuid import uuid4

from flask import current_app
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models import UploadedImage


def save_uploaded_image(file_storage: FileStorage | None, folder_key: str, prefix: str) -> str | None:
    if not file_storage or not file_storage.filename:
        return None

    filename = secure_filename(file_storage.filename)
    if not filename:
        raise ValueError("Invalid image filename.")

    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    allowed_extensions = current_app.config.get("ALLOWED_IMAGE_EXTENSIONS", set())
    if extension not in allowed_extensions:
        raise ValueError("Only image files are allowed.")

    storage_backend = current_app.config.get("IMAGE_STORAGE_BACKEND", "database").lower()
    if storage_backend == "database":
        try:
            image_id = uuid4().hex
            image = UploadedImage(
                image_id=image_id,
                filename=f"{prefix}-{filename}",
                content_type=file_storage.mimetype or f"image/{extension}",
                data=file_storage.read(),
            )
            db.session.add(image)
            db.session.flush()
            return f"db:{image_id}"
        except SQLAlchemyError as exc:
            db.session.rollback()
            current_app.logger.exception("Database-backed image upload failed for %s", filename)
            raise RuntimeError("Image upload failed. Please try a smaller image or retry.") from exc

    relative_folder = current_app.config[folder_key]
    output_dir = Path(current_app.static_folder) / relative_folder
    output_dir.mkdir(parents=True, exist_ok=True)

    output_name = f"{prefix}-{uuid4().hex}.{extension}"
    output_path = output_dir / output_name
    file_storage.save(output_path)
    return f"{relative_folder}/{output_name}".replace("\\", "/")
