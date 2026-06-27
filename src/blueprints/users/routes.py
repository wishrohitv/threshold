from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    send_file,
    abort,
)
from sqlalchemy.sql.elements import or_
from passlib.hash import sha256_crypt as encryption
from io import BytesIO
from src.app import db
from .models import User
from src.blueprints.stories.models import Story, Comments, Bookmark, Like

users = Blueprint("users", __name__, template_folder="templates")


@users.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        form = request.form
        name = form.get("name")
        username = form.get("username")
        email = form.get("email")
        password = form.get("password")
        confirm_password = form.get("confirm_password")
        avatar = request.files.get("avatar")
        term = form.get("term")

        # Check if user with username or email exist or not
        is_user: User | None = db.session.execute(
            db.select(User).filter(or_(User.username == username, User.email == email))
        ).scalar()

        if is_user:
            flash("User with already exists with this username or email", "denger")
            return redirect(url_for("users.signup"))

        if term != "on":
            flash("Please accept our terms conditions", "denger")

        hashed_password = encryption.hash(password)
        user = User(
            name=name,
            username=username,
            email=email,
            password=hashed_password,
            avatar=avatar.stream.read(),
        )
        db.session.add(user)
        db.session.commit()
        flash("Account created successfully!")
        return redirect(url_for("users.login"))
    return render_template("signup.html")


@users.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        form = request.form
        email = form.get("email")
        password = form.get("password")

        user = db.session.execute(db.select(User).filter_by(email=email)).scalar()

        if not user:
            flash("User not found")
            return redirect(url_for("users.login")), 404

        # match password
        is_match = encryption.verify(password, user.password)

        if is_match:
            session["id"] = user.id
            session["role"] = user.role
            session["username"] = user.username

            return redirect(url_for("index.index"))
        else:
            flash("Wrong password, try again!")
            return redirect(url_for("users.login", email=email))

    return render_template("login.html")


@users.route("/<string:username>", methods=["GET"])
def profile(username):
    tab = request.args.get("tab", default="post", type=str)

    if tab not in ["post", "comment"]:
        abort(404)

    user = db.session.execute(
        db.select(
            User.id,
            User.username,
            User.name,
            User.bio,
            User.date_created,
        ).filter_by(username=username)
    ).first()
    if not user:
        abort(404)

    _user = {
        "id": user.id,
        "username": user.username,
        "name": user.name,
        "bio": user.bio,
        "date_created": user.date_created.strftime("%B %Y"),
    }

    stats = db.session.execute(
        db.select(
            db.select(db.func.count(Story.id))
            .where(Story.user_id == user.id)
            .scalar_subquery()
            .label("post_count"),
            db.select(db.func.count(Like.id))
            .join(Story, Story.id == Like.story_id)
            .where(Story.user_id == user.id, Like.like == 1)
            .scalar_subquery()
            .label("like_count"),
            db.select(db.func.count(Comments.id))
            .join(Story, Story.id == Comments.story_id)
            .where(Comments.user_id == user.id)
            .scalar_subquery()
            .label("comment_count"),
            db.select(db.func.coalesce(db.func.sum(Story.views), 0))
            .where(Story.user_id == user.id)
            .scalar_subquery()
            .label("views_count"),
        )
    ).one()
    stories = None
    comments = None
    if tab == "post":
        stories = db.session.execute(
            db.select(
                Story.id,
                Story.title,
                Story.desc,
                Story.date_created,
                Story.views.label("views_count"),
                db.select(db.func.count(Like.id))
                .where(Like.story_id == Story.id, Like.like == 1)
                .scalar_subquery()
                .label("like_count"),
                db.select(db.func.count(Comments.id))
                .where(Comments.story_id == Story.id)
                .scalar_subquery()
                .label("comment_count"),
            )
            .filter_by(user_id=user.id)
            .limit(10)
            .order_by(Story.date_created.desc())
        ).all()
    else:
        comments = db.session.execute(
            db.select(
                Comments.id,
                Comments.body,
                Comments.date_created,
                Story.title.label("story_title"),
                Story.id.label("story_id"),
            )
            .join(Story, Story.id == Comments.story_id)
            .filter_by(user_id=user.id)
            .limit(15)
            .order_by(Comments.date_created.desc())
        ).all()

    return render_template(
        "profile.html",
        user=_user,
        stats=stats._mapping,
        stories=stories,
        comments=comments,
        tab=tab,
    )


@users.route("/change-password", methods=["GET", "POST"])
def change_password():
    # Check user session
    user_id = session.get("id")
    if user_id:
        redirect()

    return render_template("profile.html")


@users.route("/avatar/<int:user_id>")
def avatar(user_id):
    user = db.session.execute(db.select(User).filter_by(id=user_id)).scalar()
    image = BytesIO(user.avatar)
    return send_file(image, mimetype="image/png")
