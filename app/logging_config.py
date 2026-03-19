import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def configure_logging(app):
    log_level_name = app.config.get("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_name, logging.INFO)

    app.logger.setLevel(log_level)

    if app.debug or app.testing:
        return

    log_dir = Path(app.config.get("LOG_DIR", "logs"))
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "app.log"

    handler = RotatingFileHandler(log_file, maxBytes=1_000_000, backupCount=5)
    handler.setLevel(log_level)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s [%(name)s] %(message)s"
        )
    )

    if not any(
        isinstance(existing_handler, RotatingFileHandler)
        and getattr(existing_handler, "baseFilename", None) == str(log_file)
        for existing_handler in app.logger.handlers
    ):
        app.logger.addHandler(handler)
