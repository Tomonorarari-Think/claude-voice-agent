"""立ち絵スロット（排他グループ）モデルと役割解決。純粋ロジックでテスト可能。

立ち絵 PSD の慣習: `!` で始まるグループは「子のうち 1 つだけ表示」する排他スロット
（目・口・眉・体・腕など）。本モジュールは PSD 実体に依存せず、抽出済みの
レイアウト情報に対して役割解決と子選択を行う。
"""

from __future__ import annotations

from dataclasses import dataclass

# 役割 -> グループ名に含まれるキーワード（Shift-JIS の正確名を打たずに照合する）。
ROLE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "mouth": ("口",),
    "eyes": ("目",),
    "brows": ("眉",),
    "arms": ("腕",),
    "body": ("体", "Body"),
}


@dataclass(frozen=True, slots=True)
class Slot:
    """排他グループ 1 つ。`children` は表示候補レイヤー名（出現順）。"""

    role: str  # 'mouth' | 'eyes' | 'brows' | 'arms' | 'body' | 'other'
    group_name: str
    children: tuple[str, ...]

    def resolve_index(self, choice: int | str | None, *, default: int = 0) -> int:
        """子選択（index / 名前 / None）を有効なインデックスへ正規化する。"""
        if choice is None:
            return self._clamp(default)
        if isinstance(choice, int):
            return self._clamp(choice)
        # 名前: 完全一致 -> 部分一致の順
        if choice in self.children:
            return self.children.index(choice)
        for i, name in enumerate(self.children):
            if choice in name:
                return i
        return self._clamp(default)

    def _clamp(self, i: int) -> int:
        if not self.children:
            return 0
        return max(0, min(i, len(self.children) - 1))


@dataclass(frozen=True, slots=True)
class Layout:
    """1 つの立ち絵 PSD のスロット構成。"""

    size: tuple[int, int]
    slots: tuple[Slot, ...]
    has_flip_layer: bool = False  # `!Body:flipx` のような反転レイヤーを持つか

    def slot_for_role(self, role: str) -> Slot | None:
        return slot_for_role(self, role)


def classify_role(group_name: str) -> str:
    """グループ名から役割を判定する。`!` 接頭辞は無視。"""
    name = group_name.lstrip("!")
    for role, keywords in ROLE_KEYWORDS.items():
        if any(k in name for k in keywords):
            return role
    return "other"


def slot_for_role(layout: Layout, role: str) -> Slot | None:
    """指定役割の最初のスロットを返す（無ければ None）。"""
    for slot in layout.slots:
        if slot.role == role:
            return slot
    return None
