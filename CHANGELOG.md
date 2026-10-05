# CHANGELOG

本文件记录 funcron 的版本变更，按版本倒序排列。

## [未发布]

### 修复

- `server/port_manage.py`、`tasks/core.py`、`tool/mail.py` 的日志调用误用 stdlib
  logging 的 `%s` 占位符，farlog（loguru）不支持该语法，参数被静默丢弃；统一改为
  loguru 的 `{}` 占位符。`center/common/scheduler/cu_gevent_scheduler.py`、
  `cu_background_scheduler.py`（源自 apscheduler，用 stdlib logging）与
  `center/pages/crons/core.py` 的 `current_app.logger`（Flask 的 stdlib logger）
  `%s` 用法本身正确，未改动。
- **`JobLog.to_json()` 调用必抛 `AttributeError`**：它返回 `job_id` / `remark` /
  `traces` / `status` 四个字段，而 `job_log` 表早已不存在这些列。现按实际列
  （`id`/`log_id`/`cron_info_id`/`content`/`create_time`/`take_time`）重写，
  并加测试断言返回键集合与表列定义一致，拦住后续字段漂移。
- **`RedisCache.delete()` 永远删不掉键**：`set()`/`get()` 都按 `f"{prefix}{key}"`
  读写带前缀的键，只有 `delete()` 直接 `delete(key)`，前缀被漏掉。现统一走
  `full_key()` 拼接；`clear()` 也改为一次 `delete(*keys)` 并返回实际删除数量。
- **`RedisCache` 的连接池在不同目标库之间串用**：`hasattr(RedisCache, "pool")`
  是全类单例，第二次用不同 host/port/db 构造出的实例会静默连到第一次那个库。
  现按 `(host, port, db)` 分别缓存连接池。
- `JobLog.job_log_list()` 的参数 `id` 遮蔽内置函数，改名为 `cron_info_id`，
  并与 `cron_list()` 一致支持 `page_size` 与空页码回落；调用方同步更新。

### 新增

- `center/models.py`、`center/utils/times.py`、`center/utils/redis_cache.py`
  的公开类、函数、方法补齐位于定义体首句的中文 docstring（原先只有游离在
  模块/方法之间的三引号文本，不构成 docstring）。
- 新增 `tests/test_models.py`、`tests/test_redis_cache.py`、`tests/test_times.py`，
  覆盖上述修复的正常路径、边界与失败路径（Redis 用内存假客户端，不连真实服务）。

## [0.5.9] - 2026-10-02

### 修复

- **`funcron` 命令行此前完全不可用**：`funcron/server/script.py` 顶部
  `from funbuild.manage import BaseServer`，而 funbuild 已不再提供 `manage` 模块
  （当前及 pyproject 声明下限 1.6.75 均无），控制台脚本一启动就
  `ModuleNotFoundError: No module named 'funbuild.manage'`。已发布的 0.5.7 带着这个缺陷。
  现已重写 CLI，去掉对 funbuild/supervisor 的依赖。
- **README 示例与实现不一致**：旧 CLI 要求同时给 `cmd` 和 `service` 两个位置参数，
  README 里的 `funcron server` / `funcron status` 实际都以用法错误退出；
  `scripts/setup.sh status all` 也因为缺第三个参数退出码 1。现在 CLI 提供
  `status` / `services` 两个子命令，`scripts/setup.sh status` 的环境参数可省略
  （省略时报告 dev 与 prod 两个环境），README 示例已逐条实测可运行。
- **`db.session.execute()` 传裸字符串 SQL 在 SQLAlchemy 2.x 下直接报错**：
  `funcron/center/pages/main/views.py` 的 `cron_del`、
  `funcron/center/pages/crons/core.py` 的 `cron_check_db_sleep` / `cron_del_job_log`
  会抛 `ObjectNotExecutableError`（本仓库声明 flask-sqlalchemy>=3.1.1，即 SQLAlchemy 2.x）。
  现统一改为 `sqlalchemy.text()` + 参数绑定。
- **SQL 字符串插值改为参数绑定**：`cu_background_scheduler.py` / `cu_gevent_scheduler.py`
  的 `update_cron_info` 原先用 `"... where id='%s'" % cron_id` 拼 SQL，任务 ID 来自任务数据；
  现改为绑定参数，并在解析出的主键不是数字时拒绝执行并记日志。
  `cron_del_job_log` 的 `delete ... limit` 同样改为绑定参数。
- **prod 启动的生产包校验此前被 editable 安装架空**：`scripts/services/server.sh` 用
  `python3 -c "import funcron"` 判定「已安装」，但 `uv sync` 装的是 editable（`.pth` 指回源码），
  从仓库目录运行时裸 import 也会命中工作树，校验恒为真，`start prod` 实际在跑源码。
  现改为清空 `PYTHONPATH` + Python 隔离模式（`-I`）+ 切到 `.run/` + 断言模块文件落在
  `site-packages`/`dist-packages`；校验下沉到各服务脚本的 `command_for`，使 `run prod`
  这条路径同样被覆盖；airflow 与 coin 服务也补上了同样的 prod 校验。
  `prod` 下 gunicorn 的配置文件改为从已安装包内解析，不再引用仓库源码目录。
