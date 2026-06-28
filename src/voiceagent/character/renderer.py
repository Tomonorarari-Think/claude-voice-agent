"""立ち絵レンダラ。

psd-tools の `composite()` はレイヤー可視性を変えるたびに全レイヤーを再合成し、
1 回あたり数秒かかる。リップシンクで口形を切り替えるたびにこれを行うと実用に耐えない。

そこで「口を隠したベース画像を 1 回だけ実合成」し、各口パーツを個別に切り出して
オーバーレイ画像にしておき、フレームごとには『ベースのコピー + 口オーバーレイの alpha 合成』
（数ミリ秒）だけ行う。表情（目・眉）が変わる場合はその選択ごとにベースを作り直す。

すべてのキャッシュ・合成はスレッドセーフ（PSDImage は共有のためロックで直列化）。
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import TYPE_CHECKING

from voiceagent.character.expression_set import ExpressionSet
from voiceagent.character.mouth_map import MouthMap
from voiceagent.character.psd_loader import (
    build_layout,
    composite_base,
    open_psd,
    slot_child_overlay,
)
from voiceagent.config.characters import CharacterConfig
from voiceagent.domain.emotion import Emotion
from voiceagent.domain.phoneme import MouthShape

if TYPE_CHECKING:
    from PIL import Image

# 合成画像の最大高さ（px）。原寸 PSD は 4000px 超で重いため、表示用に縮小する。
_MAX_FRAME_HEIGHT = 1400

_MOUTH_HIDDEN = frozenset({"mouth"})


class CharacterRenderer:
    """1 キャラの PSD からフレームを合成するレンダラ（スレッドセーフ・高速）。"""

    def __init__(
        self,
        psd_path: str | Path,
        config: CharacterConfig,
        *,
        max_height: int = _MAX_FRAME_HEIGHT,
    ) -> None:
        self._psd = open_psd(psd_path)
        self.layout = build_layout(self._psd)
        self._mouth_map = MouthMap.from_config(config.mouth_config)
        self._expr = ExpressionSet.from_config(config.expression_config)
        self._mouth_slot = self.layout.slot_for_role("mouth")
        self._max_height = max_height
        self._lock = threading.Lock()

        self._base_cache: dict[tuple, "Image.Image"] = {}  # 表情選択 -> ベース(口無し)
        self._overlay_cache: dict[int, "Image.Image"] = {}  # 口index -> オーバーレイ
        self._frame_cache: dict[tuple[Emotion, MouthShape, bool], "Image.Image"] = {}
        self._preview: "Image.Image | None" = None

    # --- 縮小 -----------------------------------------------------------------

    def _downscale(self, image: "Image.Image") -> "Image.Image":
        if image.height <= self._max_height:
            return image
        from PIL import Image as _Image

        ratio = self._max_height / image.height
        size = (max(1, round(image.width * ratio)), self._max_height)
        return image.resize(size, _Image.LANCZOS)

    # --- 初期プレビュー（高速・既定の口） -------------------------------------

    def preview(self) -> "Image.Image":
        """PSD 保存済みの合成（高速）を縮小して返す。初期表示用。

        可視性を変更する前に呼ぶこと（変更後は実合成になり遅くなる）。一度だけ計算。
        """
        if self._preview is None:
            with self._lock:
                if self._preview is None:
                    image = self._psd.composite()
                    self._preview = self._downscale(image.convert("RGBA"))
        return self._preview

    # --- ベース / オーバーレイ ------------------------------------------------

    def _base_key(self, emotion: Emotion) -> tuple:
        return tuple(sorted(self._expr.selection_for(emotion).items()))

    def _base_for(self, emotion: Emotion) -> "Image.Image":
        key = self._base_key(emotion)
        cached = self._base_cache.get(key)
        if cached is not None:
            return cached
        with self._lock:
            cached = self._base_cache.get(key)
            if cached is not None:
                return cached
            selection = dict(self._expr.selection_for(emotion))
            image = composite_base(self._psd, selection, hide_roles=_MOUTH_HIDDEN)
            image = self._downscale(image)
            self._base_cache[key] = image
            return image

    def _overlay_for(self, mouth_index: int) -> "Image.Image":
        cached = self._overlay_cache.get(mouth_index)
        if cached is not None:
            return cached
        with self._lock:
            cached = self._overlay_cache.get(mouth_index)
            if cached is not None:
                return cached
            overlay = slot_child_overlay(self._psd, "mouth", mouth_index)
            overlay = self._downscale(overlay)
            self._overlay_cache[mouth_index] = overlay
            return overlay

    # --- フレーム合成 ---------------------------------------------------------

    def render(
        self,
        emotion: Emotion,
        shape: MouthShape = MouthShape.CLOSED,
        *,
        flip: bool = False,
    ) -> "Image.Image":
        """フレーム = ベース(口無し) + 口オーバーレイ。高速・キャッシュ済み。"""
        key = (emotion, shape, flip)
        cached = self._frame_cache.get(key)
        if cached is not None:
            return cached

        base = self._base_for(emotion)
        if self._mouth_slot is not None:
            mouth_index = self._mouth_map.index_for(shape, self._mouth_slot)
            overlay = self._overlay_for(mouth_index)
            frame = base.copy()
            frame.alpha_composite(overlay)
        else:
            frame = base.copy()

        if flip:
            from PIL import Image as _Image

            frame = frame.transpose(_Image.FLIP_LEFT_RIGHT)
        self._frame_cache[key] = frame
        return frame

    def prerender_mouth_states(self, emotion: Emotion, *, flip: bool = False) -> None:
        """ある感情の口開閉フレームを事前合成し、再生中のラグを避ける。"""
        for shape in (MouthShape.CLOSED, MouthShape.A):
            self.render(emotion, shape, flip=flip)
