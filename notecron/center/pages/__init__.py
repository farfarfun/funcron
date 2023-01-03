# import logging
# from logging.handlers import TimedRotatingFileHandler

# from flask import Flask
# from flask_apscheduler import APScheduler
# from flask_sqlalchemy import SQLAlchemy
# from notecron.center.common.scheduler import CuBackgroundScheduler
# from notecron.center.config import config_dict

# db = SQLAlchemy()


# scheduler = APScheduler(scheduler=CuBackgroundScheduler())


# formatter = logging.Formatter("[%(asctime)s][%(filename)s:%(lineno)d][%(levelname)s][%(thread)d] - %(message)s")


# def add_handler(app, config):
#     info_handler = TimedRotatingFileHandler(f"{config.LOGDIR}/info.log",
#                                             when="H",
#                                             interval=1, backupCount=7, encoding="UTF-8", delay=False,
#                                             utc=True)
#     # info_handler.setLevel(logging.INFO)
#     info_handler.filter = lambda record: record.levelno == logging.INFO
#     info_handler.setFormatter(formatter)

#     app.logger.addHandler(info_handler)

#     error_handler = TimedRotatingFileHandler(f"{config.LOGDIR}/error.log",
#                                              when="D",
#                                              interval=1, backupCount=15, encoding="UTF-8", delay=False,
#                                              utc=True)
#     error_handler.setLevel(logging.ERROR)
#     error_handler.setFormatter(formatter)

#     app.logger.addHandler(error_handler)


# def create_app(config_name='production'):
#     config_name = 'production'
#     #config_name = 'testing'
#     config = config_dict[config_name]
#     app = Flask(__name__)
#     app.config.from_object(config)
#     config.init_app(app)

#     logging.basicConfig(level=logging.ERROR)

#     add_handler(app, config)

#     scheduler.app = app
#     db.init_app(app)
#     # db.create_all()
#     scheduler.init_app(app)
#     scheduler.start()

#     from notecron.center.pages.main import main as main_blueprint
#     app.register_blueprint(main_blueprint)

#     # 接口对接
#     from notecron.center.pages.api import api as apis_bl
#     app.register_blueprint(apis_bl, url_prefix='/api')

#     return app
