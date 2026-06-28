@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0.."

rem === 初回セットアップ（仮想環境作成 + 依存インストール） ===
rem （このスクリプトは scripts\ 配下。リポジトリルートで実行する）

set "PYLAUNCH=py -3"
where py >nul 2>nul || set "PYLAUNCH=python"

if not exist ".venv\Scripts\python.exe" (
    echo 仮想環境を作成しています...
    %PYLAUNCH% -m venv .venv
    if errorlevel 1 (
        echo 仮想環境の作成に失敗しました。Python 3.13 以上がインストールされているか確認してください。
        pause
        exit /b 1
    )
)

echo 依存パッケージをインストールしています...
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -e ".[dev]"
if errorlevel 1 (
    echo インストールに失敗しました。
    pause
    exit /b 1
)

echo.
echo セットアップが完了しました。
echo   - 通常起動: scripts\VoiceAgent.bat
echo   - ログ確認: scripts\VoiceAgent-debug.bat
echo ※ 音声/立ち絵アセットの配置は docs\setup.md を参照してください。
pause
endlocal
