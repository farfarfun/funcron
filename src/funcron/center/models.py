"""管理后台的 SQLAlchemy 数据模型：定时任务定义与任务执行日志。"""

from sqlalchemy import Column

from funcron.center.app import db


class CronInfos(db.Model):
    """定时任务定义表（`cron_infos`）。

    每行描述一个定时任务：任务名、cron 各时间字段、要回调的 URL 以及运行状态。
    """

    __tablename__ = "cron_infos"
    id: Column = db.Column(db.Integer, primary_key=True)
    task_name: Column = db.Column(db.String(64), nullable=False)
    task_keyword: Column = db.Column(db.String(65), nullable=False, default="")
    run_date: Column = db.Column(db.String(25), default="", doc="执行时间")
    day_of_week: Column = db.Column(db.String(10), default="", doc="星期几")
    day: Column = db.Column(db.String(20), default="", doc="号(日)")
    hour: Column = db.Column(db.String(10), default="", doc="小时")
    minute: Column = db.Column(db.String(10), default="", doc="分钟")
    second: Column = db.Column(db.String(10), default="", doc="秒")
    req_url: Column = db.Column(db.String(128), default="")
    status: Column = db.Column(db.SMALLINT, default=True, doc="运行状态，0停止1运行中-1结束任务")

    @staticmethod
    def cron_list(page=1, task_name=None, page_size=20):
        """按任务名模糊查询定时任务，并按任务名倒序分页。

        参数:
            page: 页码，从 1 开始；传入 None/0/空串时按第 1 页处理。
            task_name: 任务名关键字，为空则不过滤。
            page_size: 每页条数，默认 20。
        返回:
            Flask-SQLAlchemy 的 `Pagination` 对象，`.items` 是本页的 `CronInfos` 列表。
        """
        page = int(page or 1)
        filter_arr = []
        if task_name:
            filter_arr.append(CronInfos.task_name.like(f"%{task_name}%"))
        return (
            CronInfos.query.filter(*filter_arr)
            .order_by(db.desc(CronInfos.task_name))
            .paginate(page=page, per_page=page_size)
        )


class JobLogItems(db.Model):
    """任务执行日志的明细行（`job_log_items`）。

    一次执行（`JobLog.log_id`）可以追加多条明细内容，用 `log_id` 关联。
    """

    __tablename__ = "job_log_items"
    id: Column = db.Column(db.Integer, primary_key=True)
    log_id: Column = db.Column(db.String(65), index=True, nullable=False)
    content: Column = db.Column(db.TEXT, nullable=False, default="")


class JobLog(db.Model):
    """任务执行日志主表（`job_log`），一行对应一次任务执行。"""

    __tablename__ = "job_log"
    id: Column = db.Column(db.Integer, primary_key=True)
    log_id: Column = db.Column(
        db.String(65), nullable=False, index=True, server_default="", default="log id 用uuid生成唯一id,用来用户更新"
    )
    cron_info_id: Column = db.Column(db.Integer, nullable=False, default=0, index=True)
    content: Column = db.Column(db.TEXT, nullable=False, default="", doc="返回的内容")
    create_time: Column = db.Column(db.String(25), nullable=False, default="")
    take_time: Column = db.Column(db.String(25), default="", doc="耗时时间")

    def to_json(self) -> dict:
        """把当前这条执行日志序列化成可直接 `jsonify` 的字典。

        返回:
            含 `id`、`log_id`、`cron_info_id`、`content`、`create_time`、`take_time`
            六个键的字典，键名与表字段一一对应。
        """
        return {
            "id": self.id,
            "log_id": self.log_id,
            "cron_info_id": self.cron_info_id,
            "content": self.content,
            "create_time": self.create_time,
            "take_time": self.take_time,
        }

    @staticmethod
    def job_log_list(page, cron_info_id, page_size=20):
        """按定时任务 ID 查询其执行日志，并按主键倒序分页。

        参数:
            page: 页码，从 1 开始；传入 None/0/空串时按第 1 页处理。
            cron_info_id: `CronInfos.id`，只返回该任务的执行日志。
            page_size: 每页条数，默认 20。
        返回:
            Flask-SQLAlchemy 的 `Pagination` 对象，`.items` 是本页的 `JobLog` 列表。
        """
        page = int(page or 1)
        return (
            JobLog.query.filter(JobLog.cron_info_id == cron_info_id)
            .order_by(db.desc(JobLog.id))
            .paginate(page=page, per_page=page_size)
        )
