"""口形 -> 口スロットの子インデックス対応。

既定は 2 状態（閉じ / 開き）で確実に口パクさせる。立ち絵の口レイヤーは
キャラごとに名前が異なるため、母音 5 形を使う場合は config（index 指定）で
上書きする。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from voiceagent.character.slots import Slot
from voiceagent.domain.phoneme import MouthShape

# 既定の 2 状態マッピング: 閉口=0 番、母音(開口)=1 番。
_DEFAULT_2STATE: dict[MouthShape, int] = {
    MouthShape.CLOSED: 0,
    MouthShape.A: 1,
    MouthShape.I: 1,
    MouthShape.U: 1,
    MouthShape.E: 1,
    MouthShape.O: 1,
}


@dataclass(frozen=True, slots=True)
class MouthMap:
    """MouthShape -> 口スロット内インデックスの対応。"""

    shape_to_index: dict[MouthShape, int] = field(default_factory=lambda: dict(_DEFAULT_2STATE))

    @classmethod
    def two_state(cls, *, closed: int = 0, open_: int = 1) -> "MouthMap":
        mapping = {s: (closed if s == MouthShape.CLOSED else open_) for s in MouthShape}
        return cls(shape_to_index=mapping)

    @classmethod
    def from_config(cls, raw: dict | None) -> "MouthMap":
        """TOML の [mouth] テーブルから生成。

        例:
            [mouth]
            closed_index = 0
            open_index = 1
            # 任意で母音別:
            a_index = 2
            i_index = 3
        """
        if not raw:
            return cls()
        closed = int(raw.get("closed_index", 0))
        open_ = int(raw.get("open_index", 1))
        mapping = {s: (closed if s == MouthShape.CLOSED else open_) for s in MouthShape}
        for shape in (MouthShape.A, MouthShape.I, MouthShape.U, MouthShape.E, MouthShape.O):
            key = f"{shape.value}_index"
            if key in raw:
                mapping[shape] = int(raw[key])
        return cls(shape_to_index=mapping)

    def index_for(self, shape: MouthShape, slot: Slot) -> int:
        """口形に対応する有効インデックスを返す（スロット範囲内にクランプ）。"""
        raw = self.shape_to_index.get(shape, 0)
        return slot.resolve_index(raw)
