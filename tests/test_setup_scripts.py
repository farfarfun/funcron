"""`scripts/setup.sh` 与 `scripts/lib/funcron-common.sh` 的行为测试。

覆盖：参数解析（动作/服务/环境的合法与非法组合）、status 的前后台语义、
重复启动检查对「陈旧 pid 文件 / 进程存活 / PID 被其他进程复用」的区分，
以及 prod 生产包校验对 editable / 源码树安装的拒绝。
"""

import os
import shutil
import subprocess
import sys
import textwrap

import pytest

pytestmark = pytest.mark.skipif(shutil.which("bash") is None, reason="需要 bash")


def run_setup(repo_root, *args):
    """执行 scripts/setup.sh 并返回 CompletedProcess。"""
    return subprocess.run(
        [str(repo_root / "scripts" / "setup.sh"), *args],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=False,
    )


def run_lib(repo_root, body: str, env: dict | None = None):
    """在 source 了 funcron-common.sh 的 bash 里执行 `body`。"""
    script = f'source "{repo_root / "scripts" / "lib" / "funcron-common.sh"}"\n{textwrap.dedent(body)}'
    full_env = dict(os.environ)
    if env:
        full_env.update(env)
    return subprocess.run(
        ["bash", "-c", script], capture_output=True, text=True, cwd=repo_root, check=False, env=full_env
    )


# ---------------- setup.sh 参数解析 ----------------


def test_setup_no_args_shows_usage(repo_root):
    result = run_setup(repo_root)
    assert result.returncode == 1
    assert "用法" in result.stderr


def test_setup_rejects_unknown_action(repo_root):
    result = run_setup(repo_root, "launch", "server", "dev")
    assert result.returncode == 1
    assert "未知动作" in result.stderr


def test_setup_rejects_unknown_service(repo_root):
    result = run_setup(repo_root, "status", "no-such-service", "dev")
    assert result.returncode == 1
    assert "未知服务" in result.stderr


def test_setup_rejects_unknown_env(repo_root):
    result = run_setup(repo_root, "start", "server", "staging")
    assert result.returncode == 1
    assert "dev" in result.stderr and "prod" in result.stderr


def test_setup_start_requires_env(repo_root):
    """start/stop/restart/run 必须显式带环境参数，不允许省略。"""
    result = run_setup(repo_root, "start", "server")
    assert result.returncode == 1
    assert "必须指定环境" in result.stderr


def test_setup_run_rejects_all(repo_root):
    result = run_setup(repo_root, "run", "all", "dev")
    assert result.returncode == 1
    assert "不支持 all" in result.stderr


# ---------------- status 行为（README 示例必须真的能跑） ----------------


def test_setup_status_all_without_env_reports_both_envs(repo_root):
    """README 里的 `scripts/setup.sh status all` 必须成功，并覆盖 dev 与 prod。"""
    result = run_setup(repo_root, "status", "all")
    assert result.returncode == 0, result.stderr
    for env_name in ("dev", "prod"):
        assert f"funcron-server-{env_name}" in result.stdout
        assert f"funcron-coin-{env_name}" in result.stdout
        for role in ("webserver", "scheduler", "worker", "flower"):
            assert f"funcron-airflow-{role}-{env_name}" in result.stdout


def test_setup_status_single_service_single_env(repo_root):
    result = run_setup(repo_root, "status", "server", "dev")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "funcron-server-dev: stopped"


# ---------------- 重复启动检查：三种状态必须区分开 ----------------


def test_service_state_missing(repo_root, tmp_path):
    result = run_lib(
        repo_root,
        f'funcron_service_state "{tmp_path}/x.pid" "{tmp_path}/x.meta" sleep',
    )
    assert result.stdout.strip() == "missing"


def test_service_state_running_for_recorded_process(repo_root, tmp_path):
    result = run_lib(
        repo_root,
        f"""
        sleep 30 & pid=$!
        funcron_record_process "{tmp_path}/x.pid" "{tmp_path}/x.meta" "$pid" "sleep 30"
        funcron_service_state "{tmp_path}/x.pid" "{tmp_path}/x.meta" "sleep 30"
        kill "$pid" 2>/dev/null
        """,
    )
    assert result.stdout.strip() == "running"


