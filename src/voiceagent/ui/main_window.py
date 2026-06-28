"""メインウィンドウ。透過・フレームレス・常時最前面のデスクトップウィジェット。

立ち絵はウィンドウ全体に表示し、チャットは下部に**重ねて**フロート表示する
（チャットで立ち絵が押し上げ・拡縮されないように）。前面トグルで
「立ち絵を前面 / チャットを前面」を切り替えられる。
"""

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

_CONTROL_H = 40

_CONTROL_QSS = """
QWidget#controlBar { background-color: rgba(20,20,30,150); border-radius: 10px; }
QPushButton, QComboBox {
    background-color: rgba(50,50,70,205); color: #eaeaf2;
    border: none; border-radius: 8px; padding: 4px 8px; font-size: 12px;
}
QPushButton:hover, QComboBox:hover { background-color: rgba(80,80,120,225); }
QPushButton:checked { background-color: rgba(120,90,160,235); }
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
        layout.setSpacing(5)

        self.character_box = QComboBox(self)
        for cid in CharacterId:
            self.character_box.addItem(cid.display_name, cid)
        layout.addWidget(self.character_box)

        self.model_box = QComboBox(self)
        for m in MODELS:
            self.model_box.addItem(m.label, m.id)
        layout.addWidget(self.model_box)

        self.front_btn = QPushButton("前面:チャット", self)
        self.front_btn.setCheckable(True)
        self.front_btn.setToolTip("立ち絵とチャットの前面を切り替え")
        layout.addWidget(self.front_btn)

        self.crop_btn = QPushButton("上半身", self)
        self.crop_btn.setCheckable(True)
        layout.addWidget(self.crop_btn)

        self.flip_btn = QPushButton("反転", self)
        self.flip_btn.setCheckable(True)
        layout.addWidget(self.flip_btn)

        self.new_topic_btn = QPushButton("新", self)
        self.new_topic_btn.setToolTip("新しい話題")
        layout.addWidget(self.new_topic_btn)

        layout.addStretch(1)

        self.tray_btn = QPushButton("－", self)
        self.tray_btn.setFixedWidth(26)
        self.tray_btn.setToolTip("トレイに格納")
        layout.addWidget(self.tray_btn)

        self.close_btn = QPushButton("×", self)
        self.close_btn.setFixedWidth(26)
        self.close_btn.setToolTip("終了")
        layout.addWidget(self.close_btn)

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

    def __init__(self, controller: AppController, settings: Settings) -> None:
        super().__init__()
        self._controller = controller
        self._settings = settings
        self._renderers: dict[CharacterId, CharacterRenderer] = {}
        self._character_view: CharacterView | None = None
        self._warmer: RendererWarmer | None = None

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet(_CONTROL_QSS)

        ws = settings.window
        self.setGeometry(ws.x, ws.y, ws.width, ws.height)
        self.setMinimumSize(280, 360)

        self._player = SpeechPlayer(self)
        self._build_ui()
        self._wire()
        self._load_character(settings.active_character)
        self._setup_tray()
        self._relayout()

    # --- UI 構築 --------------------------------------------------------------

    def _build_ui(self) -> None:
        self._placeholder = QLabel("立ち絵を読み込めません。SETUP.md を参照してください。", self)
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setStyleSheet("color:#fff; background:transparent;")
        self._placeholder.hide()

        self.chat = ChatOverlay(self)
        self.control_bar = _ControlBar(self)
        self._grip = QSizeGrip(self)

        # 初期 UI 状態
        self.control_bar.character_box.setCurrentIndex(
            list(CharacterId).index(self._settings.active_character)
        )
        idx = self.control_bar.model_box.findData(self._settings.model)
        if idx >= 0:
            self.control_bar.model_box.setCurrentIndex(idx)
        self.control_bar.flip_btn.setChecked(self._settings.window.flipped)
        self.control_bar.front_btn.setChecked(True)  # 既定はチャット前面

    def _wire(self) -> None:
        self.chat.submitted.connect(self._controller.send)
        self._controller.assistant_text.connect(lambda t: self.chat.add_message(t))
        self._controller.speech_ready.connect(self._player.enqueue)
        self._controller.error.connect(lambda m: self.chat.add_message(f"⚠ {m}"))
        self._controller.busy_changed.connect(self._on_busy_changed)
        self._player.frame.connect(self._on_frame)

        self.control_bar.new_topic_btn.clicked.connect(self._on_new_topic)
        self.control_bar.flip_btn.toggled.connect(self._on_flip)
        self.control_bar.crop_btn.toggled.connect(self._on_crop)
        self.control_bar.front_btn.toggled.connect(self._on_front_toggle)
        self.control_bar.model_box.currentIndexChanged.connect(self._on_model_changed)
        self.control_bar.character_box.currentIndexChanged.connect(self._on_character_changed)
        self.control_bar.tray_btn.clicked.connect(self.hide)
        self.control_bar.close_btn.clicked.connect(self._quit)

    # --- レイアウト（手動配置・重ね表示） -------------------------------------

    def _relayout(self) -> None:
        w, h = self.width(), self.height()
        self.control_bar.setGeometry(0, 0, w, _CONTROL_H)
        body_top = _CONTROL_H
        if self._character_view is not None:
            self._character_view.setGeometry(0, body_top, w, h - body_top)
        self._placeholder.setGeometry(0, body_top, w, h - body_top)
        chat_h = max(220, int(h * 0.42))
        self.chat.setGeometry(0, h - chat_h, w, chat_h)
        self._grip.setGeometry(w - 18, h - 18, 18, 18)
        self._apply_z_order()

    def _apply_z_order(self) -> None:
        chat_front = self.control_bar.front_btn.isChecked()
        if chat_front:
            # チャット前面: 立ち絵の上に重ねて表示
            if self._character_view is not None:
                self._character_view.lower()
            self.chat.show()
            self.chat.raise_()
            self.chat.set_enabled_input(not self._controller.is_busy)
        else:
            # 立ち絵前面: チャットは隠す（透過部分から透けないように）
            self.chat.hide()
            if self._character_view is not None:
                self._character_view.raise_()
        self._grip.raise_()
        self.control_bar.raise_()  # 操作バーは常に最前面

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._relayout()

    # --- キャラ切替・描画 -----------------------------------------------------

    def _get_renderer(self, character: CharacterId) -> CharacterRenderer | None:
        if character in self._renderers:
            return self._renderers[character]
        psd = resolve_psd_path(self._settings, character)
        if psd is None:
            return None
        renderer = CharacterRenderer(psd, self._controller.configs[character])
        self._renderers[character] = renderer
        return renderer

    def _load_character(self, character: CharacterId) -> None:
        if self._character_view is not None:
            self._character_view.deleteLater()
            self._character_view = None
        renderer = self._get_renderer(character)
        if renderer is None:
            self._placeholder.show()
            return
        self._placeholder.hide()
        view = CharacterView(renderer, self)
        view.set_flipped(self.control_bar.flip_btn.isChecked())
        view.set_upper_body(self.control_bar.crop_btn.isChecked())
        view.show()
        self._character_view = view
        self._relayout()
        self._warm_renderer(renderer, view)

    def _warm_renderer(self, renderer, view: CharacterView) -> None:
        warmer = RendererWarmer(renderer, Emotion.NEUTRAL, self)
        warmer.warmed.connect(view.refresh)
        warmer.finished.connect(warmer.deleteLater)
        self._warmer = warmer
        warmer.start()

    def _on_frame(self, emotion, shape) -> None:
        if self._character_view is not None:
            self._character_view.set_frame(emotion, shape)

    def _on_busy_changed(self, busy: bool) -> None:
        self.chat.set_enabled_input(not busy and self.control_bar.front_btn.isChecked())
        if busy:
            self.chat.start_thinking()
        else:
            self.chat.stop_thinking()

    # --- コントロール ---------------------------------------------------------

    def _on_new_topic(self) -> None:
        self._controller.new_topic()
        self._player.clear()
        self.chat.add_message("（新しい話題をはじめます）")

    def _on_flip(self, checked: bool) -> None:
        if self._character_view is not None:
            self._character_view.set_flipped(checked)

    def _on_crop(self, checked: bool) -> None:
        self.control_bar.crop_btn.setText("全身" if checked else "上半身")
        if self._character_view is not None:
            self._character_view.set_upper_body(checked)

    def _on_front_toggle(self, chat_front: bool) -> None:
        self.control_bar.front_btn.setText("前面:チャット" if chat_front else "前面:キャラ")
        self._apply_z_order()

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
        """アプリを完全終了する（プロセスを残さない）。"""
        from PySide6.QtWidgets import QApplication

        self._persist()
        self._player.clear()
        self._tray.hide()
        QApplication.quit()  # main 側で engines.shutdown -> os._exit する
