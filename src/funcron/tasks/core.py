from datetime import datetime
from typing import Any

from apscheduler.executors.pool import ProcessPoolExecutor, ThreadPoolExecutor
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.schedulers.blocking import BlockingScheduler
from farlog import getLogger

# from funstock.dataset.run import run_month
logger = getLogger("funcron")


def my_job(id: str = "my_job") -> None:
    """记录一次示例调度任务的执行时间。

    参数:
        id: 写入日志的任务标识，默认值为 ``"my_job"``。
    返回:
        无返回值。
    """
    logger.info("{} --> {}", id, datetime.now())  # noqa: DTZ005 - 日志里打本地时间便于对照服务器时钟


job_stores = {
    "default": MemoryJobStore(),
    # 'default': SQLAlchemyJobStore(url='sqlite:///jobs-sqlite.db')
}

executors = {"default": ThreadPoolExecutor(20), "processpool": ProcessPoolExecutor(10)}

job_defaults = {"coalesce": False, "max_instances": 3}


def my_listener(event: Any) -> None:
    """记录 APScheduler 任务事件的成功或异常状态。

    参数:
        event: APScheduler 传入的任务事件，需提供 ``exception`` 属性。
    返回:
        无返回值。
    """
    if event.exception:
        logger.error(f"任务出错了：{event.exception}")
    else:
        logger.info("任务照常运行...")


def start() -> None:
    """以前台阻塞方式启动内存任务存储的 APScheduler 示例调度器。

    参数:
        无。
    返回:
        无返回值；收到键盘中断或系统退出信号时结束。
    """
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
