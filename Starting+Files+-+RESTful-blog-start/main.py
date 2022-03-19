import os
from functools import wraps
from flask import Flask, abort, render_template, redirect, url_for, request, flash
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
import psycopg2
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, URL
from flask_ckeditor import CKEditor, CKEditorField
from form import RegisterForm, LoginForm, CommentForm
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from flask_gravatar import Gravatar
import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
ckeditor = CKEditor(app)
Bootstrap(app)
gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)

##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL").replace('postgres://', 'postgresql://') or 'sqlite:///posts.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)


##CONFIGURE TABLE
class BlogPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    img_url = db.Column(db.String(250), nullable=False)


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(100))
    posts = db.relationship("BlogPost")
    comments = db.relationship("Comment")


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("blog_post.id"), nullable=False)
    body = db.Column(db.Text, nullable=False)
    date = db.Column(db.String(250), nullable=False)
    author_id = db.Column(db.String(250), db.ForeignKey('users.id'), nullable=False)


db.create_all()


##WTForm
class CreatePostForm(FlaskForm):
    title = StringField("Blog Post Title", validators=[DataRequired()])
    subtitle = StringField("Subtitle", validators=[DataRequired()])
    # author = StringField("Your Name", validators=[DataRequired()])
    img_url = StringField("Blog Image URL", validators=[DataRequired(), URL()])
    body = CKEditorField("Blog Content", validators=[DataRequired()])
    submit = SubmitField("Submit Post")


##LOGIN FUNCTION
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login', next=request.url))
        if current_user.id != 1:
            abort(403, description="You are not authorized for this function.")
        return f(*args, **kwargs)

    return decorated_function


##RENDER HOME PAGE USING DB
@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    posts = db.session.query(User, BlogPost).filter(User.id == BlogPost.author_id).all()
    print(posts)
    return render_template("index.html", all_posts=posts)


##RENDER POST USING DB
@app.route("/post/<int:post_id>", methods=["GET", "POST"])
def show_post(post_id):
    requested_post = BlogPost.query.get(post_id)
    author_joined = db.session.query(User).filter(User.id == requested_post.id).first()
    comments = db.session.query(Comment).join(BlogPost, Comment.post_id == BlogPost.id).all()
    comments = db.session.query(Comment,
                                User,
                                BlogPost).filter(User.id == Comment.author_id).filter(Comment.post_id == BlogPost.id).all()
    form = CommentForm()
    if form.validate_on_submit():
        if not current_user.is_authenticated:
            flash("You have to log in to leave a comment")
            return redirect(url_for('login'))
        new_data = Comment(post_id=post_id,
                           body=request.form["comment"],
                           date=datetime.datetime.now().strftime("%B %d, %Y"),
                           author_id=current_user.id)

        db.session.add(new_data)
        db.session.commit()
        return redirect(url_for('show_post', post_id=post_id))

    return render_template("post.html", post=requested_post, author=author_joined, form=form, comments=comments)


##RENDER POST USING DB
@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@admin_required
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    form = CreatePostForm(
        title=post.title,
        subtitle=post.title,
        img_url=post.img_url,
        author_id=current_user.id,
        body=post.body
    )
    if form.validate_on_submit():
        target_post = db.session.query(BlogPost).get(post_id)
        target_post.title = request.form["title"]
        target_post.subtitle = request.form["subtitle"]
        target_post.img_url = request.form["img_url"]
        target_post.author = request.form["author"]
        target_post.body = request.form["body"]
        db.session.commit()
        return redirect(url_for('show_post', post_id=post_id))

    return render_template("make-post.html", post=post, context="edit", form=form)


@app.route("/new-post", methods=["POST", "GET"])
@login_required
def make_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            body=request.form["body"],
            title=request.form["title"],
            subtitle=request.form["subtitle"],
            author_id=current_user.id,
            img_url=request.form["img_url"],
            date=datetime.datetime.now().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for('get_all_posts'))

    return render_template("make-post.html", context="make", form=form)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/delete/<int:post_id>", methods=["DELETE", "GET"])
@admin_required
def delete_post(post_id):
    target_post = db.session.query(BlogPost).get(post_id)
    db.session.delete(target_post)
    db.session.commit()

    return redirect(url_for('get_all_posts'))


@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        if db.session.query(User).filter_by(email=request.form["email"]).first() is not None:
            print(db.session.query(User).filter_by(email=request.form["email"]).first)
            flash("There is already a user with the same email address.")
            return redirect(url_for('login'))
        else:
            new_user = User(
                name=request.form["name"],
                email=request.form["email"],
                password=generate_password_hash(request.form["password"], method='pbkdf2:sha256',
                                                salt_length=8)
            )

            db.session.add(new_user)
            db.session.commit()

            return redirect(url_for('get_all_posts'))

    return render_template("register.html", form=form)


@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = request.form["email"]
        password = request.form["password"]
        user = db.session.query(User).filter_by(email=email).first()
        if user is None:
            flash("Your Id does not exist. Please check your ID")
            return render_template("login.html", form=form)
        elif check_password_hash(pwhash=user.password, password=password):
            login_user(user)
            return redirect(url_for('get_all_posts'))

        else:
            flash("Please check your login information again. Invalid User ID or PW.")
            return render_template("login.html", form=form)

    return render_template("login.html", form=form)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
