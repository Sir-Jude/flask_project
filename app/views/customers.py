from app.forms import CustomerDownloadForm
from app.models import User, Device, Release
from config import basedir, Config
from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user
from flask_security import verify_password
from flask_wtf import FlaskForm
import re
import os
from urllib.parse import urlsplit
from wtforms import PasswordField, StringField, SubmitField
from wtforms.validators import InputRequired, Length


class LoginForm(FlaskForm):
    username = StringField("Username", [InputRequired(), Length(min=4, max=20)])
    password = PasswordField("Password", [InputRequired(), Length(min=8, max=20)])
    submit = SubmitField("Login", render_kw={"class": "btn btn-primary"})


customers = Blueprint("customers", __name__)


@customers.route("/home/")
@customers.route("/")
def home():
    return render_template("customers/home.html")


@customers.route("/customer_login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data.lower()).first()
        if user and user.is_active:
            if verify_password(form.password.data, user.password):
                login_user(user)
                flash("Logged in successfully.")
                next_page = request.args.get("next")
                if next_page == url_for("admin.index") and "administrator" in [
                    role.name for role in user.roles
                ]:
                    next_page = url_for("admin.index")
                elif next_page is None:
                    if "administrator" in [role.name for role in user.roles]:
                        next_page = url_for("admin.index")
                    else:
                        next_page = url_for("customers.profile", username=user.username)
                return redirect(next_page)
            else:
                flash("Wrong password - Try Again...")
        else:
            flash("Invalid username.")
    return render_template("customers/login.html", form=form)


@customers.route("/customer/<username>/", methods=["GET", "POST"])
@login_required
def profile(username):
    # Only administrators may access profiles of other users
    if "administrator" not in [r.name for r in current_user.roles]:
        # Return 403 error if current user is not accessing their own profile
        if current_user.username != username:
            return render_template("errors/403.html"), 403

    # Fetch from database the device associated with provided <username>
    country = None  # Initialize country to None initially
    device = Device.query.filter_by(name=username).first()
    if device:  # Check if User has an associated device
        country = device.country
        releases = sorted(
            Release.query.join(Device).filter(Device.name == str(device)).all(),
            key=lambda r: tuple(
                int(part) if part.isdigit() else part
                for part in re.findall(r"\d+|\D+", r.version)
            ),
            reverse=True,
        )
    else:
        releases = []  # If device is not available, set releases to an empty list

    form = CustomerDownloadForm(formdata=request.form)
    # Populate the choices for release versions in the form
    form.release_version.choices = [
        # (value submitted to the form, text displayed to the user)
        (release.version, release.version)
        for release in releases
    ]

    if form.validate_on_submit():
        release_version = form.release_version.data
        release = Release.query.filter_by(version=release_version).first()

        if release:
            version = release.release_path
            return redirect(url_for("customers.download_version", version=version))
        else:
            flash("Release not found.", "error")

    return render_template(
        "customers/profile.html",
        username=username,
        device=device,
        country=country,
        releases=releases,
        form=form,
    )


@customers.route("/device/<path:version>", methods=["GET", "POST"])
@login_required
def download_version(version):
    release = Release.query.filter_by(release_path=version).first()

    version = release.release_path
    path = os.path.join(basedir, Config.UPLOAD_FOLDER, version)
    return send_file(path_or_file=path, as_attachment=True)


@customers.route("/logout/", methods=["GET", "POST"])
@login_required
def logout():
    logout_user()
    flash("You have been logged out.")
    return redirect(url_for("customers.login"))
