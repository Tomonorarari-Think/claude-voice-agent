"""起動時のバックエンド起動を担う worker スレッド。

アプリ起動と同時に VOICEVOX / CeVIO を起動しておくことで、最初の発話時の待ち時間を
無くす。CeVIO はウィンドウを最小化する（誤操作で閉じないようにしつつ常駐）。
"""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from voiceagent.character.renderer import CharacterRenderer
from voiceagent.domain.emotion import Emotion
from voiceagent.tts.engine_manager import EngineManager


class RendererWarmer(QThread):
    """立ち絵の口開閉フレームをバックグラウンドで事前合成する。

    PSD 合成は重く GUI を固めるため、別スレッドで実行してから表示を更新する。
    """

    warmed = Signal()

    def __init__(self, renderer: CharacterRenderer, emotion: Emotion, parent=None) -> None:
        super().__init__(parent)
        self._renderer = renderer
        self._emotion = emotion

    def run(self) -> None:
        self._renderer.prerender_mouth_states(self._emotion)
        self.warmed.emit()


class BackendStarter(QThread):
    """VOICEVOX / CeVIO バックエンドをバックグラウンドで起動する。"""

    ready = Signal(dict)  # {"voicevox": bool, "cevio": bool}

    def __init__(self, engines: EngineManager, parent=None) -> None:
        super().__init__(parent)
        self._engines = engines

    def run(self) -> None:
        result = self._engines.start_backends()
        self.ready.emit(result)
