from pathlib import Path
from uuid import uuid4

from flask import current_app
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename


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

    relative_folder = current_app.config[folder_key]
    output_dir = Path(current_app.static_folder) / relative_folder
    output_dir.mkdir(parents=True, exist_ok=True)

    output_name = f"{prefix}-{uuid4().hex}.{extension}"
    output_path = output_dir / output_name
    file_storage.save(output_path)
    return f"{relative_folder}/{output_name}".replace("\\", "/")
