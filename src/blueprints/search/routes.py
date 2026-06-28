from flask import Blueprint, render_template, redirect, url_for, request
from src.blueprints.stories.models import Story, Like, Bookmark, Comments
from src.blueprints.users.models import User
from sqlalchemy import or_
from src.app import db

search_bp = Blueprint("search", __name__, template_folder="templates")


@search_bp.route("/", methods=["GET", "POST"])
def search():
    if request.method == "POST":
        query = request.form.get("query")
        stories_result = db.session.execute(
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
            .where(
                or_(
                    Story.title.ilike(f"%{query}%"),
                    Story.desc.ilike(f"%{query}%"),
                    Story.tags.ilike(f"%{query}%"),
                )
            )
        ).all()

        _results = [
            {
                "id": story.id,
                "title": story.title,
                "story_uid": story.story_uid,
                "desc": story.desc,
                "date_created": story.date_created.strftime("%d %B, %Y"),
                "views_count": story.views_count,
                "user_id": story.user_id,
                "username": story.username,
                "name": story.name,
                "like_count": story.like_count,
                "comment_count": story.comment_count,
            }
            for story in stories_result
        ]

        return render_template("search.html", results=_results, query=query)
    return render_template("search.html")
