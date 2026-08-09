import uuid
from io import BytesIO

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

from app import db
from blueprints.stories.models import Bookmark, Comments, Like, Story
from blueprints.users.models import User
from utils.generate_slug import generate_slug_from_title

stories = Blueprint("stories", __name__, template_folder="templates")


@stories.route("/<string:story_uid>", methods=["GET", "POST"])
@stories.route("/<string:slug>-<string:story_uid>", methods=["GET", "POST"])
def story(story_uid=None, slug=None):
    session_user_id = session.get("id")
    check_story = db.session.execute(
        db.select(Story).filter(Story.story_uid == story_uid)
    ).scalar()

    if not check_story:
        abort(404)

    new_slug = generate_slug_from_title(check_story.title)

    if not slug or slug != new_slug:
        return redirect(url_for("stories.story", story_uid=story_uid, slug=new_slug))
    # Update views

    check_story.views = check_story.views + 1

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

    # comments method
    if request.method == "POST":
        if not session_user_id:
            return redirect(url_for("users.login"))
        comment = request.form["comment"]
        commentsdb = Comments(story_id=story.id, user_id=session_user_id, body=comment)
        db.session.add(commentsdb)
        db.session.commit()
        return redirect(url_for("stories.story", story_uid=story_uid, slug=new_slug))
    return render_template("story.html", story=_story, comments=_comments)


@stories.route("/create", methods=["GET", "POST"])
def create():
    session_user_id = session.get("id")

    if not session_user_id:
        return redirect(url_for("users.login"))
    if request.method == "POST":
        form = request.form
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
        flash("Post created successfully", "success")
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
    if story.user_id != session_user_id:
        abort(404)
    db.session.delete(story)
    db.session.commit()
    flash("post deleted", "success")
    return redirect(url_for("index.index"))


@stories.route("/<int:story_id>/edit", methods=["GET", "POST"])
def edit(story_id):
    session_user_id = session.get("id")
    if not session_user_id:
        return redirect(url_for("users.login"), 401)
    story = db.session.execute(db.select(Story).filter_by(id=story_id)).scalar()
    if not story:
        return redirect(url_for("index.index"))
    if story.user_id != session_user_id:
        abort(404)
    db.session.delete(story)
    db.session.commit()
    flash("post deleted", "success")
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

    if not like:
        new_like = Like(user_id=session_user_id, story_id=story_id, like=1)
        db.session.add(new_like)
        db.session.commit()
        flash("Post liked", "success")
    else:
        # If dislike already exist then make to like
        if like.like == 0:
            like.like = 1
            db.session.commit()
        else:
            # Delete entire row
            db.session.delete(like)
            db.session.commit()
        flash("Like removed", "success")
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
        flash("Post disliked", "success")
    else:
        # If like already exist then make to dislike
        if like.like == 1:
            like.like = 0
            db.session.commit()
        else:
            # Delete entire row
            db.session.delete(like)
            db.session.commit()
        flash("Dislike removed", "success")
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
        flash("Post saved", "success")
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
    ).scalar()
    if bookmark:
        # Delete the row
        db.session.delete(bookmark)
        db.session.commit()
        flash("Post unsaved", "success")
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


@stories.route("/<string:story_uid>/<int:comment_id>/delete", methods=["POST"])
def delete_comment(story_uid, comment_id):
    session_user_id = session.get("id")
    if not session_user_id:
        abort(404)
    db.session.execute(
        db.delete(Comments).where(
            Comments.id == comment_id, Comments.user_id == session_user_id
        )
    )
    db.session.commit()
    flash("Comment deleted successfully", "success")
    return redirect(url_for("stories.story", story_uid=story_uid))


@stories.route("/<string:story_uid>/edit", methods=["GET", "POST"])
@stories.route("/<string:slug>-<string:story_uid>/edit", methods=["GET", "POST"])
def edit_story(story_uid, slug=None):
    session_user_id = session.get("id")
    if not session_user_id:
        return redirect(url_for("users.login"), 401)
    story = db.session.execute(
        db.select(
            Story.id, Story.title, Story.desc, Story.tags, Story.body, Story.user_id
        ).filter_by(story_uid=story_uid)
    ).first()
    if not story:
        return redirect(url_for("index.index"))
    if story.user_id != session_user_id:
        abort(404)

    if request.method == "POST":
        form = request.form
        title = form.get("title")
        body = form.get("body")
        desc = form.get("desc")
        tags = form.get("tags")

        update_obj = {}
        if story.title != title:
            update_obj["title"] = title
        if story.body != body:
            update_obj["body"] = body
        if story.desc != desc:
            update_obj["desc"] = desc
        if story.tags != tags:
            update_obj["tags"] = tags
        if "banner" in request.files:
            banner = request.files.get("banner")
            update_obj["banner"] = banner.stream.read()

        if not update_obj:
            flash("Nothing to update", "warning")
            return redirect(url_for("stories.edit_story", story_uid=story_uid))

        # update the story
        db.session.execute(
            db.update(Story).where(Story.story_uid == story_uid).values(**update_obj)
        )
        db.session.commit()
        flash("Post updated successfully", "success")
        return redirect(
            url_for(
                "stories.story",
                story_uid=story_uid,
                slug=generate_slug_from_title(title),
            )
        )
    return render_template("edit.html", story=story._mapping)