def test_service_state_stale_when_process_gone(repo_root, tmp_path):
    result = run_lib(
        repo_root,
        f"""
        sleep 30 & pid=$!
        funcron_record_process "{tmp_path}/x.pid" "{tmp_path}/x.meta" "$pid" "sleep 30"
        kill "$pid"; wait "$pid" 2>/dev/null
        funcron_service_state "{tmp_path}/x.pid" "{tmp_path}/x.meta" "sleep 30"
        """,
    )
    assert result.stdout.strip() == "stale"


def test_service_state_invalid_pid_file(repo_root, tmp_path):
    result = run_lib(
        repo_root,
        f"""
        echo "not-a-pid" > "{tmp_path}/x.pid"
        : > "{tmp_path}/x.meta"
        funcron_service_state "{tmp_path}/x.pid" "{tmp_path}/x.meta" sleep
        """,
    )
    assert result.stdout.strip() == "invalid"


def test_service_state_mismatch_when_pid_reused_by_other_command(repo_root, tmp_path):
    """PID 存活但命令特征不符（模拟 PID 被别的进程复用）→ mismatch，不能当成本服务。"""
    result = run_lib(
        repo_root,
        f"""
        sleep 30 & pid=$!
        funcron_record_process "{tmp_path}/x.pid" "{tmp_path}/x.meta" "$pid" "sleep 30"
        printf 'identity=%s\\nstarttime=%s\\n' "nginx: worker process" \\
            "$(funcron_proc_starttime "$pid")" > "{tmp_path}/x.meta"
        funcron_service_state "{tmp_path}/x.pid" "{tmp_path}/x.meta" "nginx: worker process"
        kill "$pid" 2>/dev/null
        """,
    )
    assert result.stdout.strip() == "mismatch"


def test_service_state_mismatch_when_starttime_differs(repo_root, tmp_path):
    """命令特征相同但进程启动时刻不符 → 同样判为 PID 复用。"""
    result = run_lib(
        repo_root,
        f"""
        sleep 30 & pid=$!
        printf 'identity=%s\\nstarttime=%s\\n' "sleep 30" "1" > "{tmp_path}/x.meta"
        echo "$pid" > "{tmp_path}/x.pid"
        funcron_service_state "{tmp_path}/x.pid" "{tmp_path}/x.meta" "sleep 30"
        kill "$pid" 2>/dev/null
        """,
    )
    assert result.stdout.strip() == "mismatch"


def test_service_state_mismatch_without_meta_file(repo_root, tmp_path):
    """只有 pid 文件、没有身份记录时不能贸然认领该进程（旧版脚本的遗留 pid 文件）。"""
    result = run_lib(
        repo_root,
        f"""
        sleep 30 & pid=$!
        echo "$pid" > "{tmp_path}/x.pid"
        funcron_service_state "{tmp_path}/x.pid" "{tmp_path}/x.meta" "sleep 30"
        kill "$pid" 2>/dev/null
        """,
    )
    assert result.stdout.strip() == "mismatch"


def test_clear_stale_refuses_on_mismatch(repo_root, tmp_path):
    """mismatch 时 funcron_clear_stale 必须返回非 0，由调用方中止操作，且不删 pid 文件。"""
    result = run_lib(
        repo_root,
        f"""
        echo 12345 > "{tmp_path}/x.pid"
        if funcron_clear_stale demo mismatch "{tmp_path}/x.pid" "{tmp_path}/x.meta"; then
          echo RC=0
        else
          echo RC=1
        fi
        test -f "{tmp_path}/x.pid" && echo PID_FILE_KEPT
        """,
    )
    assert "RC=1" in result.stdout
    assert "PID_FILE_KEPT" in result.stdout


