#!/usr/bin/env bash
# Airflow 各角色服务（webserver / scheduler / worker / flower）：
# 端口/AIRFLOW_HOME、运行时配置、运行时文件与启停逻辑。
# 由 scripts/setup.sh 统一调度，不要直接执行本脚本管理生命周期。
#
# 用法: scripts/services/airflow.sh {start|stop|restart|status|run} <role> <dev|prod>
#   <role>: webserver | scheduler | worker | flower
#
# dev/prod 使用完全独立的 AIRFLOW_HOME 与端口：
#   prod 对应长期部署机器上已初始化好的 AIRFLOW_HOME（默认 $HOME/airflow）；
#   dev  使用仓库内 .run/airflow-dev-home，方便本地调试而不影响 prod 数据。
#
# 配置：仓库里**不**保存 airflow.cfg。所有 funcron 需要覆盖的 Airflow 配置项都通过
# `AIRFLOW__<SECTION>__<KEY>` 环境变量在启动时注入，取值顺序为
# 「调用方已导出的环境变量 → .env 文件（见 .env.example）→ 本脚本按运行环境推导的默认值」。
# 凭据类配置（元数据库连接串、fernet key、API secret key）没有任何内置默认值，
# prod 下缺失会直接拒绝启动，而不是回落到某个写死的账号密码。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
# shellcheck source=../lib/funcron-common.sh
source "$SCRIPT_DIR/../lib/funcron-common.sh"
# shellcheck source=../lib/funcron-airflow-env.sh
source "$SCRIPT_DIR/../lib/funcron-airflow-env.sh"

RUN_DIR="$ROOT_DIR/.run"
LOG_DIR="$ROOT_DIR/.run/logs"
mkdir -p "$RUN_DIR" "$LOG_DIR"

# ---- 配置块：dev/prod 各自的端口（AIRFLOW_HOME 由 funcron_airflow_home 统一推导）----
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

AIRFLOW_HOME="$(funcron_airflow_home "$ENV_NAME" "$ROOT_DIR")"
export AIRFLOW_HOME
if [[ "$ENV_NAME" == "prod" ]]; then
  WEBSERVER_PORT="$WEBSERVER_PORT_PROD"
  FLOWER_PORT="$FLOWER_PORT_PROD"
else
  WEBSERVER_PORT="$WEBSERVER_PORT_DEV"
  FLOWER_PORT="$FLOWER_PORT_DEV"
fi

NAME="funcron-airflow-${ROLE}-${ENV_NAME}"
PID_FILE="$(funcron_pid_file "$RUN_DIR" "$NAME")"
META_FILE="$(funcron_meta_file "$RUN_DIR" "$NAME")"
LOG_FILE="$(funcron_log_file "$LOG_DIR" "$NAME")"
# airflow 会用 setproctitle 改写进程名，但各角色名仍保留在进程标题里，
# 用 "airflow <role>" 之外再配合启动时刻校验，足以识别 PID 是否被复用。
IDENTITY="airflow"

cmd=()
# prod 下校验 airflow 是已安装的正式包（而不是源码树/editable），
# 校验放在 command_for 里，保证 start 与 run 两条路径都会执行。
command_for() {
  if [[ "$ENV_NAME" == "prod" ]]; then
    funcron_require_installed_package airflow "$RUN_DIR"
  fi
  funcron_prepare_airflow_env "$ENV_NAME" "$ROOT_DIR" "$RUN_DIR"
  case "$ROLE" in
    # Airflow 3 起 `airflow webserver` 已被移除（执行会直接报
    # "Command 'airflow webserver' has been removed"），承载 Web UI 的组件
    # 改名为 api-server。本仓库声明 apache-airflow>=3.3.1，所以这里只能用 api-server；
    # 对外的服务名仍叫 airflow-webserver，保持既有脚本与 pid 文件命名不变。
    webserver) cmd=(airflow api-server --port "$WEBSERVER_PORT") ;;
    scheduler) cmd=(airflow scheduler) ;;
    worker) cmd=(airflow celery worker) ;;
    flower) cmd=(airflow celery flower -p "$FLOWER_PORT") ;;
  esac
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
  echo "启动 ${NAME} (AIRFLOW_HOME=${AIRFLOW_HOME}) ..."
  nohup "${cmd[@]}" >>"$LOG_FILE" 2>&1 &
  local pid=$!
  funcron_record_process "$PID_FILE" "$META_FILE" "$pid" "$IDENTITY"
  disown
  echo "${NAME} 已启动 (pid ${pid}, 日志 $LOG_FILE)"
}

do_run() {
  command_for
  echo "前台运行 ${NAME} (AIRFLOW_HOME=${AIRFLOW_HOME}) ..."
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
    running) echo "${NAME}: running (pid $(cat "$PID_FILE"))" ;;
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
