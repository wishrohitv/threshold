from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

db = SQLAlchemy()

def create_app():
    app = Flask(__name__, template_folder="templates")
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///blog_data.db"


    db.init_app(app)

    # import and register all blueprints

    from blueprints.core.routes import core
    from blueprints.stories.routes import stories
    from blueprints.about.routes import about

    app.register_blueprint(core, url_prefix="/")

    app.register_blueprint(stories, url_prefix= '/stories')

    app.register_blueprint(about, url_prefix= '/about')


    migrate = Migrate(app, db)

    return app