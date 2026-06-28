"""感情 -> 立ち絵スロット選択（目・眉など）の対応。

config の [expression.<emotion>] テーブル（role -> 子インデックス）から構築する。
未定義の感情・役割は「中立（既定の子）」にフォールバックするため、最低限の設定でも動く。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from voiceagent.domain.emotion import Emotion

# 表情に関与するスロット役割（口はリップシンクが別途上書きするので含めない）。
_EXPRESSION_ROLES = ("eyes", "brows")


@dataclass(frozen=True, slots=True)
class ExpressionSet:
    """感情 -> {role: 子インデックス} の対応。"""

    by_emotion: dict[Emotion, dict[str, int]] = field(default_factory=dict)

    @classmethod
    def from_config(cls, raw: dict[str, dict] | None) -> "ExpressionSet":
        """[expression] テーブル {emotion: {role: index}} から生成する。"""
        by_emotion: dict[Emotion, dict[str, int]] = {}
        for key, table in (raw or {}).items():
            try:
                emotion = Emotion(key)
            except ValueError:
                continue
            selection = {
                role: int(table[role])
                for role in _EXPRESSION_ROLES
                if role in table
            }
            by_emotion[emotion] = selection
        return cls(by_emotion=by_emotion)

    def selection_for(self, emotion: Emotion) -> dict[str, int]:
        """感情に対応する {role: index}。未定義なら空（=中立）。"""
        return dict(self.by_emotion.get(emotion, {}))
