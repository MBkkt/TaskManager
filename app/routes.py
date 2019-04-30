from flask import render_template, flash, redirect, url_for, request
from flask_login import login_user, logout_user, current_user, login_required
from app import app
from app.models import User, Task
from app.forms import (
    LoginForm, RegistrationForm, AddTask,
    EditTaskForPerformer, EditTaskForOwner, ProfileForm
)
from functools import wraps


def admin_required(func):
    @wraps(func)
    def func_new(*args, **kwargs):
        if current_user.type == 0:
            return redirect(url_for('index'))
        else:
            return func(*args, **kwargs)

    return func_new


@app.route('/')
@app.route('/index')
@login_required
def index():
    stat = current_user.tasks_quantity()
    return render_template('index.html', title='Main', stat=stat)


@app.route('/register', methods=('GET', 'POST'))
def register():
    if current_user.is_authenticated and current_user.type == 0:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        login_user(User.create(source={
            'login': form.login.data,
            'email': form.email.data,
            'first_name': form.first_name.data,
            'last_name': form.last_name.data,
            'type': form.type.data,
            'password': form.password.data,
        }), remember=True)
        next_page = request.args.get('next') or url_for('index')
        return redirect(next_page)
    return render_template('register.html', title='Register', form=form)


@app.route('/login', methods=('GET', 'POST'))
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(login=form.login.data).first()
        next_page = url_for('login')
        if user is None:
            flash('This login does not exist', 'danger')
        elif not user.check_password(form.password.data):
            flash('Wrong password', 'danger')
        else:
            login_user(user, remember=form.remember_me.data)
            next_page = request.args.get('next') or url_for('index')
        return redirect(next_page)
    return render_template('login.html', title='Log in', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/tasks')
@login_required
def tasks():
    temp = current_user.tasks
    tasks_len = temp.count() if temp else 0
    return render_template(
        'tasks.html', title='Tasks', current_user=current_user,
        tasks=temp, tasks_len=tasks_len
    )


@app.route('/assigned_tasks')
@login_required
@admin_required
def assigned_tasks():
    return render_template(
        'tasks.html', title='Assigned tasks', current_user=current_user,
        tasks=current_user.assign_tasks.all(),
        tasks_len=len(current_user.assign_tasks.all())
    )


def task_for_performer(task):
    form = EditTaskForPerformer(request.form)
    if request.method == 'POST' and form.validate_on_submit():
        task.edit_status(form.status.data)
        flash('Task status is edited', 'primary')
        return redirect(url_for('tasks'))
    return render_template(
        'add_task.html', title='Edit task', task=task,
        current_user=current_user,
        form=form
    )


@app.route('/profile/<int:user_id>', methods=('GET', 'POST'))
@login_required
def profile(user_id):
    user = User.query.filter_by(id=int(user_id)).first()
    form = ProfileForm()
    if form.validate_on_submit():
        User.edit(user, {
            'delete': form.delete.data,
            'login': form.login.data,
            'email': form.email.data,
            'first_name': form.first_name.data,
            'last_name': form.last_name.data,
            'type': form.type.data,
        })
        if form.delete.data:
            flash('Profile is deleted', 'primary')
        else:
            flash('Profile is edited', 'primary')
        return redirect(url_for('login'))
    elif request.method == 'GET':
        form.login.data = user.login
        form.email.data = user.email
        form.first_name.data = user.first_name
        form.last_name.data = user.last_name
        form.type.data = user.type
    return render_template(
        'profile.html', title='Profile', form=form,
        current_user=current_user
    )


def task_for_owner(task):
    form = EditTaskForOwner(request.form)
    form.users_id.choices = [
        (user.id, user.login) for user in User.query.all()
    ]
    if form.validate_on_submit():
        task.edit(task, {
            'delete': form.delete.data,
            'title': form.title.data,
            'description': form.description.data,
            'status': form.status.data,
            'users_id': form.users_id.data,
        })
        flash('Task is edited', 'primary')
        return redirect(url_for('assigned_tasks'))
    elif request.method == 'GET':
        form.title.data = task.title
        form.description.data = task.description
        form.status.data = task.status
        form.users_id.data = [user.id for user in task.users]
    else:
        flash('Task does not correct', 'error')
    return render_template(
        'add_task.html', title='Edit task', task=task,
        current_user=current_user,
        form=form
    )


@app.route('/task/<int:task_id>', methods=('GET', 'POST'))
@login_required
def task(task_id):
    task = Task.query.filter_by(id=int(task_id)).first()
    if current_user.id == task.author_id:
        return task_for_owner(task)
    else:
        return task_for_performer(task)


@app.route('/add_task', methods=('GET', 'POST'))
@login_required
@admin_required
def add_task():
    form = AddTask()
    form.users_id.choices = [
        (user.id, user.login) for user in User.query.all()
    ]
    task = {'author_id': current_user.id}
    if form.validate_on_submit():
        task = Task.create({
            'title': form.title.data,
            'description': form.description.data,
            'author_id': current_user.id,
            'users_id': form.users_id.data,
        })
        flash('Task successfully assigned', 'primary')

    return render_template(
        'add_task.html', title='Add task', form=form, task=task,
        current_user=current_user
    )
