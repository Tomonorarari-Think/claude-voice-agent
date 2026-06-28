"""アプリ制御。会話ターンの起動と、UI/再生器への配線を担う QObject。"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from voiceagent.app.turn_worker import AgentTurnWorker
from voiceagent.claude.agent_client import AgentClient
from voiceagent.claude.session_manager import SessionManager
from voiceagent.config.characters import CharacterConfig
from voiceagent.config.settings import Settings
from voiceagent.domain.character import CharacterId
from voiceagent.tts.engine_manager import EngineManager


class AppController(QObject):
    """1 ターンずつ会話を進める。多重送信は無視する。"""

    assistant_text = Signal(str)
    speech_ready = Signal(object)  # SpeechItem
    error = Signal(str)
    busy_changed = Signal(bool)

    def __init__(
        self,
        settings: Settings,
        configs: dict[CharacterId, CharacterConfig],
        engines: EngineManager,
        sessions: SessionManager,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._settings = settings
        self._configs = configs
        self._engines = engines
        self._sessions = sessions
        self._agent = AgentClient(sessions, cwd=settings.project_path)
        self._worker: AgentTurnWorker | None = None

    def shutdown(self) -> None:
        """エンジン等の後始末（終了時に呼ぶ）。"""
        self._engines.shutdown()

    # --- 設定変更 -------------------------------------------------------------

    @property
    def settings(self) -> Settings:
        return self._settings

    @property
    def configs(self) -> dict[CharacterId, CharacterConfig]:
        return self._configs

    def set_model(self, model_id: str) -> None:
        self._settings = self._settings.with_model(model_id)

    def set_character(self, character: CharacterId) -> None:
        self._settings = self._settings.with_character(character)
        self._sessions.new_topic()  # キャラを変えたら会話も切り替える

    def new_topic(self) -> None:
        self._sessions.new_topic()

    @property
    def is_busy(self) -> bool:
        return self._worker is not None and self._worker.isRunning()

    # --- 送信 -----------------------------------------------------------------

    def send(self, text: str) -> None:
        if self.is_busy or not text.strip():
            return
        character = self._settings.active_character
        worker = AgentTurnWorker(
            self._agent,
            self._engines,
            character,
            self._configs[character],
            self._settings.model,
            text,
        )
        worker.assistant_text.connect(self.assistant_text)
        worker.speech_ready.connect(self.speech_ready)
        worker.failed.connect(self._on_failed)
        worker.turn_done.connect(self._on_done)
        worker.finished.connect(worker.deleteLater)
        self._worker = worker
        self.busy_changed.emit(True)
        worker.start()

    def _on_failed(self, message: str) -> None:
        self.error.emit(message)
        self.busy_changed.emit(False)

    def _on_done(self, _session_id: str) -> None:
        self.busy_changed.emit(False)
