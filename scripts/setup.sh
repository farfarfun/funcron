#!/usr/bin/env bash
# 统一管理本仓库里的长期运行服务：
# funcron 自身的 Flask 管理后台（server）、Airflow 四个角色
# （webserver/scheduler/worker/flower）、funcoin 行情下载任务（coin）。
# 本脚本只做参数解析与分发；各服务的端口、运行时文件、启停逻辑见
# scripts/services/*.sh。
#
# 用法: scripts/setup.sh {start|stop|restart|run} <service> <dev|prod>
#       scripts/setup.sh status <service> [dev|prod]
#   <service>: server | airflow-webserver | airflow-scheduler | airflow-worker
#              | airflow-flower | coin | all
#
# start/stop/restart/status 管理后台进程（pid/日志统一放 .run/，按「服务名-环境」区分）；
# run 是前台阻塞运行，方便调试单个服务，不支持 all。
# status 的环境参数可省略：省略时依次报告 dev 和 prod 两个环境的状态。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

ACTION="${1:-}"
SERVICE="${2:-}"
ENV_NAME="${3:-}"
ALL_SERVICES="server airflow-webserver airflow-scheduler airflow-worker airflow-flower coin"
ALL_ENVS="dev prod"

usage() {
  echo "用法: $0 {start|stop|restart|run} <service> <dev|prod>" >&2
  echo "      $0 status <service> [dev|prod]" >&2
  echo "  <service>: ${ALL_SERVICES// /|}|all" >&2
  exit 1
}

[[ -n "$ACTION" && -n "$SERVICE" ]] || usage
case "$ACTION" in
  start | stop | restart | run | status) ;;
  *)
    echo "错误: 未知动作: ${ACTION}" >&2
    usage
    ;;
esac

if [[ -z "$ENV_NAME" ]]; then
  # 只有 status 允许省略环境：省略时报告所有环境，其余动作必须显式指定。
  if [[ "$ACTION" != "status" ]]; then
    echo "错误: ${ACTION} 必须指定环境 dev 或 prod" >&2
    usage
  fi
  ENVS="$ALL_ENVS"
else
  case "$ENV_NAME" in
    dev | prod) ENVS="$ENV_NAME" ;;
    *)
      echo "错误: 必须指定环境 dev 或 prod" >&2
      usage
      ;;
  esac
fi

if [[ "$SERVICE" == "all" ]]; then
  SERVICES="$ALL_SERVICES"
  if [[ "$ACTION" == "run" ]]; then
    echo "run 模式只能指定单个服务，不支持 all" >&2
    exit 1
  fi
else
  case " $ALL_SERVICES " in
    *" $SERVICE "*) SERVICES="$SERVICE" ;;
    *)
      echo "未知服务: $SERVICE" >&2
      usage
      ;;
  esac
fi

dispatch_one() {
  local svc="$1" env_name="$2"
  case "$svc" in
    server) "$SCRIPT_DIR/services/server.sh" "$ACTION" "$env_name" ;;
    airflow-webserver) "$SCRIPT_DIR/services/airflow.sh" "$ACTION" webserver "$env_name" ;;
    airflow-scheduler) "$SCRIPT_DIR/services/airflow.sh" "$ACTION" scheduler "$env_name" ;;
    airflow-worker) "$SCRIPT_DIR/services/airflow.sh" "$ACTION" worker "$env_name" ;;
    airflow-flower) "$SCRIPT_DIR/services/airflow.sh" "$ACTION" flower "$env_name" ;;
    coin) "$SCRIPT_DIR/services/coin.sh" "$ACTION" "$env_name" ;;
  esac
}

# run 直接 exec，保持前台语义（信号与退出码都原样透传给调用方）。
if [[ "$ACTION" == "run" ]]; then
  case "$SERVICES" in
    server) exec "$SCRIPT_DIR/services/server.sh" run "$ENVS" ;;
    airflow-webserver) exec "$SCRIPT_DIR/services/airflow.sh" run webserver "$ENVS" ;;
    airflow-scheduler) exec "$SCRIPT_DIR/services/airflow.sh" run scheduler "$ENVS" ;;
    airflow-worker) exec "$SCRIPT_DIR/services/airflow.sh" run worker "$ENVS" ;;
    airflow-flower) exec "$SCRIPT_DIR/services/airflow.sh" run flower "$ENVS" ;;
    coin) exec "$SCRIPT_DIR/services/coin.sh" run "$ENVS" ;;
  esac
fi

# 其余动作遍历「服务 × 环境」。单个服务失败不中断其余服务（否则 `status all`
# 会在第一个异常服务上整体退出，看不到后面的状态），最后用汇总退出码返回。
rc=0
for env_name in $ENVS; do
  for svc in $SERVICES; do
    dispatch_one "$svc" "$env_name" || rc=1
  done
done
exit "$rc"
