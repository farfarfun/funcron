from notecron.center.app import db
from sqlalchemy import Column


class CronInfos(db.Model):
    __tablename__ = 'cron_infos'
    id: Column = db.Column(db.Integer, primary_key=True)
    task_name: Column = db.Column(db.String(64), nullable=False)
    task_keyword: Column = db.Column(db.String(65), nullable=False, default='')
    run_date: Column = db.Column(db.String(25), default='', doc='执行时间')
    day_of_week: Column = db.Column(db.String(10), default='', doc='星期几')
    day: Column = db.Column(db.String(20), default='', doc='号(日)')
    hour: Column = db.Column(db.String(10), default='', doc='小时')
    minute: Column = db.Column(db.String(10), default='', doc='分钟')
    second: Column = db.Column(db.String(10), default='', doc='秒')
    req_url: Column = db.Column(db.String(128), default='')
    status: Column = db.Column(db.SMALLINT, default=True, doc='运行状态，0停止1运行中-1结束任务')

    @staticmethod
    def cron_list(page=1, task_name=None, page_size=20):
        page = int(page or 1)
        filter_arr = []
        if task_name:
            filter_arr.append(CronInfos.task_name.like('%{}%'.format(task_name)))
        return CronInfos.query.filter(*filter_arr).order_by(db.desc(CronInfos.task_name)).paginate(page=page,
                                                                                                   per_page=page_size)


class JobLogItems(db.Model):
    __tablename__ = 'job_log_items'
    id: Column = db.Column(db.Integer, primary_key=True)
    log_id: Column = db.Column(db.String(65), index=True, nullable=False)
    content: Column = db.Column(db.TEXT, nullable=False, default='')


class JobLog(db.Model):
    __tablename__ = 'job_log'
    id: Column = db.Column(db.Integer, primary_key=True)
    log_id: Column = db.Column(db.String(65), nullable=False, index=True, server_default='',
                               default='log id 用uuid生成唯一id,用来用户更新')
    cron_info_id: Column = db.Column(db.Integer, nullable=False, default=0, index=True)
    content: Column = db.Column(db.TEXT, nullable=False, default='', doc='返回的内容')
    create_time: Column = db.Column(db.String(25), nullable=False, default='')
    take_time: Column = db.Column(db.String(25), default='', doc='耗时时间')

    def to_json(self):
        return {
            'id': self.id,
            'job_id': self.job_id,
            'remark': self.remark,
            'content': self.content,
            'traces': self.traces,
            'status': self.status,
            'create_time': self.create_time
        }

    @staticmethod
    def job_log_list(page, id):
        return JobLog.query.filter(JobLog.cron_info_id == id).order_by(db.desc(JobLog.id)).paginate(
            page=page, per_page=20)
