"""Claude レイヤーのスモークテスト CLI。

実際の Claude Agent SDK でプロンプトを送り、応答テキストをストリーム表示する。
2 ターン送って `resume` によるセッション継続が効くことも確認する。

使い方:
    python -m voiceagent.claude.smoke --character kasukabe_tsumugi --model claude-haiku-4-5-20251001
"""

from __future__ import annotations

import argparse
import asyncio

from voiceagent.claude.agent_client import AgentClient
from voiceagent.claude.events import AgentDone, AgentError, AgentTextChunk
from voiceagent.claude.session_manager import SessionManager
from voiceagent.config.characters import load_character_configs
from voiceagent.domain.character import CharacterId


async def _ask(client: AgentClient, prompt: str, config, model: str) -> None:
    print(f"\n>>> {prompt}")
    async for event in client.stream(prompt, config, model):
        if isinstance(event, AgentTextChunk):
            print(f"[say] {event.text}")
        elif isinstance(event, AgentDone):
            print(f"[done] session={event.session_id} cost=${event.cost_usd}")
        elif isinstance(event, AgentError):
            print(f"[error] {event.message}")


async def _main(character: CharacterId, model: str) -> int:
    config = load_character_configs()[character]
    sm = SessionManager()
    client = AgentClient(sm)

    await _ask(client, "こんにちは。あなたの名前を教えて。", config, model)
    # 2 ターン目: 直前の会話を覚えているか（resume）
    await _ask(client, "さっき何て名乗ったか覚えてる？", config, model)
    print(f"\n[session continued] id={sm.session_id}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="VoiceAgent Claude smoke test")
    parser.add_argument(
        "--character",
        default=CharacterId.KASUKABE_TSUMUGI.value,
        choices=[c.value for c in CharacterId],
    )
    parser.add_argument("--model", default="claude-haiku-4-5-20251001")
    args = parser.parse_args()
    return asyncio.run(_main(CharacterId(args.character), args.model))


if __name__ == "__main__":
    raise SystemExit(main())
