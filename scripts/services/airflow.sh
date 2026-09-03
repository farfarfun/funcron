#!/usr/bin/env bash
# Airflow 各角色服务（webserver / scheduler / worker / flower）：
# 端口/AIRFLOW_HOME、运行时文件与启停逻辑。
# 由 scripts/setup.sh 统一调度，不要直接执行本脚本管理生命周期。
#
# 用法: scripts/services/airflow.sh {start|stop|restart|status|run} <role> <dev|prod>
#   <role>: webserver | scheduler | worker | flower
#
# dev/prod 使用完全独立的 AIRFLOW_HOME 与端口：
#   prod 对应长期部署机器上已初始化好的 AIRFLOW_HOME（默认 $HOME/airflow）；
#   dev  使用仓库内 .run/airflow-dev-home，方便本地调试而不影响 prod 数据。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
# shellcheck source=../lib/funcron-common.sh
source "$SCRIPT_DIR/../lib/funcron-common.sh"

RUN_DIR="$ROOT_DIR/.run"
LOG_DIR="$ROOT_DIR/.run/logs"
mkdir -p "$RUN_DIR" "$LOG_DIR"

# ---- 配置块：dev/prod 各自的 AIRFLOW_HOME 与端口 ----
AIRFLOW_HOME_PROD="${AIRFLOW_HOME_PROD:-$HOME/airflow}"
AIRFLOW_HOME_DEV="${AIRFLOW_HOME_DEV:-$ROOT_DIR/.run/airflow-dev-home}"
WEBSERVER_PORT_PROD=8061
WEBSERVER_PORT_DEV=18061
FLOWER_PORT_PROD=8062
FLOWER_PORT_DEV=18062

ACTION="${1:-}"
ROLE="${2:-}"
ENV_NAME="${3:-}"

usage() {
  echo "用法: $0 {start|stop|restart|status|run} <webserver|scheduler|worker|flower> <dev|prod>" >&2
  exit 1
}

[[ -n "$ACTION" ]] || usage
case "$ROLE" in
  webserver | scheduler | worker | flower) ;;
  *)
    echo "错误: 未知 role: ${ROLE}" >&2
    usage
    ;;
esac
case "$ENV_NAME" in
  dev | prod) ;;
  *)
    echo "错误: 必须指定环境 dev 或 prod" >&2
    usage
    ;;
esac

if [[ "$ENV_NAME" == "prod" ]]; then
  export AIRFLOW_HOME="$AIRFLOW_HOME_PROD"
  WEBSERVER_PORT="$WEBSERVER_PORT_PROD"
  FLOWER_PORT="$FLOWER_PORT_PROD"
else
  export AIRFLOW_HOME="$AIRFLOW_HOME_DEV"
  WEBSERVER_PORT="$WEBSERVER_PORT_DEV"
  FLOWER_PORT="$FLOWER_PORT_DEV"
  mkdir -p "$AIRFLOW_HOME"
fi

NAME="funcron-airflow-${ROLE}-${ENV_NAME}"
PID_FILE="$(funcron_pid_file "$RUN_DIR" "$NAME")"
LOG_FILE="$(funcron_log_file "$LOG_DIR" "$NAME")"

cmd=()
service_cmd() {
  case "$ROLE" in
    webserver) cmd=(airflow webserver -p "$WEBSERVER_PORT") ;;
    scheduler) cmd=(airflow scheduler) ;;
    worker) cmd=(airflow celery worker) ;;
    flower) cmd=(airflow celery flower -p "$FLOWER_PORT") ;;
  esac
}

do_start() {
  service_cmd
  if funcron_is_running "$PID_FILE"; then
    echo "${NAME} 已在运行 (pid $(cat "$PID_FILE"))"
    return 0
  fi
  echo "启动 ${NAME} (AIRFLOW_HOME=${AIRFLOW_HOME}) ..."
  nohup "${cmd[@]}" >>"$LOG_FILE" 2>&1 &
  echo $! >"$PID_FILE"
  disown
  echo "${NAME} 已启动 (pid $(cat "$PID_FILE"), 日志 $LOG_FILE)"
}

do_run() {
  service_cmd
  echo "前台运行 ${NAME} (AIRFLOW_HOME=${AIRFLOW_HOME}) ..."
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
