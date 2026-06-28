"""立ち絵表示ウィジェット。感情・口形フレームを描画し、拡大率・左右反転に対応。"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtWidgets import QWidget

from voiceagent.app.qt_image import pil_to_qpixmap
from voiceagent.character.renderer import CharacterRenderer
from voiceagent.domain.emotion import Emotion
from voiceagent.domain.phoneme import MouthShape


class CharacterView(QWidget):
    """透過背景に立ち絵を描画する。"""

    def __init__(self, renderer: CharacterRenderer, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._renderer = renderer
        self._flip = False
        self._emotion = Emotion.NEUTRAL
        self._shape = MouthShape.CLOSED
        self._key: tuple | None = None
        self._pixmap: QPixmap | None = None
        self._pixmap_cache: dict[tuple, QPixmap] = {}
        self._refresh_pixmap()

    # --- 状態更新 -------------------------------------------------------------

    def set_frame(self, emotion: Emotion, shape: MouthShape) -> None:
        """表示フレームを更新（変化が無ければ何もしない）。"""
        if (emotion, shape) == (self._emotion, self._shape):
            return
        self._emotion, self._shape = emotion, shape
        self._refresh_pixmap()

    def set_flipped(self, flipped: bool) -> None:
        if flipped == self._flip:
            return
        self._flip = flipped
        self._refresh_pixmap()

    @property
    def flipped(self) -> bool:
        return self._flip

    def _refresh_pixmap(self) -> None:
        key = (self._emotion, self._shape, self._flip)
        if key == self._key:
            return
        pixmap = self._pixmap_cache.get(key)
        if pixmap is None:
            image = self._renderer.render(self._emotion, self._shape, flip=self._flip)
            pixmap = pil_to_qpixmap(image)
            self._pixmap_cache[key] = pixmap
        self._key = key
        self._pixmap = pixmap
        self.update()

    # --- 描画 -----------------------------------------------------------------

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt API)
        if self._pixmap is None:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        scaled = self._pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        x = (self.width() - scaled.width()) // 2
        y = self.height() - scaled.height()  # 下揃え（上半身クロップしやすい）
        painter.drawPixmap(x, y, scaled)
