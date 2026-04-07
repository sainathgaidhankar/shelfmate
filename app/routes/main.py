from io import BytesIO
from pathlib import Path

from flask import Blueprint, abort, current_app, render_template, send_file, url_for

from app.models import UploadedImage


def media_url(path: str | None, default_path: str) -> str:
    if not path:
        return url_for("static", filename=default_path)
    if path.startswith("db:"):
        return url_for("main.media_asset", image_id=path.split(":", 1)[1])
    if not (Path(current_app.static_folder) / path).exists():
        current_app.logger.warning("Requested missing legacy image asset: %s", path)
        return url_for("static", filename=default_path)
    return url_for("static", filename=path)


main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def welcome():
    return render_template("welcome.html")


@main_bp.route("/media/<string:image_id>")
def media_asset(image_id):
    image = UploadedImage.query.get(image_id)
    if not image:
        current_app.logger.warning("Requested missing uploaded image asset: %s", image_id)
        abort(404)
    return send_file(
        BytesIO(image.data),
        mimetype=image.content_type,
        download_name=image.filename,
        max_age=60 * 60 * 24 * 30,
    )
