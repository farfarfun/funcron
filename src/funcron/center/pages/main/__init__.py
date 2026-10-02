"""Web 管理后台蓝图包：导入 `views`/`errors` 完成路由与错误页注册。"""

from . import errors, views
from .core import blue_print
from .core import blue_print as main

__all__ = ["blue_print", "errors", "main", "views"]