- **重复启动检查会把任意存活 PID 当成本服务**：`funcron_is_running` 原先只 `kill -0` PID 文件里的
  数字。现在 PID 文件旁多记一份 `.meta`（进程启动时刻 + 命令特征串），状态细分为
  `missing`/`invalid`/`stale`/`mismatch`/`running`：陈旧文件清理后继续，PID 被其他进程复用时
  拒绝操作并提示人工确认（`stop` 也不会去 kill 未通过身份校验的进程）。
- **`default` / `testing` 配置默认开着 DEBUG**：`config_dict` 的 `default` 原先指向
  `DevelopmentConfig`（`DEBUG = True`）。现在 `default` 指向 `ProductionConfig`，新增
  `TestingConfig`（只开 `TESTING`，不开 `DEBUG`），`DEBUG` 只在显式选 `development` 时开启。
- **`create_app()` 无条件改写调用方传入的配置名**：函数体第一行 `config_name = "production"`
  让参数形同虚设。现在尊重入参，未知配置名直接抛 `KeyError` 而不是静默回落。
- **`api_deal_return` 对不支持的返回值隐式返回 None**：视图返回 `None` 或其他未覆盖类型时
  装饰器什么都不返回，Flask 随后报 "did not return a valid response"，排查不到真正原因。
  现在返回带类型名的明确错误响应。顺带把 `type(x) == str` 这类判断改为 `isinstance`。
- **缺失的运行时依赖补齐声明**：`requests`、`six`、`sqlalchemy` 在代码里直接 import，
  此前完全没有声明，靠传递依赖"运气好"装上。`fundata` 下限提到 1.0.3（1.0.1/1.0.2 的
  wheel 里带着失效的 notetool/notebuild import）。
- `funcron status` 的 IP 探测失败不再让命令整体崩溃，改为回落到 `127.0.0.1` / `unknown`
  并记录警告。端口清单里移除了已不再使用的 supervisor 条目，补上 funcron 管理后台自身端口。
- **非 root 环境 `import funcron.center.common.config` 直接 PermissionError**：配置模块在
  import 期间就 `WorkApp("funcron").create()`，而 `fundata` 的默认工作目录写死在
  `/opt/farfarfun/apps/funcron`，普通用户下 `os.makedirs` 抛 `PermissionError`，
  连测试收集都会整体失败。现在工作目录按
  `FUNCRON_APP_DIR` → `FUNDATA_APP_DIR` → `/opt/farfarfun/apps/funcron`（可写才用）
  → `~/.funcron` 的顺序解析，并有 4 个测试覆盖这条优先级链。
- **404 / 500 错误页以 HTTP 200 返回**：`funcron/center/pages/main/errors.py` 的
  `app_errorhandler` 只返回一个字符串，Flask 不会自动套上异常的状态码，于是「找不到页面」
  和「服务端异常」在 HTTP 层都表现为成功，探活与调用方无法区分。现在显式返回
  `(正文, 404)` / `(正文, 500)`，并有测试断言状态码。
- **`funcron.tool.mail` 里写死的真实邮箱地址与收件人**：发件账号 `15068733021@163.com`
  与默认收件人（两个个人 QQ 邮箱）直接写在源码里，随包发布到 PyPI。现在发件账号、
  口令、默认收件人全部经 `funsecret` 下发，缺配置时抛 `ValueError` 而不是静默发往写死的
  地址；顺带修掉「多个收件人时只有第一个出现在 `To` 头里」以及异常时 `smtp.close()`
  不会被执行（改用 `with`）两个问题。

### 变更

- **源码改为 src 布局**：`funcron/` → `src/funcron/`（SPEC 4.1），同步调整 hatch 构建配置
  与服务脚本路径。包名、发布名、import 路径都不变（仍是 `funcron`），对使用方无影响；
  附带好处是在仓库根目录不会再误把工作树源码当成已安装包 import 到。
- **不再依赖 supervisor 做进程守护**：进程托管统一由 `scripts/setup.sh` + `.run/` 负责，
  `supervisor` 与 `funbuild` 已从运行时依赖中移除（`funbuild` 本就只是构建/发布工具）。
- 新增 `[tool.ruff]` 配置（line-length 120、显式 select 规则集）与 `[tool.pytest.ini_options]`，
  `ruff` 加入 dev 依赖组；补上 `[project.urls]`。`ruff check` 与 `ruff format --check`
  现已全仓库通过（存量问题逐条修掉或带理由标注豁免，不是靠放宽规则集蒙过去）。
