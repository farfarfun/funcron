#!/usr/bin/env bash
# funcron 各服务脚本共享的 PID / 日志文件工具函数。
# 只提供函数定义，由 scripts/services/*.sh 通过 source 加载，不单独执行。

# 用法: funcron_pid_file <run_dir> <name>
funcron_pid_file() {
  printf '%s/%s.pid' "$1" "$2"
}

# 用法: funcron_log_file <log_dir> <name>
funcron_log_file() {
  printf '%s/%s-%s.log' "$1" "$2" "$(date +%Y-%m-%d)"
}

# 用法: funcron_is_running <pid_file>
# 判断 pid 文件里记录的进程是否还活着；能区分「陈旧 PID 文件」与「进程真的活着」。
funcron_is_running() {
  local pf="$1"
  [[ -f "$pf" ]] && kill -0 "$(cat "$pf")" 2>/dev/null
}
