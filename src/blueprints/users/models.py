from src.app import db
from datetime import datetime


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.VARCHAR(150), nullable=False, unique=True)
    email = db.Column(db.VARCHAR(150), nullable=False, unique=True)
    name = db.Column(db.String(25), nullable=True)
    password = db.Column(db.TEXT, nullable=False)
    avatar = db.Column(db.LargeBinary, nullable=False)
    bio = db.Column(db.String(50), nullable=True)
    role = db.Column(db.String(10), default="user")
    date_created = db.Column(db.DateTime, default=datetime.now)

    def __repr__(self):
        return f"""User( 
            id={self.id!r},
            username={self.username!r},
            email={self.email!r},
            password={self.password!r},
            avatar={self.avatar!r},
            date_created={self.date_created!r}
            )"""


class BlockedUser(db.Model):
    __tablename__ = "blocked_users"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    target_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.now)
