"""メインウィンドウ。透過・フレームレス・常時最前面のデスクトップウィジェット。"""

from __future__ import annotations

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QAction, QIcon, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QSizeGrip,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from voiceagent.app.assets import resolve_psd_path
from voiceagent.app.controller import AppController
from voiceagent.app.speech_player import SpeechPlayer
from voiceagent.app.startup import RendererWarmer
from voiceagent.character.renderer import CharacterRenderer
from voiceagent.claude.model_registry import MODELS
from voiceagent.config.settings import Settings, WindowState, save_settings
from voiceagent.domain.character import CharacterId
from voiceagent.domain.emotion import Emotion
from voiceagent.ui.character_view import CharacterView
from voiceagent.ui.chat_overlay import ChatOverlay

_CONTROL_QSS = """
QWidget#controlBar { background-color: rgba(20,20,30,140); border-radius: 10px; }
QPushButton, QComboBox {
    background-color: rgba(50,50,70,200); color: #eaeaf2;
    border: none; border-radius: 8px; padding: 4px 10px; font-size: 12px;
}
QPushButton:hover, QComboBox:hover { background-color: rgba(80,80,120,220); }
QPushButton#flip:checked { background-color: rgba(120,90,160,230); }
"""


class _ControlBar(QWidget):
    """ドラッグでウィンドウ移動できる操作バー。"""

    def __init__(self, window: "MainWindow") -> None:
        super().__init__(window)
        self.setObjectName("controlBar")
        self._window = window
        self._drag_offset: QPoint | None = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        self.character_box = QComboBox(self)
        for cid in CharacterId:
            self.character_box.addItem(cid.display_name, cid)
        layout.addWidget(self.character_box)

        self.model_box = QComboBox(self)
        for m in MODELS:
            self.model_box.addItem(m.label, m.id)
        layout.addWidget(self.model_box)

        self.flip_btn = QPushButton("反転", self)
        self.flip_btn.setObjectName("flip")
        self.flip_btn.setCheckable(True)
        layout.addWidget(self.flip_btn)

        self.new_topic_btn = QPushButton("新しい話題", self)
        layout.addWidget(self.new_topic_btn)

        layout.addStretch(1)

        self.hide_btn = QPushButton("×", self)
        self.hide_btn.setFixedWidth(28)
        layout.addWidget(self.hide_btn)

    # ウィンドウ移動
    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = (
                event.globalPosition().toPoint() - self._window.frameGeometry().topLeft()
            )

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._drag_offset is not None:
            self._window.move(event.globalPosition().toPoint() - self._drag_offset)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        self._drag_offset = None


