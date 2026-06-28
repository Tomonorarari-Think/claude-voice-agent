"""立ち絵レンダラ。感情と口形からフレーム画像を合成・キャッシュする。

リップシンクは少数のフレーム（感情ベース × 口形）に限られるため、
合成結果を (感情, 口形, 反転) でキャッシュして再利用する。
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from voiceagent.character.expression_set import ExpressionSet
from voiceagent.character.mouth_map import MouthMap
from voiceagent.character.psd_loader import build_layout, composite, open_psd
from voiceagent.config.characters import CharacterConfig
from voiceagent.domain.emotion import Emotion
from voiceagent.domain.phoneme import MouthShape

if TYPE_CHECKING:
    from PIL import Image


class CharacterRenderer:
    """1 キャラの PSD からフレームを合成するレンダラ。"""

    def __init__(self, psd_path: str | Path, config: CharacterConfig) -> None:
        self._psd = open_psd(psd_path)
        self.layout = build_layout(self._psd)
        self._mouth_map = MouthMap.from_config(config.mouth_config)
        self._expr = ExpressionSet.from_config(config.expression_config)
        self._cache: dict[tuple[Emotion, MouthShape, bool], "Image.Image"] = {}

    def _selection(self, emotion: Emotion, shape: MouthShape) -> dict[str, int]:
        selection = self._expr.selection_for(emotion)
        mouth_slot = self.layout.slot_for_role("mouth")
        if mouth_slot is not None:
            selection["mouth"] = self._mouth_map.index_for(shape, mouth_slot)
        return selection

    def render(
        self,
        emotion: Emotion,
        shape: MouthShape = MouthShape.CLOSED,
        *,
        flip: bool = False,
    ) -> "Image.Image":
        """感情・口形・反転に対応するフレーム画像を返す（キャッシュ）。"""
        key = (emotion, shape, flip)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        image = composite(self._psd, self._selection(emotion, shape), flip=flip)
        self._cache[key] = image
        return image

    def prerender_mouth_states(self, emotion: Emotion, *, flip: bool = False) -> None:
        """ある感情の口開閉フレームを事前合成し、再生中のラグを避ける。"""
        for shape in (MouthShape.CLOSED, MouthShape.A):
            self.render(emotion, shape, flip=flip)
