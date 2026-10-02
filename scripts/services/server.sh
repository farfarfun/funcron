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

# ---- 配置块：dev/prod 各自的端口 ----
SERVER_PORT_PROD=8445
SERVER_PORT_DEV=18445

WSGI_APP="funcron.server.funcron_server:app"

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
else
  SERVER_PORT="$SERVER_PORT_DEV"
fi

NAME="funcron-server-${ENV_NAME}"
PID_FILE="$(funcron_pid_file "$RUN_DIR" "$NAME")"
META_FILE="$(funcron_meta_file "$RUN_DIR" "$NAME")"
LOG_FILE="$(funcron_log_file "$LOG_DIR" "$NAME")"
# gunicorn 会用 setproctitle 把进程名改写成 "gunicorn: master [<wsgi app>]"，
# 其中仍然包含 WSGI 入口字符串，所以用它作为进程身份特征串。
IDENTITY="$WSGI_APP"

cmd=()
# 构造实际执行命令。prod 下先硬校验「funcron 是已安装的正式包」，
# gunicorn 配置文件也取自安装包内，不引用仓库源码目录。
# 校验下沉到这里（而不是脚本顶层），保证 start 和 run 两条路径都会走到。
command_for() {
  if [[ "$ENV_NAME" == "prod" ]]; then
    funcron_require_installed_package funcron "$RUN_DIR"
    local gunicorn_conf
    gunicorn_conf="$(funcron_installed_package_file funcron "$RUN_DIR" "server/config.py")"
    cmd=(gunicorn -c "$gunicorn_conf" -b "0.0.0.0:${SERVER_PORT}" "$WSGI_APP")
  else
    cmd=(gunicorn -c "$ROOT_DIR/src/funcron/server/config.py" -b "0.0.0.0:${SERVER_PORT}" "$WSGI_APP")
  fi
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
  echo "启动 ${NAME} (port ${SERVER_PORT}) ..."
  nohup "${cmd[@]}" >>"$LOG_FILE" 2>&1 &
  local pid=$!
  funcron_record_process "$PID_FILE" "$META_FILE" "$pid" "$IDENTITY"
  disown
  echo "${NAME} 已启动 (pid ${pid}, 日志 $LOG_FILE)"
}

do_run() {
  command_for
  echo "前台运行 ${NAME} (port ${SERVER_PORT}) ..."
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
  local state
  state="$(funcron_service_state "$PID_FILE" "$META_FILE" "$IDENTITY")"
  case "$state" in
    running) echo "${NAME}: running (pid $(cat "$PID_FILE"), port ${SERVER_PORT})" ;;
    missing) echo "${NAME}: stopped" ;;
    stale | invalid) echo "${NAME}: stopped (存在陈旧 pid 文件 ${PID_FILE})" ;;
    mismatch) echo "${NAME}: unknown (pid 文件记录的 PID 已属于其他进程，见 ${PID_FILE})" ;;
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
