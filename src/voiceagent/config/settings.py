"""永続設定（ユーザー環境固有）。local_settings.json に保存（.gitignore 対象）。"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path

from voiceagent.domain.character import CharacterId

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_SETTINGS_PATH = _REPO_ROOT / "local_settings.json"

_DEFAULT_MODEL = "claude-opus-4-8"


@dataclass(frozen=True, slots=True)
class WindowState:
    x: int = 100
    y: int = 100
    width: int = 460
    height: int = 820
    flipped: bool = False
    character_scale: float = 1.0
    click_through: bool = False


@dataclass(frozen=True, slots=True)
class Settings:
    """アプリの永続設定。すべて不変。更新は replace で新インスタンスを作る。"""

    active_character: CharacterId = CharacterId.KASUKABE_TSUMUGI
    model: str = _DEFAULT_MODEL
    asset_root: str | None = None
    voicevox_run_exe: str | None = None
    cevio_dir: str | None = None
    project_path: str | None = None  # Claude Code の作業ディレクトリ（cwd）
    window: WindowState = field(default_factory=WindowState)

    def with_model(self, model: str) -> "Settings":
        return replace(self, model=model)

    def with_character(self, character: CharacterId) -> "Settings":
        return replace(self, active_character=character)

    def with_window(self, window: WindowState) -> "Settings":
        return replace(self, window=window)


def load_settings(path: Path = _DEFAULT_SETTINGS_PATH) -> Settings:
    """設定をロード。存在しなければ既定値を返す（副作用なし）。"""
    if not path.exists():
        return Settings()
    raw = json.loads(path.read_text(encoding="utf-8"))
    window = WindowState(**raw.pop("window", {}))
    char = raw.pop("active_character", None)
    settings = Settings(
        active_character=CharacterId(char) if char else Settings().active_character,
        window=window,
        **raw,
    )
    return settings


def save_settings(settings: Settings, path: Path = _DEFAULT_SETTINGS_PATH) -> None:
    """設定を JSON で保存する。"""
    data = asdict(settings)
    data["active_character"] = settings.active_character.value
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
