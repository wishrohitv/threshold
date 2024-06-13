from flask import request, render_template, redirect, url_for, Blueprint

# from blueprints.app import db

core = Blueprint('core', __name__, template_folder='templates')

@core.route('/')
def index():
    # bgPost = core.query.all()
    return render_template("core/index.html")
