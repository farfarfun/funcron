"""配置默认值的安全性测试（SPEC 9.3：代码内默认值必须安全，不能默认开调试）。

`funcron.center.common.config` 这里是直接 import 的：配置模块的工作目录已改为
按可写性回落（见 `config._resolve_app_dir`），非 root 环境下 import 不再因为
`/opt/farfarfun` 的 PermissionError 而失败。用真实 import 而不是 importorskip，
是为了让这些断言在环境退化时直接报错，而不是悄悄跳过。
"""

import pytest

from funcron.center.common.config import config as config_mod


def test_default_config_is_not_debug():
    """`default` 必须指向非调试配置——这是「没显式选环境」时的兜底值。"""
    assert config_mod.config_dict["default"] is config_mod.ProductionConfig
    assert config_mod.config_dict["default"].DEBUG is False


def test_production_config_is_not_debug():
    assert config_mod.config_dict["production"].DEBUG is False


def test_testing_config_is_not_debug():
    """testing 要开 TESTING，但不能顺手把 DEBUG 也打开（调试器会暴露在测试环境）。"""
    testing = config_mod.config_dict["testing"]
    assert testing.TESTING is True
    assert testing.DEBUG is False


def test_development_config_is_the_only_debug_one():
    """只有显式选 development 才开 DEBUG。"""
    debug_names = [name for name, cfg in config_mod.config_dict.items() if getattr(cfg, "DEBUG", False)]
    assert debug_names == ["development"]


def test_config_alias_points_to_same_mapping():
    assert config_mod.config is config_mod.config_dict


def test_get_config_has_no_builtin_credentials():
    """凭据类字段不得带可直接使用的默认值（未配置时必须是空串）。"""
    values = config_mod.get_config()
    for key in ("redis_pwd", "login_pwd", "error_notice_api_key", "api_access_token"):
        assert key in values
        assert isinstance(values[key], str)


def test_get_config_value_reads_from_get_config():
    assert config_mod.get_config_value("is_single") == config_mod.get_config()["is_single"]


def test_get_config_value_unknown_key_raises():
    with pytest.raises(KeyError):
        config_mod.get_config_value("definitely-not-a-config-key")


def test_app_dir_prefers_explicit_env(monkeypatch, tmp_path):
    """显式配了 FUNCRON_APP_DIR 就必须按配置走，不做可写性回落。"""
    monkeypatch.setenv("FUNCRON_APP_DIR", str(tmp_path / "explicit"))
    monkeypatch.setenv("FUNDATA_APP_DIR", str(tmp_path / "ignored"))
    assert config_mod._resolve_app_dir() == str(tmp_path / "explicit")


def test_app_dir_falls_back_to_fundata_env(monkeypatch, tmp_path):
    monkeypatch.delenv("FUNCRON_APP_DIR", raising=False)
    monkeypatch.setenv("FUNDATA_APP_DIR", str(tmp_path / "fromfundata"))
    assert config_mod._resolve_app_dir() == str(tmp_path / "fromfundata")


def test_app_dir_falls_back_to_home_when_system_dir_unwritable(monkeypatch):
    """`/opt/farfarfun` 不可写时回落到 `~/.funcron`，import 不应再抛 PermissionError。"""
    monkeypatch.delenv("FUNCRON_APP_DIR", raising=False)
    monkeypatch.delenv("FUNDATA_APP_DIR", raising=False)
    monkeypatch.setattr(config_mod.os, "access", lambda *_args, **_kwargs: False)
    resolved = config_mod._resolve_app_dir()
    assert resolved.endswith("/.funcron")
    assert not resolved.startswith("/opt/")


def test_app_dir_uses_system_dir_when_writable(monkeypatch):
    monkeypatch.delenv("FUNCRON_APP_DIR", raising=False)
    monkeypatch.delenv("FUNDATA_APP_DIR", raising=False)
    monkeypatch.setattr(config_mod.os, "access", lambda *_args, **_kwargs: True)
    assert config_mod._resolve_app_dir() == "/opt/farfarfun/apps/funcron"
