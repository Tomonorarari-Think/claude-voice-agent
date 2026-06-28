"""キャラクター識別子と音声エンジン種別。"""

from __future__ import annotations

from enum import Enum


class EngineKind(str, Enum):
    """音声合成エンジンの種別。"""

    VOICEVOX = "voicevox"
    CEVIO = "cevio"


class CharacterId(str, Enum):
    """対応キャラクター。読み上げエンジンが異なる。"""

    KOHARU_RIKKA = "koharu_rikka"  # CeVIO AI
    KASUKABE_TSUMUGI = "kasukabe_tsumugi"  # VOICEVOX

    @property
    def display_name(self) -> str:
        return _DISPLAY_NAMES[self]


_DISPLAY_NAMES: dict[CharacterId, str] = {
    CharacterId.KOHARU_RIKKA: "小春六花",
    CharacterId.KASUKABE_TSUMUGI: "春日部つむぎ",
}
