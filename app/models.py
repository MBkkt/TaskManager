from app import db, login
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

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

    def __repr__(self):
        return f'<User {self.login}>'

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    @staticmethod
    def create(form):
        user = User(
            login=form.login.data,
            email=form.email.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            type=int(form.type.data),
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        return user

    @staticmethod
    def edit(user, form):
        if form.__dict__.get('delete', False) and form.delete.data:
            for task in user.assign_tasks:
                db.session.delete(task)
            db.session.delete(user)
        else:
            user.login = form.login.data
            user.email = form.email.data
            user.first_name = form.first_name.data
            user.last_name = form.last_name.data
            user.type = form.type.data
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

    @staticmethod
    def create(form, author_id):
        task = Task(
            title=form.title.data,
            description=form.description.data,
            author_id=author_id,
            started=datetime.utcnow(),
        )
        for user_id in form.users_id.data:
            task.users.append(User.query.get(user_id))

        db.session.add(task)
        db.session.commit()
        return task

    @staticmethod
    def edit(task, form):
        if form.__dict__.get('delete', False) and form.delete.data:
            db.session.delete(task)
        else:
            task.title = form.title.data
            task.description = form.description.data

            if task.status != 3 == int(form.status.data):
                task.finished = datetime.utcnow()
            task.status = int(form.status.data)

            users_id = {user.id for user in task.users}
            for user_id in form.users_id.data:
                if user_id not in users_id:
                    task.users.append(User.query.get(user_id))

            new_users_id = set(form.users_id.data)
            for user in task.users:
                if user.id not in new_users_id:
                    task.users.remove(user)
        db.session.commit()

    def edit_status(self, form):
        self.status = int(form.status.data)
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
