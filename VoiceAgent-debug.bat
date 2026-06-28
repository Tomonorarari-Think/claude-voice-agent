@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

rem === VoiceAgent 起動（コンソール表示・ログ確認用） ===
rem 起動しない/落ちるときはこちらでエラーを確認してください。

if not exist ".venv\Scripts\python.exe" (
    echo 仮想環境が見つかりません。先に setup.bat を実行してください。
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m voiceagent.app.main
echo.
echo --- 終了しました（終了コード: %errorlevel%） ---
pause
endlocal
