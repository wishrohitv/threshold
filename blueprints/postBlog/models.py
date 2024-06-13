from blueprints.app import db

class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    pid = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.VARCHAR(100), nullable=False)
    body = db.Column(db.TEXT, nullable=False)

    def __repr__(self):
        return f"{self.title} {self.body}"


