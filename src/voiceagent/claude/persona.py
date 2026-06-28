"""キャラ persona を Claude の system prompt へ反映する。

Claude Code の標準挙動（preset）を保ちつつ、キャラの口調・性格と
「読み上げ向けの整形ルール」を append する。
"""

from __future__ import annotations

from voiceagent.config.characters import CharacterConfig

# 読み上げ前提の共通ルール（フィルタとは別に、生成段階でも会話的にさせる）。
_SPEECH_RULES = """
あなたの応答は音声で読み上げられます。次を守ってください:
- 長いコードブロックや URL をそのまま書かず、何をするものか一言で説明する。
- 箇条書きの記号や Markdown 記法を多用せず、話し言葉で簡潔に。
- 専門用語は必要に応じてやさしく補足する。
"""


def build_system_prompt(config: CharacterConfig) -> dict:
    """Claude Code preset に persona と読み上げルールを append した system_prompt を返す。"""
    append = f"{config.persona}\n{_SPEECH_RULES}".strip()
    return {"type": "preset", "preset": "claude_code", "append": append}
