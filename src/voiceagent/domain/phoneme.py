"""音素・口形モデル。リップシンクの中核データ。"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class MouthShape(str, Enum):
    """口形（あいうえお + 閉口）。立ち絵の口レイヤーに対応する。"""

    A = "a"
    I = "i"  # noqa: E741 — 母音「い」の口形
    U = "u"
    E = "e"
    O = "o"  # noqa: E741 — 母音「お」の口形
    CLOSED = "closed"


@dataclass(frozen=True, slots=True)
class Phoneme:
    """単一音素の発話区間（秒）。

    CeVIO `GetPhonemes()` / VOICEVOX AudioQuery の双方を、
    この共通表現へ正規化する。
    """

    phoneme: str
    start: float
    end: float

    def __post_init__(self) -> None:
        if self.start < 0 or self.end < self.start:
            raise ValueError(f"invalid phoneme interval: start={self.start}, end={self.end}")

    @property
    def duration(self) -> float:
        return self.end - self.start


@dataclass(frozen=True, slots=True)
class MouthFrame:
    """ある時刻から表示する口形。リップシンク再生のタイムライン要素。"""

    start: float
    shape: MouthShape
