"""`funcron.center.models` 的公开 API 测试。"""

from funcron.center.models import JobLog


def test_to_json_keys_match_columns():
    """`to_json()` 的键必须与 `job_log` 表实际定义的列一一对应。

    历史上这里返回的是 `job_id`/`remark`/`traces`/`status` 四个早已不存在的字段，
    调用即 `AttributeError`，这条断言就是用来拦住这类字段漂移的。
    """
    columns = {column.name for column in JobLog.__table__.columns}
    log = JobLog()
    assert set(log.to_json()) == columns


def test_to_json_normal_path():
    """正常路径：各字段原样进入序列化结果。"""
    log = JobLog(
        id=1,
        log_id="7b1f",
        cron_info_id=9,
        content="done",
        create_time="2026-01-02 03:04:05",
        take_time="1.25",
    )
    assert log.to_json() == {
        "id": 1,
        "log_id": "7b1f",
        "cron_info_id": 9,
        "content": "done",
        "create_time": "2026-01-02 03:04:05",
        "take_time": "1.25",
    }


def test_to_json_on_unsaved_instance():
    """边界：未落库的实例各列为 None 时也要能序列化，而不是抛异常。"""
    assert JobLog().to_json() == {
        "id": None,
        "log_id": None,
        "cron_info_id": None,
        "content": None,
        "create_time": None,
        "take_time": None,
    }
