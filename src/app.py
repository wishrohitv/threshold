from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from settings import Settings
from werkzeug.middleware.proxy_fix import ProxyFix
import os

if Settings.DEBUG_MODE:
    # Allow insecure HTTP connections for local testing
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

from .utils.error_handler.page_not_found import return_404_page
from .utils.context_processors.return_story_slug import return_story_slug

db = SQLAlchemy()


def create_app():
    app = Flask(__name__, template_folder="templates")

    # Tell Flask to read X-Forwarded-Proto from Railway's proxy
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

    app.config["SQLALCHEMY_DATABASE_URI"] = Settings.DATABASE_URI
    app.config["SECRET_KEY"] = Settings.SECRET_KEY

    # Keep these to ensure the cookie survives the OAuth redirect
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['SESSION_COOKIE_SECURE'] = True

    db.init_app(app)

    # import models so SQLAlchemy can resolve relationships
    from .blueprints.users.models import User, BlockedUser  # noqa: F401
    from .blueprints.stories.models import Story, Comments, Like  # noqa: F401

    # create all tables
    with app.app_context():
        db.create_all()

    # Register context processor
    app.context_processor(return_story_slug)

    # import and register all blueprints
    from .blueprints.index.routes import index_bp
    from .blueprints.users.routes import users
    from .blueprints.stories.routes import stories
    from .blueprints.about.routes import about
    from .blueprints.search.routes import search_bp

    app.register_blueprint(index_bp, url_prefix="/")

    app.register_blueprint(users, url_prefix="/users")

    app.register_blueprint(stories, url_prefix="/stories")

    app.register_blueprint(about, url_prefix="/about")

    app.register_blueprint(search_bp, url_prefix="/search")

    @app.errorhandler(404)
    def handle_404(e):
        return return_404_page(e)

    migrate = Migrate(app, db)  # noqa: F841

    return app
