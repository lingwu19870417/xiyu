@echo off
chcp 65001 >nul
cd /d "%~dp0"

set HF_ENDPOINT=https://hf-mirror.com
set HF_HOME=%~dp0models
rem GPT-SoVITS 整合包的位置。不用它就把 config.json 的 tts.engine 改成 f5-tts，
rem 然后把下面这行指向一个不存在的目录即可（脚本会自动跳过语音服务）。
set GSV_DIR=D:\gpt-sovits\GPT-SoVITS-v2pro-20250604

echo.
echo   夕语 - 启动中
echo.

rem ===== 第一步：语音服务（GPT-SoVITS，端口 9880）=====
netstat -ano | findstr ":9880" | findstr "LISTENING" >nul 2>&1
if %errorlevel%==0 (
  echo   [1/2] 语音服务已在运行，跳过启动
  goto :launch_app
)

if not exist "%GSV_DIR%\runtime\python.exe" (
  echo   [1/2] 没找到语音服务目录：%GSV_DIR%
  echo         界面会照常打开，但暂时没有声音。
  goto :launch_app
)

echo   [1/2] 正在启动语音服务，首次约 15~40 秒 ...
start "夕语-语音服务" /min /d "%GSV_DIR%" "%GSV_DIR%\runtime\python.exe" api_v2.py -a 127.0.0.1 -p 9880 -c GPT_SoVITS/configs/tts_infer.yaml

set /a _n=0
:wait_sovits
timeout /t 2 /nobreak >nul
netstat -ano | findstr ":9880" | findstr "LISTENING" >nul 2>&1
if %errorlevel%==0 goto :sovits_ok
set /a _n+=1
if %_n% GEQ 45 (
  echo   [1/2] 语音服务没起来，先继续启动界面，稍后可在网页上点"重试"
  goto :launch_app
)
goto :wait_sovits

:sovits_ok
echo   [1/2] 语音服务就绪

:launch_app
echo   [2/2] 正在启动界面 ...
echo.
echo   ============================================
echo    浏览器会自动打开 http://127.0.0.1:8765
echo    这个黑窗口不要关，关掉服务就停了。
echo    关闭时请先关这个窗口，语音服务会在后台退出。
echo   ============================================
echo.

rem ===== 对话模型的 key =====
rem 不用改这个文件。key 存在 persona\llm-key.txt，网页上也能改。
rem 想临时覆盖，取消下面这行的注释。
rem set XIYU_API_KEY=xxxxxxxxxxxxxxxx

".venv\Scripts\python.exe" app.py

echo.
echo   [界面已停止] 正在关闭语音服务 ...
taskkill /FI "WINDOWTITLE eq 夕语-语音服务*" /F >nul 2>&1
echo   全部关闭完成。如果刚才有报错，把上面的内容发给我。
pause
