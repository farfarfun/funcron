from farlog import getLogger
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

from funcron.center.common import database
from funcron.center.common.config import config_dict

db: SQLAlchemy = database.db
scheduler = database.scheduler
logger = getLogger("funcron")


def create_app(config_name="production"):
    config_name = "production"
    # config_name = 'testing'
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
