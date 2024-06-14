from flask import request, render_template, redirect, url_for, Blueprint, flash, jsonify

from blueprints.app import db

from blueprints.stories.models import BlogPost

stories = Blueprint('stories', __name__, template_folder='templates')
# stories.secret_key = "rohit"

@stories.route('/')
def index():
    bgPost = BlogPost.query.all()
    # print(bgPost[0].pid)
    return render_template('stories/index.html', bgPost=bgPost)

@stories.route('/create', methods=['GET', 'POST'])
def create():
    if request.method == 'POST':
        title = request.json.get('title')
        body = request.json.get('body')
        desc = request.json.get('desc')
        new_post = BlogPost(title=title, body=body, desc=desc)
        print(new_post)
        db.session.add(new_post)
        db.session.commit()
        print("done")
        # return redirect(url_for('stories.index'))
        return jsonify({'redirect_url': url_for('stories.index')})
    return render_template('stories/create.html')


@stories.route('/delete/<int:pid>', methods =  ['POST', 'GET'])
def delete(pid):
    bgPost = BlogPost.query.filter_by(pid=pid).first()
    db.session.delete(bgPost)
    db.session.commit()
    # flash('post deleted')
    return redirect(url_for('stories.index'))

@stories.route('/<int:storie_id>', methods =  ['POST', 'GET'])
def readByStoryId(storie_id):
    bgPost = BlogPost.query.filter_by(pid=storie_id).first()
    return render_template('stories/stories.html', content=bgPost)

