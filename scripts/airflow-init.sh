#!/usr/bin/env bash
# Airflow 元数据库初始化（一次性操作，不是服务启停脚本）。
#
# 用法: scripts/airflow-init.sh <dev|prod>
#   dev  → AIRFLOW_HOME 取 .run/airflow-dev-home
#   prod → AIRFLOW_HOME 取 $AIRFLOW_HOME_PROD（默认 $HOME/airflow）
#
# 配置不走 airflow.cfg：仓库内不保存该文件（凭据不能进版本库，Airflow 要求的绝对
# 路径也不能写死在包里）。所有配置项由 scripts/lib/funcron-airflow-env.sh 统一按
# AIRFLOW__* 环境变量推导，凭据写在仓库根目录的 .env 里（模板见 .env.example）。
#
# 初始化完成后，各长期运行服务统一用：
#   scripts/setup.sh start {airflow-webserver|airflow-scheduler|airflow-worker|airflow-flower} <dev|prod>
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_NAME="${1:-}"

case "$ENV_NAME" in
  dev | prod) ;;
  *)
    echo "用法: $0 <dev|prod>" >&2
    exit 1
    ;;
esac

# shellcheck source=lib/funcron-common.sh
source "$ROOT_DIR/scripts/lib/funcron-common.sh"
# shellcheck source=lib/funcron-airflow-env.sh
source "$ROOT_DIR/scripts/lib/funcron-airflow-env.sh"

RUN_DIR="$ROOT_DIR/.run"
funcron_prepare_airflow_env "$ENV_NAME" "$ROOT_DIR" "$RUN_DIR"

echo "初始化 Airflow 元数据库 (AIRFLOW_HOME=${AIRFLOW_HOME}) ..."
# Airflow 3 已移除 `airflow db init`，建库与升级统一走 `airflow db migrate`。
airflow db migrate
echo "完成。管理员账号由所选 auth manager 创建，见 README「Airflow」一节。"
