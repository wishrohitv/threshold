from blueprints.app import db

class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    pid = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.VARCHAR(150), nullable=False)
    desc = db.Column(db.VARCHAR(200), nullable=False)
    body = db.Column(db.TEXT, nullable=False)

    def __repr__(self):
        return f"{self.title} {self.body} {self.desc}"


