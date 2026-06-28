"""感情モデル。エンジン非依存の共通感情を定義し、各エンジン側でマッピングする。"""

from __future__ import annotations

from enum import Enum


class Emotion(str, Enum):
    """エンジン非依存の共通感情ラベル。

    CeVIO 小春六花 (嬉しい/普通/怒り/哀しみ/落ち着き) と
    VOICEVOX のスタイルの双方へ、各エンジンのアダプタで写像する。
    """

    NEUTRAL = "neutral"
    HAPPY = "happy"
    ANGRY = "angry"
    SAD = "sad"
    CALM = "calm"

    @property
    def label_ja(self) -> str:
        return _JA_LABELS[self]


_JA_LABELS: dict[Emotion, str] = {
    Emotion.NEUTRAL: "普通",
    Emotion.HAPPY: "嬉しい",
    Emotion.ANGRY: "怒り",
    Emotion.SAD: "哀しみ",
    Emotion.CALM: "落ち着き",
}
