"""チャットオーバーレイ。入力欄は常時表示、メッセージは一定時間でフェードする。

「デスクトップにチャットボットではなくキャラがいる」感覚のため、履歴は残さず
時間経過で消える。返答待ちの間は「考え中…」をドットアニメーションで表示する。
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
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

_VISIBLE_MS = 9000
_FADE_MS = 1500
_THINKING_MS = 400  # ドット更新間隔

_BUBBLE_QSS = """
QLabel {
    background-color: rgba(20, 20, 30, 190);
    color: #f5f5fa;
    border-radius: 12px;
    padding: 8px 12px;
    font-size: 14px;
}
"""

_THINKING_QSS = """
QLabel {
    background-color: rgba(60, 50, 90, 190);
    color: #d8d8ff;
    border-radius: 12px;
    padding: 6px 12px;
    font-size: 13px;
}
"""

_INPUT_QSS = """
QLineEdit {
    background-color: rgba(30, 30, 40, 205);
    color: #ffffff;
    border: 1px solid rgba(140, 140, 200, 160);
    border-radius: 16px;
    padding: 8px 14px;
    font-size: 14px;
}
QLineEdit:disabled { color: rgba(255,255,255,120); }
"""


class _Bubble(QLabel):
    """一定時間で自動的にフェードアウトして消えるメッセージ。"""

    def __init__(self, text: str, *, accent: bool, parent: QWidget) -> None:
        super().__init__(text, parent)
        self.setWordWrap(True)
        self.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.setMaximumWidth(380)
        qss = _BUBBLE_QSS
        if accent:
            qss = _BUBBLE_QSS.replace("rgba(20, 20, 30, 190)", "rgba(80, 60, 120, 200)")
        self.setStyleSheet(qss)
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
    """フェードするメッセージ列 +「考え中」表示 + 常時表示の入力欄。"""

    submitted = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumHeight(240)  # メッセージが切れて見えないのを防ぐ

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        layout.addStretch(1)

        self._messages = QVBoxLayout()
        self._messages.setSpacing(6)
        self._messages.setAlignment(Qt.AlignmentFlag.AlignBottom)
        layout.addLayout(self._messages)

        self._thinking = QLabel("考え中", self)
        self._thinking.setStyleSheet(_THINKING_QSS)
        self._thinking.hide()
        layout.addWidget(self._thinking, 0, Qt.AlignmentFlag.AlignLeft)

        self._thinking_dots = 0
        self._thinking_timer = QTimer(self)
        self._thinking_timer.setInterval(_THINKING_MS)
        self._thinking_timer.timeout.connect(self._tick_thinking)

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

    # --- 「考え中…」インジケータ ----------------------------------------------

    def start_thinking(self) -> None:
        self._thinking_dots = 0
        self._thinking.setText("考え中")
        self._thinking.show()
        self._thinking_timer.start()

    def stop_thinking(self) -> None:
        self._thinking_timer.stop()
        self._thinking.hide()

    def _tick_thinking(self) -> None:
        self._thinking_dots = (self._thinking_dots + 1) % 4  # 0,1,2,3 を循環
        self._thinking.setText("考え中" + "." * self._thinking_dots)

    def set_enabled_input(self, enabled: bool) -> None:
        self._input.setEnabled(enabled)
        if enabled:
            self._input.setFocus()
