#!/usr/bin/env bash
# funcron / Airflow / funcoin 长期服务的统一分发入口。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ACTION="${1:-}"
TARGET="${2:-}"
ALL_SERVICES="server airflow-webserver airflow-scheduler airflow-worker airflow-flower coin"

usage() {
  echo "用法: $0 {start|stop|restart|run|status} <service>" >&2
  echo "      $0 {install-dev|publish}" >&2
  echo "      $0 install-prod [version]" >&2
  echo "  <service>: ${ALL_SERVICES// /|}|all" >&2
  exit 1
}

require_funbuild() {
  command -v funbuild >/dev/null 2>&1 || {
    echo "错误: 需要先安装 funbuild" >&2
    exit 1
  }
}

case "$ACTION" in
  install-dev)
    [[ $# -eq 1 ]] || usage
    require_funbuild
    cd "$ROOT_DIR"
    exec funbuild install
    ;;
  install-prod)
    [[ $# -le 2 ]] || usage
    exec python3 -m pip install "funcron${TARGET:+==$TARGET}"
    ;;
  publish)
    [[ $# -eq 1 ]] || usage
    require_funbuild
    cd "$ROOT_DIR"
    exec funbuild build
    ;;
esac

[[ $# -eq 2 ]] || usage
case "$ACTION" in
  start | stop | restart | run | status) ;;
  *)
    echo "错误: 未知动作: ${ACTION}" >&2
    usage
    ;;
esac

if [[ "$TARGET" == "all" ]]; then
  SERVICES="$ALL_SERVICES"
  if [[ "$ACTION" == "run" ]]; then
    echo "run 模式只能指定单个服务，不支持 all" >&2
    exit 1
  fi
else
  case " $ALL_SERVICES " in
    *" $TARGET "*) SERVICES="$TARGET" ;;
    *)
      echo "未知服务: $TARGET" >&2
      usage
      ;;
  esac
fi

dispatch_one() {
  local service="$1"
  case "$service" in
    server) "$SCRIPT_DIR/services/server.sh" "$ACTION" ;;
    airflow-webserver) "$SCRIPT_DIR/services/airflow.sh" "$ACTION" webserver ;;
    airflow-scheduler) "$SCRIPT_DIR/services/airflow.sh" "$ACTION" scheduler ;;
    airflow-worker) "$SCRIPT_DIR/services/airflow.sh" "$ACTION" worker ;;
    airflow-flower) "$SCRIPT_DIR/services/airflow.sh" "$ACTION" flower ;;
    coin) "$SCRIPT_DIR/services/coin.sh" "$ACTION" ;;
  esac
}

if [[ "$ACTION" == "run" ]]; then
  case "$SERVICES" in
    server) exec "$SCRIPT_DIR/services/server.sh" run ;;
    airflow-webserver) exec "$SCRIPT_DIR/services/airflow.sh" run webserver ;;
    airflow-scheduler) exec "$SCRIPT_DIR/services/airflow.sh" run scheduler ;;
    airflow-worker) exec "$SCRIPT_DIR/services/airflow.sh" run worker ;;
    airflow-flower) exec "$SCRIPT_DIR/services/airflow.sh" run flower ;;
    coin) exec "$SCRIPT_DIR/services/coin.sh" run ;;
  esac
fi

rc=0
for service in $SERVICES; do
  dispatch_one "$service" || rc=1
done
exit "$rc"
