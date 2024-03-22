from app.extensions import db
from flask_security import RoleMixin, UserMixin, SQLAlchemyUserDatastore
from sqlalchemy import Boolean, Column, event, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
import uuid


class UserRole(db.Model):
    __tablename__ = "roles_users"
    id = Column(Integer(), primary_key=True)
    user_id = Column("user_id", Integer(), ForeignKey("users.user_id"))
    role_id = Column("role_id", Integer(), ForeignKey("roles.role_id"))


class User(db.Model, UserMixin):
    __tablename__ = "users"
    user_id = Column(Integer, primary_key=True)
    username = Column(String(100), unique=True, index=True)
    password = Column(String(80))
    device_name = Column(String, ForeignKey("devices.name"), unique=True)
    active = Column(Boolean())
    roles = relationship(
        "Role", secondary="roles_users", back_populates="users", lazy=True
    )
    device = relationship("Device", back_populates="user", uselist=False)
    fs_uniquifier = Column(
        String(255),
        unique=True,
        nullable=False,
        # Line below necessary to avoid "ValueError: Constraint must have a name"
        name="unique_fs_uniquifier_constraint",
    )

    def versions(self):
        if self.devices:
            return ", ".join(release.version for release in self.devices.releases)
        else:
            return ""

    def __repr__(self):
        return self.username


class Role(db.Model, RoleMixin):
    __tablename__ = "roles"
    role_id = Column(Integer(), primary_key=True)
    name = Column(String(20), unique=True)
    description = Column(String(255))
    users = relationship(
        "User", secondary="roles_users", back_populates="roles", lazy=True
    )

    def __repr__(self):
        return f"{self.name} (role_id={self.role_id})"


class Country(db.Model):
    __tablename__ = "countries"
    country_id = Column(Integer, primary_key=True)
    name = Column(String(40), unique=True)
    devices = relationship("Device", back_populates="country", lazy=True)

    def __repr__(self):
        return f"{self.name}"


class Device(db.Model):
    __tablename__ = "devices"
    device_id = Column(Integer, primary_key=True)
    name = Column(String(20), unique=True)
    country_id = Column(Integer, ForeignKey("countries.country_id"))
    user = relationship("User", back_populates="device", uselist=False, lazy=True)
    releases = relationship("Release", back_populates="device", lazy=True)
    country = relationship("Country", back_populates="devices", lazy=True)

    def __repr__(self):
        return f"{self.name}"


class Release(db.Model):
    __tablename__ = "releases"
    release_id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey("devices.device_id"))
    version = Column(String(20))  # e.g. 8.0.122
    release_path = Column(String(255))
    flag_visible = Column(Boolean())
    device = relationship("Device", back_populates="releases", uselist=False, lazy=True)

    def __repr__(self):
        return f"{self.version}"


# Generate a random fs_uniquifier: users cannot login without it
@event.listens_for(User, "before_insert")
def before_insert_listener(mapper, connection, target):
    if target.fs_uniquifier is None:
        target.fs_uniquifier = str(uuid.uuid4())


user_datastore = SQLAlchemyUserDatastore(db, User, Role)
