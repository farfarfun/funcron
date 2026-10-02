import os
from typing import Any, ClassVar

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from fundata.work import WorkApp
from funsecret import read_secret

# 数据库连接串、Redis 密码、登录口令、API 密钥等敏感信息统一通过 funsecret 下发。
# 非敏感连接信息保留本地默认值；凭据缺失时使用空值，由使用方拒绝需要鉴权的操作。
host = read_secret(cate1="funcron", cate2="database", cate3="mysql", cate4="host", value="127.0.0.1")
database = read_secret(cate1="funcron", cate2="database", cate3="mysql", cate4="database", value="funcron")
username = read_secret(cate1="funcron", cate2="database", cate3="mysql", cate4="user", value="funcron")
password = read_secret(cate1="funcron", cate2="database", cate3="mysql", cate4="password", value="")

db_path = f"mysql+pymysql://{username}:{password}@{host}/{database}"


def _resolve_app_dir() -> str:
    """选出一个当前进程真的能写的工作目录。

    `fundata.work.WorkApp` 默认落在 `/opt/farfarfun/apps/<name>`，这需要系统级写权限；
    非 root 环境下仅仅 `import funcron.center.common.config` 就会在 `os.makedirs` 上抛
    `PermissionError`（连 CLI、测试收集都跟着挂）。这里按优先级挑一个可写目录：
    `FUNCRON_APP_DIR` → `FUNDATA_APP_DIR` → `/opt/farfarfun/apps/funcron`（可写才用）
    → `~/.funcron`。显式配了环境变量就按配置走，不再做可写性回落。
    """
    for env_name in ("FUNCRON_APP_DIR", "FUNDATA_APP_DIR"):
        configured = os.environ.get(env_name)
        if configured:
            return configured

    system_dir = "/opt/farfarfun/apps/funcron"
    probe = system_dir
    while probe != "/" and not os.path.exists(probe):
        probe = os.path.dirname(probe)
    if os.access(probe, os.W_OK):
        return system_dir

    return os.path.join(os.path.expanduser("~"), ".funcron")


app = WorkApp("funcron", dir_app=_resolve_app_dir())
app.create()
basedir = app.dir_common

login_password = read_secret(cate1="funcron", cate2="web", cate3="login", cate4="password", value="")
logs_path = app.dir_log

cron_db_url = db_path
cron_job_log_db_url = db_path


def get_config() -> dict:
    """返回运行时配置字典（Redis 连接信息、数据库地址、登录口令、告警/接口密钥等）。

    敏感字段均经 funsecret 下发，未配置时为空，不提供可直接使用的默认凭据。
    """
    return {
        "is_single": 0,
        "redis_host": read_secret(cate1="funcron", cate2="redis", cate3="host", value="127.0.0.1"),
        "redis_pwd": read_secret(cate1="funcron", cate2="redis", cate3="password", value=""),
        "redis_db": 1,
        "cron_db_url": cron_db_url,
        "cron_job_log_db_url": cron_job_log_db_url,
        "redis_port": 6379,
        "login_pwd": login_password,
        "error_notice_api_key": read_secret(cate1="funcron", cate2="notice", cate3="error_api_key", value=""),
        "job_log_counts": 1000,
        "api_access_token": read_secret(cate1="funcron", cate2="api", cate3="access_token", value=""),
        "error_keyword": "fail",
    }


def get_config_value(key: str):
    """按 `key` 从 `get_config()` 返回的配置字典中取出对应的值。"""
    return get_config()[key]


class Config:
    """Flask 应用基础配置，`DevelopmentConfig`/`ProductionConfig` 在此基础上覆盖差异项。"""

    JSON_AS_ASCII = False
    JSONIFY_PRETTYPRINT_REGULAR = False
    SECRET_KEY = read_secret(cate1="funcron", cate2="web", cate3="flask", cate4="secret_key", value="")
    SQLALCHEMY_COMMIT_ON_TEARDOWN = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SCHEDULER_API_ENABLED = False
    CRON_DB_URL = cron_db_url
    LOGIN_PWD = login_password
    BASEDIR = basedir
    LOGDIR = logs_path

    # 这几项是类级共享配置（Flask 会整体读取），显式标注 ClassVar 表明不是实例属性默认值。
    SCHEDULER_JOBSTORES: ClassVar[dict[str, Any]] = {"default": SQLAlchemyJobStore(url=cron_db_url)}
    SCHEDULER_EXECUTORS: ClassVar[dict[str, Any]] = {"default": {"type": "threadpool", "max_workers": 30}}
    SCHEDULER_JOB_DEFAULTS: ClassVar[dict[str, Any]] = {
        "coalesce": False,
        "max_instances": 20,
        "misfire_grace_time": 50,
    }

    JOBS: ClassVar[list[dict[str, Any]]] = [
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
    """开发配置：开启 Flask DEBUG，只能由调用方显式选择，不作为任何默认值。"""

    DEBUG = True
    SQLALCHEMY_DATABASE_URI = cron_job_log_db_url


class TestingConfig(Config):
    """测试配置：开启 TESTING，但**不**开启 DEBUG，避免交互式调试器暴露在测试环境。"""

    DEBUG = False
    TESTING = True
    SQLALCHEMY_DATABASE_URI = cron_job_log_db_url


class ProductionConfig(Config):
    """生产配置：关闭 DEBUG。"""

    DEBUG = False
    SQLALCHEMY_DATABASE_URI = cron_job_log_db_url


#: 配置名到配置类的映射。`default` 指向 `ProductionConfig`——代码内默认值必须是安全的
#: 非调试配置，要用 DEBUG 必须由调用方显式传入 `development`。
config_dict: dict[str, type[Config]] = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": ProductionConfig,
}

#: `config_dict` 的历史别名，保留以兼容既有导入。
config = config_dict
