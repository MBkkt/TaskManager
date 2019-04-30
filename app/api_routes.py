from functools import wraps
from flask import request, jsonify
from app import app
from app.models import User, Task
from app.errors import bad_request


def jsonify_(func):
    @wraps(func)
    def func_new(*args, **kwargs):
        try:
            data = request.get_json() or {}
            return jsonify(func(data, *args, **kwargs))
        except Exception as e:
            return bad_request(str(e))

    return func_new


def check_fields(source, field_names):
    if any(field_name not in source for field_name in field_names):
        return {
            'result': False,
            'message': 'Few fields are not exist',
            'data': source,
        }

    elif any(not field if field != 0 else False for field in source.values()):
        return {
            'result': False,
            'message': 'Few fields are empty',
            'data': source,
        }


def check_user_exist(source):
    user = (User.query.filter_by(login=source.get('login', '')).first() or
            User.query.filter_by(email=source.get('email', '')).first())
    if user is None:
        return False, {
            'result': False,
            'message': 'Account no exist',
            'data': source,
        }

    elif not user.check_password(source.get('password', '')):
        return False, {
            'result': False,
            'message': 'Wrong password',
            'data': source,
        }
    else:
        return True, user


def check_task_exist(source):
    task = Task.query.filter_by(title=source.get('title', '')).first()
    if task is None:
        return False, {
            'result': False,
            'message': 'Task no exist',
            'data': source,
        }
    else:
        return True, task


@app.route('/api')
@jsonify_
def api(data):
    return {
        'api_function': ('get_users', 'add_users', 'edit_users',
                         'get_tasks', 'add_tasks', 'edit_tasks')
    }


@app.route('/api/add_users', methods=('POST',))
@jsonify_
def add_users(data):
    response = []
    for user_data in data:
        error_msg = check_fields(
            user_data,
            ('login', 'email', 'first_name', 'last_name', 'type', 'password')
        )
        if error_msg is not None:
            response.append(error_msg)
            continue  # Waiting for Python 3.8 and PEP 572

        is_exist, user_or_msg = check_user_exist(user_data)
        if is_exist:
            response.append({
                'result': False,
                'message': 'User exist',
                'data': user_data,

            })
            continue

        User.create(source=user_data)
        response.append({
            'result': True,
            'message': 'User successfully added',
            'data': user_data,
        })
    return response


@app.route('/api/get_users', methods=('POST',))
@jsonify_
def get_users(data):
    response = []
    for user_data in data:
        is_exist, user_or_msg = check_user_exist(user_data)
        if is_exist:
            response.append(user_or_msg.get_json())
        else:
            response.append(user_or_msg)
    return response


@app.route('/api/edit_users', methods=('POST',))
@jsonify_
def edit_users(data):
    response = []
    for user_data in data:
        is_exist, user_or_msg = check_user_exist(user_data)
        if is_exist:
            User.edit(user_or_msg, user_data)
            response.append({
                'result': is_exist,
                'message': 'User successfully edited',
                'data': user_data,
            })
        else:
            response.append(user_or_msg)
    return response


@app.route('/api/add_tasks', methods=('POST',))
@jsonify_
def add_tasks(data):
    response = []
    for task_data in data:
        error_msg = check_fields(
            task_data, ('title', 'description', 'author', 'users')
        )
        if error_msg is not None:
            response.append(error_msg)
            continue

        is_exist, task = check_task_exist(task_data)
        if is_exist:
            response.append({
                'result': False,
                'message': 'Task exist',
                'data': task_data
            })
            continue

        Task.create(source=task_data)
        response.append({
            'result': True,
            'message': 'Task successfully added',
            'data': task_data,
        })

    return response


@app.route('/api/get_tasks', methods=('POST',))
@jsonify_
def get_tasks(data):
    response = []
    for task_data in data:
        is_exist, task_or_msg = check_task_exist(task_data)
        if is_exist:
            response.append(task_or_msg.get_json())
        else:
            response.append(task_or_msg)
    return response


@app.route('/api/edit_tasks', methods=('POST',))
@jsonify_
def edit_tasks(data):
    response = []
    for task_data in data:
        is_exist, task_or_msg = check_task_exist(task_data)
        if is_exist:
            Task.edit(task_or_msg, task_data)
            response.append({
                'result': is_exist,
                'message': 'Task successfully edited',
                'data': task_data,
            })
        else:
            response.append(task_or_msg)
    return response
