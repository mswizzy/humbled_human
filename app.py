import os
from dotenv import load_dotenv
import pymongo
import datetime
from bson.objectid import ObjectId
from flask import Flask, request, render_template, redirect, url_for, session, flash
from flask_login import LoginManager, UserMixin, current_user, login_user, logout_user, login_required
import bcrypt
from functools import wraps
import getpass
from werkzeug.urls import url_parse

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

## necessary for python-dotenv ##
BASEDIR = os.path.abspath(os.path.dirname(__file__))
dotenv_path = os.path.join(BASEDIR, '.env')
#APP_ROOT = os.path.join(os.path.dirname(__file__), '..')   # refers to application_top
#dotenv_path = os.path.join(APP_ROOT, '.env')
load_dotenv(dotenv_path)

mongo = os.getenv('MONGO')

#client=pymongo.MongoClient("mongodb+srv://humbled:I71VYTOXl7kKCAjD@cluster0.ovp7x.mongodb.net/humbled?retryWrites=true&w=majority")

client = pymongo.MongoClient(os.getenv('MONGO'))

db = client['humbled'] # Mongo collection
users = db['users'] # Mongo document/table
roles = db['roles'] # Mongo document/table
causes = db['causes'] # Mongo document/table
posts = db['posts'] # Mongo document/table

login = LoginManager()
login.init_app(app)
login.login_view = 'login'

@login.user_loader
def load_user(email):
    u = users.find_one({"email": email})
    if not u:
        return None
    return User(email=u['email'], role=u['role'], id=u['_id'], username=u['username'])

class User: ##user class for login purposes
    def __init__(self, id, role, email, username):
        self._id = id
        self.email = email
        self.username = username
        self.role = role
        #self.email = email

    @staticmethod
    def is_authenticated():
        return True

    @staticmethod
    def is_active():
        return True

    @staticmethod
    def is_anonymous():
        return False

    def get_id(self):
        return self.email


##password hashing below
'''
    @staticmethod
    def check_password(password_hash, password):
        return check_password_hash(password_hash, password)
'''

### custom wrap to determine role access  ### 
def roles_required(*role_names):
    def decorator(original_route):
        @wraps(original_route)
        def decorated_route(*args, **kwargs):
            if not current_user.is_authenticated:
                print('The user is not authenticated.')
                return redirect(url_for('login'))
            
            print(current_user.role)
            print(role_names)
            if not current_user.role in role_names:
                print('The user does not have this role.')
                return redirect(url_for('login'))
            else:
                print('The user is in this role.')
                return original_route(*args, **kwargs)
        return decorated_route
    return decorator


@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html')

@app.route('/about', methods=['GET', 'POST'])
def about():
    return render_template('about.html')


