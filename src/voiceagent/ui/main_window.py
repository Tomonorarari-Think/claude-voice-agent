"""メインウィンドウ。透過・フレームレス・常時最前面のデスクトップウィジェット。

立ち絵はウィンドウ全体に表示。入力バー（モデル切替＋新規チャット＋入力欄）は常に最前面・
常時表示。チャット履歴はキャラの前面/背面を切り替え可能。操作は**キャラ上で右クリック**の
メニューに集約し、普段はボタンを表示しない。
"""

from __future__ import annotations

import os

from PySide6.QtGui import QAction, QActionGroup, QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMenu,
    QSizeGrip,
    QSystemTrayIcon,
    QWidget,
)
from PySide6.QtCore import Qt

from voiceagent.app.assets import resolve_psd_path
from voiceagent.app.controller import AppController
from voiceagent.app.speech_player import SpeechPlayer
from voiceagent.app.startup import RendererWarmer
from voiceagent.character.renderer import CharacterRenderer
from voiceagent.config.settings import Settings, WindowState, save_settings
from voiceagent.domain.character import CharacterId
from voiceagent.domain.emotion import Emotion
from voiceagent.ui.character_view import CharacterView
from voiceagent.ui.chat_history import ChatHistory
from voiceagent.ui.input_bar import InputBar


