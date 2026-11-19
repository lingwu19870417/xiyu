@echo off
chcp 65001 >nul
setlocal
set ROOT=%~dp0
set PY=D:\gpt-sovits\GPT-SoVITS-v2pro-20250604\runtime\python.exe
set EXP=xiyu_rd
set EPOCHS=8

if not exist "%ROOT%out\list.txt" (
  echo [ERROR] 没有 out\list.txt，先跑「一键整理.bat」
  pause & exit /b 1
)

"%PY%" "%ROOT%tools\train_reading.py" --list "%ROOT%out\list.txt" --exp %EXP% --epochs %EPOCHS%
if errorlevel 1 (
  echo.
  echo [ERROR] 训练失败，日志：D:\gpt-sovits\logs\%EXP%\train.log
  pause & exit /b 1
)

echo.
echo ================================================
echo  训练完成。权重：
echo    SoVITS_weights_v2Pro\%EXP%_e*.pth
echo    GPT_weights_v2Pro\%EXP%-e*.ckpt
echo  下一步：接进 9880 服务试听，选最像的那一轮
echo ================================================
pause
