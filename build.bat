@echo off
chcp 65001 >nul
cd /d "%~dp0"
title RainTranslater

echo.
echo ╔══════════════════════════════════════════╗
echo ║      RainTranslater 一键启动              ║
echo ║      本地模型 + 在线兜底                  ║
echo ╚══════════════════════════════════════════╝
echo.

set "PYTHON=D:\Software\Python\python.exe"

:: 检查 Python
if not exist "%PYTHON%" (
    echo [错误] 未找到 Python: %PYTHON%
    pause
    exit /b 1
)

:: 安装依赖
echo [1/2] 检查依赖...
"%PYTHON%" -m pip install -q -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com -r requirements.txt 2>nul
if %ERRORLEVEL% neq 0 (
    echo [警告] 部分依赖安装失败，尝试继续...
)

:: 启动
echo [2/2] 启动 RainTranslater...
echo.
"%PYTHON%" main.py
pause
