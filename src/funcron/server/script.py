"""`funcron` 命令行入口。

本仓库的长期运行服务（Flask 管理后台、Airflow 各角色、funcoin 行情下载）统一由
`scripts/setup.sh` 托管，CLI 这里只保留与进程托管无关的查询类子命令。

子命令:
    status      打印本机常用服务端口的可访问状态。
    services    列出 `scripts/setup.sh` 支持的服务名。
"""

import argparse
from collections.abc import Sequence

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
    "    scripts/setup.sh start server prod\n"
    "    scripts/setup.sh run airflow-scheduler dev"
)


def build_parser() -> argparse.ArgumentParser:
    """构造 `funcron` 命令行参数解析器。

    返回:
        配置好 `status` / `services` 两个子命令的 `argparse.ArgumentParser`。
    """
    parser = argparse.ArgumentParser(
        prog="funcron",
        description="funcron 命令行工具；长期运行服务的启停请使用 scripts/setup.sh。",
        epilog=_SETUP_HINT,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("status", help="打印本机常用服务端口的可访问状态")
    subparsers.add_parser("services", help="列出 scripts/setup.sh 支持的服务名")
    return parser


def funcron(argv: Sequence[str] | None = None) -> int:
    """`funcron` 控制台脚本入口。

    参数:
        argv: 命令行参数（不含程序名）；为 None 时取 `sys.argv[1:]`。
    返回:
        进程退出码，0 表示成功，2 表示没有指定子命令（已打印用法）。
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "status":
        PortManage().fprint()
        return 0
    if args.command == "services":
        for name in SETUP_SERVICES:
            print(name)
        print()
        print(_SETUP_HINT)
        return 0
    parser.print_help()
    return 2


if __name__ == "__main__":  # pragma: no cover - 手工调试入口
    raise SystemExit(funcron())
