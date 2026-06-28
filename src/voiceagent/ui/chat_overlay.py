"""チャットオーバーレイ。入力欄は常時表示、メッセージは一定時間でフェードする。

「デスクトップにチャットボットではなくキャラがいる」感覚のため、履歴は残さず
時間経過で消える。
"""

from __future__ import annotations

from PySide6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtWidgets import (
    QGraphicsOpacityEffect,
    QLineEdit,
    QVBoxLayout,
    QLabel,
    QWidget,
)

_VISIBLE_MS = 8000
_FADE_MS = 1500

_BUBBLE_QSS = """
QLabel {
    background-color: rgba(20, 20, 30, 180);
    color: #f5f5fa;
    border-radius: 12px;
    padding: 8px 12px;
    font-size: 14px;
}
"""

_INPUT_QSS = """
QLineEdit {
    background-color: rgba(30, 30, 40, 200);
    color: #ffffff;
    border: 1px solid rgba(140, 140, 200, 160);
    border-radius: 16px;
    padding: 8px 14px;
    font-size: 14px;
}
"""


class _Bubble(QLabel):
    """一定時間で自動的にフェードアウトして消えるメッセージ。"""

    def __init__(self, text: str, *, accent: bool, parent: QWidget) -> None:
        super().__init__(text, parent)
        self.setWordWrap(True)
        self.setStyleSheet(_BUBBLE_QSS)
        self.setMaximumWidth(360)
        if accent:
            self.setStyleSheet(
                _BUBBLE_QSS.replace("rgba(20, 20, 30, 180)", "rgba(80, 60, 120, 190)")
            )
        self._effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._effect)
        self._effect.setOpacity(1.0)
        QTimer.singleShot(_VISIBLE_MS, self._fade_out)

    def _fade_out(self) -> None:
        self._anim = QPropertyAnimation(self._effect, b"opacity", self)
        self._anim.setDuration(_FADE_MS)
        self._anim.setStartValue(1.0)
        self._anim.setEndValue(0.0)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self._anim.finished.connect(self.deleteLater)
        self._anim.start()


class ChatOverlay(QWidget):
    """フェードするメッセージ列 + 常時表示の入力欄。"""

    submitted = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        layout.addStretch(1)

        self._messages = QVBoxLayout()
        self._messages.setSpacing(6)
        self._messages.setAlignment(Qt.AlignmentFlag.AlignBottom)
        layout.addLayout(self._messages)

        self._input = QLineEdit(self)
        self._input.setPlaceholderText("メッセージを入力…  (Enter で送信)")
        self._input.setStyleSheet(_INPUT_QSS)
        self._input.returnPressed.connect(self._on_return)
        layout.addWidget(self._input)

    def _on_return(self) -> None:
        text = self._input.text().strip()
        if not text:
            return
        self._input.clear()
        self.add_message(text, accent=True)
        self.submitted.emit(text)

    def add_message(self, text: str, *, accent: bool = False) -> None:
        bubble = _Bubble(text, accent=accent, parent=self)
        self._messages.addWidget(bubble, 0, Qt.AlignmentFlag.AlignLeft)

    def set_enabled_input(self, enabled: bool) -> None:
        self._input.setEnabled(enabled)
        if enabled:
            self._input.setFocus()
