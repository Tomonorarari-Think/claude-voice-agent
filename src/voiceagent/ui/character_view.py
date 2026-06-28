"""立ち絵表示ウィジェット。感情・口形フレームを描画し、左右反転に対応。

立ち絵領域のドラッグでウィンドウを移動できる。描画は (フレーム, 表示サイズ) 単位で
スケール済みピクスマップをキャッシュし、毎フレームの再スケールを避ける。
"""

from __future__ import annotations

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtWidgets import QWidget

from voiceagent.app.qt_image import pil_to_qpixmap
from voiceagent.character.renderer import CharacterRenderer
from voiceagent.domain.emotion import Emotion
from voiceagent.domain.phoneme import MouthShape


class CharacterView(QWidget):
    """透過背景に立ち絵を描画し、ドラッグでウィンドウを移動する。"""

    def __init__(
        self,
        renderer: CharacterRenderer,
        parent: QWidget | None = None,
        *,
        upper_body_fraction: float = 0.5,
    ) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self._renderer = renderer
        self._upper_fraction = max(0.2, min(upper_body_fraction, 1.0))
        self._flip = False
        self._emotion = Emotion.NEUTRAL
        self._shape = MouthShape.CLOSED
        self._key: tuple | None = None
        self._pixmap: QPixmap | None = None
        self._pixmap_cache: dict[tuple, QPixmap] = {}
        self._scaled: QPixmap | None = None
        self._scaled_for: tuple | None = None
        self._drag_offset: QPoint | None = None
        self._upper_body = False  # True で上半身ズーム（YouTube 風）
        # 初期表示は高速プレビュー（既定の口）。重いレイヤー合成はウォームアップ後に
        # refresh() で差し替える。背景が焼き込まれた PSD は preview() が None を返すため、
        # その場合はウォームアップ完了まで何も描かない（白背景を出さない）。
        preview = self._renderer.preview()
        if preview is not None:
            self._pixmap = pil_to_qpixmap(preview)
        self._scaled_for = None

    def refresh(self) -> None:
        """現在の状態でフレームを再構築して表示する（ウォームアップ後に呼ぶ）。"""
        self._key = None
        self._refresh_pixmap()

    # --- 状態更新 -------------------------------------------------------------

    def set_frame(self, emotion: Emotion, shape: MouthShape) -> None:
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

    def set_upper_body(self, enabled: bool) -> None:
        """上半身ズーム表示の切替（幅いっぱい・上揃えで脚を画面外へ）。"""
        if enabled == self._upper_body:
            return
        self._upper_body = enabled
        self._scaled_for = None
        self.update()

    @property
    def upper_body(self) -> bool:
        return self._upper_body

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
        self._scaled_for = None  # 再スケールが必要
        self.update()

    # --- 描画 -----------------------------------------------------------------

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt API)
        if self._pixmap is None:
            return
        cache_key = (self._key, self.width(), self.height(), self._upper_body)
        if self._scaled_for != cache_key or self._scaled is None:
            source = self._pixmap
            if self._upper_body:
                # 上から一定割合だけを切り出す（スカートが映らない程度の上半身）。
                crop_h = max(1, int(source.height() * self._upper_fraction))
                source = source.copy(0, 0, source.width(), crop_h)
            # 切り出した領域全体が収まるよう内接スケール（上揃えで脚・スカートを画面外へ）
            self._scaled = source.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self._scaled_for = cache_key
        scaled = self._scaled
        painter = QPainter(self)
        x = (self.width() - scaled.width()) // 2
        # 全身・上半身とも下揃え（立ち絵が入力欄の上にぴったり立つ。浮かない）
        y = self.height() - scaled.height()
        painter.drawPixmap(x, y, scaled)

    # --- ドラッグでウィンドウ移動 ---------------------------------------------

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            window = self.window()
            self._drag_offset = (
                event.globalPosition().toPoint() - window.frameGeometry().topLeft()
            )
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._drag_offset is not None:
            self.window().move(event.globalPosition().toPoint() - self._drag_offset)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        self._drag_offset = None
        self.setCursor(Qt.CursorShape.OpenHandCursor)
