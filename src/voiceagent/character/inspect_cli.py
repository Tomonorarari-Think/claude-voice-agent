"""PSD レイヤー調査 CLI。

ユーザーが自分の立ち絵 PSD のスロット構成（口・目・眉の子レイヤーと
インデックス）を確認し、キャラ TOML の [mouth] / [expression] を埋めるための補助。

使い方:
    python -m voiceagent.character.inspect_cli "path/to/character.psd"
"""

from __future__ import annotations

import argparse

from voiceagent.character.psd_loader import build_layout, open_psd


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect a tachie PSD layout")
    parser.add_argument("psd_path", help="PSD ファイルのパス")
    args = parser.parse_args()

    psd = open_psd(args.psd_path)
    layout = build_layout(psd)
    print(f"size: {layout.size}, flip_layer: {layout.has_flip_layer}")
    print(f"slots ({len(layout.slots)}):")
    for slot in layout.slots:
        print(f"\n[{slot.role}] {slot.group_name!r}  ({len(slot.children)} children)")
        for i, name in enumerate(slot.children):
            print(f"  {i:3d}: {name!r}")

    mouth = layout.slot_for_role("mouth")
    if mouth:
        print("\nヒント: キャラ TOML の [mouth] に closed_index / open_index を、")
        print("       [expression.<emotion>] に eyes / brows の index を設定できます。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
