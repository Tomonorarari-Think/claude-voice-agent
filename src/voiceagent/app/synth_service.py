"""常駐する音声合成スレッド。

会話ターンごとに別スレッドを起こすと、CeVIO の COM オブジェクトがスレッドに
束縛されてクロススレッド呼び出しで失敗する（キャラ切替後に読み上げが止まる原因）。
そこで合成は**単一の常駐スレッド**で直列処理し、COM を 1 スレッドに固定する。
Claude のストリーム処理（asyncio）とも分離する。
"""

from __future__ import annotations

import queue

from PySide6.QtCore import QThread, Signal

from voiceagent.app.speech_item import SpeakRequest, SpeechItem
from voiceagent.tts.engine_base import EngineUnavailableError
from voiceagent.tts.engine_manager import EngineManager
from voiceagent.tts.lipsync import build_mouth_timeline


class SynthService(QThread):
    """合成依頼を順番に処理し、再生用の SpeechItem を発行する常駐スレッド。"""

    ready = Signal(object)  # SpeechItem
    failed = Signal(str)

    def __init__(self, engines: EngineManager, parent=None) -> None:
        super().__init__(parent)
        self._engines = engines
        self._queue: queue.Queue = queue.Queue()
        self._generation = 0  # clear() で更新。古い依頼を破棄するための世代番号。

    def submit(self, request: SpeakRequest) -> None:
        self._queue.put((self._generation, request))

    def clear(self) -> None:
        """未処理の依頼を破棄する（新しい話題・キャラ切替時）。"""
        self._generation += 1

    def stop(self) -> None:
        self._queue.put(None)  # 終了センチネル

    def run(self) -> None:
        while True:
            item = self._queue.get()
            if item is None:
                return
            generation, request = item
            if generation != self._generation:
                continue  # clear 済みの古い依頼はスキップ
            try:
                engine = self._engines.get_engine(request.character)
                utterance = engine.synthesize(request.text, request.emotion)
            except EngineUnavailableError as exc:
                self.failed.emit(str(exc))
                continue
            except Exception as exc:  # 合成の想定外失敗で全体を止めない
                self.failed.emit(f"音声合成エラー: {exc}")
                continue
            if generation != self._generation:
                continue  # 合成中に clear された
            timeline = build_mouth_timeline(utterance.phonemes)
            self.ready.emit(
                SpeechItem(
                    text=request.text,
                    emotion=request.emotion,
                    wav=utterance.wav,
                    mouth_timeline=timeline,
                )
            )
