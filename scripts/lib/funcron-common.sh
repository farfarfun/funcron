#!/usr/bin/env bash
# funcron 各服务脚本共享的 PID / 日志 / 生产包校验工具函数。
# 只提供函数定义，由 scripts/services/*.sh 通过 source 加载，不单独执行。

# 用法: funcron_pid_file <run_dir> <name>
funcron_pid_file() {
  printf '%s/%s.pid' "$1" "$2"
}

# 用法: funcron_meta_file <run_dir> <name>
# 与 pid 文件配套的进程身份文件，记录「进程启动时刻 + 命令特征串」，
# 用来区分「PID 被其他进程复用」和「确实是我们托管的那个进程」。
funcron_meta_file() {
  printf '%s/%s.meta' "$1" "$2"
}

# 用法: funcron_log_file <log_dir> <name>
funcron_log_file() {
  printf '%s/%s-%s.log' "$1" "$2" "$(date +%Y-%m-%d)"
}

# 用法: funcron_proc_starttime <pid>
# 输出进程启动时刻（Linux 取 /proc/<pid>/stat 的 starttime 字段，其他平台回落到 ps lstart）。
# 进程不存在时输出空串。
funcron_proc_starttime() {
  local pid="$1"
  if [[ -r "/proc/${pid}/stat" ]]; then
    # 第 2 字段 comm 可能含空格和括号，先截掉到最后一个 ')' 为止，
    # 剩下部分从 state 开始，starttime 是 stat 的第 22 字段 = 剩余部分的第 20 字段。
    sed 's/^.*) //' "/proc/${pid}/stat" 2>/dev/null | awk '{print $20}'
    return 0
  fi
  ps -o lstart= -p "$pid" 2>/dev/null | tr -s ' '
}

# 用法: funcron_proc_cmdline <pid>
# 输出进程命令行（Linux 用 /proc/<pid>/cmdline，NUL 换成空格；否则用 ps -o args=）。
funcron_proc_cmdline() {
  local pid="$1"
  if [[ -r "/proc/${pid}/cmdline" ]]; then
    tr '\0' ' ' <"/proc/${pid}/cmdline" 2>/dev/null
    return 0
  fi
  ps -o args= -p "$pid" 2>/dev/null
}

# 用法: funcron_record_process <pid_file> <meta_file> <pid> <identity>
# 记录 PID 以及用于后续校验的身份信息（命令特征串 + 启动时刻）。
funcron_record_process() {
  local pid_file="$1" meta_file="$2" pid="$3" identity="$4"
  printf '%s\n' "$pid" >"$pid_file"
  {
    printf 'identity=%s\n' "$identity"
    printf 'starttime=%s\n' "$(funcron_proc_starttime "$pid")"
  } >"$meta_file"
}

# 用法: funcron_service_state <pid_file> <meta_file> <identity>
# 输出下列状态之一，供调用方区别处理：
#   missing   —— 没有 pid 文件，服务未启动
#   invalid   —— pid 文件内容不是合法 PID
#   stale     —— pid 文件存在但进程已退出（陈旧 pid 文件）
#   mismatch  —— PID 存活但身份校验不通过，说明该 PID 已被别的进程复用
#   running   —— PID 存活，且启动时刻与命令特征串都与记录一致（确认是本服务）
funcron_service_state() {
  local pid_file="$1" meta_file="$2" identity="$3"
  if [[ ! -f "$pid_file" ]]; then
    echo missing
    return 0
  fi

  local pid
  pid="$(tr -d '[:space:]' <"$pid_file")"
  if [[ ! "$pid" =~ ^[1-9][0-9]*$ ]]; then
    echo invalid
    return 0
  fi

  if ! kill -0 "$pid" 2>/dev/null; then
    echo stale
    return 0
  fi

  # 没有 meta 文件（例如旧版脚本留下的 pid 文件）时无法确认身份，按 mismatch 处理：
  # 宁可报错让人工确认，也不要贸然把一个未知进程当成本服务去 kill。
  if [[ ! -f "$meta_file" ]]; then
    echo mismatch
    return 0
  fi

  local recorded_identity="" recorded_starttime=""
  while IFS='=' read -r key value; do
    case "$key" in
      identity) recorded_identity="$value" ;;
      starttime) recorded_starttime="$value" ;;
    esac
  done <"$meta_file"

  local now_starttime
  now_starttime="$(funcron_proc_starttime "$pid")"
  if [[ -z "$recorded_starttime" || "$recorded_starttime" != "$now_starttime" ]]; then
    echo mismatch
    return 0
  fi

  local token="${recorded_identity:-$identity}"
  if [[ -n "$token" ]]; then
    local cmdline
    cmdline="$(funcron_proc_cmdline "$pid")"
    if [[ "$cmdline" != *"$token"* ]]; then
      echo mismatch
      return 0
    fi
  fi

  echo running
}

# 用法: funcron_is_running <pid_file> <meta_file> <identity>
# 仅当状态为 running（身份校验通过）时返回 0。
funcron_is_running() {
  [[ "$(funcron_service_state "$1" "$2" "$3")" == "running" ]]
}

