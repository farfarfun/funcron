"""`scripts/lib/funcron-airflow-env.sh` 与 Airflow 服务脚本的配置注入测试。

覆盖：仓库内不得再出现带凭据/开发机绝对路径的 airflow.cfg、AIRFLOW__* 默认值推导、
.env 覆盖优先级、prod 缺少元数据库连接串时拒绝启动，以及 Airflow 3 下的 CLI 子命令。
"""

import os
import shutil
import subprocess
import textwrap

import pytest

pytestmark = pytest.mark.skipif(shutil.which("bash") is None, reason="需要 bash")


def run_airflow_env(repo_root, body: str, env: dict | None = None, cwd=None):
    """在 source 了 funcron-common.sh + funcron-airflow-env.sh 的 bash 里执行 `body`。"""
    lib = repo_root / "scripts" / "lib"
    script = (
        f'set -euo pipefail\nsource "{lib / "funcron-common.sh"}"\nsource "{lib / "funcron-airflow-env.sh"}"\n'
        + textwrap.dedent(body)
    )
    full_env = dict(os.environ)
    # 避免本机真实 .env / AIRFLOW_* 环境变量干扰断言。
    for key in list(full_env):
        if key.startswith("AIRFLOW"):
            del full_env[key]
    full_env["FUNCRON_ENV_FILE"] = "/nonexistent-funcron-env"
    if env:
        full_env.update(env)
    return subprocess.run(
        ["bash", "-c", script],
        capture_output=True,
        text=True,
        cwd=cwd or repo_root,
        check=False,
        env=full_env,
    )


# ---------------- 仓库里不得再有写死凭据/绝对路径的 airflow.cfg ----------------


def test_no_airflow_cfg_in_repo(repo_root):
    """airflow.cfg 里曾带明文 mysql 口令、flask secret_key 和三处开发机绝对路径，必须不再存在。"""
    assert not (repo_root / "src" / "funcron" / "airflow" / "airflow.cfg").exists()


def test_no_hardcoded_db_credentials_in_tracked_files(repo_root):
    """全仓库不得再出现那串明文连接串。

    排除 CHANGELOG.md（里面是对这条历史问题的记述）和本测试文件自身（needle 就写在这儿）。
    """
    # 拆开拼接，免得这个字面量本身又被当成一次新的泄露。
    needle = "funcron" + ":" + "funcron" + "@"
    tracked = subprocess.run(
        ["git", "ls-files"], cwd=repo_root, capture_output=True, text=True, check=True
    ).stdout.split()
    skip = {"CHANGELOG.md", "tests/test_airflow_env.py"}
    offenders = []
    for rel in tracked:
        if rel in skip:
            continue
        path = repo_root / rel
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if needle in text:
            offenders.append(rel)
    assert offenders == []


def test_no_developer_absolute_paths_in_scripts(repo_root):
    """服务脚本与包内文件不得写死任何开发机绝对路径。"""
    for rel in ("scripts/services/airflow.sh", "scripts/lib/funcron-airflow-env.sh", "scripts/airflow-init.sh"):
        text = (repo_root / rel).read_text(encoding="utf-8")
        assert "/home/bingtao" not in text, rel
        assert "/fundata/" not in text, rel


# ---------------- AIRFLOW__* 默认值推导 ----------------


def test_dev_defaults_are_derived_from_repo_and_airflow_home(repo_root, tmp_path):
    """dev：DAG 目录指向源码树，其余目录落在 AIRFLOW_HOME 下。"""
    home = tmp_path / "afhome"
    result = run_airflow_env(
        repo_root,
        f"""
        funcron_prepare_airflow_env dev "{repo_root}" "{tmp_path}/run"
        echo "HOME=$AIRFLOW_HOME"
        echo "DAGS=$AIRFLOW__CORE__DAGS_FOLDER"
        echo "PLUGINS=$AIRFLOW__CORE__PLUGINS_FOLDER"
        echo "LOGS=$AIRFLOW__LOGGING__BASE_LOG_FOLDER"
        echo "TZ=$AIRFLOW__CORE__DEFAULT_TIMEZONE"
        """,
        env={"AIRFLOW_HOME_DEV": str(home)},
    )
    assert result.returncode == 0, result.stderr
    out = dict(line.split("=", 1) for line in result.stdout.strip().splitlines())
    assert out["HOME"] == str(home)
    assert out["DAGS"] == str(repo_root / "src" / "funcron" / "airflow" / "dags")
    assert out["PLUGINS"] == str(home / "plugins")
    assert out["LOGS"] == str(home / "logs")
    # "GMT+8" 不是 IANA 时区名，按 POSIX TZ 语义解释反而是 UTC-8，不能作为默认值。
    assert out["TZ"] == "Asia/Shanghai"


def test_dev_dags_folder_really_exists(repo_root, tmp_path):
    """dev 推导出来的 DAG 目录必须真实存在，否则 Airflow 启动即空跑。"""
    result = run_airflow_env(
        repo_root,
        f"""
        funcron_prepare_airflow_env dev "{repo_root}" "{tmp_path}/run"
        test -d "$AIRFLOW__CORE__DAGS_FOLDER" && echo EXISTS
        """,
        env={"AIRFLOW_HOME_DEV": str(tmp_path / "afhome")},
    )
    assert "EXISTS" in result.stdout, result.stderr


