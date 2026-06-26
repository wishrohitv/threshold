import uuid
from io import BytesIO
from flask import (
    request,
    render_template,
    redirect,
    session,
    url_for,
    Blueprint,
    flash,
    abort,
    send_file,
)
from src.utils.generate_slug import generate_slug_from_title
from src.app import db
from src.blueprints.stories.models import Story, Comments, Like, Bookmark
from src.blueprints.users.models import User

stories = Blueprint("stories", __name__, template_folder="templates")


@stories.route("/<string:story_uid>", methods=["GET", "POST"])
@stories.route("/<string:slug>-<string:story_uid>", methods=["GET", "POST"])
def story(story_uid=None, slug=None):
    session_user_id = session.get("id")
    check_story = db.session.execute(
        db.select(Story.id, Story.title, Story.views).filter_by(story_uid=story_uid)
    ).first()

    if not check_story:
        abort(404)

    new_slug = generate_slug_from_title(check_story.title)

    if not slug or slug != new_slug:
        return redirect(url_for("stories.story", story_uid=story_uid, slug=new_slug))
    # Update views

    db.session.execute(
        db.update(Story)
        .where(Story.id == check_story.id)
        .values(views=Story.views or 0 + 1)
    )
    db.session.commit()

    like_count = (
        db.select(db.func.count(Like.id))
        .where(Like.story_id == Story.id, Like.like == 1)
        .scalar_subquery()
    )
    dislike_count = (
        db.select(db.func.count(Like.id))
        .where(Like.story_id == Story.id, Like.like == 0)
        .scalar_subquery()
    )
    bookmark_count = (
        db.select(db.func.count(Bookmark.id))
        .where(Bookmark.story_id == Story.id)
        .scalar_subquery()
    )
    comment_count = (
        db.select(db.func.count(Comments.id))
        .where(Comments.story_id == Story.id)
        .scalar_subquery()
    )

    is_liked = (
        db.select(1)
        .where(
            Like.story_id == Story.id, Like.user_id == session_user_id, Like.like == 1
        )
        .correlate(Story)
        .exists()
    )
    is_disliked = (
        db.select(1)
        .where(
            Like.story_id == Story.id, Like.user_id == session_user_id, Like.like == 0
        )
        .correlate(Story)
        .exists()
    )
    is_bookmarked = (
        db.select(1)
        .where(
            Bookmark.story_id == Story.id,
            Bookmark.user_id == session_user_id,
        )
        .correlate(Story)
        .exists()
    )

    story = db.session.execute(
        db.select(
            Story.id,
            Story.title,
            Story.desc,
            Story.body,
            Story.story_uid,
            Story.views,
            Story.tags,
            Story.date_created,
            User.id.label("user_id"),
            User.name.label("name"),
            User.username.label("username"),
            like_count.label("like_count"),
            dislike_count.label("dislike_count"),
            bookmark_count.label("bookmark_count"),
            comment_count.label("comment_count"),
            is_liked.label("is_liked"),
            is_disliked.label("is_disliked"),
            is_bookmarked.label("is_bookmarked"),
        )
        .join(User)
        .where(Story.story_uid == story_uid)
    ).first()

    _story = {
        "id": story.id,
        "title": story.title,
        "desc": story.desc,
        "body": story.body,
        "views": story.views,
        "story_uid": story.story_uid,
        "tags": story.tags.split(","),  # Convert comma sepateded string into list
        "date_created": story.date_created.strftime("%d %B, %y"),
        "user_id": story.user_id,
        "name": story.name,
        "username": story.username,
        "like_count": story.like_count,
        "dislike_count": story.dislike_count,
        "bookmark_count": story.bookmark_count,
        "comment_count": story.comment_count,
        "is_liked": story.is_liked,
        "is_disliked": story.is_disliked,
        "is_bookmarked": story.is_bookmarked,
    }

    comments = db.session.execute(
        db.select(
            Comments.id,
            Comments.body,
            Comments.date_created,
            User.id.label("user_id"),
            User.name,
            User.username,
        )
        .join(User, Comments.user_id == User.id)
        .where(Comments.story_id == story.id)
    ).all()

    _comments = [
        {
            "id": comment.id,
            "body": comment.body,
            "date_created": comment.date_created.strftime("%d %B, %y"),
            "user_id": comment.user_id,
            "username": comment.username,
            "name": comment.name,
        }
        for comment in comments
    ]

    [print(comment) for comment in comments]

    # comments method
    if request.method == "POST":
        if not session_user_id:
            return redirect(url_for("users.login"))
        comment = request.form["comment"]
        commentsdb = Comments(story_id=story.id, user_id=session_user_id, body=comment)
        db.session.add(commentsdb)
        db.session.commit()
        return redirect("/")
    return render_template("stories.html", story=_story, comments=_comments)


