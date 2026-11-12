"""测试共用 fixture。"""

import tomllib
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def repo_root() -> Path:
    """仓库根目录（tests/ 的父目录）。"""
    return Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def project_version(repo_root: Path) -> str:
    """返回 `pyproject.toml` 里 `[project].version` 的值。"""
    return tomllib.loads((repo_root / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]["version"]
