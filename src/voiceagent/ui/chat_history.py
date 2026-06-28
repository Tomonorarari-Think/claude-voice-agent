"""チャット履歴。入力欄と同じ横幅の吹き出しを、一定時間でフェード表示する。

Agent の応答は 1 ターン = 1 吹き出しにまとめ、改行を含む返答もきれいに表示する。
履歴は「キャラの前面/背面」を切り替えられる（入力欄は常に最前面・別ウィジェット）。
"""

from __future__ import annotations

from PySide6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    Qt,
    QTimer,
)
from PySide6.QtWidgets import (
    QGraphicsOpacityEffect,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

_VISIBLE_MS = 9000
_FADE_MS = 1500
_THINKING_MS = 400

_BUBBLE_QSS = """
QLabel {
    background-color: rgba(20, 20, 30, 195);
    color: #f5f5fa;
    border-radius: 12px;
    padding: 8px 12px;
    font-size: 14px;
}
"""
_USER_QSS = _BUBBLE_QSS.replace("rgba(20, 20, 30, 195)", "rgba(80, 60, 120, 205)")
_THINKING_QSS = _BUBBLE_QSS.replace("rgba(20, 20, 30, 195)", "rgba(60, 50, 90, 195)")


class _Bubble(QLabel):
    """入力欄幅いっぱいの吹き出し。一定時間後にフェードして消える。"""

    def __init__(self, text: str, qss: str, parent: QWidget) -> None:
        super().__init__(text, parent)
        self.setWordWrap(True)
        self.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setStyleSheet(qss)
        self._effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._effect)
        self._effect.setOpacity(1.0)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._fade_out)
        self.touch()

    def touch(self) -> None:
        """表示時間を延長（更新中の吹き出しを消さない）。"""
        self._effect.setOpacity(1.0)
        self._timer.start(_VISIBLE_MS)

    def set_body(self, text: str) -> None:
        self.setText(text)
        self.touch()

    def _fade_out(self) -> None:
        self._anim = QPropertyAnimation(self._effect, b"opacity", self)
        self._anim.setDuration(_FADE_MS)
        self._anim.setStartValue(1.0)
        self._anim.setEndValue(0.0)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self._anim.finished.connect(self.deleteLater)
        self._anim.start()


class ChatHistory(QWidget):
    """フェードする吹き出しの履歴。Agent 応答はターン単位で 1 吹き出しに集約。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 0)
        layout.setSpacing(6)
        layout.addStretch(1)
        self._layout = layout

        self._current_assistant: _Bubble | None = None
        self._assistant_text = ""

        self._thinking = QLabel("考え中", self)
        self._thinking.setStyleSheet(_THINKING_QSS)
        self._thinking.hide()
        layout.addWidget(self._thinking, 0, Qt.AlignmentFlag.AlignLeft)
        self._dots = 0
        self._thinking_timer = QTimer(self)
        self._thinking_timer.setInterval(_THINKING_MS)
        self._thinking_timer.timeout.connect(self._tick_thinking)

    # --- メッセージ -----------------------------------------------------------

    def add_user(self, text: str) -> None:
        self._finalize_assistant()
        self._add_bubble(text, _USER_QSS)

    def append_assistant(self, text: str) -> None:
        """Agent の文を現在ターンの吹き出しに追記（改行を含めて整形表示）。"""
        if self._current_assistant is None:
            self._assistant_text = text
            self._current_assistant = self._add_bubble(text, _BUBBLE_QSS)
        else:
            sep = "" if self._assistant_text.endswith(("\n", "。", "！", "？")) else " "
            self._assistant_text = f"{self._assistant_text}{sep}{text}".strip()
            self._current_assistant.set_body(self._assistant_text)

    def add_notice(self, text: str) -> None:
        self._finalize_assistant()
        self._add_bubble(text, _THINKING_QSS)

    def _finalize_assistant(self) -> None:
        self._current_assistant = None
        self._assistant_text = ""

    def _add_bubble(self, text: str, qss: str) -> _Bubble:
        bubble = _Bubble(text, qss, self)
        # 「考え中」表示の直前（最後から2番目）に挿入し、入力寄りに新しいものを並べる
        self._layout.insertWidget(self._layout.count() - 1, bubble)
        return bubble

    def clear(self) -> None:
        self._finalize_assistant()
        for i in reversed(range(self._layout.count())):
            w = self._layout.itemAt(i).widget()
            if isinstance(w, _Bubble):
                self._layout.takeAt(i)
                w.deleteLater()

    # --- 考え中インジケータ ---------------------------------------------------

    def start_thinking(self) -> None:
        self._dots = 0
        self._thinking.setText("考え中")
        self._thinking.show()
        self._thinking_timer.start()

    def stop_thinking(self) -> None:
        self._thinking_timer.stop()
        self._thinking.hide()

    def _tick_thinking(self) -> None:
        self._dots = (self._dots + 1) % 4
        self._thinking.setText("考え中" + "." * self._dots)
