from farlog import getLogger
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

from funcron.center.common import database
from funcron.center.common.config import config_dict

db: SQLAlchemy = database.db
scheduler = database.scheduler
logger = getLogger("funcron")


def create_app(config_name: str = "production") -> Flask:
    """创建并初始化 Flask 应用。

    参数:
        config_name: 配置名，取值见 `funcron.center.common.config.config_dict`
            （`development` / `testing` / `production` / `default`）。默认 `production`
            （不开 DEBUG）。调用方传入的值会被尊重，不再被无条件改写；未知名字直接抛
            `KeyError`，不做静默回落，避免用错配置却毫无察觉。
    返回:
        已加载配置、初始化数据库与调度器并注册蓝图的 `Flask` 实例。
    """
    if config_name not in config_dict:
        raise KeyError(f"未知的配置名 {config_name!r}，可选值: {sorted(config_dict)}")
    config = config_dict[config_name]
    app = Flask(__name__)
    app.config.from_object(config)
    config.init_app(app)

    scheduler.app = app
    db.init_app(app)
    # db.create_all()
    scheduler.init_app(app)
    scheduler.start()

    from funcron.center.pages.main import main as main_blueprint

    app.register_blueprint(main_blueprint)

    # 接口对接
    from funcron.center.pages.api import api as apis_bl

    app.register_blueprint(apis_bl, url_prefix="/api")

    return app
