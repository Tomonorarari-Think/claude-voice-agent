"""エージェント応答ストリームのイベント。UI/TTS レイヤーが消費する。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AgentTextChunk:
    """Agent の発話テキスト断片（読み上げ対象になりうる生テキスト）。"""

    text: str


@dataclass(frozen=True, slots=True)
class AgentDone:
    """1 ターン完了。セッション ID とコストを通知。"""

    session_id: str | None
    cost_usd: float | None = None


@dataclass(frozen=True, slots=True)
class AgentError:
    """ストリーム中のエラー通知。"""

    message: str


AgentEvent = AgentTextChunk | AgentDone | AgentError