def test_clear_stale_removes_stale_files(repo_root, tmp_path):
    result = run_lib(
        repo_root,
        f"""
        echo 12345 > "{tmp_path}/x.pid"
        : > "{tmp_path}/x.meta"
        funcron_clear_stale demo stale "{tmp_path}/x.pid" "{tmp_path}/x.meta" && echo RC=0
        test -f "{tmp_path}/x.pid" || echo PID_FILE_REMOVED
        """,
    )
    assert "RC=0" in result.stdout
    assert "PID_FILE_REMOVED" in result.stdout


# ---------------- prod 生产包校验 ----------------


def test_require_installed_package_accepts_real_site_packages_install(repo_root, tmp_path):
    """已正常安装（落在 site-packages）的包应通过校验。"""
    result = run_lib(
        repo_root,
        f'funcron_require_installed_package pytest "{tmp_path}/run" && echo OK',
    )
    assert "OK" in result.stdout, result.stderr


def test_require_installed_package_rejects_missing_package(repo_root, tmp_path):
    result = run_lib(
        repo_root,
        f"""
        if funcron_require_installed_package definitely_not_installed_pkg "{tmp_path}/run"; then
          echo RC=0
        else
          echo RC=1
        fi
        """,
    )
    assert "RC=1" in result.stdout


def _make_fake_pkg(parent, name="fake_src_pkg"):
    pkg_dir = parent / name
    pkg_dir.mkdir(parents=True, exist_ok=True)
    (pkg_dir / "__init__.py").write_text("")
    return pkg_dir


def test_require_installed_package_rejects_source_tree_on_pythonpath(repo_root, tmp_path):
    """PYTHONPATH 指向源码树时必须被拒绝——这正是旧版 `python3 -c "import X"` 会漏掉的情况。"""
    srctree = tmp_path / "srctree"
    _make_fake_pkg(srctree)

    # 前置条件：不清 PYTHONPATH 的朴素校验确实会「通过」，否则这条测试就是空跑。
    probe = subprocess.run(
        [sys.executable, "-c", "import fake_src_pkg; print(fake_src_pkg.__file__)"],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(srctree)},
        check=False,
    )
    assert probe.returncode == 0, "前置条件不成立：源码树里的包本应可被朴素 import 命中"

    result = run_lib(
        repo_root,
        f"""
        if funcron_require_installed_package fake_src_pkg "{tmp_path}/run"; then
          echo RC=0
        else
          echo RC=1
        fi
        """,
        env={"PYTHONPATH": str(srctree)},
    )
    assert "RC=1" in result.stdout, result.stderr


def test_require_installed_package_rejects_package_in_cwd(repo_root, tmp_path):
    """校验目录里恰好有同名源码包时也必须被拒绝（CWD 不得进 sys.path）。"""
    run_dir = tmp_path / "run"
    _make_fake_pkg(run_dir, "fake_cwd_pkg")

    # 前置条件：在该目录下朴素 import 确实能命中这个源码包。
    probe = subprocess.run(
        [sys.executable, "-c", "import fake_cwd_pkg; print(fake_cwd_pkg.__file__)"],
        capture_output=True,
        text=True,
        cwd=run_dir,
        check=False,
    )
    assert probe.returncode == 0, "前置条件不成立：CWD 里的包本应可被朴素 import 命中"

    result = run_lib(
        repo_root,
        f"""
        if funcron_require_installed_package fake_cwd_pkg "{run_dir}"; then
          echo RC=0
        else
          echo RC=1
        fi
        """,
    )
    assert "RC=1" in result.stdout, result.stderr


def test_installed_package_file_resolves_inside_installed_package(repo_root, tmp_path):
    """prod 用的配置文件路径必须从已安装包里解析出来，而不是仓库源码目录。"""
    result = run_lib(
        repo_root,
        f'funcron_installed_package_file pytest "{tmp_path}/run" "__init__.py"',
    )
    assert result.returncode == 0, result.stderr
    resolved = result.stdout.strip()
    assert resolved.endswith("pytest/__init__.py")
    assert "site-packages" in resolved or "dist-packages" in resolved
    # 注意不能断言 "repo_root 不在路径里"：.venv 本身就在仓库目录下。
    # 真正要排除的是仓库源码树 src/。
    assert not resolved.startswith(f"{repo_root}/src/")
