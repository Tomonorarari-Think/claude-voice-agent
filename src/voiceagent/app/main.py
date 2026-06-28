"""エントリポイント。設定をロードし、依存を組み立ててウィンドウを表示する。"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from voiceagent.app.controller import AppController
from voiceagent.app.startup import BackendStarter
from voiceagent.claude.session_manager import SessionManager
from voiceagent.config.characters import load_character_configs
from voiceagent.config.paths import resolve_engine_paths
from voiceagent.config.settings import load_settings
from voiceagent.tts.engine_manager import EngineManager
from voiceagent.ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # トレイ常駐のため

    settings = load_settings()
    configs = load_character_configs()
    paths = resolve_engine_paths(
        voicevox_run_exe=settings.voicevox_run_exe,
        cevio_dir=settings.cevio_dir,
    )
    engines = EngineManager(paths, configs)
    sessions = SessionManager()
    controller = AppController(settings, configs, engines, sessions)

    window = MainWindow(controller, settings)
    window.show()

    # バックエンド（VOICEVOX / CeVIO）をアプリ起動と同時に裏で起動しておく。
    starter = BackendStarter(engines)
    starter.ready.connect(
        lambda r: window.history.add_notice(
            f"準備完了（VOICEVOX: {'OK' if r.get('voicevox') else '未接続'} / "
            f"CeVIO: {'OK' if r.get('cevio') else '未接続'}）"
        )
    )
    starter.start()

    try:
        code = app.exec()
    finally:
        starter.wait(2000)
        engines.shutdown()
    # 実行中の QThread / 子プロセスが残ってプロセスが生き続けるのを防ぐため、
    # 後始末後に確実に終了する。
    import os

    os._exit(code)


if __name__ == "__main__":
    main()
