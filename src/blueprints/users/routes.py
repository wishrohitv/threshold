import json
import os
import random
from io import BytesIO

import google.oauth2.credentials
import google_auth_oauthlib.flow
import requests
from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from googleapiclient.discovery import build
from passlib.hash import sha256_crypt as encryption
from sqlalchemy.sql.elements import or_

from src.app import db
from src.blueprints.stories.models import Bookmark, Comments, Like, Story

from .models import User

users = Blueprint("users", __name__, template_folder="templates")

OAUTH_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]

flow = None


def _get_flow():
    """Build the OAuth flow from the GOOGLE_CLIENT_SECRET env var (production)
    or from client_secret.json on disk (local dev).
    """
    client_secret_path = f"{os.getcwd()}/client_secret.json"

    if os.path.exists(client_secret_path):
        # Local dev — use the file directly
        return google_auth_oauthlib.flow.Flow.from_client_secrets_file(
            client_secret_path, scopes=OAUTH_SCOPES
        )

    # Production — load JSON from env var, no temp file needed
    secret_json = os.environ.get("GOOGLE_CLIENT_SECRET")

    if not secret_json:
        raise RuntimeError(
            "Google OAuth is not configured. "
            "Set the GOOGLE_CLIENT_SECRET environment variable "
            "to the contents of client_secret.json."
        )
    client_config = json.loads(secret_json)
    return google_auth_oauthlib.flow.Flow.from_client_config(
        client_config, scopes=OAUTH_SCOPES
    )


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
        terms = form.get("terms")

        # Check if user with username or email exist or not
        is_user: User | None = db.session.execute(
            db.select(User).filter(or_(User.username == username, User.email == email))
        ).scalar()

        if is_user:
            flash("User with already exists with this username or email", "denger")
            return redirect(url_for("users.signup"))

        if terms != "on":
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
        flash("Account created successfully!", "success")
        return redirect(url_for("users.login", email=email))
    return render_template("signup.html")


@users.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        form = request.form
        email = form.get("email")
        password = form.get("password")

        user = db.session.execute(db.select(User).filter(User.email == email)).scalar()

        if not user:
            flash("User not found", "denger")
            return redirect(url_for("users.login"))

        # match password
        is_match = encryption.verify(password, user.password)

        if is_match:
            session["id"] = user.id
            session["role"] = user.role
            session["username"] = user.username
            flash("Logged in successfully", "success")
            return redirect(url_for("index.index"))
        else:
            flash("Wrong password, try again!", "denger")
            return redirect(url_for("users.login", email=email))

    return render_template("login.html")


@users.route("/<string:username>", methods=["GET"])
def profile(username):
    tab = request.args.get("tab", default="post", type=str)

    if tab not in ["post", "comment", "saved"]:
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
    saved_stories = None
    if tab == "post":
        stories = db.session.execute(
            db.select(
                Story.id,
                Story.title,
                Story.story_uid,
                Story.desc,
                Story.date_created,
                Story.views.label("views_count"),
                User.id.label("user_id"),
                User.username.label("username"),
                User.name.label("name"),
                db.select(db.func.count(Like.id))
                .where(Like.story_id == Story.id, Like.like == 1)
                .scalar_subquery()
                .label("like_count"),
                db.select(db.func.count(Comments.id))
                .where(Comments.story_id == Story.id)
                .scalar_subquery()
                .label("comment_count"),
            )
            .join(User)
            .filter(Story.user_id == user.id)
            .limit(10)
            .order_by(Story.date_created.desc())
        ).all()
    elif tab == "comment":
        comments = db.session.execute(
            db.select(
                Comments.id,
                Comments.body,
                Comments.date_created,
                Story.title.label("story_title"),
                Story.id.label("story_id"),
                Story.story_uid.label("story_uid"),
            )
            .join(Story, Story.id == Comments.story_id)
            .filter(Comments.user_id == user.id)
            .limit(15)
            .order_by(Comments.date_created.desc())
        ).all()
    else:
        saved_stories = db.session.execute(
            db.select(
                Story.id,
                Story.title,
                Story.story_uid,
                Story.desc,
                Story.date_created,
                Story.views.label("views_count"),
                User.id.label("user_id"),
                User.username.label("username"),
                User.name.label("name"),
                db.select(db.func.count(Like.id))
                .where(Like.story_id == Story.id, Like.like == 1)
                .scalar_subquery()
                .label("like_count"),
                db.select(db.func.count(Comments.id))
                .where(Comments.story_id == Story.id)
                .scalar_subquery()
                .label("comment_count"),
            )
            .join(User)
            .join(Bookmark, Bookmark.story_id == Story.id)
            .where(Bookmark.user_id == user.id)
            .limit(10)
            .order_by(Story.date_created.desc())
        ).all()

    return render_template(
        "profile.html",
        user=_user,
        stats=stats._mapping,
        stories=stories,
        comments=comments,
        saved_stories=saved_stories,
        tab=tab,
    )


