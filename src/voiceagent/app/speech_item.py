"""読み上げ 1 単位（合成済み音声 + 感情 + 口形タイムライン）。

会話オーケストレータ（worker スレッド）が生成し、GUI スレッドの再生器が消費する。
"""

from __future__ import annotations

from dataclasses import dataclass

from voiceagent.domain.emotion import Emotion
from voiceagent.domain.phoneme import MouthFrame


@dataclass(frozen=True, slots=True)
class SpeechItem:
    """1 文の読み上げ素材。"""

    text: str
    emotion: Emotion
    wav: bytes
    mouth_timeline: tuple[MouthFrame, ...]


@dataclass(frozen=True, slots=True)
class SpeakRequest:
    """合成依頼（テキスト + 感情 + どのキャラのエンジンを使うか）。"""

    text: str
    emotion: Emotion
    character: "object"  # CharacterId（循環 import 回避のため緩く保持）
