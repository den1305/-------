#!/usr/bin/env bash
# 一键启动：激活虚拟环境并运行本地服务（全程离线，无需联网）。
# 适用于 macOS / Linux；Windows 请使用 start.bat。
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -x .venv/bin/python ]; then
  echo "[!] 尚未安装依赖，请先运行 ./install.sh"
  exit 1
fi
# shellcheck disable=SC1091
. .venv/bin/activate

PORT="${SCENIC_PORT:-5000}"
echo "========================================"
echo " 正在启动：http://127.0.0.1:$PORT"
echo " 按 Ctrl+C 可停止服务"
echo "========================================"
exec python app.py