@users.route("/<string:username>/change-password", methods=["GET", "POST"])
def change_password(username):
    # Check user session
    session_user_id = session.get("id")
    if not session_user_id:
        abort(404)
    if request.method == "POST":
        form = request.form
        current_passowrd = form.get("current_password")
        new_password = form.get("new_password")
        confirm_password = form.get("confirm_password")

        user = db.session.execute(
            db.select(User).filter_by(id=session_user_id)
        ).scalar()
        is_match = encryption.verify(current_passowrd, user.password)
        if not is_match:
            flash("Current password is wrong!", "danger")
            return render_template("change_password.html")

        if new_password != confirm_password:
            flash("New password and confirm password does not match!", "danger")
            return render_template("change_password.html")

        hashed_password = encryption.hash(new_password)
        db.session.execute(
            db.update(User)
            .where(User.id == session_user_id)
            .values(password=hashed_password)
        )
        db.session.commit()
        flash("Password changed successfully!", "success")
        return redirect(url_for("users.profile", username=user.username))
    return render_template("change_password.html")


@users.route("/avatar/<int:user_id>")
def avatar(user_id):
    user = db.session.execute(db.select(User).filter_by(id=user_id)).scalar()
    image = BytesIO(user.avatar)
    return send_file(image, mimetype="image/png")


@users.route("/oauth/gogole")
def google_oauth():
    global flow
    if not flow:
        flow = _get_flow()

    flow.redirect_uri = f"{request.url_root}users/oauth/google/callback"
    authorization_url, state = flow.authorization_url(
        # Recommended, enable offline access so that you can refresh an access token without
        # re-prompting the user for permission. Recommended for web server apps.
        access_type="offline",
        # Optional, enable incremental authorization. Recommended as a best practice.
        include_granted_scopes="true",
        # Optional, set prompt to 'consent' will prompt the user for consent
        prompt="consent",
    )
    return redirect(authorization_url)


@users.route("/oauth/google/callback")
def google_oauth_callback():
    global flow
    if not flow:
        flow = _get_flow()
    flow.redirect_uri = f"{request.url_root}users/oauth/google/callback"
    state = session.get("state")

    authorization_response = request.url
    flow.fetch_token(authorization_response=authorization_response)

    # Store the credentials in browser session storage, but for security: client_id, client_secret,
    # and token_uri are instead stored only on the backend server.
    credentials = flow.credentials
    # Assuming 'credentials' is obtained from authorized flow

    service = build("oauth2", "v2", credentials=credentials)
    user_info = service.userinfo().get().execute()

    email = user_info.get("email")
    name = user_info.get("name")
    avatar = requests.get(user_info.get("picture")).content

    is_user = db.session.execute(db.select(User).filter_by(email=email)).scalar()
    user = None
    if not is_user:
        prepaired_username = name.split(" ")
        username = "".join(prepaired_username)
        while True:
            if db.session.execute(
                db.select(User.id).filter(
                    or_(
                        User.username == username,
                        User.email == email,
                    )
                )
            ).scalar():
                username = f"{username}{random.randint(1000, 9999)}"
            else:
                break

        new_user = User(
            name=name,
            email=email,
            username=username,
            avatar=avatar,
            provider="google",
        )
        db.session.add(new_user)
        db.session.commit()
        user = new_user
        flash("Account created successfully", "success")
    else:
        user = db.session.execute(db.select(User).filter_by(email=email)).scalar()
        flash("Login successfull!", "success")
    session["id"] = user.id
    session["role"] = user.role
    session["username"] = user.username

    return redirect(url_for("index.index"))


