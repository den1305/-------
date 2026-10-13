@echo off
rem 一键安装：创建虚拟环境，并优先从本地 wheels 目录离线安装依赖。
rem 适用于 Windows；macOS / Linux 请使用 install.sh。
setlocal
cd /d "%~dp0"

echo ========================================
echo  景点介绍 · 一键安装
echo ========================================

set "PYCMD="
call :tryver "py -3.12" && goto got
call :tryver "py -3.11" && goto got
call :tryver "py -3.10" && goto got
call :tryver "python"   && goto got

echo.
echo [!] 未找到 Python 3.10 - 3.12（sherpa-onnx 官方 wheel 的覆盖范围）。
if exist "installer\python-3.12.10-amd64.exe" goto installpy
echo     请安装 Python 3.12 后重试：https://www.python.org/downloads/
echo     或把官方安装包 python-3.12.10-amd64.exe 放到 installer\ 目录后重新运行本脚本。
pause
exit /b 1

:installpy
echo [i] 使用本地安装包静默安装 Python 3.12.10 …
installer\python-3.12.10-amd64.exe /quiet InstallAllUsers=0 PrependPath=1 Include_launcher=1 Include_test=0
echo.
echo [i] Python 已安装。请关闭本窗口，重新运行 install.bat。
pause
exit /b 0

:got
echo [i] 使用 Python：%PYCMD%
if not exist ".venv" (
  %PYCMD% -m venv .venv
  echo [i] 已创建虚拟环境 .venv
)
call ".venv\Scripts\activate.bat"

if exist "wheels\win_amd64" (
  echo [i] 从本地 wheels 离线安装依赖：wheels\win_amd64
  python -m pip install --no-index --find-links="wheels\win_amd64" -r requirements.txt
) else (
  echo [i] 未找到本地 wheels，改为联网安装（需要网络）…
  python -m pip install -r requirements.txt
)

echo.
echo [√] 安装完成。运行 start.bat 启动项目。
pause
exit /b 0

:tryver
%~1 -c "import sys; sys.exit(0 if (3,10) <= sys.version_info[:2] <= (3,12) else 1)" >nul 2>&1
if errorlevel 1 exit /b 1
set "PYCMD=%~1"
exit /b 0
