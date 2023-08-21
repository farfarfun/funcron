
import pymysql
from flask_apscheduler import APScheduler
from flask_sqlalchemy import SQLAlchemy
from notecron.center.common.scheduler import CuBackgroundScheduler

pymysql.install_as_MySQLdb()
db: SQLAlchemy = SQLAlchemy()
scheduler: APScheduler = APScheduler(scheduler=CuBackgroundScheduler())
