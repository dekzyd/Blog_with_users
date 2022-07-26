from flask import Flask, render_template, redirect, url_for, flash, request, abort
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
from flask_gravatar import Gravatar
from sqlalchemy.exc import IntegrityError
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)

# initialize LoginManager
login_manager = LoginManager()
login_manager.init_app(app)

# CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


# Initialize gravatar
gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)


# CONFIGURE TABLES
class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    # Create Foreign Key, "users.id" the users refers to the table-name of User.
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    # Create reference to the User object, the "posts" refers to the posts property in the User class.
    author = relationship("User", back_populates="posts")
    # PARENT RELATIONSHIP
    # Create reference to the Comment object, the "parent_post" refers to the parent_post property in the Comment class.
    comments = relationship("Comment", back_populates="parent_post")


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(250), unique=True, nullable=False)
    password = db.Column(db.String(250), nullable=False)
    name = db.Column(db.String(250), nullable=False)
    # This will act like a List of BlogPost objects attached to each User.
    # The "author" refers to the author property in the BlogPost class.
    posts = relationship("BlogPost", back_populates="author")
    # This will act like a List of Comment objects attached to each User.
    # The "comment_author" refers to the comment_author property in the Comment class.
    comments = relationship("Comment", back_populates='comment_author')


class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    # Create Foreign Key, "users.id" the users refers to the table-name of User.
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    # Create Foreign Key, "blog_posts.id" the blog_posts refers to the table-name of BlogPost.
    post_id = db.Column(db.Integer, db.ForeignKey('blog_posts.id'))
    # Create reference to the User object, the "comments" refers to the comments property in the User class.
    comment_author = relationship("User", back_populates="comments")
    # CHILD RELATIONSHIP
    # Create reference to the BlogPost object, the "comments" refers to the comments property in the BlogPost class.
    parent_post = relationship("BlogPost", back_populates='comments')


# db.create_all()


# login_manager user loader
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Decorator function
def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # If id is not 1 then return abort with 403 error
        if not current_user.is_authenticated or current_user.id != 1:
            return abort(403)
        # Otherwise continue with the route function
        return f(*args, **kwargs)

    return decorated_function


# ROUTES
@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts)


@app.route('/register', methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if request.method == 'POST':
        try:
            # Hash and salt password
            raw_pswd = request.form['password']
            hashed_password = generate_password_hash(raw_pswd, salt_length=6)

            user = User(
                email=request.form['email'],
                password=hashed_password,
                name=request.form['name']
            )
            db.session.add(user)
            db.session.commit()
            flash("You've been successfully registered and logged in.", category="success")
            login_user(user)
            return redirect(url_for('get_all_posts'))
        except IntegrityError:
            flash("You've already signed up with that email. Login instead!", category='error')
            return redirect(url_for('login'))

    return render_template("register.html", form=form)


@app.route('/login', methods=["POST", "GET"])
def login():
    form = LoginForm()
    if request.method == "POST":
        # search if typed in email exists in db
        user = User.query.filter_by(email=request.form['email']).first()
        # if email exists check if typed_pswd_hash matches db_pswd_hash
        if user:
            if check_password_hash(user.password, request.form['password']):
                login_user(user)
                flash("You've been successfully logged in", category="success")
                return redirect(url_for("get_all_posts", logged_in=current_user.is_authenticated))
            else:
                flash("Password is incorrect, Try again.", category="error")
                return redirect(url_for('login'))
        else:
            flash("Email doesn't exist, Try again.", category="error")
            return redirect(url_for('login'))

    return render_template("login.html", form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods=["POST", "GET"])
def show_post(post_id):
    form = CommentForm()
    # Load comment from db associated with current post and pass them to post.html so they can be shown.
    comments = Comment.query.filter_by(post_id=post_id).all()
    if request.method == 'POST':
        if current_user.is_authenticated:
            comment = request.form['comment']
            author_id = current_user.id
            post_id_var = post_id
            # create new comment object in Comment table
            new_comment = Comment(
                text=comment,
                author_id=author_id,
                post_id=post_id_var
            )
            db.session.add(new_comment)
            db.session.commit()

            return redirect(url_for('show_post', post_id=post_id))
        else:
            flash('You need to Register or Login to comment', category='error')
            return redirect(url_for('login'))

    requested_post = BlogPost.query.get(post_id)
    return render_template("post.html", post=requested_post, form=form, comments=comments, gravatar=gravatar)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/new-post", methods=['GET', 'POST'])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)


@app.route("/edit-post/<int:post_id>", methods=['GET', 'POST'])
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form)


@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    app.run(debug=True)
