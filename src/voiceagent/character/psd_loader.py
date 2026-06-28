"""PSD のロードとレイヤー合成。

`!` 接頭辞グループを排他スロットとして扱い、役割（口・目・眉…）ごとに
表示する子を 1 つだけ選んで合成する。左右反転は合成後の画像をミラーする。

PSD 実体に依存する処理はここに閉じ込め、選択ロジック（slots.py）と分離する。
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from voiceagent.character.slots import Layout, Slot, classify_role

if TYPE_CHECKING:  # 重い依存は型のみ
    from PIL import Image
    from psd_tools import PSDImage

_SLOT_PREFIX = "!"
_FLIP_SUFFIX = ":flipx"


def open_psd(path: str | Path) -> "PSDImage":
    from psd_tools import PSDImage

    return PSDImage.open(str(path))


def build_layout(psd: "PSDImage") -> Layout:
    """PSD のトップレベルから排他スロット構成を抽出する。"""
    slots: list[Slot] = []
    has_flip = False
    for layer in psd:
        name = layer.name
        if name.endswith(_FLIP_SUFFIX) or _FLIP_SUFFIX in name:
            has_flip = True
        if layer.is_group() and name.startswith(_SLOT_PREFIX):
            children = tuple(child.name for child in layer)
            slots.append(
                Slot(role=classify_role(name), group_name=name, children=children)
            )
    return Layout(size=tuple(psd.size), slots=tuple(slots), has_flip_layer=has_flip)


def _apply_selection(psd: "PSDImage", role_selection: dict[str, int]) -> None:
    """各排他スロットで、選択した子のみ表示する。"""
    for layer in psd:
        if not (layer.is_group() and layer.name.startswith(_SLOT_PREFIX)):
            continue
        role = classify_role(layer.name)
        children = list(layer)
        if not children:
            continue
        chosen = role_selection.get(role, 0)
        chosen = max(0, min(chosen, len(children) - 1))
        layer.visible = True
        for i, child in enumerate(children):
            child.visible = i == chosen


def composite(
    psd: "PSDImage",
    role_selection: dict[str, int],
    *,
    flip: bool = False,
) -> "Image.Image":
    """役割選択に従って合成した RGBA 画像を返す。flip=True で左右反転。"""
    _apply_selection(psd, role_selection)
    image = psd.composite()
    if image is None:  # pragma: no cover - 想定外
        raise RuntimeError("PSD composite returned no image")
    image = image.convert("RGBA")
    if flip:
        from PIL import Image as _Image

        image = image.transpose(_Image.FLIP_LEFT_RIGHT)
    return image
