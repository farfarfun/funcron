"""`funcron` 命令行入口。

本仓库的长期运行服务（Flask 管理后台、Airflow 各角色、funcoin 行情下载）统一由
`scripts/setup.sh` 托管，CLI 这里只保留与进程托管无关的查询类子命令。

子命令:
    status      打印本机常用服务端口的可访问状态。
    services    列出 `scripts/setup.sh` 支持的服务名。
"""

from collections.abc import Sequence

import typer

from funcron.server.port_manage import PortManage

#: `scripts/setup.sh` 支持的服务名，与 scripts/setup.sh 里的 ALL_SERVICES 保持一致。
SETUP_SERVICES: tuple[str, ...] = (
    "server",
    "airflow-webserver",
    "airflow-scheduler",
    "airflow-worker",
    "airflow-flower",
    "coin",
)

_SETUP_HINT = (
    "服务的启停请使用仓库内的 scripts/setup.sh，例如:\n"
    "    scripts/setup.sh start server\n"
    "    scripts/setup.sh run airflow-scheduler"
)

app = typer.Typer(
    add_completion=False,
    epilog=_SETUP_HINT,
    help="funcron 命令行工具；长期运行服务的启停请使用 scripts/setup.sh。",
    invoke_without_command=True,
    no_args_is_help=False,
)


@app.callback()
def main(context: typer.Context) -> None:
    """funcron 的查询命令。"""
    if context.invoked_subcommand is None:
        typer.echo(context.get_help())
        raise typer.Exit(2)


@app.command()
def status() -> None:
    """打印本机常用服务端口的可访问状态。"""
    PortManage().fprint()


@app.command()
def services() -> None:
    """列出 scripts/setup.sh 支持的服务名。"""
    for name in SETUP_SERVICES:
        typer.echo(name)
    typer.echo()
    typer.echo(_SETUP_HINT)


def funcron(argv: Sequence[str] | None = None) -> int:
    """`funcron` 控制台脚本入口。

    参数:
        argv: 命令行参数（不含程序名）；为 None 时取 `sys.argv[1:]`。
    返回:
        进程退出码，0 表示成功，2 表示没有指定子命令（已打印用法）。
    """
    try:
        app(args=list(argv) if argv is not None else None, prog_name="funcron")
    except SystemExit as exc:
        return int(exc.code or 0)
    return 0


if __name__ == "__main__":  # pragma: no cover - 手工调试入口
    raise SystemExit(funcron())
