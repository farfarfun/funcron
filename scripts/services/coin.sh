#!/usr/bin/env bash
# funcoin 行情下载任务（长期运行的下载循环，作为后台服务托管）。
# 由 scripts/setup.sh 统一调度，不要直接执行本脚本管理生命周期。
#
# 用法: scripts/services/coin.sh {start|stop|restart|status|run}
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
# shellcheck source=../lib/funcron-common.sh
source "$SCRIPT_DIR/../lib/funcron-common.sh"

RUN_DIR="$ROOT_DIR/.run"
LOG_DIR="$ROOT_DIR/.run/logs"
mkdir -p "$RUN_DIR" "$LOG_DIR"

ACTION="${1:-}"

usage() {
  echo "用法: $0 {start|stop|restart|status|run}" >&2
  exit 1
}

[[ -n "$ACTION" && $# -eq 1 ]] || usage

NAME="funcron-coin"
PID_FILE="$(funcron_pid_file "$RUN_DIR" "$NAME")"
META_FILE="$(funcron_meta_file "$RUN_DIR" "$NAME")"
LOG_FILE="$(funcron_log_file "$LOG_DIR" "$NAME")"
IDENTITY="funcoin"

cmd=()
command_for() {
  funcron_require_installed_package funcoin "$RUN_DIR"
  cmd=(funcoin download)
}

do_start() {
  local state
  state="$(funcron_service_state "$PID_FILE" "$META_FILE" "$IDENTITY")"
  if [[ "$state" == "running" ]]; then
    echo "${NAME} 已在运行 (pid $(cat "$PID_FILE"))"
    return 0
  fi
  funcron_clear_stale "$NAME" "$state" "$PID_FILE" "$META_FILE"

  command_for
  echo "启动 ${NAME} ..."
  nohup "${cmd[@]}" >>"$LOG_FILE" 2>&1 &
  local pid=$!
  funcron_record_process "$PID_FILE" "$META_FILE" "$pid" "$IDENTITY"
  disown
  echo "${NAME} 已启动 (pid ${pid}, 日志 $LOG_FILE)"
}

do_run() {
  command_for
  echo "前台运行 ${NAME} ..."
  exec "${cmd[@]}"
}

do_stop() {
  local state
  state="$(funcron_service_state "$PID_FILE" "$META_FILE" "$IDENTITY")"
  case "$state" in
    running)
      kill "$(cat "$PID_FILE")"
      rm -f "$PID_FILE" "$META_FILE"
      echo "${NAME} 已停止"
      ;;
    missing)
      echo "${NAME} 未在运行"
      ;;
    *)
      funcron_clear_stale "$NAME" "$state" "$PID_FILE" "$META_FILE"
      echo "${NAME} 未在运行"
      ;;
  esac
}

do_status() {
  local state version
  state="$(funcron_service_state "$PID_FILE" "$META_FILE" "$IDENTITY")"
  version="$(funcron_installed_version funcoin)"
  case "$state" in
    running) echo "${NAME} ${version}: running (pid $(cat "$PID_FILE"))" ;;
    missing) echo "${NAME} ${version}: stopped" ;;
    stale | invalid) echo "${NAME} ${version}: stopped (存在陈旧 pid 文件 ${PID_FILE})" ;;
    mismatch) echo "${NAME} ${version}: unknown (pid 文件记录的 PID 已属于其他进程，见 ${PID_FILE})" ;;
  esac
}

case "$ACTION" in
  start) do_start ;;
  stop) do_stop ;;
  restart)
    do_stop
    do_start
    ;;
  status) do_status ;;
  run) do_run ;;
  *) usage ;;
esac
