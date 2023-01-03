import os

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from notedata.work import WorkApp
from notetool import read_secret

host = read_secret(cate1="notecron", cate2="database", cate3="mysql", cate4='host') or '127.0.0.1'
database = read_secret(cate1="notecron", cate2="database", cate3="mysql", cate4='database') or 'notecron'
username = read_secret(cate1="notecron", cate2="database", cate3="mysql", cate4='user') or 'notecron'
password = read_secret(cate1="notecron", cate2="database", cate3="mysql", cate4='password') or 'notecron'

db_path = f'mysql+pymysql://{username}:{password}@{host}/{database}'


app = WorkApp('notecron')
app.create()
basedir = app.dir_common  # os.path.abspath(os.path.dirname(__file__))

#redis_host = '192.168.3.122'

login_password = '123456'
logs_path = app.dir_log

cron_db_url = db_path
#cron_db_url = 'sqlite:///'+app.db_file('cron.sqlite')
#cron_db_url = 'sqlite:////root/workspace/notechats/notecron/notecron/temp/cron.sqlite'
#cron_db_url = 'sqlite:///'+os.path.abspath(os.path.dirname(__file__))+'/cron.sqlite'

cron_job_log_db_url = db_path
#cron_job_log_db_url = 'sqlite:///'+app.db_file('db.sqlite')
#cron_job_log_db_url = 'sqlite:////root/workspace/notechats/notecron/notecron/temp/db.sqlite'
#cron_job_log_db_url = 'sqlite:///'+os.path.abspath(os.path.dirname(__file__))+'/db.sqlite'


def get_config():
    data = {
        'is_single': 0,
        'redis_host': '192.168.3.122',
        'redis_pwd': '123456',
        'redis_db': 1,
        'cron_db_url': cron_db_url,
        'cron_job_log_db_url': cron_job_log_db_url,
        'redis_port': 6379,
        'login_pwd': login_password,
        'error_notice_api_key': 123456,
        'job_log_counts': 1000,
        'api_access_token': 'abcdedf',
        'error_keyword': 'fail'
    }
    return data


def get_config_value(key):
    data = {
        'is_single': 0,
        'redis_host': '192.168.3.122',
        'redis_pwd': '123456',
        'redis_db': 1,
        'cron_db_url': cron_db_url,
        'cron_job_log_db_url': cron_job_log_db_url,
        'redis_port': 6379,
        'login_pwd': login_password,
        'error_notice_api_key': 123456,
        'job_log_counts': 1000,
        'api_access_token': 'abcdedf',
        'error_keyword': 'fail'
    }
    return data[key]


class Config:
    JSON_AS_ASCII = False
    JSONIFY_PRETTYPRINT_REGULAR = False
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'hard to guess string'
    SQLALCHEMY_COMMIT_ON_TEARDOWN = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SCHEDULER_API_ENABLED = False
    CRON_DB_URL = cron_db_url
    LOGIN_PWD = login_password
    BASEDIR = basedir
    LOGDIR = logs_path

    SCHEDULER_JOBSTORES = {
        'default': SQLAlchemyJobStore(url=cron_db_url)
    }
    SCHEDULER_EXECUTORS = {
        'default': {
            'type': 'threadpool',
            'max_workers': 30
        }
    }
    # 'misfire_grace_time':30
    SCHEDULER_JOB_DEFAULTS = {
        'coalesce': False,
        'max_instances': 20,
        'misfire_grace_time': 50
    }

    JOBS = [
        {
            'id': 'cron_check',
            'func': 'notecron.center.pages.crons:cron_check',
            'args': None,
            'replace_existing': True,
            'trigger': 'cron',
            'day_of_week': "*",
            'day': '*',
            'hour': '*',
            'minute': '*/30'
        },
        {
            'id': 'cron_del_job_log',
            'func': 'notecron.center.pages.crons:cron_del_job_log',
            'args': None,
            'replace_existing': True,
            'trigger': 'cron',
            'day_of_week': "*",
            'day': '*',
            'hour': '*/8'
        },
        {
            'id': 'cron_check_db_sleep',
            'func': 'notecron.center.pages.crons:cron_check_db_sleep',
            'args': None,
            'replace_existing': True,
            'trigger': 'cron',
            'day_of_week': "*",
            'day': '*',
            'hour': '*',
            'minute': '*/10',
        }
    ]

    @staticmethod
    def init_app(app):
        if not os.path.exists(logs_path):
            os.mkdir(logs_path)


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = cron_job_log_db_url


class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = cron_job_log_db_url


config = {
    'development': DevelopmentConfig,
    'testing': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

config_dict = {
    'development': DevelopmentConfig,
    'testing': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
