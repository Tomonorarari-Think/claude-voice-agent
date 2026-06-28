@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0.."

rem === VoiceAgent 起動（コンソールを残さず GUI を起動） ===
rem （このスクリプトは scripts\ 配下。リポジトリルートで実行する）

if not exist ".venv\Scripts\pythonw.exe" (
    echo 仮想環境が見つかりません。先に scripts\setup.bat を実行してください。
    pause
    exit /b 1
)

start "VoiceAgent" ".venv\Scripts\pythonw.exe" -m voiceagent.app.main
endlocal
