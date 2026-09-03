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

安装完成后，通过内置的 `funcron` 命令行查看可用服务、启动 Web 管理后台，或查看本机常用端口的可访问状态：

```bash
# 前台启动 Web 管理后台（调试用）
funcron server

# 查看本机常用服务端口状态
funcron status
```

## 服务启动（scripts/setup.sh）

生产环境或本地长期运行各服务，统一通过 `scripts/setup.sh` 管理，按 `动作 → 服务 → 环境` 解析参数：

```bash
# 用法: scripts/setup.sh {start|stop|restart|status|run} <service> <dev|prod>
#   <service>: server | airflow-webserver | airflow-scheduler | airflow-worker
#              | airflow-flower | coin | all

# 后台启动生产环境的 Web 管理后台
scripts/setup.sh start server prod

# 前台运行开发环境的 Airflow scheduler，方便调试
scripts/setup.sh run airflow-scheduler dev

# 查看所有服务状态
scripts/setup.sh status all
```

`start`/`stop`/`restart`/`status` 管理后台进程，PID 与日志统一放在仓库根目录的 `.run/` 下
（按「服务名-环境」区分）；`run` 是前台阻塞运行，方便调试单个服务，不支持 `all`。
`prod` 环境要求 funcron/funcoin 已通过 `pip install`/`uv sync` 安装为正式包，未安装会直接报错退出，
不会回退到仓库源码运行。

---

## 关于 farfarfun

[farfarfun](https://github.com/farfarfun) 是一个专注于实用工具库的开源组织，
涵盖云存储、数据处理、AI、多媒体与开发工具链等方向。

- 🏠 组织主页：<https://github.com/farfarfun>
- 📦 PyPI：<https://pypi.org/user/niuliangtao/>
- 📧 联系：farfarfun@qq.com

本项目基于 [MIT](LICENSE) 协议开源。
