from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required, login_user, logout_user
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db
from app.models import Student
from app.services.upload_service import save_uploaded_image


auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        existing_student = Student.query.filter_by(email=request.form["email"]).first()
        if existing_student:
            flash("Email already registered. Please login instead.", "danger")
            return redirect(url_for("auth.login"))

        try:
            profile_image = save_uploaded_image(
                request.files.get("profile_image"),
                "STUDENT_UPLOAD_FOLDER",
                "student",
            )
        except ValueError as exc:
            flash(str(exc), "danger")
            return redirect(url_for("auth.register"))

        new_student = Student(
            name=request.form["name"],
            usn=request.form["usn"],
            department=request.form["department"],
            section=request.form["section"],
            semester=request.form["semester"],
            academic_status="active",
            completion_year=None,
            profile_image=profile_image,
            contact=request.form["contact"],
            email=request.form["email"],
            password=generate_password_hash(request.form["password"]),
            approved=False,
            is_admin=False,
        )
        db.session.add(new_student)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("Email already registered. Please login instead.", "danger")
            return redirect(url_for("auth.login"))
        flash("Registration request submitted. Await admin approval.", "info")
        return redirect(url_for("auth.login"))

    return render_template("register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        student = Student.query.filter_by(email=request.form["email"]).first()

        if student and check_password_hash(student.password, request.form["password"]):
            if not student.approved:
                flash("Your account is pending admin approval.", "warning")
                return redirect(url_for("auth.login"))
            login_user(student)
            flash("Login successful!", "success")
            return redirect(url_for("student.dashboard"))

        flash("Invalid credentials.", "danger")

    return render_template("login.html")


@auth_bp.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        admin = Student.query.filter_by(
            email=request.form["email"],
            is_admin=True,
        ).first()
        if admin and check_password_hash(admin.password, request.form["password"]):
            login_user(admin)
            flash("Admin login successful!", "success")
            return redirect(url_for("admin.dashboard"))

        flash("Invalid admin credentials.", "danger")

    return render_template("admin_login.html")


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return redirect(url_for("main.welcome"))
