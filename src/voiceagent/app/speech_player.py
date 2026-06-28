"""GUI スレッドの読み上げ再生器 + リップシンク駆動。

SpeechItem を順番に再生し、再生位置に同期して口形フレームを `frame` シグナルで通知する。
立ち絵レンダラはこのシグナルを受けて表示を更新する。
"""

from __future__ import annotations

from collections import deque

from PySide6.QtCore import QObject, QTimer, Signal

from voiceagent.app.speech_item import SpeechItem
from voiceagent.audio.player import AudioPlayer
from voiceagent.domain.emotion import Emotion
from voiceagent.domain.phoneme import MouthShape
from voiceagent.tts.lipsync import shape_at

_TICK_MS = 33  # ~30fps


class SpeechPlayer(QObject):
    """SpeechItem キューの逐次再生とリップシンク。"""

    frame = Signal(Emotion, MouthShape)  # 表示すべき感情・口形
    idle = Signal()  # キューが空になった

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._queue: deque[SpeechItem] = deque()
        self._player = AudioPlayer()
        self._current: SpeechItem | None = None
        self._timer = QTimer(self)
        self._timer.setInterval(_TICK_MS)
        self._timer.timeout.connect(self._tick)

    def enqueue(self, item: SpeechItem) -> None:
        self._queue.append(item)
        if self._current is None:
            self._start_next()

    def _start_next(self) -> None:
        if not self._queue:
            self._current = None
            self.idle.emit()
            return
        item = self._queue.popleft()
        self._current = item
        self._player.play(item.wav)
        self.frame.emit(item.emotion, MouthShape.CLOSED)
        self._timer.start()

    def _tick(self) -> None:
        item = self._current
        if item is None:
            return
        if self._player.is_playing():
            shape = shape_at(item.mouth_timeline, self._player.position())
            self.frame.emit(item.emotion, shape)
        else:
            self._timer.stop()
            self.frame.emit(item.emotion, MouthShape.CLOSED)  # 発話終了で口を閉じる
            self._start_next()

    def clear(self) -> None:
        """再生とキューを停止・破棄する（新しい話題への切替時など）。"""
        self._queue.clear()
        self._player.stop()
        self._timer.stop()
        self._current = None
