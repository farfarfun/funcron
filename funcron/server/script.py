import argparse
import os

from funbuild.manage import BaseServer
from funcron.server.port_manage import PortManage

# sudo kill -9 `sudo lsof -t -i:5860`
# gunicorn -c gun.py manage:app
# nohup gunicorn -c gun.py manage:app  >>/fundata/logs/notecorn/server-$(date +%Y-%m-%d).log 2>&1 &


class CronServer(BaseServer):
    def __init__(self):
        path = os.path.abspath(os.path.dirname(__file__))
        super(CronServer, self).__init__("funcron_server", path)

    def init(self):
        self.manage.init()
        self.manage.add_job(
            server_name=self.server_name,
            directory=self.current_path,
            command="gunicorn -c config.py funcron_server:app",
            stdout_logfile="/fundata/logs/funcron/funcron.log",
        )
        self.manage.start()


class CronScheduler(BaseServer):
    def __init__(self):
        path = os.path.abspath(os.path.dirname(__file__))
        super(CronScheduler, self).__init__("funcron_scheduler", path)

    def init(self):
        self.manage.init()
        self.manage.add_job(
            server_name=self.server_name,
            directory=self.current_path,
            command="airflow scheduler",
            stdout_logfile="/fundata/logs/funcron/scheduler.log",
        )
        self.manage.start()


class CronWebServer(BaseServer):
    def __init__(self):
        path = os.path.abspath(os.path.dirname(__file__))
        super(CronWebServer, self).__init__("funcron_webserver", path)

    def init(self):
        self.manage.init()
        self.manage.add_job(
            server_name=self.server_name,
            directory=self.current_path,
            command="airflow webserver -p 8061",
            stdout_logfile="/fundata/logs/funcron/webserver.log",
        )
        self.manage.start()


class CronWorker(BaseServer):
    def __init__(self):
        path = os.path.abspath(os.path.dirname(__file__))
        super(CronWorker, self).__init__("funcron_worker", path)

    def init(self):
        self.manage.init()
        self.manage.add_job(
            server_name=self.server_name,
            directory=self.current_path,
            command="airflow celery worker",
            stdout_logfile="/fundata/logs/funcron/worker.log",
        )
        self.manage.start()


class CronFlower(BaseServer):
    def __init__(self):
        path = os.path.abspath(os.path.dirname(__file__))
        super(CronFlower, self).__init__("funcron_flower", path)

    def init(self):
        self.manage.init()
        self.manage.add_job(
            server_name=self.server_name,
            directory=self.current_path,
            command="airflow celery flower -p 8062",
            stdout_logfile="/fundata/logs/funcron/flower.log",
        )
        self.manage.start()


def funcron():
    parser = argparse.ArgumentParser()
    parser.add_argument("cmd", default="unknown", help="init, stop, start, restart")
    parser.add_argument("service", default="status, scheduler, worker, flower")
    values, unknown = parser.parse_known_args()
    if values.service == "server":
        CronServer().parse_and_run()
    elif values.service == "webserver":
        CronWebServer().parse_and_run()
    elif values.service == "scheduler":
        CronScheduler().parse_and_run()
    elif values.service == "worker":
        CronWorker().parse_and_run()
    elif values.service == "flower":
        CronFlower().parse_and_run()
    elif values.service == "status":
        PortManage().fprint()
    else:
        parser.print_help()
