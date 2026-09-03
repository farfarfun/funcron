#!/usr/bin/env bash
# funcron 自身的 Flask 管理后台（gunicorn + gevent worker）。
# 由 scripts/setup.sh 统一调度，不要直接执行本脚本管理生命周期。
#
# 用法: scripts/services/server.sh {start|stop|restart|status|run} <dev|prod>
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
# shellcheck source=../lib/funcron-common.sh
source "$SCRIPT_DIR/../lib/funcron-common.sh"

RUN_DIR="$ROOT_DIR/.run"
LOG_DIR="$ROOT_DIR/.run/logs"
mkdir -p "$RUN_DIR" "$LOG_DIR"

SERVER_DIR="$ROOT_DIR/funcron/server"

# ---- 配置块：dev/prod 各自的端口 ----
SERVER_PORT_PROD=8445
SERVER_PORT_DEV=18445

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

if [[ "$ENV_NAME" == "prod" ]]; then
  SERVER_PORT="$SERVER_PORT_PROD"
  # prod 必须运行已安装的生产包，不能回退到本地源码：这里用「能否 import」
  # 作为已安装的判定，import 失败直接硬失败，不做任何兜底。
  if ! python3 -c "import funcron" >/dev/null 2>&1; then
    echo "错误: 未检测到已安装的 funcron 生产包（import funcron 失败），请先 pip install/uv sync 安装后再启动 prod" >&2
    exit 1
  fi
else
  SERVER_PORT="$SERVER_PORT_DEV"
fi

NAME="funcron-server-${ENV_NAME}"
PID_FILE="$(funcron_pid_file "$RUN_DIR" "$NAME")"
LOG_FILE="$(funcron_log_file "$LOG_DIR" "$NAME")"

# 用完整模块路径（而不是 cd 到源码目录）调用，这样 prod 下实际执行的是
# 已安装包里的 funcron.server 模块，不依赖仓库源码所在位置。
cmd=(gunicorn -c "$SERVER_DIR/config.py" -b "0.0.0.0:${SERVER_PORT}" funcron.server.funcron_server:app)

do_start() {
  if funcron_is_running "$PID_FILE"; then
    echo "${NAME} 已在运行 (pid $(cat "$PID_FILE"))"
    return 0
  fi
  echo "启动 ${NAME} (port ${SERVER_PORT}) ..."
  nohup "${cmd[@]}" >>"$LOG_FILE" 2>&1 &
  echo $! >"$PID_FILE"
  disown
  echo "${NAME} 已启动 (pid $(cat "$PID_FILE"), 日志 $LOG_FILE)"
}

do_run() {
  echo "前台运行 ${NAME} (port ${SERVER_PORT}) ..."
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
    echo "${NAME}: running (pid $(cat "$PID_FILE"), port ${SERVER_PORT})"
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