class MainWindow(QWidget):
    """立ち絵 + チャット + 操作（右クリックメニュー）のデスクトップ常駐ウィンドウ。"""

    def __init__(self, controller: AppController, settings: Settings) -> None:
        super().__init__()
        self._controller = controller
        self._settings = settings
        self._renderers: dict[CharacterId, CharacterRenderer] = {}
        self._character_view: CharacterView | None = None
        self._warmer: RendererWarmer | None = None
        self._flip = settings.window.flipped
        self._upper = False
        self._history_front = True

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        ws = settings.window
        self.setGeometry(ws.x, ws.y, ws.width, ws.height)
        self.setMinimumSize(280, 380)

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

        self.history = ChatHistory(self)
        self.input_bar = InputBar(self)
        self.input_bar.set_model(self._settings.model)
        self._grip = QSizeGrip(self)

    def _wire(self) -> None:
        self.input_bar.submitted.connect(self._on_submit)
        self.input_bar.model_changed.connect(self._controller.set_model)
        self.input_bar.new_topic.connect(self._on_new_topic)
        self.input_bar.history_toggled.connect(self._on_history_toggled)

        self._controller.assistant_text.connect(self.history.append_assistant)
        self._controller.speech_ready.connect(self._player.enqueue)
        self._controller.error.connect(lambda m: self.history.add_notice(f"⚠ {m}"))
        self._controller.busy_changed.connect(self._on_busy_changed)
        self._player.frame.connect(self._on_frame)

    # --- レイアウト（手動配置・重ね表示） -------------------------------------

    def _relayout(self) -> None:
        w, h = self.width(), self.height()
        input_h = self.input_bar.sizeHint().height()
        input_top = h - input_h - 8
        # 立ち絵は入力欄の上までを占有（下揃えで描画 → 浮かずに入力欄の上に立つ）
        if self._character_view is not None:
            self._character_view.setGeometry(0, 0, w, input_top)
        self._placeholder.setGeometry(0, 0, w, input_top)

        self.input_bar.setGeometry(8, input_top, w - 16, input_h)
        hist_h = max(160, int(h * 0.5))
        self.history.setGeometry(0, max(0, input_top - hist_h), w, hist_h)
        self._grip.setGeometry(w - 16, h - 16, 16, 16)
        self._apply_z_order()

    def _apply_z_order(self) -> None:
        self.history.show()
        if self._history_front:
            if self._character_view is not None:
                self._character_view.lower()
            self.history.raise_()
        else:
            # 履歴をキャラの背面に（透過部分から覗く）
            self.history.lower()
            if self._character_view is not None:
                self._character_view.raise_()
        self.input_bar.raise_()  # 入力バーは常に最前面
        self._grip.raise_()

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
        fraction = self._controller.configs[character].upper_body_fraction
        view = CharacterView(renderer, self, upper_body_fraction=fraction)
        view.set_flipped(self._flip)
        view.set_upper_body(self._upper)
        view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        view.customContextMenuRequested.connect(
            lambda pos, v=view: self._show_menu(v.mapToGlobal(pos))
        )
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
        self.input_bar.set_busy(busy)
        if busy:
            self.history.start_thinking()
        else:
            self.history.stop_thinking()

    # --- 操作 -----------------------------------------------------------------

    def _on_submit(self, text: str) -> None:
        self.history.add_user(text)
        self._controller.send(text)

    def _on_new_topic(self) -> None:
        self._controller.new_topic()
        self._player.clear()
        self.history.clear()
        self.history.add_notice("（新しい話題をはじめます）")

    def _set_character(self, character: CharacterId) -> None:
        if character == self._settings.active_character:
            return
        self._settings = self._settings.with_character(character)
        self._controller.set_character(character)
        self._player.clear()
        self.history.clear()
        self._load_character(character)

    def _toggle_flip(self) -> None:
        self._flip = not self._flip
        if self._character_view is not None:
            self._character_view.set_flipped(self._flip)

    def _toggle_upper(self) -> None:
        self._upper = not self._upper
        if self._character_view is not None:
            self._character_view.set_upper_body(self._upper)

    def _toggle_history_front(self) -> None:
        self._history_front = not self._history_front
        self._apply_z_order()

    def _on_history_toggled(self, persistent: bool) -> None:
        # 履歴 ON: セッションのログを非フェードで一覧表示。OFF: ライブ（フェード）表示。
        self.history.set_persistent(persistent)
        self._apply_z_order()

    # --- 右クリックメニュー ---------------------------------------------------

    def _show_menu(self, global_pos) -> None:
        menu = QMenu(self)

        char_menu = menu.addMenu("キャラクター")
        group = QActionGroup(char_menu)
        group.setExclusive(True)
        for cid in CharacterId:
            act = QAction(cid.display_name, char_menu, checkable=True)
            act.setChecked(cid == self._settings.active_character)
            act.triggered.connect(lambda _c, c=cid: self._set_character(c))
            group.addAction(act)
            char_menu.addAction(act)

        flip = QAction("左右反転", menu, checkable=True)
        flip.setChecked(self._flip)
        flip.triggered.connect(self._toggle_flip)
        menu.addAction(flip)

        upper = QAction("上半身表示", menu, checkable=True)
        upper.setChecked(self._upper)
        upper.triggered.connect(self._toggle_upper)
        menu.addAction(upper)

        front = QAction("チャット履歴を前面", menu, checkable=True)
        front.setChecked(self._history_front)
        front.triggered.connect(self._toggle_history_front)
        menu.addAction(front)

        menu.addSeparator()
        tray = QAction("トレイに格納", menu)
        tray.triggered.connect(self.hide)
        menu.addAction(tray)
        quit_act = QAction("終了", menu)
        quit_act.triggered.connect(self._quit)
        menu.addAction(quit_act)

        menu.exec(global_pos)

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

    def _persist(self) -> None:
        g = self.geometry()
        window = WindowState(
            x=g.x(), y=g.y(), width=g.width(), height=g.height(),
            flipped=self._flip,
            character_scale=self._settings.window.character_scale,
        )
        self._settings = self._controller.settings.with_window(window)
        save_settings(self._settings)

    def _quit(self) -> None:
        """アプリを完全終了する（プロセスを確実に終了）。"""
        try:
            self._persist()
            self._player.clear()
            self._tray.hide()
            self._controller.shutdown()
        finally:
            QApplication.quit()
            os._exit(0)  # 残留プロセス防止（QThread / 子プロセスを確実に断つ）

    def closeEvent(self, event) -> None:  # noqa: N802
        event.ignore()
        self._quit()
