import os

from flask_migrate import Migrate

from funcron.center.app import create_app, db
from funcron.center.models import CronInfos, JobLog, JobLogItems

app = create_app("production")

migrate = Migrate(app, db)

with app.app_context():
    db.create_all()


@app.shell_context_processor
def make_shell_context():
    return dict(app=app, JobLog=JobLog, CronInfos=CronInfos, JobLogItems=JobLogItems)


if __name__ == "__main__":
    # gunicorn -b 0.0.0.0:8445 -w 1 -k gevent manage:app
    # 等价于原 flask_script 的 `manager.run()`：
    #   - `python funcron_server.py` 直接启动开发服务器（等价于原 runserver 命令）
    #   - `flask --app funcron.server.funcron_server shell` 进入 shell（Flask 原生命令，
    #     通过上面的 shell_context_processor 提供与原 make_shell_context 相同的上下文）
    app.run()
