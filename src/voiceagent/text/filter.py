"""読み上げ用テキスト整形。

要件: 「会話しているようにするために、URL やコード等の読み上げは行わない」。
コードブロック・インラインコード・URL・ファイルパス・Markdown 記法を除去し、
話し言葉として自然なテキストに整える。各段は新しい文字列を返す純粋関数。
"""

from __future__ import annotations

import re

# 多くの記号を含むインラインコードは読み上げ対象から外す閾値。
_SYMBOLISH = re.compile(r"[\\/_<>{}()\[\];=|&%$#@^~`]")

_FENCED_CODE = re.compile(r"```.*?```", re.DOTALL)
_INDENTED_CODE = re.compile(r"(?m)^(?: {4}|\t).*$")
_INLINE_CODE = re.compile(r"`([^`]+)`")
_URL = re.compile(r"https?://\S+|www\.\S+")
_MD_LINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")  # [text](url) -> text
_MD_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]+\)")  # ![alt](url) -> 除去
# Windows ドライブパス / Unix 風パス（拡張子付き or ディレクトリ区切り 2 つ以上）
_WIN_PATH = re.compile(r"[A-Za-z]:\\[^\s]+")
_UNIX_PATH = re.compile(r"(?<!\w)(?:\.{0,2}/)?(?:[\w.\-]+/){2,}[\w.\-]+")
_FILE_WITH_EXT = re.compile(
    r"(?<!\w)[\w.\-]+\.(?:py|js|ts|tsx|jsx|json|toml|yaml|yml|md|txt|csv|html|css|"
    r"cpp|c|h|rs|go|java|kt|swift|sh|ps1|sql|xml|ini|cfg|lock)\b"
)
_MD_HEADING = re.compile(r"(?m)^\s{0,3}#{1,6}\s*")
_MD_BLOCKQUOTE = re.compile(r"(?m)^\s{0,3}>\s?")
_MD_LIST_MARKER = re.compile(r"(?m)^\s{0,3}(?:[-*+]|\d+\.)\s+")
_MD_EMPHASIS = re.compile(r"(\*\*|\*|__|_|~~)(.+?)\1")
_MULTISPACE = re.compile(r"[ \t]{2,}")
_MULTINEWLINE = re.compile(r"\n{3,}")


def _strip_inline_code(text: str) -> str:
    """インラインコードは、記号が多ければ除去、短く平易なら中身を残す。"""

    def repl(m: re.Match[str]) -> str:
        inner = m.group(1)
        if _SYMBOLISH.search(inner) or len(inner) > 24:
            return ""  # コードらしい -> 読まない
        return inner  # `npm` のような短い語は残す

    return _INLINE_CODE.sub(repl, text)


def _strip_emphasis(text: str) -> str:
    # ネスト解消のため数回適用
    for _ in range(3):
        new = _MD_EMPHASIS.sub(lambda m: m.group(2), text)
        if new == text:
            break
        text = new
    return text


def clean_for_speech(text: str) -> str:
    """Agent のテキストを読み上げ向けに整形して返す。"""
    if not text:
        return ""

    text = _FENCED_CODE.sub(" ", text)
    text = _MD_IMAGE.sub(" ", text)
    text = _MD_LINK.sub(r"\1", text)
    text = _URL.sub(" ", text)
    text = _WIN_PATH.sub(" ", text)
    text = _UNIX_PATH.sub(" ", text)
    text = _FILE_WITH_EXT.sub(" ", text)
    text = _strip_inline_code(text)
    text = _INDENTED_CODE.sub(" ", text)

    text = _MD_HEADING.sub("", text)
    text = _MD_BLOCKQUOTE.sub("", text)
    text = _MD_LIST_MARKER.sub("", text)
    text = _strip_emphasis(text)

    # 罫線・余分な記号
    text = re.sub(r"(?m)^\s*[-=*_]{3,}\s*$", " ", text)

    text = _MULTISPACE.sub(" ", text)
    text = _MULTINEWLINE.sub("\n\n", text)
    return text.strip()
