@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

set "PY="
python -c "import sys" >nul 2>&1 && set "PY=python"
if not defined PY (
    py -3 -c "import sys" >nul 2>&1 && set "PY=py -3"
)
if not defined PY (
    echo [错误] 没有找到 Python，请先安装 Python 3.10 或更高版本。
    echo        下载地址：https://www.python.org/downloads/
    echo        安装时记得勾选 "Add Python to PATH"。
    pause
    exit /b 1
)

%PY% "%~dp0start.py" %*
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
    echo.
    echo [失败] 启动器退出码 %RC%，上面有具体原因。
    if "%~1"=="" pause
)
exit /b %RC%
