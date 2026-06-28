"""発話モデル。合成済み音声 + リップシンク用音素列をまとめる。"""

from __future__ import annotations

from dataclasses import dataclass, field

from voiceagent.domain.character import CharacterId
from voiceagent.domain.emotion import Emotion
from voiceagent.domain.phoneme import Phoneme


@dataclass(frozen=True, slots=True)
class Utterance:
    """1 文ぶんの合成結果。

    `wav` は 44.1k/24k 等の WAV バイト列（エンジン依存）。
    `phonemes` は再生位置に同期させる口パク用の音素タイムライン。
    """

    text: str
    character: CharacterId
    emotion: Emotion
    wav: bytes
    phonemes: tuple[Phoneme, ...] = field(default_factory=tuple)

    @property
    def duration(self) -> float:
        return self.phonemes[-1].end if self.phonemes else 0.0
