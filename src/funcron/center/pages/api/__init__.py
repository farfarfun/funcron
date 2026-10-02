"""API 蓝图包：导入 `views` 完成路由注册，并对外暴露蓝图对象 `api`。"""

from . import views
from .core import api

__all__ = ["api", "views"]