# 用法: funcron_clear_stale <name> <state> <pid_file> <meta_file>
# stale/invalid 清掉残留文件并提示；mismatch 时报错返回 1，由调用方中止操作。
funcron_clear_stale() {
  local name="$1" state="$2" pid_file="$3" meta_file="$4"
  case "$state" in
    stale)
      echo "提示: ${name} 的 pid 文件是陈旧残留（进程已退出），已清理 ${pid_file}" >&2
      rm -f "$pid_file" "$meta_file"
      ;;
    invalid)
      echo "提示: ${name} 的 pid 文件内容不是合法 PID，已清理 ${pid_file}" >&2
      rm -f "$pid_file" "$meta_file"
      ;;
    mismatch)
      echo "错误: ${name} 的 pid 文件记录的 PID $(cat "$pid_file" 2>/dev/null) 当前属于另一个进程" >&2
      echo "      （启动时刻/命令特征校验不通过），拒绝把它当作本服务操作。" >&2
      echo "      确认无误后手工删除 ${pid_file} 与 ${meta_file} 再重试。" >&2
      return 1
      ;;
  esac
  return 0
}

funcron_installed_version() {
  python3 -I - "$1" <<'PYVERSION' 2>/dev/null || printf '未安装\n'
import importlib.metadata
import sys

print(importlib.metadata.version(sys.argv[1]))
PYVERSION
}

# 用法: funcron_require_installed_package <import_name> <safe_cwd>
# 启动前确认 <import_name> 解析到的是已安装包，而不是仓库源码树。
#
# 为什么不能只用 `python3 -c "import X"`：
#   1) 从仓库根目录运行时 CWD 在 sys.path 里，裸 import 可能命中工作树里的源码目录；
#   2) `uv sync` 装的是 editable 包，.pth 指回源码，import 同样"永远成功"。
# 所以这里三道一起上：清空 PYTHONPATH、用 `python3 -I`（隔离模式，CWD 与 user site 都不进
# sys.path）、切到一个不含 Python 模块的目录（.run/），最后断言模块文件落在
# site-packages / dist-packages 下；editable 安装（.pth 指回源码）会被判为不合格。
# 注意不要用 `cd /` 跑校验：farlog 会在当前目录建相对 logs/，在 / 下会 PermissionError。
funcron_require_installed_package() {
  local import_name="$1" safe_cwd="$2"
  mkdir -p "$safe_cwd"
  if ! (
    cd "$safe_cwd" || exit 1
    PYTHONPATH="" python3 -I - "$import_name" <<'PYCHECK'
import importlib
import sys
from pathlib import Path

name = sys.argv[1]
try:
    module = importlib.import_module(name)
except Exception as exc:
    print(f"import {name} 失败: {exc.__class__.__name__}: {exc}", file=sys.stderr)
    raise SystemExit(1) from None

origin = getattr(module, "__file__", None)
if origin is None:
    print(f"{name} 没有 __file__，无法确认安装来源", file=sys.stderr)
    raise SystemExit(1)

resolved = Path(origin).resolve()
if not any(part in ("site-packages", "dist-packages") for part in resolved.parts):
    print(f"{name} 解析到 {resolved}，不在 site-packages/dist-packages 下", file=sys.stderr)
    print("（典型原因：editable 安装，或直接从源码工作树导入）", file=sys.stderr)
    raise SystemExit(1)
print(resolved)
PYCHECK
  ); then
    echo "错误: 要求运行已安装的 ${import_name} 包，当前校验未通过。" >&2
    echo "      请先执行 install-dev 或 install-prod，不要使用 editable 安装。" >&2
    return 1
  fi
  return 0
}

# 用法: funcron_installed_package_file <import_name> <safe_cwd> <relative_path>
# 输出已安装包内某个文件的绝对路径（例如 prod 下 gunicorn 要用的 config.py），
# 保证 prod 引用的是安装包里的文件而不是仓库源码。校验失败返回非 0。
funcron_installed_package_file() {
  local import_name="$1" safe_cwd="$2" rel="$3"
  mkdir -p "$safe_cwd"
  (
    cd "$safe_cwd" || exit 1
    PYTHONPATH="" python3 -I - "$import_name" "$rel" <<'PYPATH'
import importlib
import sys
from pathlib import Path

name, rel = sys.argv[1], sys.argv[2]
module = importlib.import_module(name)
origin = getattr(module, "__file__", None)
if origin is None:
    raise SystemExit(1)
resolved = Path(origin).resolve().parent / rel
if not resolved.is_file():
    print(f"{resolved} 不存在", file=sys.stderr)
    raise SystemExit(1)
print(resolved)
PYPATH
  )
}

# 用法: funcron_installed_package_dir <import_name> <safe_cwd> <relative_path>
# 与 funcron_installed_package_file 同样的隔离解析方式，但要求目标是**目录**
# （例如 prod 下 Airflow 要用的 dags/ 目录）。目录不存在时返回非 0。
funcron_installed_package_dir() {
  local import_name="$1" safe_cwd="$2" rel="$3"
  mkdir -p "$safe_cwd"
  (
    cd "$safe_cwd" || exit 1
    PYTHONPATH="" python3 -I - "$import_name" "$rel" <<'PYDIR'
import importlib
import sys
from pathlib import Path

name, rel = sys.argv[1], sys.argv[2]
module = importlib.import_module(name)
origin = getattr(module, "__file__", None)
if origin is None:
    raise SystemExit(1)
resolved = Path(origin).resolve().parent / rel
if not resolved.is_dir():
    print(f"{resolved} 不是目录或不存在", file=sys.stderr)
    raise SystemExit(1)
print(resolved)
PYDIR
  )
}