def test_explicit_env_var_wins_over_default(repo_root, tmp_path):
    """调用方显式导出的 AIRFLOW__* 必须优先于脚本默认值。"""
    result = run_airflow_env(
        repo_root,
        f"""
        funcron_prepare_airflow_env dev "{repo_root}" "{tmp_path}/run"
        echo "DAGS=$AIRFLOW__CORE__DAGS_FOLDER"
        echo "EXECUTOR=$AIRFLOW__CORE__EXECUTOR"
        """,
        env={
            "AIRFLOW_HOME_DEV": str(tmp_path / "afhome"),
            "AIRFLOW__CORE__DAGS_FOLDER": "/tmp/my-dags",
            "AIRFLOW__CORE__EXECUTOR": "LocalExecutor",
        },
    )
    assert "DAGS=/tmp/my-dags" in result.stdout
    assert "EXECUTOR=LocalExecutor" in result.stdout


def test_env_file_is_loaded(repo_root, tmp_path):
    """.env 里的配置会被加载，并覆盖脚本默认值。"""
    env_file = tmp_path / "custom.env"
    env_file.write_text("AIRFLOW__CORE__EXECUTOR=LocalExecutor\n", encoding="utf-8")
    result = run_airflow_env(
        repo_root,
        f"""
        funcron_prepare_airflow_env dev "{repo_root}" "{tmp_path}/run"
        echo "EXECUTOR=$AIRFLOW__CORE__EXECUTOR"
        """,
        env={"AIRFLOW_HOME_DEV": str(tmp_path / "afhome"), "FUNCRON_ENV_FILE": str(env_file)},
    )
    assert "EXECUTOR=LocalExecutor" in result.stdout, result.stderr


# ---------------- prod 的凭据前置校验 ----------------


def test_prod_without_sql_alchemy_conn_is_rejected(repo_root, tmp_path):
    """prod 缺元数据库连接串时必须报错返回非 0，而不是悄悄回落到 SQLite。"""
    result = run_airflow_env(
        repo_root,
        f"""
        if funcron_require_airflow_conn prod "{repo_root}"; then echo RC=0; else echo RC=1; fi
        """,
        env={"AIRFLOW_HOME_PROD": str(tmp_path / "prodhome")},
    )
    assert "RC=1" in result.stdout
    assert "AIRFLOW__DATABASE__SQL_ALCHEMY_CONN" in result.stderr


def test_prod_with_sql_alchemy_conn_passes(repo_root, tmp_path):
    """显式提供连接串后校验通过。"""
    result = run_airflow_env(
        repo_root,
        f'funcron_require_airflow_conn prod "{repo_root}" && echo RC=0',
        env={
            "AIRFLOW_HOME_PROD": str(tmp_path / "prodhome"),
            "AIRFLOW__DATABASE__SQL_ALCHEMY_CONN": "sqlite:////tmp/x.db",
        },
    )
    assert "RC=0" in result.stdout, result.stderr


def test_dev_without_sql_alchemy_conn_is_allowed(repo_root):
    """dev 不强制要求连接串（回落到 AIRFLOW_HOME 下的 SQLite 即可）。"""
    result = run_airflow_env(repo_root, f'funcron_require_airflow_conn dev "{repo_root}" && echo RC=0')
    assert "RC=0" in result.stdout, result.stderr


# ---------------- Airflow 3 CLI 子命令 ----------------


def test_webserver_role_uses_api_server_command(repo_root):
    """Airflow 3 已移除 `airflow webserver`，脚本必须改用 `airflow api-server`。"""
    text = (repo_root / "scripts" / "services" / "airflow.sh").read_text(encoding="utf-8")
    assert "cmd=(airflow api-server" in text
    assert "cmd=(airflow webserver" not in text


def test_init_script_uses_db_migrate(repo_root):
    """Airflow 3 已移除 `airflow db init`，初始化脚本必须用 `airflow db migrate`。"""
    text = (repo_root / "scripts" / "airflow-init.sh").read_text(encoding="utf-8")
    code = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))
    assert "airflow db migrate" in code
    assert "airflow db init" not in code


@pytest.mark.skipif(shutil.which("airflow") is None, reason="未安装 airflow CLI")
def test_airflow_cli_really_has_api_server_and_not_webserver(tmp_path):
    """实跑一次 CLI，确认 api-server 存在而 webserver 确已移除（不是只看文档）。"""
    env = {**os.environ, "AIRFLOW_HOME": str(tmp_path / "afhome")}
    ok = subprocess.run(["airflow", "api-server", "--help"], capture_output=True, text=True, env=env, check=False)
    assert ok.returncode == 0, ok.stderr
    gone = subprocess.run(["airflow", "webserver", "--help"], capture_output=True, text=True, env=env, check=False)
    assert gone.returncode != 0


def test_init_script_syntax_is_valid(repo_root):
    """init.sh 必须通过 bash 语法检查。"""
    result = subprocess.run(
        ["bash", "-n", str(repo_root / "scripts" / "airflow-init.sh")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
