from app import app, db
from app.models import User, Task, users_tasks


@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'users_tasks': users_tasks, 'User': User, 'Task': Task, }
