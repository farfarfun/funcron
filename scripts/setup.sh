#!/usr/bin/env bash
# 统一管理本仓库里的长期运行服务：
# funcron 自身的 Flask 管理后台（server）、Airflow 四个角色
# （webserver/scheduler/worker/flower）、funcoin 行情下载任务（coin）。
# 本脚本只做参数解析与分发；各服务的端口、运行时文件、启停逻辑见
# scripts/services/*.sh。
#
# 用法: scripts/setup.sh {start|stop|restart|status|run} <service> <dev|prod>
#   <service>: server | airflow-webserver | airflow-scheduler | airflow-worker
#              | airflow-flower | coin | all
#
# start/stop/restart/status 管理后台进程（pid/日志统一放 .run/，按「服务名-环境」区分）；
# run 是前台阻塞运行，方便调试单个服务，不支持 all。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

ACTION="${1:-}"
SERVICE="${2:-}"
ENV_NAME="${3:-}"
ALL_SERVICES="server airflow-webserver airflow-scheduler airflow-worker airflow-flower coin"

usage() {
  echo "用法: $0 {start|stop|restart|status|run} <service> <dev|prod>" >&2
  echo "  <service>: ${ALL_SERVICES// /|}|all" >&2
  exit 1
}

[[ -n "$ACTION" && -n "$SERVICE" && -n "$ENV_NAME" ]] || usage
case "$ENV_NAME" in
  dev | prod) ;;
  *)
    echo "错误: 必须指定环境 dev 或 prod" >&2
    usage
    ;;
esac

dispatch_one() {
  local svc="$1"
  case "$svc" in
    server) "$SCRIPT_DIR/services/server.sh" "$ACTION" "$ENV_NAME" ;;
    airflow-webserver) "$SCRIPT_DIR/services/airflow.sh" "$ACTION" webserver "$ENV_NAME" ;;
    airflow-scheduler) "$SCRIPT_DIR/services/airflow.sh" "$ACTION" scheduler "$ENV_NAME" ;;
    airflow-worker) "$SCRIPT_DIR/services/airflow.sh" "$ACTION" worker "$ENV_NAME" ;;
    airflow-flower) "$SCRIPT_DIR/services/airflow.sh" "$ACTION" flower "$ENV_NAME" ;;
    coin) "$SCRIPT_DIR/services/coin.sh" "$ACTION" "$ENV_NAME" ;;
    *)
      echo "未知服务: $svc" >&2
      exit 1
      ;;
  esac
}

if [[ "$SERVICE" == "all" ]]; then
  if [[ "$ACTION" == "run" ]]; then
    echo "run 模式只能指定单个服务，不支持 all" >&2
    exit 1
  fi
  for s in $ALL_SERVICES; do
    dispatch_one "$s"
  done
else
  case "$SERVICE" in
    server) exec "$SCRIPT_DIR/services/server.sh" "$ACTION" "$ENV_NAME" ;;
    airflow-webserver) exec "$SCRIPT_DIR/services/airflow.sh" "$ACTION" webserver "$ENV_NAME" ;;
    airflow-scheduler) exec "$SCRIPT_DIR/services/airflow.sh" "$ACTION" scheduler "$ENV_NAME" ;;
    airflow-worker) exec "$SCRIPT_DIR/services/airflow.sh" "$ACTION" worker "$ENV_NAME" ;;
    airflow-flower) exec "$SCRIPT_DIR/services/airflow.sh" "$ACTION" flower "$ENV_NAME" ;;
    coin) exec "$SCRIPT_DIR/services/coin.sh" "$ACTION" "$ENV_NAME" ;;
    *)
      echo "未知服务: $SERVICE" >&2
      usage
      ;;
  esac
fi