@users.route("/<string:username>/edit", methods=["GET", "POST"])
def edit_profile(username):
    session_user_id = session.get("id")
    if not session_user_id:
        abort(404)
    user = db.session.execute(
        db.select(User.id, User.name, User.username, User.bio, User.website).filter_by(
            id=session_user_id
        )
    ).first()
    if not user:
        abort(404)

    if request.method == "POST":
        form = request.form
        name = form.get("name")
        bio = form.get("bio")
        username = form.get("username")
        website = form.get("website")
        avatar = request.files.get("avatar")
        is_user = db.session.execute(
            db.select(User.id).filter_by(username=username)
        ).scalar()
        if is_user and is_user != session_user_id:
            flash("Username already taken!", "danger")
            return render_template("edit_profile.html", user=user._mapping)

        update_obj = {}
        if name != user.name:
            update_obj["name"] = name
        if username != user.username:
            update_obj["username"] = username
        if bio != user.bio:
            update_obj["bio"] = bio
        if website != user.website:
            update_obj["website"] = website
        if avatar:
            update_obj["avatar"] = avatar.stream.read()

        db.session.execute(
            db.update(User).where(User.id == session_user_id).values(**update_obj)
        )
        db.session.commit()
        flash("Updated successfully!", "success")
        return redirect(url_for("users.profile", username=username))

    return render_template("edit_profile.html", user=user._mapping)


@users.route("/delete", methods=["POST"])
def delete_account():
    session_user_id = session.get("id")
    if not session_user_id:
        abort(404)
    db.session.execute(db.delete(User).where(User.id == session_user_id))
    db.session.commit()
    session.clear()
    flash("Account deleted successfully")
    return redirect(url_for("index.index"))


@users.route("<string:username>/all-stories")
def users_all_stories(username):
    user = db.session.execute(
        db.select(
            User.id,
        ).filter_by(username=username)
    ).first()
    if not user:
        abort(404)
    stories = db.session.execute(
        db.select(
            Story.id,
            Story.title,
            Story.story_uid,
            Story.desc,
            Story.date_created,
            Story.views.label("views_count"),
            User.id.label("user_id"),
            User.username.label("username"),
            User.name.label("name"),
            db.select(db.func.count(Like.id))
            .where(Like.story_id == Story.id, Like.like == 1)
            .scalar_subquery()
            .label("like_count"),
            db.select(db.func.count(Comments.id))
            .where(Comments.story_id == Story.id)
            .scalar_subquery()
            .label("comment_count"),
        )
        .join(User)
        .filter(Story.user_id == user.id)
        .limit(10)
        .order_by(Story.date_created.desc())
    ).all()
    return render_template("user_all_stories.html", stories=stories)


@users.route("<string:username>/all-comments")
def users_all_comments(username):
    user = db.session.execute(
        db.select(
            User.id,
        ).filter_by(username=username)
    ).first()
    if not user:
        abort(404)
    comments = db.session.execute(
        db.select(
            Comments.id,
            Comments.body,
            Comments.date_created,
            Story.title.label("story_title"),
            Story.id.label("story_id"),
            Story.story_uid.label("story_uid"),
        )
        .join(Story, Story.id == Comments.story_id)
        .filter(Comments.user_id == user.id)
        .limit(15)
        .order_by(Comments.date_created.desc())
    ).all()
    return render_template("user_all_comments.html", comments=comments)


@users.route("<string:username>/all-saved-stories")
def users_all_saved_stories(username):
    user = db.session.execute(
        db.select(
            User.id,
        ).filter_by(username=username)
    ).first()
    if not user:
        abort(404)
    saved_stories = db.session.execute(
        db.select(
            Story.id,
            Story.title,
            Story.story_uid,
            Story.desc,
            Story.date_created,
            Story.views.label("views_count"),
            User.id.label("user_id"),
            User.username.label("username"),
            User.name.label("name"),
            db.select(db.func.count(Like.id))
            .where(Like.story_id == Story.id, Like.like == 1)
            .scalar_subquery()
            .label("like_count"),
            db.select(db.func.count(Comments.id))
            .where(Comments.story_id == Story.id)
            .scalar_subquery()
            .label("comment_count"),
        )
        .join(User)
        .join(Bookmark, Bookmark.story_id == Story.id)
        .where(Bookmark.user_id == user.id)
        .limit(10)
        .order_by(Story.date_created.desc())
    ).all()
    return render_template("user_all_saved_stories .html", saved_stories=saved_stories)


@users.route("/logout", methods=["POST"])
def logout():
    if session.get("id"):
        session.clear()
    return redirect(url_for("index.index"))
