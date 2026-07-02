from flask import request, render_template, redirect, url_for, Blueprint, session, abort
from sqlalchemy import literal
from src.app import db
from src.blueprints.stories.models import Story, Like, Comments, Bookmark
from src.blueprints.users.models import User

index_bp = Blueprint("index", __name__, template_folder="templates")


@index_bp.route("/")
def index():
    session_user_id = session.get("id")

    sort_by = request.args.get("sort_by", "latest")
    if sort_by not in ["latest", "old", "popular"]:
        abort(404)

    _filter = []
    if sort_by == "latest":
        _filter.append(Story.date_created.desc())
    if sort_by == "old":
        _filter.append(Story.date_created.asc())
    if sort_by == "popular":
        _filter.append(Story.views.desc())

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

    # is_bookmarked = db.select(
    #     literal(False)
    #     if session_user_id is None
    #     else db.exists(1).where(
    #         Bookmark.story_id == Story.id, Bookmark.user_id == session_user_id
    #     )
    # ).scalar_subquery()
    is_bookmarked = (
        db.select(1)
        .where(
            Bookmark.story_id == Story.id,
            Bookmark.user_id == session_user_id,
        )
        .correlate(Story)
        .exists()
    )

    stories = db.session.execute(
        db.select(
            Story.id,
            Story.title,
            Story.desc,
            Story.body,
            Story.story_uid,
            Story.tags,
            Story.date_created,
            User.id.label("user_id"),
            User.name.label("name"),
            User.username.label("username"),
            like_count.label("like_count"),
            dislike_count.label("dislike_count"),
            bookmark_count.label("bookmark_count"),
            comment_count.label("comment_count"),
            is_bookmarked.label("is_bookmarked"),
        )
        .join(User)
        .order_by(*_filter)
    ).all()

    _stories = [
        {
            "id": story.id,
            "title": story.title,
            "desc": story.desc,
            "body": story.body,
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
            "is_bookmarked": story.is_bookmarked,
        }
        for story in stories
    ]

    return render_template(
        "index.html", stories=_stories, sort_by=f"{sort_by[0].upper()}{sort_by[1:]}"
    )
