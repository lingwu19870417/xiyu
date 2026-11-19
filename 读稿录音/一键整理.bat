@echo off
chcp 65001 >nul
setlocal
set ROOT=%~dp0
set PY=D:\gpt-sovits\GPT-SoVITS-v2pro-20250604\runtime\python.exe

if not exist "%PY%" (
  echo [ERROR] python not found: %PY%
  pause & exit /b 1
)
if not exist "%ROOT%raw" (
  echo [ERROR] 没找到 raw 文件夹。请把录音文件放进 读稿录音\raw\
  pause & exit /b 1
)

"%PY%" "%ROOT%tools\align_script.py" --audio "%ROOT%raw" --script "%ROOT%脚本.txt" --out "%ROOT%out"
if errorlevel 1 (
  echo.
  echo [ERROR] 处理失败，把上面的报错发给小夕
  pause & exit /b 1
)

echo.
echo ================================================
echo  完成。报告已打开，看「已采用」和「需补读」两栏。
echo ================================================
start "" "%ROOT%out\报告.md"
pause
