from config import basedir, Config
from flask import current_app
from flask_security import (
    RegisterForm,
    LoginForm,
    unique_identity_attribute,
    lookup_identity,
)
from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    FileField,
    PasswordField,
    SelectField,
    StringField,
    SubmitField,
)
from wtforms.validators import InputRequired, Length, ValidationError
from werkzeug.local import LocalProxy
import os


def username_validator(form, field):
    # Side-effect - field.data is updated to normalized value.
    # Use proxy to we can declare this prior to initializing Security.
    _security = LocalProxy(lambda: current_app.extensions["security"])
    msg, field.data = _security._username_util.validate(field.data)
    if msg:
        raise ValidationError(msg)


class ExtendedRegisterForm(RegisterForm):
    email = StringField(
        "Username", [InputRequired(), username_validator, unique_identity_attribute]
    )
    password = PasswordField("Password", [InputRequired(), Length(min=8, max=20)])
    device = StringField("Device")
    active = BooleanField("Active")
    roles = SelectField(
        "Roles",
        choices=[
            ("customer"),
            ("administrator"),
            ("sales"),
            ("production"),
            ("application"),
            ("software"),
        ],
        validators=[InputRequired()],
    )


class ExtendedLoginForm(LoginForm):
    email = StringField("Username", [InputRequired()])

    def validate(self, **kwargs):
        self.user = lookup_identity(self.email.data)
        # Setting 'ifield' informs the default login form validation
        # handler that the identity has already been confirmed.
        self.ifield = self.email
        if not super().validate(**kwargs):
            return False
        return True


class DeviceSearchForm(FlaskForm):
    device_name = StringField("Device: ")
    selected_release_version = StringField("Release: ")
    submit = SubmitField("Search", render_kw={"class": "btn btn-primary"})


class DownloadReleaseForm(FlaskForm):
    release_version = SelectField("Version: ")
    submit = SubmitField("Download", render_kw={"class": "btn btn-primary"})


class UploadReleaseForm(FlaskForm):
    device = StringField("Device: ")
    version = FileField("Version: ")
    submit = SubmitField("Upload", render_kw={"class": "btn btn-primary"})

    def __init__(self, device_value=None, *args, **kwargs):
        super(UploadReleaseForm, self).__init__(*args, **kwargs)
        if device_value:
            self.device.data = device_value

    def allowed_file(self):
        version = self.version.data
        return (
            "." in version.filename
            and version.filename.rsplit(".", 1)[1].lower() in Config.ALLOWED_EXTENSIONS
        )

    def path_exists(self):
        upload_path = os.path.join(basedir, Config.UPLOAD_FOLDER, self.device.data)
        print(upload_path)
        return os.path.exists(upload_path)
