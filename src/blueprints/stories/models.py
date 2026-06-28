import base64
from src.app import db
from datetime import datetime


class Story(db.Model):
    __tablename__ = "stories"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    banner = db.Column(db.LargeBinary, nullable=False)
    title = db.Column(db.VARCHAR(150), nullable=False)
    desc = db.Column(db.VARCHAR(200), nullable=False)
    body = db.Column(db.TEXT, nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.now)
    last_edited = db.Column(db.DateTime, nullable=True, default=datetime.now)
    comments = db.relationship(
        "Comments", backref="story", lazy=True, cascade="all, delete-orphan"
    )
    # user = db.relationship("User", backref="stories", lazy=True)
    views = db.Column(db.Integer, default=0)
    likes = db.relationship(
        "Like", backref="story", lazy=True, cascade="all, delete-orphan"
    )
    bookmark = db.relationship(
        "Bookmark", backref="story", lazy=True, cascade="all, delete-orphan"
    )
    story_uid = db.Column(db.String(18), nullable=False, unique=True)
    tags = db.Column(db.String(50), nullable=False)

    def __repr__(self):
        return f"""<Story(
            id={self.id!r},
            user_id={self.user_id!r},
            title={self.title!r},
            desc={self.desc!r},
            body={self.body!r},
            date_created={self.date_created!r},
            views={self.views!r},
            likes={self.likes!r},
            bookmark={self.bookmark!r},
            story_uid={self.story_uid!r},
            tags={self.tags!r}
            )>"""


class Like(db.Model):
    __tablename__ = "likes"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    story_id = db.Column(db.Integer, db.ForeignKey("stories.id"), nullable=False)
    like = db.Column(db.Integer, default=1)  # 1 for like, 0 for unlike
    user = db.relationship("User", backref="likes", lazy=True)

    def __repr__(self):
        return f"""<Like(
            id={self.id!r},
            user_id={self.user_id!r},
            story_id={self.story_id!r},
            like={self.like!r},
            user={self.user!r},
            story={self.story!r},
            )>"""


class Bookmark(db.Model):
    __tablename__ = "bookmarks"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    story_id = db.Column(db.Integer, db.ForeignKey("stories.id"), nullable=False)
    user = db.relationship("User", backref="bookmark", lazy=True)

    def __repr__(self):
        return f"""<Bookmark(
            id={self.id!r},
            user_id={self.user_id!r},
            story_id={self.story_id!r},
            user={self.user!r},
            )>"""


class Comments(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    story_id = db.Column(db.Integer, db.ForeignKey("stories.id"), nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.now)
    body = db.Column(db.String(200), nullable=False)

    def __repr__(self):
        return f"""<Comments(
            id={self.id!r},
            user_id={self.user_id!r},
            story_id={self.story_id!r},
            date_created={self.date_created!r},
            body={self.body!r},
            )>"""
