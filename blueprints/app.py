from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

db = SQLAlchemy()

def create_app():
    app = Flask(__name__, template_folder="templates")
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///blog_data.db"
    app.secret_key = "threshold"


    db.init_app(app)

    # import and register all blueprints

    from blueprints.core.routes import core
    from blueprints.postBlog.routes import postBlog

    app.register_blueprint(core, url_prefix="/")

    app.register_blueprint(postBlog, url_prefix= '/postBlog')


    migrate = Migrate(app, db)

    return app