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


def _apply_selection(
    psd: "PSDImage",
    role_selection: dict[str, int],
    *,
    hide_roles: frozenset[str] = frozenset(),
) -> None:
    """制御対象スロット（口・目・眉など）のみ、選択した子だけを表示する。

    体パーツやアクセサリーなどの非排他グループ（複数レイヤーを同時表示）は
    PSD のデフォルト表示を保つため、`role_selection` に含まれる役割だけを操作する。
    `hide_roles` に指定した役割のグループは全子を非表示にする（口を消したベース合成用）。
    """
    for layer in psd:
        if not (layer.is_group() and layer.name.startswith(_SLOT_PREFIX)):
            continue
        role = classify_role(layer.name)
        if role in hide_roles:
            layer.visible = True
            for child in layer:
                child.visible = False
            continue
        if role not in role_selection:
            continue  # 非制御グループ（体・アクセサリー等）は既定の見た目を維持
        children = list(layer)
        if not children:
            continue
        chosen = max(0, min(role_selection[role], len(children) - 1))
        layer.visible = True
        for i, child in enumerate(children):
            child.visible = i == chosen


def find_group_by_role(psd: "PSDImage", role: str):
    """指定役割の `!` スロットグループ（PSD レイヤー）を返す。無ければ None。"""
    for layer in psd:
        if layer.is_group() and layer.name.startswith(_SLOT_PREFIX):
            if classify_role(layer.name) == role:
                return layer
    return None


def composite_base(
    psd: "PSDImage",
    role_selection: dict[str, int],
    *,
    hide_roles: frozenset[str] = frozenset(),
) -> "Image.Image":
    """口などを隠したベース画像を実合成して返す（高コスト・1 回だけ）。"""
    _apply_selection(psd, role_selection, hide_roles=hide_roles)
    image = psd.composite(force=True)
    if image is None:  # pragma: no cover
        raise RuntimeError("PSD composite returned no image")
    return image.convert("RGBA")


def slot_child_overlay(psd: "PSDImage", role: str, index: int) -> "Image.Image":
    """指定スロットの 1 子レイヤーを、PSD 全体サイズの透明キャンバス上に配置して返す。

    ベース画像へ alpha 合成するためのオーバーレイ（口パーツ等）。
    """
    from PIL import Image as _Image

    canvas = _Image.new("RGBA", psd.size, (0, 0, 0, 0))
    group = find_group_by_role(psd, role)
    if group is None:
        return canvas
    children = list(group)
    if not children:
        return canvas
    index = max(0, min(index, len(children) - 1))
    child = children[index]

    # ベース合成で口を隠した状態（child.visible=False）だと composite() が空になるため、
    # 一時的に対象の子だけ可視化してから切り出し、元の状態へ戻す。
    prev_group = group.visible
    prev_children = [c.visible for c in children]
    group.visible = True
    for i, c in enumerate(children):
        c.visible = i == index
    try:
        sub = child.composite()
    finally:
        group.visible = prev_group
        for c, vis in zip(children, prev_children):
            c.visible = vis

    if sub is None:
        return canvas
    sub = sub.convert("RGBA")
    canvas.alpha_composite(sub, (int(child.left), int(child.top)))
    return canvas


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
