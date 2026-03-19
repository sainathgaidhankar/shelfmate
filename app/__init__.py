from flask import Flask

from app.error_handlers import register_error_handlers
from app.extensions import csrf, db, login_manager, migrate
from app.logging_config import configure_logging
from app.models import Student
from app.routes import admin_bp, auth_bp, main_bp, student_bp
from config import get_config


def create_app(config_class=None):
    if config_class is None:
        config_class = get_config()

    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(config_class)
    config_class.validate()

    db.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    configure_logging(app)

    @login_manager.user_loader
    def load_user(student_id):
        return Student.query.get(int(student_id))

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(admin_bp)
    register_error_handlers(app)

    return app
