# funcron

基于 Flask 与 Airflow 的定时任务调度管理中心，提供 Web 管理后台，以及 server（管理后台）/
scheduler/webserver/worker/flower（Airflow 各角色）/coin（行情下载）等长期运行服务。

## 安装

```bash
uv add funcron
# 或
pip install funcron
```

## 最小可运行示例

安装完成后，`funcron` 命令行提供两个查询类子命令：

```bash
# 查看本机常用服务端口的可访问状态
funcron status

# 列出 scripts/setup.sh 支持托管的服务名
funcron services
```

长期运行服务的启停不走 CLI，统一由 `scripts/setup.sh` 管理，见下一节。

## 服务启动（scripts/setup.sh）

生产环境或本地长期运行各服务，统一通过 `scripts/setup.sh` 管理，按 `动作 → 服务 → 环境` 解析参数：

```bash
# 用法: scripts/setup.sh {start|stop|restart|run} <service> <dev|prod>
#       scripts/setup.sh status <service> [dev|prod]
#   <service>: server | airflow-webserver | airflow-scheduler | airflow-worker
#              | airflow-flower | coin | all

# 后台启动生产环境的 Web 管理后台
scripts/setup.sh start server prod

# 前台运行开发环境的 Airflow scheduler，方便调试
scripts/setup.sh run airflow-scheduler dev

# 查看所有服务在 dev 与 prod 两个环境下的状态（status 的环境参数可省略）
scripts/setup.sh status all

# 只看生产环境
scripts/setup.sh status all prod
```

`start`/`stop`/`restart` 管理后台进程，`run` 是前台阻塞运行，方便调试单个服务，不支持 `all`。
`start`/`stop`/`restart`/`run` 必须显式带 `dev` 或 `prod`；只有 `status` 允许省略环境参数，
省略时依次报告两个环境。

PID、进程身份记录与日志统一放在仓库根目录的 `.run/` 下（按「服务名-环境」区分）。重复启动检查会
校验 PID 对应进程的启动时刻与命令特征：进程已退出的陈旧 PID 文件会被清理后继续启动；PID 已被
其他进程复用时拒绝操作并提示人工确认，不会误杀无关进程。

`prod` 环境要求 funcron / airflow / funcoin 已安装为**正式包**：校验会清空 `PYTHONPATH`、用
Python 隔离模式导入，并断言模块文件落在 `site-packages` 下，因此 editable 安装（`pip install -e`、
`uv sync`）或直接从源码工作树运行都会被拒绝；`prod` 下 gunicorn 的配置文件也从已安装包内解析，
不引用仓库源码。本地源码调试请用 `dev`。

## 凭据配置

数据库密码、Web 登录密码、Redis 密码、通知 API key、API access token、Flask session key
均从 `funsecret` 读取，不提供默认凭据。对应路径位于 `funcron/database/mysql/password`、
`funcron/web/login/password`、`funcron/redis/password`、`funcron/notice/error_api_key`、
`funcron/api/access_token` 和 `funcron/web/flask/secret_key`。缺少登录密码时 Web 登录会拒绝访问；
缺少 API access token 时 API 会返回配置错误；可选的 Redis 密码和通知 API key 为空时不启用相应认证或通知。

Flask 配置名可取 `development` / `testing` / `production` / `default`，由 `create_app(config_name)`
显式选择。只有 `development` 会开启 `DEBUG`；`default` 指向生产配置，`testing` 只开 `TESTING`。

## 工作目录

数据库文件、日志与中间文件放在工作目录下，按以下顺序解析：`FUNCRON_APP_DIR` 环境变量 →
`FUNDATA_APP_DIR` 环境变量 → `/opt/farfarfun/apps/funcron`（当前用户可写时）→ `~/.funcron`。
显式设置环境变量时按设置值使用，不再做可写性回落。

## 开发

```bash
uv sync
uv run pytest
uv run ruff check
uv run ruff format --check
```

源码采用 src 布局（`src/funcron/`），因此在仓库根目录直接 `import funcron` 不会命中工作树，
需要先 `uv sync` 安装。

---

## 关于 farfarfun

[farfarfun](https://github.com/farfarfun) 是一个专注于实用工具库的开源组织，
涵盖云存储、数据处理、AI、多媒体与开发工具链等方向。

- 🏠 组织主页：<https://github.com/farfarfun>
- 📦 PyPI：<https://pypi.org/user/niuliangtao/>
- 📧 联系：farfarfun@qq.com

本项目基于 [MIT](LICENSE) 协议开源。
