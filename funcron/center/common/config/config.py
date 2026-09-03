import os

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from fundata.work import WorkApp
from funsecret import read_secret

# 数据库连接串、Redis 密码、登录口令、API 密钥等敏感信息统一通过 funsecret 下发，
# 不在代码中硬编码真实凭据；未配置时回落到仅供本地开发使用、明显不可用于生产的占位值。
host = read_secret(cate1="funcron", cate2="database", cate3="mysql", cate4="host", value="127.0.0.1")
database = read_secret(cate1="funcron", cate2="database", cate3="mysql", cate4="database", value="funcron")
username = read_secret(cate1="funcron", cate2="database", cate3="mysql", cate4="user", value="funcron")
password = read_secret(cate1="funcron", cate2="database", cate3="mysql", cate4="password", value="funcron")

db_path = f"mysql+pymysql://{username}:{password}@{host}/{database}"


app = WorkApp("funcron")
app.create()
basedir = app.dir_common  # os.path.abspath(os.path.dirname(__file__))

login_password = read_secret(cate1="funcron", cate2="web", cate3="login", cate4="password", value="123456")
logs_path = app.dir_log

cron_db_url = db_path
cron_job_log_db_url = db_path


def get_config() -> dict:
    """返回运行时配置字典（Redis 连接信息、数据库地址、登录口令、告警/接口密钥等）。

    敏感字段均经 funsecret 下发，未配置密钥库时回落到仅供本地开发使用的占位值。
    """
    return {
        "is_single": 0,
        "redis_host": read_secret(cate1="funcron", cate2="redis", cate3="host", value="127.0.0.1"),
        "redis_pwd": read_secret(cate1="funcron", cate2="redis", cate3="password", value="123456"),
        "redis_db": 1,
        "cron_db_url": cron_db_url,
        "cron_job_log_db_url": cron_job_log_db_url,
        "redis_port": 6379,
        "login_pwd": login_password,
        "error_notice_api_key": read_secret(
            cate1="funcron", cate2="notice", cate3="error_api_key", value="123456"
        ),
        "job_log_counts": 1000,
        "api_access_token": read_secret(
            cate1="funcron", cate2="api", cate3="access_token", value="abcdedf"
        ),
        "error_keyword": "fail",
    }


def get_config_value(key: str):
    """按 `key` 从 `get_config()` 返回的配置字典中取出对应的值。"""
    return get_config()[key]


class Config:
    """Flask 应用基础配置，`DevelopmentConfig`/`ProductionConfig` 在此基础上覆盖差异项。"""

    JSON_AS_ASCII = False
    JSONIFY_PRETTYPRINT_REGULAR = False
    SECRET_KEY = os.environ.get("SECRET_KEY") or "hard to guess string"
    SQLALCHEMY_COMMIT_ON_TEARDOWN = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SCHEDULER_API_ENABLED = False
    CRON_DB_URL = cron_db_url
    LOGIN_PWD = login_password
    BASEDIR = basedir
    LOGDIR = logs_path

    SCHEDULER_JOBSTORES = {"default": SQLAlchemyJobStore(url=cron_db_url)}
    SCHEDULER_EXECUTORS = {"default": {"type": "threadpool", "max_workers": 30}}
    # 'misfire_grace_time':30
    SCHEDULER_JOB_DEFAULTS = {"coalesce": False, "max_instances": 20, "misfire_grace_time": 50}

    JOBS = [
        {
            "id": "cron_check",
            "func": "funcron.center.pages.crons:cron_check",
            "args": None,
            "replace_existing": True,
            "trigger": "cron",
            "day_of_week": "*",
            "day": "*",
            "hour": "*",
            "minute": "*/30",
        },
        {
            "id": "cron_del_job_log",
            "func": "funcron.center.pages.crons:cron_del_job_log",
            "args": None,
            "replace_existing": True,
            "trigger": "cron",
            "day_of_week": "*",
            "day": "*",
            "hour": "*/8",
        },
        {
            "id": "cron_check_db_sleep",
            "func": "funcron.center.pages.crons:cron_check_db_sleep",
            "args": None,
            "replace_existing": True,
            "trigger": "cron",
            "day_of_week": "*",
            "day": "*",
            "hour": "*",
            "minute": "*/10",
        },
    ]

    @staticmethod
    def init_app(app) -> None:
        """确保日志目录存在；供 `create_app()` 在应用启动时调用。"""
        if not os.path.exists(logs_path):
            os.mkdir(logs_path)


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = cron_job_log_db_url


class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = cron_job_log_db_url


config = {
    "development": DevelopmentConfig,
    "testing": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}

config_dict = {
    "development": DevelopmentConfig,
    "testing": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
