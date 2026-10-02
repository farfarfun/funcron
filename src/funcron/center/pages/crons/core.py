import json
import time
import traceback
import uuid

import records
import requests
from flask import current_app
from sqlalchemy import text

from funcron.center.common import database
from funcron.center.common.config import get_config_value
from funcron.center.common.functions import single_task, wechat_info_err
from funcron.center.models import CronInfos, JobLog
from funcron.center.utils.times import get_now_time

db = database.db
scheduler = database.scheduler


@single_task()
def cron_check_db_sleep():
    with scheduler.app.app_context():
        # SQLAlchemy 2.x 要求可执行对象，裸字符串会抛 ObjectNotExecutableError。
        db.session.execute(text("select 1")).first()


"""
定时操作
"""


@single_task()
def cron_do(cron_id):
    with scheduler.app.app_context():
        try:
            nows = get_now_time()

            cif = CronInfos.query.get(cron_id)

            if not cif:
                jl = JobLog(cron_info_id=cron_id, content="定时任务不存在", create_time=nows, take_time=0)
                db.session.add(jl)
                db.session.commit()
            else:
                req_url = cif.req_url
                if not req_url:
                    jl = JobLog(cron_info_id=cron_id, content="请求链接不存在", create_time=nows, take_time=0)
                    db.session.add(jl)
                    db.session.commit()
                else:
                    if req_url.find("http") == -1:
                        jl = JobLog(
                            cron_info_id=cron_id,
                            content="请求链接有误，请检查一下",
                            create_time=nows,
                            take_time=0,
                        )
                        db.session.add(jl)
                        db.session.commit()
                    else:
                        try:
                            xiaoniu_cron_log_id = str(uuid.uuid1())

                            t = time.time()

                            req = requests.get(
                                req_url,
                                params={"xiaoniu_cron_log_id": xiaoniu_cron_log_id},
                                timeout=2 * 60,
                                headers={"user-agent": "xiaoniu_cron"},
                            )

                            ret = req.text

                            try:
                                ret = req.json()
                            except requests.exceptions.JSONDecodeError:
                                current_app.logger.debug(
                                    "cron response is not JSON; using text body (cron_id=%s, url=%s)",
                                    cron_id,
                                    req_url,
                                )

                            if isinstance(ret, dict):
                                ret = json.dumps(ret, ensure_ascii=False)

                            error_keyword = get_config_value("error_keyword")

                            if error_keyword:
                                error_keyword = error_keyword.replace("，", ",").split(",")
                                for item in error_keyword:
                                    if item.strip().lower() in ret.lower():
                                        wechat_info_err(f"定时任务【{cif.task_name}】发生错误", f"返回信息:{ret}")
                                        break

                            jl = JobLog(
                                cron_info_id=cron_id,
                                content=ret,
                                create_time=nows,
                                take_time=time.time() - t,
                                log_id=xiaoniu_cron_log_id,
                            )
                            db.session.add(jl)
                            db.session.commit()
                        except Exception as e:
                            jl = JobLog(
                                cron_info_id=cron_id,
                                content=f"发生严重错误:{e!s}",
                                create_time=nows,
                                take_time=time.time() - t,
                            )
                            db.session.add(jl)
                            db.session.commit()

                            wechat_info_err(f"定时任务【{cif.task_name}】发生严重错误", f"返回信息:{e!s}")

        except Exception as e:
            trace_info = traceback.format_exc()
            current_app.logger.error("==============")
            current_app.logger.error(str(e))
            current_app.logger.error(trace_info)
            current_app.logger.error("==============")
            wechat_info_err("定时任务发生严重错误", f"返回信息:{e!s}")

    return "ok"


@single_task()
def cron_check():
    with scheduler.app.app_context():
        try:

            def dbs():
                url = current_app.config.get("CRON_DB_URL")
                db = records.Database(url)
                db = db.get_connection()  # 新加
                return db

            job_db = dbs()
            job_arr = []
            jobs = job_db.query("select id from apscheduler_jobs").all()
            if jobs:
                for item in jobs:
                    job_arr.append(item.id)

            cifs = CronInfos.query.all()

            if cifs:
                for item in cifs:
                    if f"cron_{item.id}" not in job_arr:
                        item.status = -1
                        db.session.add(item)
                        db.session.commit()
        except Exception as e:
            trace_info = traceback.format_exc()
            current_app.logger.error("==============")
            current_app.logger.error(str(e))
            current_app.logger.error(trace_info)
            current_app.logger.error("==============")
            wechat_info_err("定时任务发生严重错误", f"返回信息:{e!s}")
    return "ok"


"""
保留一千条数据
"""


@single_task()
def cron_del_job_log():
    with scheduler.app.app_context():
        try:
            job_log_counts = get_config_value("job_log_counts") or 0
            if int(job_log_counts) != 0:
                crons = CronInfos.query.all()
                for item in crons:
                    counts = JobLog.query.filter(JobLog.cron_info_id == item.id).count()
                    if counts > int(job_log_counts):
                        # text() + 参数绑定：任务 ID 与删除条数都走绑定参数，不拼进 SQL。
                        db.session.execute(
                            text("delete from job_log where cron_info_id = :cron_id limit :row_limit"),
                            {"cron_id": item.id, "row_limit": counts - int(job_log_counts)},
                        )
                        db.session.commit()
        except Exception as e:
            trace_info = traceback.format_exc()
            current_app.logger.error("==============")
            current_app.logger.error(str(e))
            current_app.logger.error(trace_info)
            current_app.logger.error("==============")
    return "ok"
