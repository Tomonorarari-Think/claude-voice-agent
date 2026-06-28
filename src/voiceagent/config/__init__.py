"""設定レイヤー。エンジン/アセットのパス、永続設定、キャラ定義のロード。"""

from voiceagent.config.characters import CharacterConfig, load_character_configs
from voiceagent.config.paths import EnginePaths, resolve_engine_paths
from voiceagent.config.settings import Settings, load_settings, save_settings

__all__ = [
    "CharacterConfig",
    "load_character_configs",
    "EnginePaths",
    "resolve_engine_paths",
    "Settings",
    "load_settings",
    "save_settings",
]
