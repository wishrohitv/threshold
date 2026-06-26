from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    send_file,
)
from sqlalchemy.sql.elements import or_
from passlib.hash import sha256_crypt as encryption
from io import BytesIO
from src.app import db
from .models import User

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
    user = db.session.execute(
        db.select(
            User.id,
            User.username,
            User.name,
            User.date_created,
        ).filter_by(username=username)
    ).first()
    return render_template("profile.html", user=user)


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
