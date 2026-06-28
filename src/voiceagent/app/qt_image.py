"""PIL.Image -> QPixmap 変換ヘルパー。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtGui import QImage, QPixmap

if TYPE_CHECKING:
    from PIL import Image


def pil_to_qpixmap(img: "Image.Image") -> QPixmap:
    """RGBA PIL 画像を QPixmap へ変換する（データをコピーして所有権問題を避ける）。"""
    rgba = img.convert("RGBA")
    data = rgba.tobytes("raw", "RGBA")
    qimg = QImage(data, rgba.width, rgba.height, QImage.Format.Format_RGBA8888)
    return QPixmap.fromImage(qimg.copy())
