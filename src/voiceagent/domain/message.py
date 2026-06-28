"""会話メッセージモデル。"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum


class Role(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


@dataclass(frozen=True, slots=True)
class Message:
    """チャット欄に表示する 1 メッセージ。"""

    role: Role
    text: str
    created_at: float = field(default_factory=time.time)

    def appended(self, more: str) -> "Message":
        """ストリーム途中のテキスト追記。新インスタンスを返す（不変）。"""
        return Message(role=self.role, text=self.text + more, created_at=self.created_at)
