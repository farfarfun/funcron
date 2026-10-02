"""`funcron` CLI（`funcron.server.script`）的参数解析与各子命令行为测试。

重点回归：`funcron.server.script` 过去 `from funbuild.manage import BaseServer`，
而 funbuild 已不再提供 `manage` 模块，导致整个控制台脚本一 import 就 ModuleNotFoundError。
这里的 import 本身就是对那条路径的回归拦截。
"""

import pytest

from funcron.server import script


def test_module_imports_without_optional_build_deps():
    # 入口模块必须能独立 import，不依赖 funbuild/supervisor 这类已移除的依赖。
    assert callable(script.funcron)
    assert callable(script.build_parser)


def test_parser_accepts_status_without_extra_positional():
    # 旧实现要求 cmd + service 两个位置参数，`funcron status` 会直接报用法错误。
    args = script.build_parser().parse_args(["status"])
    assert args.command == "status"


def test_parser_accepts_services():
    args = script.build_parser().parse_args(["services"])
    assert args.command == "services"


def test_parser_rejects_unknown_command():
    with pytest.raises(SystemExit) as exc:
        script.build_parser().parse_args(["definitely-not-a-command"])
    assert exc.value.code == 2


def test_funcron_status_invokes_port_manage(monkeypatch):
    calls = []

    class FakePortManage:
        def fprint(self):
            calls.append("fprint")

    monkeypatch.setattr(script, "PortManage", lambda: FakePortManage())
    assert script.funcron(["status"]) == 0
    assert calls == ["fprint"]


def test_funcron_services_lists_all_setup_services(capsys):
    assert script.funcron(["services"]) == 0
    out = capsys.readouterr().out
    for name in script.SETUP_SERVICES:
        assert name in out
    # 必须指向 scripts/setup.sh，而不是让用户以为 CLI 能托管服务。
    assert "scripts/setup.sh" in out


def test_funcron_without_subcommand_prints_help_and_returns_2(capsys):
    assert script.funcron([]) == 2
    out = capsys.readouterr().out
    assert "usage" in out.lower()


def test_setup_services_match_setup_sh(repo_root):
    """CLI 里列出的服务名必须与 scripts/setup.sh 的 ALL_SERVICES 完全一致。"""
    text = (repo_root / "scripts" / "setup.sh").read_text(encoding="utf-8")
    line = next(ln for ln in text.splitlines() if ln.startswith("ALL_SERVICES="))
    declared = line.split("=", 1)[1].strip().strip('"').split()
    assert declared == list(script.SETUP_SERVICES)
