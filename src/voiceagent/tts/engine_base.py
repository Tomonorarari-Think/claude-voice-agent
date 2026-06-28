"""音声エンジンの抽象インターフェース。

VOICEVOX / CeVIO の差異をこの Protocol で吸収する。上位レイヤーは
具体エンジンを知らずに `synthesize` を呼ぶ。
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from voiceagent.domain.emotion import Emotion
from voiceagent.domain.utterance import Utterance


class EngineUnavailableError(RuntimeError):
    """エンジン（バックエンド）に接続できない/起動していない場合。"""


@runtime_checkable
class VoiceEngine(Protocol):
    """テキスト -> 音声 + 音素タイミング を返すエンジン。"""

    def is_available(self) -> bool:
        """バックエンドが応答可能かを返す（副作用なし・例外を投げない）。"""
        ...

    def synthesize(self, text: str, emotion: Emotion = Emotion.NEUTRAL) -> Utterance:
        """1 文を合成。失敗時は EngineUnavailableError を送出。"""
        ...
