"""チャット履歴。

2 つの表示モード:
- ライブ（既定）: 吹き出しが一定時間でフェードして消える（キャラがいる雰囲気）。
- 履歴（「履歴」ボタン ON）: セッションの会話ログをフェードさせずスクロール表示する。

Agent の応答は 1 ターン = 1 吹き出しにまとめ、改行を含む返答もきれいに表示する。
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
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

_VISIBLE_MS = 9000
_FADE_MS = 1500
_THINKING_MS = 400

_BASE_QSS = """
QLabel {{
    background-color: {bg};
    color: #f5f5fa;
    border-radius: 12px;
    padding: 8px 12px;
    font-size: 14px;
}}
"""
_QSS = {
    "assistant": _BASE_QSS.format(bg="rgba(20, 20, 30, 195)"),
    "user": _BASE_QSS.format(bg="rgba(80, 60, 120, 205)"),
    "notice": _BASE_QSS.format(bg="rgba(60, 50, 90, 195)"),
}
_SCROLL_QSS = "QScrollArea { background: transparent; border: none; }"


class _Bubble(QLabel):
    """吹き出し。fade=True のとき一定時間後にフェードして消える。"""

    def __init__(self, text: str, kind: str, parent: QWidget, *, fade: bool) -> None:
        super().__init__(text, parent)
        self.setWordWrap(True)
        self.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        # 右クリックは独自メニューを出さず親（ウィンドウ）へ委譲する。
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setStyleSheet(_QSS[kind])
        self._effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._effect)
        self._effect.setOpacity(1.0)
        self._fade = fade
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._fade_out)
        self.touch()

    def touch(self) -> None:
        self._effect.setOpacity(1.0)
        if self._fade:
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
    """フェード（ライブ）/ 非フェード（履歴）の 2 モードを持つ会話表示。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self._scroll = QScrollArea(self)
        self._scroll.setStyleSheet(_SCROLL_QSS)
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.viewport().setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        outer.addWidget(self._scroll)

        self._content = QWidget()
        self._content.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._layout = QVBoxLayout(self._content)
        self._layout.setContentsMargins(8, 8, 8, 0)
        self._layout.setSpacing(6)
        self._layout.addStretch(1)
        self._scroll.setWidget(self._content)

        self._thinking = QLabel("考え中", self._content)
        self._thinking.setStyleSheet(_QSS["notice"])
        self._thinking.hide()
        self._layout.addWidget(self._thinking, 0, Qt.AlignmentFlag.AlignLeft)
        self._dots = 0
        self._thinking_timer = QTimer(self)
        self._thinking_timer.setInterval(_THINKING_MS)
        self._thinking_timer.timeout.connect(self._tick_thinking)

        self._log: list[tuple[str, str]] = []  # (kind, text) セッションの会話ログ
        self._persistent = False
        self._current: _Bubble | None = None
        self._current_text = ""

    # --- メッセージ -----------------------------------------------------------

    def add_user(self, text: str) -> None:
        self._finalize_assistant()
        self._log.append(("user", text))
        self._add_bubble(text, "user")
        self._scroll_to_bottom()

    def append_assistant(self, text: str) -> None:
        if self._current is None:
            self._current_text = text
            self._log.append(("assistant", text))
            self._current = self._add_bubble(text, "assistant")
        else:
            sep = "" if self._current_text.endswith(("\n", "。", "！", "？")) else " "
            self._current_text = f"{self._current_text}{sep}{text}".strip()
            self._current.set_body(self._current_text)
            if self._log and self._log[-1][0] == "assistant":
                self._log[-1] = ("assistant", self._current_text)
        self._scroll_to_bottom()

    def add_notice(self, text: str) -> None:
        self._finalize_assistant()
        self._log.append(("notice", text))
        self._add_bubble(text, "notice")
        self._scroll_to_bottom()

    def _finalize_assistant(self) -> None:
        self._current = None
        self._current_text = ""

    def _add_bubble(self, text: str, kind: str) -> _Bubble:
        bubble = _Bubble(text, kind, self._content, fade=not self._persistent)
        self._layout.insertWidget(self._layout.count() - 1, bubble)
        return bubble

    def clear(self) -> None:
        self._finalize_assistant()
        self._log.clear()
        self._clear_bubbles()

    def _clear_bubbles(self) -> None:
        for i in reversed(range(self._layout.count())):
            w = self._layout.itemAt(i).widget()
            if isinstance(w, _Bubble):
                self._layout.takeAt(i)
                w.deleteLater()

    # --- 表示モード -----------------------------------------------------------

    def set_persistent(self, on: bool) -> None:
        """履歴モードの切替。ON でログ全体を非フェード表示、OFF でライブに戻す。"""
        self._persistent = on
        self._finalize_assistant()
        self._clear_bubbles()
        if on:
            for kind, text in self._log:
                bubble = _Bubble(text, kind, self._content, fade=False)
                self._layout.insertWidget(self._layout.count() - 1, bubble)
            self._scroll_to_bottom()

    def _scroll_to_bottom(self) -> None:
        QTimer.singleShot(0, lambda: self._scroll.verticalScrollBar().setValue(
            self._scroll.verticalScrollBar().maximum()
        ))

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
