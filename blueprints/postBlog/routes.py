from flask import request, render_template, redirect, url_for, Blueprint, flash

from blueprints.app import db

from blueprints.postBlog.models import BlogPost

postBlog = Blueprint('postBlog', __name__, template_folder='templates')

@postBlog.route('/')
def index():
    bgPost = BlogPost.query.all()
    # print(bgPost[0].pid)
    return render_template('postBlog/index.html', bgPost=bgPost)

@postBlog.route('/create', methods=['GET', 'POST'])
def create():
    if request.method == 'POST':
        title = request.form['title']
        body = request.form['body']
        new_post = BlogPost(title=title, body=body)
        print(new_post)
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for('postBlog.index'))
    return render_template('postBlog/create.html')

@postBlog.route('/delete/<int:pid>', methods =  ['POST', 'GET'])
def delete(pid):
    bgPost = BlogPost.query.filter_by(pid=pid).first()
    db.session.delete(bgPost)
    db.session.commit()
    flash('post deleted')
    return redirect(url_for('postBlog.index'))