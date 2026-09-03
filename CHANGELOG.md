# CHANGELOG

本文件记录 funcron 的版本变更，按版本倒序排列。

## [0.5.8] - 2026-09-03

### 新增

- 新增 `scripts/setup.sh` + `scripts/services/*.sh`，统一管理 server / airflow-webserver /
  airflow-scheduler / airflow-worker / airflow-flower / coin 等长期运行服务，支持
  `start`/`stop`/`restart`/`status`/`run`，区分 `dev`/`prod` 环境，运行时文件统一放在 `.run/`。
- README 补充安装命令、最小可运行示例、服务启动说明及组织介绍区块。

### 修复

- 修复 `pyproject.toml` 中依赖 `redi`（无关的 REDCap 导入工具）误当作 `redis` 声明的问题，
  改为正确声明 `redis`；为全部运行时依赖补充经验证的最低版本号，并提交 `uv.lock`。
- `funcron/core/core.py` 不再从已废弃的 `funbuild.shell` 导入 `run_shell`/`run_shell_list`
  （该入口已迁移到独立的 `funshell` 包，旧路径已失效）。
- `funcron/center/common/config/config.py`、`funcron/tool/mail.py`、`funcron/airflow/create_account.py`
  中硬编码的登录口令、Redis 密码、通知 API key、API access token、Airflow 管理员账号密码
  改为通过 `funsecret`/环境变量下发，代码中不再出现明文真实凭据。
- `funcron/center/pages/main/views.py`、`funcron/center/common/scheduler/cu_background_scheduler.py`、
  `cu_gevent_scheduler.py` 中吞掉异常的裸 `except`/`except Exception: pass` 改为记录带上下文的错误日志。
- `funcron/tasks/core.py`、`funcron/center/common/functions.py` 中用于诊断的 `print` 改为
  `farlog` 日志输出。

### 变更

- 统一日志入口为 `farlog.getLogger`，移除 `funcron/center/app.py` 中手写的 `logging`
  handler 配置，以及 `funtool.tool.log` 的使用。
- 模块文件名改为 snake_case：`CuBackgroundScheduler.py` → `cu_background_scheduler.py`、
  `CuGeventScheduler.py` → `cu_gevent_scheduler.py`、`RedisCache.py` → `redis_cache.py`
  （类名保持不变，仅重命名文件并同步更新导入）。
- `.gitignore` 补充 `*.pyc`、`*.db`、`*.rar`、`.venv/`、`.run/`、`.idea/`、`.vscode/`、
  `node_modules/`。

### 废弃

- 无。

## 历史版本

0.5.8 之前的版本未维护本文件，历史变更请参考 Git 提交记录。
