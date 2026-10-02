"""测试共用 fixture。"""

import re
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def repo_root() -> Path:
    """仓库根目录（tests/ 的父目录）。"""
    return Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def project_version(repo_root: Path) -> str:
    """`pyproject.toml` 里 `[project].version` 的值。

    不用 tomllib（3.11+ 才有，本项目 requires-python >= 3.10），只做最小行解析。
    """
    text = (repo_root / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, flags=re.MULTILINE)
    assert match, "pyproject.toml 里找不到 [project].version"
    return match.group(1)
