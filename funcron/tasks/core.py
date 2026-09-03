from datetime import datetime

from apscheduler.executors.pool import ProcessPoolExecutor, ThreadPoolExecutor
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.schedulers.blocking import BlockingScheduler
from farlog import getLogger

# from funstock.dataset.run import run_month
logger = getLogger("funcron")


def my_job(id="my_job"):
    logger.info(f"{id} --> {datetime.now()}")


job_stores = {
    "default": MemoryJobStore(),
    # 'default': SQLAlchemyJobStore(url='sqlite:///jobs-sqlite.db')
}

executors = {"default": ThreadPoolExecutor(20), "processpool": ProcessPoolExecutor(10)}

job_defaults = {"coalesce": False, "max_instances": 3}


def my_listener(event):
    if event.exception:
        logger.error(f"任务出错了：{event.exception}")
    else:
        logger.info("任务照常运行...")


def start():
    scheduler = BlockingScheduler(jobstores=job_stores, executors=executors, job_defaults=job_defaults)
    # scheduler = BackgroundScheduler(
    #    jobstores=job_stores, executors=executors, job_defaults=job_defaults)

    # scheduler.add_job(watch_product,  'interval', seconds=120, args=['44434'])
    # scheduler.add_job(watch_product,  'interval', seconds=120, args=['44435'])
    # scheduler.add_job(run_month, 'interval', seconds=120, args=[])

    try:
        scheduler.start()
        logger.info(f"scheduler state: {scheduler.state}")
    except (KeyboardInterrupt, SystemExit):
        pass
