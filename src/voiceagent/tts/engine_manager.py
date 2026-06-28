"""エンジンのライフサイクル管理。

要件: 「本体 GUI を立ち上げる必要がない場合はバックエンドだけで完結させる」。
- VOICEVOX: HTTP エンジン (`run.exe`) を必要時に **ウィンドウなし** で起動し常駐させる。
- CeVIO: `CevioEngine` 側で `StartHost(False)` によりバックエンド起動（GUI 非表示）。

各キャラに対応する `VoiceEngine` を生成・キャッシュして返す。
"""

from __future__ import annotations

import subprocess
import sys
import time

import httpx

from voiceagent.config.characters import CharacterConfig
from voiceagent.config.paths import EnginePaths
from voiceagent.domain.character import CharacterId, EngineKind
from voiceagent.tts.cevio_engine import _PROGID_CONTROL, CevioEngine
from voiceagent.tts.engine_base import EngineUnavailableError, VoiceEngine
from voiceagent.tts.voicevox_engine import VoicevoxEngine


class EngineManager:
    """キャラ -> 音声エンジンの生成と、バックエンドの起動を司る。"""

    def __init__(
        self,
        paths: EnginePaths,
        character_configs: dict[CharacterId, CharacterConfig],
    ) -> None:
        self._paths = paths
        self._configs = character_configs
        self._engines: dict[CharacterId, VoiceEngine] = {}
        self._voicevox_proc: subprocess.Popen | None = None

    # --- VOICEVOX バックエンド ------------------------------------------------

    def _voicevox_base(self) -> str:
        return f"http://{self._paths.voicevox_host}:{self._paths.voicevox_port}"

    def _voicevox_alive(self) -> bool:
        try:
            return httpx.get(f"{self._voicevox_base()}/version", timeout=1.5).status_code == 200
        except (httpx.HTTPError, OSError):
            return False

    def ensure_voicevox(self, *, startup_timeout: float = 30.0) -> None:
        """VOICEVOX エンジンが起動していなければ run.exe をウィンドウなしで起動する。"""
        if self._voicevox_alive():
            return
        exe = self._paths.voicevox_run_exe
        if not exe or not exe.exists():
            raise EngineUnavailableError(
                f"VOICEVOX エンジンが起動しておらず、run.exe も見つかりません: {exe}"
            )
        creationflags = 0
        if sys.platform == "win32":
            creationflags = subprocess.CREATE_NO_WINDOW  # コンソール窓を出さない
        self._voicevox_proc = subprocess.Popen(
            [str(exe), "--host", self._paths.voicevox_host, "--port", str(self._paths.voicevox_port)],
            creationflags=creationflags,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        deadline = time.monotonic() + startup_timeout
        while time.monotonic() < deadline:
            if self._voicevox_alive():
                return
            time.sleep(0.5)
        raise EngineUnavailableError("VOICEVOX エンジンの起動がタイムアウトしました")

    # --- CeVIO バックエンド ---------------------------------------------------

    def start_cevio_host(self) -> bool:
        """CeVIO AI ホストをバックエンド起動し、ウィンドウを最小化する。

        ここでは host プロセスを起動するだけで、Talker2（COM）は生成しない。
        実際の合成は各 worker スレッドで遅延生成され、起動済みホストへ接続する。
        呼び出しスレッドで COM を初期化するため、専用スレッドから呼ぶこと。
        戻り値は起動に成功したか。
        """
        if not any(c.engine == EngineKind.CEVIO for c in self._configs.values()):
            return False
        try:
            import pythoncom  # type: ignore
            import win32com.client  # type: ignore
        except ImportError:
            return False
        try:
            pythoncom.CoInitialize()
            control = win32com.client.Dispatch(_PROGID_CONTROL)
            control.StartHost(False)
            self._minimize_cevio_window()
            return True
        except Exception:
            return False
        finally:
            try:
                pythoncom.CoUninitialize()
            except Exception:
                pass

    @staticmethod
    def _minimize_cevio_window(*, timeout: float = 12.0) -> None:
        """CeVIO AI のメインウィンドウを探して最小化する。"""
        if sys.platform != "win32":
            return
        try:
            import win32con  # type: ignore
            import win32gui  # type: ignore
        except ImportError:
            return

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            found: list[int] = []

            def _cb(hwnd: int, _ctx) -> None:
                if not win32gui.IsWindowVisible(hwnd):
                    return
                title = win32gui.GetWindowText(hwnd)
                if title and title.startswith("CeVIO AI"):
                    found.append(hwnd)

            win32gui.EnumWindows(_cb, None)
            if found:
                for hwnd in found:
                    win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
                return
            time.sleep(0.5)

    def start_backends(self) -> dict[str, bool]:
        """VOICEVOX と CeVIO のバックエンドを起動する（専用スレッドから呼ぶ）。"""
        result: dict[str, bool] = {}
        try:
            self.ensure_voicevox()
            result["voicevox"] = True
        except EngineUnavailableError:
            result["voicevox"] = False
        result["cevio"] = self.start_cevio_host()
        return result

    # --- エンジン取得 ---------------------------------------------------------

    def get_engine(self, character: CharacterId) -> VoiceEngine:
        """キャラに対応するエンジンを返す（生成済みならキャッシュを返す）。"""
        if character in self._engines:
            return self._engines[character]

        config = self._configs[character]
        engine: VoiceEngine
        if config.engine == EngineKind.VOICEVOX:
            self.ensure_voicevox()
            engine = VoicevoxEngine(
                host=self._paths.voicevox_host,
                port=self._paths.voicevox_port,
                default_style_id=config.voicevox_default_style_id or 0,
                character=character,
            )
        elif config.engine == EngineKind.CEVIO:
            engine = CevioEngine(config, character=character)
        else:  # pragma: no cover - 将来のエンジン追加用
            raise EngineUnavailableError(f"未対応のエンジン: {config.engine}")

        self._engines[character] = engine
        return engine

    def shutdown(self) -> None:
        """起動した VOICEVOX プロセスがあれば終了する（自前で起動した場合のみ）。"""
        for engine in self._engines.values():
            close = getattr(engine, "close", None)
            if callable(close):
                close()
        self._engines.clear()
        if self._voicevox_proc is not None:
            self._voicevox_proc.terminate()
            self._voicevox_proc = None
