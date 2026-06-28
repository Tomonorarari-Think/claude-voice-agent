"""設定レイヤーのテスト。"""

import json

from voiceagent.config import (
    Settings,
    load_character_configs,
    load_settings,
    resolve_engine_paths,
    save_settings,
)
from voiceagent.config.settings import WindowState
from voiceagent.domain.character import CharacterId, EngineKind
from voiceagent.domain.emotion import Emotion


def test_resolve_engine_paths_from_md(tmp_path):
    md = tmp_path / "VoiceAppPath.md"
    md.write_text(
        "## VOICEVOX\nE:\\VOICEVOX\\vv-engine\\run.exe\n\n## CeVIO AI\nD:\\CeVIO\\CeVIO AI\n",
        encoding="utf-8",
    )
    paths = resolve_engine_paths(md_path=md)
    assert paths.voicevox_run_exe.name == "run.exe"
    assert paths.cevio_dir.name == "CeVIO AI"
    assert paths.voicevox_port == 50021


def test_resolve_engine_paths_explicit_override(tmp_path):
    md = tmp_path / "none.md"
    paths = resolve_engine_paths(voicevox_run_exe="X:\\vv\\run.exe", md_path=md)
    assert str(paths.voicevox_run_exe).endswith("run.exe")
    assert paths.cevio_dir is None


def test_settings_roundtrip(tmp_path):
    path = tmp_path / "local_settings.json"
    s = Settings(model="claude-sonnet-4-6").with_character(CharacterId.KOHARU_RIKKA)
    s = s.with_window(WindowState(x=10, y=20, flipped=True, character_scale=1.5))
    save_settings(s, path)

    loaded = load_settings(path)
    assert loaded.model == "claude-sonnet-4-6"
    assert loaded.active_character == CharacterId.KOHARU_RIKKA
    assert loaded.window.flipped is True
    assert loaded.window.character_scale == 1.5
    # JSON は enum を文字列で保存している
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["active_character"] == "koharu_rikka"


def test_load_settings_defaults_when_missing(tmp_path):
    s = load_settings(tmp_path / "absent.json")
    assert s.model == "claude-opus-4-8"
    assert s.active_character == CharacterId.KASUKABE_TSUMUGI


def test_settings_updates_are_immutable():
    s = Settings()
    s2 = s.with_model("claude-haiku-4-5-20251001")
    assert s.model == "claude-opus-4-8"
    assert s2.model == "claude-haiku-4-5-20251001"


def test_load_bundled_character_configs():
    configs = load_character_configs()
    assert set(configs) == {CharacterId.KOHARU_RIKKA, CharacterId.KASUKABE_TSUMUGI}

    rikka = configs[CharacterId.KOHARU_RIKKA]
    assert rikka.engine == EngineKind.CEVIO
    assert rikka.cevio_cast == "小春六花"
    assert rikka.persona
    assert rikka.cevio_value_for(Emotion.HAPPY) == 70
    assert rikka.emotion_expressions[Emotion.NEUTRAL] == "通常"

    tsumugi = configs[CharacterId.KASUKABE_TSUMUGI]
    assert tsumugi.engine == EngineKind.VOICEVOX
    assert tsumugi.style_id_for(Emotion.HAPPY) == 8
    assert tsumugi.voicevox_default_style_id == 8