@stories.route("/create", methods=["GET", "POST"])
def create():
    session_user_id = session.get("id")

    if not session_user_id:
        return redirect(url_for("users.login"))
    if request.method == "POST":
        form = request.form
        print(form)
        title = form["title"]
        body = form["body"]
        desc = form["desc"]
        tags = form["tags"]
        banner = request.files.get("banner")
        # create unique string id
        story_uid = str(uuid.uuid4())[24:]
        while True:
            existing_story = db.session.execute(
                db.select(Story).filter_by(story_uid=story_uid)
            ).scalar()
            if existing_story:
                story_uid += str(1)
            else:
                break

        new_post = Story(
            user_id=session["id"],
            title=title,
            body=body,
            desc=desc,
            tags=tags,
            banner=banner.stream.read(),
            story_uid=story_uid,
        )

        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("stories.story", story_uid=story_uid))
    return render_template("create.html")


@stories.route("/<int:story_id>/delete", methods=["POST"])
def delete(story_id):
    session_user_id = session.get("id")
    if not session_user_id:
        return redirect(url_for("users.login"), 401)
    story = db.session.execute(db.select(Story).filter_by(id=story_id)).scalar()
    if not story:
        return redirect(url_for("index.index"))

    db.session.delete(story)
    db.session.commit()
    flash("post deleted")
    return redirect(url_for("index.index"))


@stories.route("/<int:story_id>/like", methods=["POST"])
def like(story_id):
    session_user_id = session.get("id")
    if not session_user_id:
        return redirect(url_for("users.login"), 401)
    story = db.session.execute(db.select(Story).filter_by(id=story_id)).scalar()
    if not story:
        return redirect(url_for("index.index"))
    like = db.session.execute(
        db.select(Like).filter_by(
            story_id=story_id,
            user_id=session_user_id,
        )
    ).scalar()
    print(like, "like tesing")
    if not like:
        new_like = Like(user_id=session_user_id, story_id=story_id, like=1)
        db.session.add(new_like)
        db.session.commit()
        flash("Post liked")
    else:
        # If dislike already exist then make to like
        if like.like == 0:
            like.like = 1
            db.session.commit()
        else:
            # Delete entire row
            db.session.delete(like)
            db.session.commit()
        flash("Like removed")
    return redirect(
        url_for(
            "stories.story",
            story_uid=story.story_uid,
            slug=generate_slug_from_title(story.title),
        )
    )


@stories.route("/<int:story_id>/dislike", methods=["POST"])
def dislike(story_id):
    session_user_id = session.get("id")
    if not session_user_id:
        return redirect(url_for("users.login"), 401)

    story = db.session.execute(db.select(Story).filter_by(id=story_id)).scalar()
    if not story:
        return redirect(url_for("index.index"))
    like = db.session.execute(
        db.select(Like).filter_by(
            story_id=story_id,
            user_id=session_user_id,
        )
    ).scalar()
    if not like:
        new_like = Like(user_id=session_user_id, story_id=story_id, like=0)
        db.session.add(new_like)
        db.session.commit()
        flash("Post disliked")
    else:
        # If like already exist then make to dislike
        if like.like == 1:
            like.like = 0
            db.session.commit()
        else:
            # Delete entire row
            db.session.delete(like)
            db.session.commit()
        flash("Dislike removed")
    return redirect(
        url_for(
            "stories.story",
            story_uid=story.story_uid,
            slug=generate_slug_from_title(story.title),
        )
    )


@stories.route("/<int:story_id>/bookmark", methods=["POST"])
def bookmark(story_id):
    session_user_id = session.get("id")
    if not session_user_id:
        return redirect(url_for("users.login"), 401)
    story = db.session.execute(db.select(Story).filter_by(id=story_id)).scalar()
    if not story:
        return redirect(url_for("index.index"))
    bookmark = db.session.execute(
        db.select(Bookmark).filter_by(
            story_id=story_id,
            user_id=session_user_id,
        )
    ).first()
    if not bookmark:
        new_bookmark = Bookmark(user_id=session_user_id, story_id=story_id)
        db.session.add(new_bookmark)
        db.session.commit()
        flash("Post Bookmarked")
    return redirect(
        url_for(
            "stories.story",
            story_uid=story.story_uid,
            slug=generate_slug_from_title(story.title),
        )
    )


@stories.route("/<int:story_id>/remove-bookmark", methods=["POST"])
def remove_bookmark(story_id):
    session_user_id = session.get("id")
    if not session_user_id:
        return redirect(url_for("users.login"), 401)
    story = db.session.execute(db.select(Story).filter_by(id=story_id)).scalar()
    if not story:
        return redirect(url_for("index.index"))
    bookmark = db.session.execute(
        db.select(Bookmark).filter_by(
            story_id=story_id,
            user_id=session_user_id,
        )
    ).first()
    if bookmark:
        db.delete(bookmark)
        db.session.commit()
        flash("Bookmark removed")
    return redirect(
        url_for(
            "stories.story",
            story_uid=story.story_uid,
            slug=generate_slug_from_title(story.title),
        )
    )


@stories.route("/banner/<int:story_id>")
def banner(story_id):
    banner_data = db.session.execute(
        db.select(Story.banner).filter_by(id=story_id)
    ).scalar()

    banner = BytesIO(banner_data)

    return send_file(banner, mimetype="image/png")
