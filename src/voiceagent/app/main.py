"""エントリポイント。設定をロードし、依存を組み立ててウィンドウを表示する。"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from voiceagent.app.controller import AppController
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
    try:
        return app.exec()
    finally:
        engines.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
