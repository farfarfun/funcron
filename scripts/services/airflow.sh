#!/usr/bin/env bash
# Airflow 各角色服务（webserver / scheduler / worker / flower）：
# 端口/AIRFLOW_HOME、运行时配置、运行时文件与启停逻辑。
# 由 scripts/setup.sh 统一调度，不要直接执行本脚本管理生命周期。
#
# 用法: scripts/services/airflow.sh {start|stop|restart|status|run} <role>
#   <role>: webserver | scheduler | worker | flower
#
# 配置：仓库里**不**保存 airflow.cfg。所有 funcron 需要覆盖的 Airflow 配置项都通过
# `AIRFLOW__<SECTION>__<KEY>` 环境变量在启动时注入，取值顺序为
# 「调用方已导出的环境变量 → .env 文件（见 .env.example）→ 本脚本默认值」。
# 凭据类配置（元数据库连接串、fernet key、API secret key）没有任何内置默认值，
# 缺失会直接拒绝启动，而不是回落到某个写死的账号密码。
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

# ---- 配置块 ----
WEBSERVER_PORT="${FUNCRON_AIRFLOW_WEBSERVER_PORT:-8061}"
FLOWER_PORT="${FUNCRON_AIRFLOW_FLOWER_PORT:-8062}"

ACTION="${1:-}"
ROLE="${2:-}"

usage() {
  echo "用法: $0 {start|stop|restart|status|run} <webserver|scheduler|worker|flower>" >&2
  exit 1
}

[[ -n "$ACTION" && $# -eq 2 ]] || usage
case "$ROLE" in
  webserver | scheduler | worker | flower) ;;
  *)
    echo "错误: 未知 role: ${ROLE}" >&2
    usage
    ;;
esac
NAME="funcron-airflow-${ROLE}"
PID_FILE="$(funcron_pid_file "$RUN_DIR" "$NAME")"
META_FILE="$(funcron_meta_file "$RUN_DIR" "$NAME")"
LOG_FILE="$(funcron_log_file "$LOG_DIR" "$NAME")"
# airflow 会用 setproctitle 改写进程名，但各角色名仍保留在进程标题里，
# 用 "airflow <role>" 之外再配合启动时刻校验，足以识别 PID 是否被复用。
IDENTITY="airflow"

cmd=()
command_for() {
  funcron_require_installed_package airflow "$RUN_DIR"
  funcron_prepare_airflow_env prod "$ROOT_DIR" "$RUN_DIR"
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
  local state version
  state="$(funcron_service_state "$PID_FILE" "$META_FILE" "$IDENTITY")"
  version="$(funcron_installed_version apache-airflow)"
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