- `uv.lock` 中的传递依赖升级，修掉 Dependabot 报出的安全告警（纯锁文件升级，本包代码未变，
  测试全绿）：
  - `urllib3` 2.7.0 → 2.8.0：2 HIGH + 1 MEDIUM（`HTTPResponse.stream()/read_chunked()`
    无界缓冲、HTTPS 代理的 TLS 配置可能被忽略、chunked deflate 响应可能无限循环）。
  - `pyjwt` 2.13.0 → 2.15.1：1 CRITICAL + 5 HIGH + 多个 MEDIUM（非对称 PEM 检测绕过、
    公钥被当作 HMAC 密钥、BOM 绕过、空 HMAC 密钥、`PyJWKClient` 跟随重定向等）。
  - `tornado` 6.5.8 → 6.5.10：2 HIGH（`CurlAsyncHTTPClient` 解压无响应大小上限、
    `StaticFileHandler` 跟随软链接越出静态根目录）。
  - 仍未修复的 `diskcache`（unsafe pickle 反序列化）上游无可用修复版本，funcron 只把它
    当本地缓存用、不反序列化外部输入，暂维持现状。
- 把 `script/__version__.md` 与 `pyproject.toml` 的 `[project].version` 对齐（此前漂成
  0.5.8 / 0.5.7：funbuild 的 `sync_all_manifest_versions()` 不同步 `script/__version__.md`）。
  新增 `tests/test_version_consistency.py` 断言两处一致，拦截后续漂移。

### 新增

- `funcron` CLI 新增 `services` 子命令，列出 `scripts/setup.sh` 能托管的服务名；
  并有测试断言这份名单与 `scripts/setup.sh` 的 `ALL_SERVICES` 一致。
- 测试从 3 个文件 / 1 条断言扩充到 10 个文件 / 74 条，新增：CLI 子命令与参数解析、
  `scripts/setup.sh` 的动作/服务/环境参数校验与 `status` 行为、重复启动检查五种状态的
  逐一验证、prod 生产包校验对源码树/editable 的拒绝（含「朴素 import 确实会通过」的
  前置断言，避免测试空跑）、`api_deal_return`/`login_required` 的正常与边界路径、
  配置默认值的安全性与工作目录解析优先级、邮件发送的缺配置/多收件人路径、
  404/500 错误页的状态码。原先两个用 `pytest.importorskip` 兜住 fundata 问题的测试
  已改为真实 import，环境退化时直接失败而不是静默跳过。
- Web/API 视图函数、蓝图模块与错误处理器补齐中文 docstring；`api/views.py` 里
  `except Exception` 收窄为 `(TypeError, ValueError)`。

### 废弃

- **移除 `funcron.core` 模块（`JobScheduler` 与 `funcron.core.funcron`）**。
  替代品：`scripts/setup.sh {start|stop|restart|status|run} <service> <dev|prod>`。
  移除原因：该模块通过 `subprocess(..., shell=True)` 执行 `nohup funcron _start ...`、
  并用 `ps x | grep funcron` 的文本输出拼 `kill -9 <pid>` 来停服务——既不安全（命令拼接、
  按进程名文本匹配可能误杀），也早已跑不通（它调用的 `funcron _start` 子命令在已注册的
  控制台脚本里并不存在）。迁移方法：
  原 `funcron.core.JobScheduler().start()/stop()/restart()`
  → `scripts/setup.sh start|stop|restart <service> <dev|prod>`。
- **移除 `funcron.tasks.ba` 模块**。该模块是 2020 年给某德国电商站点写的个人抢购脚本：
  funcron 内部没有任何调用点，与「定时任务调度中心」这个定位无关，且源码里带着一整份
  写死的第三方站点会话 Cookie（`frontend`、`bfd_sid`、`sensorsdata2015jssdkcross` 等）
  和两个个人 QQ 邮箱地址，随包发布到 PyPI。随之移除仅由它使用的 `demjson3` 运行时依赖。
  无迁移路径——它从未被 funcron 的任何入口暴露。

## [0.5.8] - 未发布（未推送到 PyPI，内容已并入 0.5.9）

### 新增

- 新增 `scripts/setup.sh` + `scripts/services/*.sh`，统一管理 server / airflow-webserver /
  airflow-scheduler / airflow-worker / airflow-flower / coin 等长期运行服务，支持
  `start`/`stop`/`restart`/`status`/`run`，区分 `dev`/`prod` 环境，运行时文件统一放在 `.run/`。
- README 补充安装命令、最小可运行示例、服务启动说明及组织介绍区块。

### 修复

- 修复 `pyproject.toml` 中依赖 `redi`（无关的 REDCap 导入工具）误当作 `redis` 声明的问题，
  改为正确声明 `redis`；为全部运行时依赖补充经验证的最低版本号，并提交 `uv.lock`。
- 删除 `funcron/core/core.py` 里 `from funbuild.shell import run_shell, run_shell_list`
  这行死 import（funcron 从未调用过这两个函数，且 funbuild 已不再提供 `shell` 模块，
  对应能力在独立的 `funshell` 包里）。这是 funcron 内部的未使用 import，不是 funcron
  自己对外暴露过的入口，使用方无需做任何迁移。
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
PyPI 上的最后一个已发布版本是 0.5.7；0.5.8 只在仓库里打了版本号、没有发布。
