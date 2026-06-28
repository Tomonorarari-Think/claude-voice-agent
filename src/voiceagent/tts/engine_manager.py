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
from voiceagent.tts.cevio_engine import CevioEngine
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
