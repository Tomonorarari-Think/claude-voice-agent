"""Claude Agent SDK ラッパー。

`query()` をストリーム消費し、Agent のテキストを `AgentTextChunk` として
逐次 yield する。セッション ID を `SessionManager` に記録して継続を可能にし、
モデル切替・persona 注入に対応する。

MVP は「対話コンパニオン」として既定でツール実行を行わない（`allowed_tools=[]`）。
ファイル操作などのツール実行モードは後フェーズで追加する。
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    query,
)

from voiceagent.claude.events import AgentDone, AgentError, AgentEvent, AgentTextChunk
from voiceagent.claude.persona import build_system_prompt
from voiceagent.claude.session_manager import SessionManager
from voiceagent.config.characters import CharacterConfig


class AgentClient:
    """会話 1 件分のストリームを生成するクライアント。"""

    def __init__(
        self,
        session_manager: SessionManager,
        *,
        max_turns: int = 200,
        permission_mode: str = "bypassPermissions",
        cwd: str | None = None,
    ) -> None:
        self._sessions = session_manager
        # ツール実行のたびに 1 ターン消費するため、応答が途中で止まらないよう十分大きく。
        self._max_turns = max_turns
        # 参考: .discordbot/bot.py の --dangerously-skip-permissions に相当（自分の PC・本人指示）。
        # 権限プロンプトで止まらないよう bypass する。
        self._permission_mode = permission_mode
        self._cwd = cwd

    def _build_options(self, config: CharacterConfig, model_id: str) -> ClaudeAgentOptions:
        kwargs: dict = dict(
            model=model_id,
            resume=self._sessions.session_id,
            system_prompt=build_system_prompt(config),
            permission_mode=self._permission_mode,
            max_turns=self._max_turns,
        )
        if self._cwd:
            kwargs["cwd"] = self._cwd
        return ClaudeAgentOptions(**kwargs)

    async def stream(
        self,
        prompt: str,
        config: CharacterConfig,
        model_id: str,
    ) -> AsyncIterator[AgentEvent]:
        """プロンプトを送り、応答イベントを逐次 yield する。"""
        if not prompt.strip():
            raise ValueError("prompt must not be empty")

        options = self._build_options(config, model_id)
        try:
            async for message in query(prompt=prompt, options=options):
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock) and block.text:
                            yield AgentTextChunk(block.text)
                elif isinstance(message, ResultMessage):
                    self._sessions.remember(message.session_id)
                    yield AgentDone(
                        session_id=message.session_id,
                        cost_usd=message.total_cost_usd,
                    )
        except Exception as exc:  # SDK/CLI 由来の例外を UI へ伝える
            yield AgentError(message=str(exc))
