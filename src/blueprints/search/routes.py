from flask import Blueprint, render_template, redirect, url_for, request
from src.blueprints.stories.models import Story, Like, Bookmark, Comments
from sqlalchemy import or_
from src.app import db

search_bp = Blueprint("search", __name__, template_folder="templates")


@search_bp.route("/", methods=["GET", "POST"])
def search():
    if request.method == "POST":
        query = request.form.get("query")
        result = db.session.execute(
            db.select(Story).where(
                or_(
                    Story.title.ilike(f"%{query}%"),
                    Story.desc.ilike(f"%{query}%"),
                    Story.tags.ilike(f"%{query}%"),
                )
            )
        ).all()
        print(result)
        return render_template("search.html", result=result, query=query)
    return render_template("search.html")
