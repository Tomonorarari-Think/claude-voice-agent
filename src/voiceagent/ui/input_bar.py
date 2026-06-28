"""入力バー。常に最前面・常時表示。入力欄の直上にモデル切替と新規チャットを並べる。"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from voiceagent.claude.model_registry import MODELS

_QSS = """
QWidget#inputBar { background-color: rgba(18,18,26,170); border-radius: 12px; }
QLineEdit {
    background-color: rgba(30,30,40,215); color: #fff;
    border: 1px solid rgba(140,140,200,160); border-radius: 16px;
    padding: 8px 14px; font-size: 14px;
}
QLineEdit:disabled { color: rgba(255,255,255,120); }
QComboBox, QPushButton {
    background-color: rgba(50,50,70,210); color: #eaeaf2;
    border: none; border-radius: 8px; padding: 4px 10px; font-size: 12px;
}
QComboBox:hover, QPushButton:hover { background-color: rgba(80,80,120,230); }
"""


class InputBar(QWidget):
    """モデル切替 + 新規チャット + 入力欄。"""

    submitted = Signal(str)
    model_changed = Signal(str)
    new_topic = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("inputBar")
        self.setStyleSheet(_QSS)

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 6, 8, 8)
        root.setSpacing(6)

        top = QHBoxLayout()
        top.setSpacing(6)
        self.model_box = QComboBox(self)
        for m in MODELS:
            self.model_box.addItem(m.label, m.id)
        self.model_box.currentIndexChanged.connect(
            lambda _i: self.model_changed.emit(self.model_box.currentData())
        )
        top.addWidget(self.model_box)

        self.new_btn = QPushButton("新規チャット", self)
        self.new_btn.clicked.connect(self.new_topic.emit)
        top.addWidget(self.new_btn)
        top.addStretch(1)
        root.addLayout(top)

        self.input = QLineEdit(self)
        self.input.setPlaceholderText("メッセージを入力…  (Enter で送信)")
        self.input.returnPressed.connect(self._on_return)
        root.addWidget(self.input)

    def _on_return(self) -> None:
        text = self.input.text().strip()
        if not text:
            return
        self.input.clear()
        self.submitted.emit(text)

    def set_model(self, model_id: str) -> None:
        idx = self.model_box.findData(model_id)
        if idx >= 0:
            self.model_box.setCurrentIndex(idx)

    def set_busy(self, busy: bool) -> None:
        self.input.setEnabled(not busy)
        if not busy:
            self.input.setFocus()
