from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login

users_tasks = db.Table(
    'users_tasks',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('task_id', db.Integer, db.ForeignKey('task.id')),
)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    login = db.Column(db.String(32), index=True, unique=True)
    email = db.Column(db.String(32), index=True, unique=True)
    first_name = db.Column(db.String(64))
    last_name = db.Column(db.String(64))
    type = db.Column(db.Integer, default=0)
    password_hash = db.Column(db.String(256))
    tasks = db.relationship(
        'Task', secondary=users_tasks, backref=db.backref('users'),
        lazy='dynamic'
    )
    assign_tasks = db.relationship(
        'Task',
        backref='author',
        lazy='dynamic',
        foreign_keys='Task.author_id'
    )

    def get_json(self):
        return {'result': True,
                'message': 'Success',
                'data': {
                    'login': self.login,
                    'email': self.email,
                    'first_name': self.first_name,
                    'last_name': self.last_name,
                    'type': self.type,
                    'assign_tasks': [task.title for task in self.assign_tasks],
                    'tasks': [task.title for task in self.tasks]
                }}

    def __repr__(self):
        return f'<User {self.login}>'

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    @staticmethod
    def create(source):
        user = User(
            login=source['login'],
            email=source['email'],
            first_name=source['first_name'],
            last_name=source['last_name'],
            type=source['type'],
        )
        user.set_password(source['password'])
        db.session.add(user)
        db.session.commit()
        return user

    @staticmethod
    def edit(user, source):
        if source.get('delete', False):
            for task in user.assign_tasks:
                db.session.delete(task)
            db.session.delete(user)
        else:
            user.login = source.get('login', user.login)
            user.email = source.get('email', user.email)
            user.first_name = source.get('first_name', user.first_name)
            user.last_name = source.get('last_name', user.last_name)
            user.type = source.get('type', user.type)
        db.session.commit()

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def tasks_quantity(self):
        to = self.tasks
        by = self.assign_tasks.all()
        return {
            'to': {
                'all': to.count(),
                'to_do': sum(i.status == 0 for i in to),
                'in_progress': sum(i.status == 1 for i in to),
                'on_review': sum(i.status == 2 for i in to),
                'done': sum(i.status == 3 for i in to),
            },
            'by': {
                'all': len(by),
                'to_do': sum(i.status == 0 for i in by),
                'in_progress': sum(i.status == 1 for i in by),
                'on_review': sum(i.status == 2 for i in by),
                'done': sum(i.status == 3 for i in by),
            },
        }


@login.user_loader
def load_user(id_):
    return User.query.get(int(id_))


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(64), index=True, unique=True)
    description = db.Column(db.Text)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    status = db.Column(db.Integer, default=0)
    started = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    finished = db.Column(db.DateTime, index=True, nullable=True)

    def __repr__(self):
        return f'<Task {self.title}>'

    def get_json(self):
        return {'result': True,
                'message': 'Success',
                'data': {
                    'title': self.title,
                    'description': self.description,
                    'author': User.query.get(self.author_id).login,
                    'status': self.status,
                    'users': [user.login for user in self.users],
                }}

    @staticmethod
    def create(source):
        author_id = source.get('author_id') or User.query.filter_by(
            login=source.get('author', '')).first().id
        task = Task(
            title=source['title'],
            description=source['description'],
            author_id=author_id,
            started=datetime.utcnow(),
        )
        for user_id in source.get('users_id', ''):
            task.users.append(User.query.get(user_id))
        for user_login in source.get('users', ''):
            task.users.append(User.query.filter_by(login=user_login).first())

        db.session.add(task)
        db.session.commit()
        return task

    @staticmethod
    def edit(task, source):
        if source.get('delete', False):
            db.session.delete(task)
        else:
            task.title = source.get('title', task.title)
            task.description = source.get('description', task.description)

            if task.status != 3 == source.get('status', 0):
                task.finished = datetime.utcnow()
            task.status = source.get('status', task.status)
            if source.get('users_id') is not None:
                users_id = {user.id for user in task.users}
                for user_id in source.get('users_id', ''):
                    if user_id not in users_id:
                        task.users.append(User.query.get(user_id))

                new_users_id = set(source.get('users_id', users_id))
                for user in task.users:
                    if user.id not in new_users_id:
                        task.users.remove(user)
            else:
                users_login = {user.login for user in task.users}
                for user_login in source.get('users', ''):
                    if user_login not in users_login:
                        task.users.append(
                            User.query.filter_by(login=user_login).first())

                new_users_login = set(source.get('users_login', users_login))
                for user in task.users:
                    if user.login not in new_users_login:
                        task.users.remove(user)
        db.session.commit()

    def edit_status(self, status):
        self.status = status
        if self.status == 3:
            self.finished = datetime.utcnow()
        db.session.commit()

    def timedelta(self):
        if self.finished and self.status == 3:
            return self.finished - self.started
        else:
            return datetime.utcnow() - self.started

    def get_text_status(self):
        if self.status == 0:
            return 'TO DO'
        elif self.status == 1:
            return 'IN PROGRESS'
        elif self.status == 2:
            return 'ON REVIEW'
        else:
            return 'DONE'

    def get_author(self):
        return User.query.get(self.author_id)

    def get_users_name(self):
        return ', '.join(map(lambda x: x.login, self.users))