class MainWindow(QWidget):
    """立ち絵 + チャット + 操作をまとめたデスクトップ常駐ウィンドウ。"""

    def __init__(
        self,
        controller: AppController,
        settings: Settings,
    ) -> None:
        super().__init__()
        self._controller = controller
        self._settings = settings
        self._renderers: dict[CharacterId, CharacterRenderer] = {}

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool  # タスクバーに出さない
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet(_CONTROL_QSS)

        ws = settings.window
        self.setGeometry(ws.x, ws.y, ws.width, ws.height)

        self._player = SpeechPlayer(self)
        self._build_ui()
        self._wire()
        self._load_character(settings.active_character)
        self._setup_tray()

    # --- UI 構築 --------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(4)

        self.control_bar = _ControlBar(self)
        root.addWidget(self.control_bar)

        self._char_container = QVBoxLayout()
        root.addLayout(self._char_container, 3)  # 立ち絵を主役に
        self._char_placeholder = QLabel("立ち絵を読み込めません。SETUP.md を参照してください。", self)
        self._char_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._char_placeholder.setStyleSheet("color:#ffffff; background:transparent;")
        self._char_container.addWidget(self._char_placeholder)
        self._character_view: CharacterView | None = None

        self.chat = ChatOverlay(self)
        root.addWidget(self.chat)

        grip_row = QHBoxLayout()
        grip_row.addStretch(1)
        grip_row.addWidget(QSizeGrip(self), 0, Qt.AlignmentFlag.AlignRight)
        root.addLayout(grip_row)

        # 初期 UI 状態
        self.control_bar.character_box.setCurrentIndex(
            list(CharacterId).index(self._settings.active_character)
        )
        idx = self.control_bar.model_box.findData(self._settings.model)
        if idx >= 0:
            self.control_bar.model_box.setCurrentIndex(idx)
        self.control_bar.flip_btn.setChecked(self._settings.window.flipped)

    def _wire(self) -> None:
        self.chat.submitted.connect(self._controller.send)
        self._controller.assistant_text.connect(lambda t: self.chat.add_message(t))
        self._controller.speech_ready.connect(self._player.enqueue)
        self._controller.error.connect(lambda m: self.chat.add_message(f"⚠ {m}"))
        self._controller.busy_changed.connect(self._on_busy_changed)
        self._player.frame.connect(self._on_frame)

        self.control_bar.new_topic_btn.clicked.connect(self._on_new_topic)
        self.control_bar.flip_btn.toggled.connect(self._on_flip)
        self.control_bar.model_box.currentIndexChanged.connect(self._on_model_changed)
        self.control_bar.character_box.currentIndexChanged.connect(self._on_character_changed)
        self.control_bar.hide_btn.clicked.connect(self.hide)

    # --- キャラ切替・描画 -----------------------------------------------------

    def _get_renderer(self, character: CharacterId) -> CharacterRenderer | None:
        if character in self._renderers:
            return self._renderers[character]
        psd = resolve_psd_path(self._settings, character)
        if psd is None:
            return None
        config = self._controller.configs[character]
        renderer = CharacterRenderer(psd, config)
        self._renderers[character] = renderer
        return renderer

    def _load_character(self, character: CharacterId) -> None:
        if self._character_view is not None:
            self._character_view.deleteLater()
            self._character_view = None
        renderer = self._get_renderer(character)
        if renderer is None:
            self._char_placeholder.show()
            return
        self._char_placeholder.hide()
        view = CharacterView(renderer, self)
        view.set_flipped(self.control_bar.flip_btn.isChecked())
        self._char_container.addWidget(view)
        self._character_view = view
        self._warm_renderer(renderer, view)

    def _on_frame(self, emotion, shape) -> None:
        if self._character_view is not None:
            self._character_view.set_frame(emotion, shape)

    def _on_busy_changed(self, busy: bool) -> None:
        self.chat.set_enabled_input(not busy)
        if busy:
            self.chat.start_thinking()
        else:
            self.chat.stop_thinking()

    def _warm_renderer(self, renderer, view: CharacterView) -> None:
        """口開閉フレームを別スレッドで合成し、完了後に立ち絵を表示する（初回ラグ回避）。"""
        warmer = RendererWarmer(renderer, Emotion.NEUTRAL, self)
        warmer.warmed.connect(view.refresh)
        warmer.finished.connect(warmer.deleteLater)
        self._warmer = warmer  # GC 防止
        warmer.start()

    # --- コントロール ---------------------------------------------------------

    def _on_new_topic(self) -> None:
        self._controller.new_topic()
        self._player.clear()
        self.chat.add_message("（新しい話題をはじめます）")

    def _on_flip(self, checked: bool) -> None:
        if self._character_view is not None:
            self._character_view.set_flipped(checked)

    def _on_model_changed(self, _index: int) -> None:
        self._controller.set_model(self.control_bar.model_box.currentData())

    def _on_character_changed(self, _index: int) -> None:
        character = self.control_bar.character_box.currentData()
        self._controller.set_character(character)
        self._player.clear()
        self._load_character(character)

    # --- トレイ・終了 ---------------------------------------------------------

    def _setup_tray(self) -> None:
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.GlobalColor.darkCyan)
        self._tray = QSystemTrayIcon(QIcon(pixmap), self)
        self._tray.setToolTip("VoiceAgent")
        menu = QMenu()
        show_action = QAction("表示", self)
        show_action.triggered.connect(self.showNormal)
        quit_action = QAction("終了", self)
        quit_action.triggered.connect(self._quit)
        menu.addAction(show_action)
        menu.addAction(quit_action)
        self._tray.setContextMenu(menu)
        self._tray.activated.connect(
            lambda reason: self.showNormal()
            if reason == QSystemTrayIcon.ActivationReason.Trigger
            else None
        )
        self._tray.show()

    def _current_window_state(self) -> WindowState:
        g = self.geometry()
        return WindowState(
            x=g.x(),
            y=g.y(),
            width=g.width(),
            height=g.height(),
            flipped=self.control_bar.flip_btn.isChecked(),
            character_scale=self._settings.window.character_scale,
        )

    def _persist(self) -> None:
        self._settings = self._controller.settings.with_window(self._current_window_state())
        save_settings(self._settings)

    def _quit(self) -> None:
        self._persist()
        self._tray.hide()
        from PySide6.QtWidgets import QApplication

        QApplication.quit()

    def closeEvent(self, event) -> None:  # noqa: N802
        self._persist()
        super().closeEvent(event)
