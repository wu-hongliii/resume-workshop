@echo off
setlocal
cd /d "%~dp0"
python -m app.main
if errorlevel 1 (
  echo.
  echo 启动失败。请确认已安装 Python 3.12，然后运行：
  echo python -m pip install -r requirements.txt
  pause
)

