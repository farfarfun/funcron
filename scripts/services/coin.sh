#!/usr/bin/env bash
# funcoin 行情下载任务（长期运行的下载循环，作为后台服务托管）。
# 由 scripts/setup.sh 统一调度，不要直接执行本脚本管理生命周期。
#
# 用法: scripts/services/coin.sh {start|stop|restart|status|run} <dev|prod>
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
# shellcheck source=../lib/funcron-common.sh
source "$SCRIPT_DIR/../lib/funcron-common.sh"

RUN_DIR="$ROOT_DIR/.run"
LOG_DIR="$ROOT_DIR/.run/logs"
mkdir -p "$RUN_DIR" "$LOG_DIR"

ACTION="${1:-}"
ENV_NAME="${2:-}"

usage() {
  echo "用法: $0 {start|stop|restart|status|run} <dev|prod>" >&2
  exit 1
}

[[ -n "$ACTION" ]] || usage
case "$ENV_NAME" in
  dev | prod) ;;
  *)
    echo "错误: 必须指定环境 dev 或 prod" >&2
    usage
    ;;
esac

if [[ "$ENV_NAME" == "prod" ]] && ! command -v funcoin >/dev/null 2>&1; then
  echo "错误: 未检测到已安装的 funcoin 生产包（command -v funcoin 失败），请先安装后再启动 prod" >&2
  exit 1
fi

NAME="funcron-coin-${ENV_NAME}"
PID_FILE="$(funcron_pid_file "$RUN_DIR" "$NAME")"
LOG_FILE="$(funcron_log_file "$LOG_DIR" "$NAME")"

cmd=(funcoin download)

do_start() {
  if funcron_is_running "$PID_FILE"; then
    echo "${NAME} 已在运行 (pid $(cat "$PID_FILE"))"
    return 0
  fi
  echo "启动 ${NAME} ..."
  nohup "${cmd[@]}" >>"$LOG_FILE" 2>&1 &
  echo $! >"$PID_FILE"
  disown
  echo "${NAME} 已启动 (pid $(cat "$PID_FILE"), 日志 $LOG_FILE)"
}

do_run() {
  echo "前台运行 ${NAME} ..."
  exec "${cmd[@]}"
}

do_stop() {
  if funcron_is_running "$PID_FILE"; then
    kill "$(cat "$PID_FILE")"
    rm -f "$PID_FILE"
    echo "${NAME} 已停止"
  else
    echo "${NAME} 未在运行"
    rm -f "$PID_FILE"
  fi
}

do_status() {
  if funcron_is_running "$PID_FILE"; then
    echo "${NAME}: running (pid $(cat "$PID_FILE"))"
  else
    echo "${NAME}: stopped"
  fi
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