@app.route('/register/add-user', methods=['GET', 'POST'])
def add_user():
    if request.method == 'POST':
        form = request.form
        
        password = request.form['password']
        
        email = users.find_one({"email": request.form['email']})
        if email:
            flash('This email is already registered.', 'warning')
            return 'This email has already been registered.'
        new_user = {
            'username': form['username'],
            'first_name': form['first_name'],
            'last_name': form['last_name'],
            'email': form['email'],
            'password': password,
            'organization': form['organization'],
            'dob': form['dob'],
            'role': form['role'],
            'date_added': datetime.datetime.now(),
            'date_modified': datetime.datetime.now()
        }
        users.insert_one(new_user)
        flash(new_user['email'] + ' user has been added.', 'success')
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        print('user is authenticated')
        return redirect(url_for('index'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        print('user is already logged in')
        return redirect(url_for('index'))

    if request.method == 'POST':
        user = users.find_one({"email": request.form['email']})
        #print(user['email'])
        if user and user['password'] == request.form['password']:
            user_obj = User(email=user['email'], role=user['role'], id=user['_id'], username=user['username'])
            login_user(user_obj)
            print('logged in')
            next_page = request.args.get('next')

            if not next_page or url_parse(next_page).netloc != '':
                next_page = url_for('index')
                return redirect(next_page)
            flash("Logged in successfully!", category='success')
            return redirect(request.args.get("next") or url_for("index"))

        flash("Wrong username or password!", category='error')
    return render_template('login.html')


@app.route('/logout', methods=['GET', 'POST'])
def logout():
    logout_user()
    flash('You have successfully logged out.', 'success')
    return redirect(url_for('login'))


@app.route('/admin', methods=['GET', 'POST'])
@login_required
@roles_required('admin')
def admin():
    return render_template('admin.html')


@app.route('/my-account/<user_id>', methods=['GET', 'POST'])
@login_required
@roles_required('user', 'contributor', 'admin') ##all accounts can see this
def my_account(user_id):
    edit_account = users.find_one({'_id': ObjectId(user_id)})
    if edit_account:
        return render_template('my-account.html', user=edit_account)
    flash('User not found.', 'warning')
    return redirect(url_for('index'))

@app.route('/update-myaccount/<user_id>', methods=['GET', 'POST'])
@login_required
@roles_required('user', 'contributor', 'admin')
def update_myaccount(user_id):
    if request.method == 'POST':
        form = request.form

        password = request.form['password']

        users.update({'_id': ObjectId(user_id)},
            {
            'username': form['username'],
            'first_name': form['first_name'],
            'last_name': form['last_name'],
            'email': form['email'],
            'password': password,
            'organization': form['organization'],
            'dob': form['dob'],
            'role': form['role'],
            'date_added': form['date_added'],
            'date_modified': datetime.datetime.now()
            })
        update_account = users.find_one({'_id': ObjectId(user_id)})
        flash(update_account['email'] + ' has been modified.', 'success')
        return redirect(url_for('index'))
    return redirect(url_for('index'))


##########  Admin functionality -- User management ##########

@app.route('/admin/users', methods=['GET', 'POST'])
@login_required
@roles_required('admin')
def admin_users():
    return render_template('users.html', all_roles=roles.find(), all_users=users.find())

@app.route('/admin/add-user', methods=['GET', 'POST'])
@login_required
@roles_required('admin')
def admin_add_user():
    if request.method == 'POST':
        form = request.form
        
        password = request.form['password']
        
        email = users.find_one({"email": request.form['email']})
        if email:
            flash('This email is already registered.', 'warning')
            return 'This email has already been registered.'
        new_user = {
            'username': form['username'],
            'first_name': form['first_name'],
            'last_name': form['last_name'],
            'email': form['email'],
            'password': password,
            'organization': form['organization'],
            'dob': form['dob'],
            'role': form['role'],
            'date_added': datetime.datetime.now(),
            'date_modified': datetime.datetime.now()
        }
        users.insert_one(new_user)
        flash(new_user['email'] + ' user has been added.', 'success')
        return redirect(url_for('admin_users'))
    return render_template('users.html', all_roles=roles.find(), all_users=users.find())

@app.route('/admin/delete-user/<user_id>', methods=['GET', 'POST'])
@login_required
@roles_required('admin')
def admin_delete_user(user_id):
    delete_user = users.find_one({'_id': ObjectId(user_id)})
    if delete_user:
        users.delete_one(delete_user)
        flash(delete_user['email'] + ' has been deleted.', 'warning')
        return redirect(url_for('admin_users'))
    flash('User not found.', 'warning')
    return redirect(url_for('admin_users'))

@app.route('/admin/edit-user/<user_id>', methods=['GET', 'POST'])
@login_required
@roles_required('admin')
def admin_edit_user(user_id):
    edit_user = users.find_one({'_id': ObjectId(user_id)})
    if edit_user:
        return render_template('edit-user.html', user=edit_user, all_roles=roles.find())
    flash('User not found.', 'warning')
    return redirect(url_for('admin_users'))

@app.route('/admin/update-user/<user_id>', methods=['GET', 'POST'])
@login_required
@roles_required('admin')
def admin_update_user(user_id):
    if request.method == 'POST':
        form = request.form

        password = request.form['password']

        users.update({'_id': ObjectId(user_id)},
            {
            'username': form['username'],
            'first_name': form['first_name'],
            'last_name': form['last_name'],
            'email': form['email'],
            'password': password,
            'organization': form['organization'],
            'dob': form['dob'],
            'role': form['role'],
            'date_added': form['date_added'],
            'date_modified': datetime.datetime.now()
            })
        update_user = users.find_one({'_id': ObjectId(user_id)})
        flash(update_user['email'] + ' has been added.', 'success')
        return redirect(url_for('admin_users'))
    return render_template('users.html', all_roles=roles.find(), all_users=users.find())

@app.route('/admin/delete-post/<user_id>', methods=['GET', 'POST'])
@login_required
@roles_required('admin')
def admin_delete_post(post_id):
    delete_post = posts.find_one({'_id': ObjectId(post_id)})
    if delete_post:
        posts.delete_post(delete_post)
        flash(delete_post['title'] + ' has been deleted.', 'warning')
        return redirect(url_for('admin_users'))
    flash('Post not found.', 'warning')
    return redirect(url_for('admin_users'))



##########  Posts ##########
@app.route('/discover/view-post/<post_id>', methods=['GET', 'POST'])
def view_post(post_id):
    view_post = posts.find_one({'_id': ObjectId(post_id)})
    if view_post:
        return render_template('view_post.html', post=view_post)
    flash('Post not found.', 'danger')
    return redirect(url_for('discover'))

@app.route('/posts', methods=['GET', 'POST'])
def view_posts():
    return render_template('discover.html', all_posts=posts.find())

#@app.route('/share', methods=['GET', 'POST'])
#@login_required
#@roles_required('admin', 'contributor')
#def share():
#    return render_template('share.html')

@app.route('/posts/new-post', methods=['GET','POST'])
@login_required
@roles_required('admin', 'contributor')
def new_post():
    return render_template('share.html', all_causes=causes.find())


@app.route('/posts/add-post', methods=['GET', 'POST'])
@login_required
@roles_required('admin', 'contributor')
def add_post():
    if request.method == 'POST':
        form = request.form
        post = posts.find_one({'title': request.form['title']})
        if post:
            flash('This post has already been submitted.', 'warning')
            return 'This post has already been submitted'
        new_post = {
            "title": form["title"],
            "organization": form["organization"],
            "cause": form["cause"],
            "link": form["link"],
            "description": form["description"],
            "username": form["username"],
            "date_added": datetime.datetime.now(),
            "date_modified": datetime.datetime.now()
        }
        posts.insert_one(new_post)
        #print('post inserted')
        flash(new_post['title'] + ' post has been added.', 'success')
        return render_template('view_post.html', post=new_post)

    return render_template('share.html', all_causes=causes.find())

@app.route('/post/edit-post/<post_id>', methods=['GET', 'POST'])
@login_required
@roles_required('admin', 'contributor')
def edit_post(post_id):
    edit_post = posts.find_one({'_id': ObjectId(post_id)})
    if edit_post:
        return render_template('edit-post.html', post=edit_post, all_causes=causes.find())
    flash('Post not found.', 'danger')
    return redirect(url_for('view_posts'))

@app.route('/post/update-post/<post_id>', methods=['POST'])
@login_required
@roles_required('admin', 'contributor')
def update_post(post_id):
    if request.method == 'POST':
        form = request.form
        posts.update({'_id': ObjectId(post_id)},
        {
            "title": form["title"],
            "organization": form["organization"],
            "cause": form["cause"],
            "link": form["link"],
            "description": form["description"],
            "username": form["username"],
            "date_added": form['date_added'],
            "date_modified": datetime.datetime.now()
        })
        update_post = posts.find_one({'_id': ObjectId(post_id)})
        flash(update_post['title'] + ' has been updated.', 'success')
        return render_template('view_post.html', post=update_post)
    return render_template('edit-post.html', all_causes=causes.find())

@app.route('/post/delete-post/<post_id>', methods=['GET', 'POST'])
@login_required
@roles_required('admin')
def delete_post(post_id):
    delete_post = posts.find_one({'_id': ObjectId(post_id)})
    if delete_post:
        posts.delete_one(delete_post)
        flash(delete_post['title'] + ' has been delete.', 'danger')
        return redirect(url_for('view_posts'))
    flash('Recipe not found.', 'warning')
    return redirect(url_for('view_recipes'))



    

if __name__ == "__main__":
    app.run(debug=True)
