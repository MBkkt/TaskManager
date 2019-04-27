from datetime import datetime
from flask import render_template, flash, redirect, url_for, request
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.urls import url_parse
from app import app, db
from app.forms import LoginForm, RegistrationForm, AddTask
from app.models import User, Task


@app.route('/')
@app.route('/index')
@login_required
def index():
    stat = current_user.tasks_quantity()
    return render_template('index.html', title='Main', stat=stat)


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm(request.form)
    if request.method == 'POST' and form.validate_on_submit():
        login_user(User.create(form=form), remember=True)
        next_page = request.args.get('next') or url_for('index')
        return redirect(next_page)
    return render_template('register.html', title='Register', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm(request.form)
    if request.method == 'POST' and form.validate_on_submit():
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
    return render_template(
        'tasks_for_user.html', title='Tasks', tasks=current_user.tasks
    )


@app.route('/assigned_tasks')
def assigned_tasks():
    tasks_list = current_user.assign_tasks.all()
    return render_template(
        'tasks_for_admins.html', title='Assigned tasks', tasks=tasks_list,
        current_user=current_user
    )


@app.route('/task/<int:task_id>', methods=['GET', 'POST'])
@login_required
def task(task_id):
    task = Task.query.filter_by(id=int(task_id)).first()
    form = AddTask(request.form)
    if current_user.type == 0:
        form.status.choices = [('1', 'IN PROGRESS'), ('2', 'ON REVIEW')]
        form.title.data = task.title
        form.description.data = task.description
        if request.method == 'POST' and form.is_submitted():
            task.edit_status(form)
            flash('Task status is edited', 'primary')
            return redirect(url_for('tasks'))

    elif current_user.type == 1:
        form.status.choices = [('0', 'TO DO'), ('1', 'IN PROGRESS'),
                               ('2', 'ON REVIEW'), ('3', 'DONE')]
        form.users_id.choices = [
            (user.id, user.login) for user in User.query.all()
        ]
        if request.method == 'POST' and form.validate_on_submit():
            task.edit(form)
            flash('Task is edited', 'primary')
            return redirect(url_for('assigned_tasks'))
        elif request.method == 'GET':
            form.title.data = task.title
            form.description.data = task.description
            form.status.data = task.status
    return render_template(
        'add_task.html', title='Task', task=task,
        current_user=current_user,
        form=form
    )


@app.route('/add_task', methods=['GET', 'POST'])
@login_required
def add_task():
    if current_user.type == 0:
        return redirect(url_for('index'))
    form = AddTask(request.form)
    form.users_id.choices = [
        (user.id, user.login) for user in User.query.all()
    ]

    if request.method == 'POST' and form.validate_on_submit():
        Task.create(form, current_user.id)
        flash('Task is assigned', 'primary')
    return render_template(
        'add_task.html', title='Assign task', form=form
    )
