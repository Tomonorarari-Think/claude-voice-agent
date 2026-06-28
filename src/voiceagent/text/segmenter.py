"""文分割。ストリーム読み上げのため、確定した文を順次 TTS へ渡せるようにする。"""

from __future__ import annotations

import re

# 日本語/英語の文末（句点・感嘆・疑問・改行）。終端記号は文に含める。
_SENTENCE_END = re.compile(r"[^。！？!?\n]*[。！？!?]+|\S[^\n]*(?=\n)|\S[^\n]*$")


def split_sentences(text: str) -> list[str]:
    """テキストを文単位に分割する（空白のみの断片は除外）。"""
    if not text or not text.strip():
        return []
    sentences = [m.group(0).strip() for m in _SENTENCE_END.finditer(text)]
    return [s for s in sentences if s]


def extract_complete_sentences(buffer: str) -> tuple[list[str], str]:
    """ストリーム用: バッファから「終端記号で終わった文」だけを取り出す。

    返り値は (確定文のリスト, 未確定の残り)。残りは次のチャンクと結合して再評価する。
    """
    if not buffer:
        return [], ""
    complete: list[str] = []
    last_end = 0
    for m in re.finditer(r"[。！？!?]+", buffer):
        end = m.end()
        chunk = buffer[last_end:end].strip()
        if chunk:
            complete.append(chunk)
        last_end = end
    remainder = buffer[last_end:]
    return complete, remainder
