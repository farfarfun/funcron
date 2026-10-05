#!/usr/bin/env bash
# Airflow 运行时配置的唯一推导入口，由 scripts/services/airflow.sh 与
# scripts/airflow-init.sh 共同 source，保证「初始化」与「运行」用的是同一套配置。
# 只提供函数定义，不单独执行。
#
# 为什么没有 airflow.cfg：
#   1) 配置文件里一旦写上元数据库连接串，账号密码就会随版本库和 PyPI 包一起发出去；
#   2) Airflow 的 dags_folder / plugins_folder / base_log_folder 必须是绝对路径，
#      写进包里就变成了「只在某台开发机上成立」的死路径。
# 所以 funcron 需要覆盖的配置项一律通过 `AIRFLOW__<SECTION>__<KEY>` 环境变量注入，
# 取值顺序：调用方已导出的环境变量 → .env 文件 → 这里按运行环境推导的默认值。
# 凭据类配置没有任何内置默认值。

# 用法: funcron_airflow_home <dev|prod> <root_dir>
# 输出该环境应使用的 AIRFLOW_HOME。
# dev 用仓库内 .run/airflow-dev-home，与 prod 数据完全隔离。
funcron_airflow_home() {
  local env_name="$1" root_dir="$2"
  if [[ "$env_name" == "prod" ]]; then
    printf '%s\n' "${AIRFLOW_HOME_PROD:-$HOME/airflow}"
  else
    printf '%s\n' "${AIRFLOW_HOME_DEV:-$root_dir/.run/airflow-dev-home}"
  fi
}

# 用法: funcron_load_env_file <root_dir>
# 读取并导出 .env（路径可用 FUNCRON_ENV_FILE 覆盖）里的变量。
# 该文件不进版本库，用来存放元数据库连接串等凭据，模板见仓库根目录 .env.example。
funcron_load_env_file() {
  local root_dir="$1"
  local env_file="${FUNCRON_ENV_FILE:-$root_dir/.env}"
  [[ -f "$env_file" ]] || return 0
  set -a
  # shellcheck disable=SC1090
  source "$env_file"
  set +a
}

# 用法: funcron_default_env <变量名> <默认值>
# 仅在变量尚未设置（或为空）时导出默认值，保证调用方与 .env 的显式配置优先。
funcron_default_env() {
  local name="$1" value="$2"
  [[ -n "${!name:-}" ]] && return 0
  export "$name=$value"
}

# 用法: funcron_require_airflow_conn <dev|prod> <root_dir>
# prod 必须显式提供元数据库连接串，缺失时报错返回 1。
# 不提供默认值的原因：回落到 AIRFLOW_HOME 下的 SQLite 在生产上多进程并发必然出问题，
# 而写一个带账号密码的默认值等于把凭据硬编码进仓库。
funcron_require_airflow_conn() {
  local env_name="$1" root_dir="$2"
  [[ "$env_name" == "prod" ]] || return 0
  [[ -n "${AIRFLOW__DATABASE__SQL_ALCHEMY_CONN:-}" ]] && return 0
  echo "错误: prod 必须提供 AIRFLOW__DATABASE__SQL_ALCHEMY_CONN（元数据库连接串）。" >&2
  echo "      在 ${FUNCRON_ENV_FILE:-$root_dir/.env} 里配置，格式见仓库根目录 .env.example；" >&2
  echo "      仓库内不保存任何账号密码。" >&2
  return 1
}

# 用法: funcron_resolve_dags_folder <dev|prod> <root_dir> <run_dir>
# 按「脚本自身位置 / 已安装包位置」解析 DAG 目录并导出，不写死任何开发机绝对路径：
#   dev  → 仓库源码树 src/funcron/airflow/dags
#   prod → 已安装的 funcron 包内 funcron/airflow/dags
# 已显式设置 AIRFLOW__CORE__DAGS_FOLDER 时原样保留。
funcron_resolve_dags_folder() {
  local env_name="$1" root_dir="$2" run_dir="$3"
  [[ -n "${AIRFLOW__CORE__DAGS_FOLDER:-}" ]] && return 0
  local dags
  if [[ "$env_name" == "prod" ]]; then
    if ! dags="$(funcron_installed_package_dir funcron.airflow "$run_dir" dags)"; then
      echo "错误: 无法在已安装的 funcron 包内定位 airflow/dags 目录。" >&2
      return 1
    fi
  else
    dags="$root_dir/src/funcron/airflow/dags"
  fi
  export AIRFLOW__CORE__DAGS_FOLDER="$dags"
}

# 用法: funcron_prepare_airflow_env <dev|prod> <root_dir> <run_dir>
# 导出本次启动/初始化要用的全部 AIRFLOW__* 配置（含 AIRFLOW_HOME）。
# 任一前置校验不通过时返回 1，由调用方中止。
funcron_prepare_airflow_env() {
  local env_name="$1" root_dir="$2" run_dir="$3"

  AIRFLOW_HOME="$(funcron_airflow_home "$env_name" "$root_dir")"
  export AIRFLOW_HOME
  mkdir -p "$AIRFLOW_HOME/plugins" "$AIRFLOW_HOME/logs"

  funcron_load_env_file "$root_dir"
  funcron_require_airflow_conn "$env_name" "$root_dir" || return 1
  funcron_resolve_dags_folder "$env_name" "$root_dir" "$run_dir" || return 1

  # 目录类配置统一落在 AIRFLOW_HOME 下，随运行环境走，不依赖任何固定机器路径。
  funcron_default_env AIRFLOW__CORE__PLUGINS_FOLDER "$AIRFLOW_HOME/plugins"
  funcron_default_env AIRFLOW__LOGGING__BASE_LOG_FOLDER "$AIRFLOW_HOME/logs"
  funcron_default_env AIRFLOW__LOGGING__DAG_PROCESSOR_MANAGER_LOG_LOCATION \
    "$AIRFLOW_HOME/logs/dag_processor_manager/dag_processor_manager.log"

  funcron_default_env AIRFLOW__CORE__LOAD_EXAMPLES False
  # IANA 时区名。注意不要写 "GMT+8"：那不是 IANA 名字，按 POSIX TZ 语义解释反而是 UTC-8。
  funcron_default_env AIRFLOW__CORE__DEFAULT_TIMEZONE Asia/Shanghai
  funcron_default_env AIRFLOW__CORE__EXECUTOR CeleryExecutor
  funcron_default_env AIRFLOW__CELERY__BROKER_URL "redis://127.0.0.1:6379/0"
  funcron_default_env AIRFLOW__CELERY__RESULT_BACKEND "redis://127.0.0.1:6379/0"
}
