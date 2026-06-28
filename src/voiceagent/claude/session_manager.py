"""セッション継続の管理。

Claude のセッション ID を保持し、次回の `resume` に使う。
「新しい話題」で ID を破棄すると、次回は新規セッションになる。
"""

from __future__ import annotations


class SessionManager:
    """現在の会話セッション ID を保持する小さな可変ホルダー。"""

    def __init__(self) -> None:
        self._session_id: str | None = None

    @property
    def session_id(self) -> str | None:
        return self._session_id

    def remember(self, session_id: str | None) -> None:
        """応答完了時に得たセッション ID を記録する。"""
        if session_id:
            self._session_id = session_id

    def new_topic(self) -> None:
        """セッションを破棄し、次回を新規会話にする。"""
        self._session_id = None
