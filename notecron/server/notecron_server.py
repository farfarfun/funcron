
import os

from flask_migrate import Migrate
from flask_script import Manager, Shell

from notecron.center.app import create_app, db
from notecron.center.models import CronInfos, JobLog, JobLogItems

app = create_app('production')

manager = Manager(app)

migrate = Migrate(app, db)

with app.app_context():
    db.create_all()


def make_shell_context():
    return dict(
        app=app,
        JobLog=JobLog,
        CronInfos=CronInfos,
        JobLogItems=JobLogItems
    )


manager.add_command("shell", Shell(make_context=make_shell_context))

if __name__ == '__main__':
    # gunicorn -b 0.0.0.0:8445 -w 1 -k gevent manage:app
    manager.run()
