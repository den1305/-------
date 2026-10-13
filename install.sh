#!/usr/bin/env bash
# 一键安装：创建虚拟环境，并优先从本地 wheels 目录离线安装依赖。
# 适用于 macOS / Linux；Windows 请使用 install.bat。
set -euo pipefail
cd "$(dirname "$0")"

echo "========================================"
echo " 景点介绍 · 一键安装"
echo "========================================"

# 1) 查找可用的 Python（需要 3.10 - 3.12，这是 sherpa-onnx 官方 wheel 的覆盖范围）
PY=""
for cand in python3.12 python3.11 python3.10 python3 python; do
  if command -v "$cand" >/dev/null 2>&1; then
    if "$cand" -c 'import sys; sys.exit(0 if (3,10) <= sys.version_info[:2] <= (3,12) else 1)' >/dev/null 2>&1; then
      PY="$cand"
      break
    fi
  fi
done

if [ -z "$PY" ]; then
  echo "[!] 未找到 Python 3.10 - 3.12。"
  echo "    macOS:         brew install python@3.12"
  echo "    Ubuntu/Debian: sudo apt install python3.12 python3.12-venv"
  echo "    其他平台请在官网安装 3.12：https://www.python.org/downloads/"
  exit 1
fi
echo "[i] 使用 Python：$PY（$("$PY" -c 'import sys; print(".".join(map(str, sys.version_info[:3])))')）"

# 2) 创建虚拟环境
if [ ! -d .venv ]; then
  "$PY" -m venv .venv
  echo "[i] 已创建虚拟环境 .venv"
fi
# shellcheck disable=SC1091
. .venv/bin/activate

# 3) 安装依赖：有本地 wheels 就完全离线安装，没有才联网
case "$(uname -s)-$(uname -m)" in
  Linux-x86_64) WHEELS="wheels/linux_x86_64" ;;
  Darwin-arm64) WHEELS="wheels/macos_arm64" ;;
  *)            WHEELS="" ;;
esac

if [ -n "$WHEELS" ] && [ -d "$WHEELS" ]; then
  echo "[i] 从本地 wheels 离线安装依赖：$WHEELS"
  python -m pip install --no-index --find-links="$WHEELS" -r requirements.txt
else
  echo "[i] 未找到匹配本机平台的 wheels，改为联网安装（需要网络）…"
  python -m pip install -r requirements.txt
fi

echo
echo "[√] 安装完成。运行 ./start.sh 启动项目。"
