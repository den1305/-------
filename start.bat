@echo off
rem 一键启动：激活虚拟环境并运行本地服务（全程离线，无需联网）。
rem 适用于 Windows；macOS / Linux 请使用 start.sh。
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
  echo [!] 尚未安装依赖，请先运行 install.bat
  pause
  exit /b 1
)
call ".venv\Scripts\activate.bat"

echo ========================================
echo  正在启动：http://127.0.0.1:5000
echo  按 Ctrl+C 可停止服务
echo ========================================
rem 稍候 4 秒再打开浏览器，等待服务就绪
start "" /min cmd /c "timeout /t 4 /nobreak >nul & start http://127.0.0.1:5000"
python app.py

pause
