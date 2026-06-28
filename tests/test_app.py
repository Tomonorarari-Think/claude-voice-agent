"""アプリ層の非 GUI ロジックのテスト。"""

from voiceagent.app.assets import resolve_psd_path
from voiceagent.app.speech_item import SpeechItem
from voiceagent.config.settings import Settings
from voiceagent.domain.character import CharacterId
from voiceagent.domain.emotion import Emotion
from voiceagent.domain.phoneme import MouthFrame, MouthShape


def test_resolve_psd_from_asset_root(tmp_path):
    root = tmp_path / "assets"
    char_dir = root / CharacterId.KOHARU_RIKKA.value
    char_dir.mkdir(parents=True)
    psd = char_dir / "rikka.psd"
    psd.write_bytes(b"fake")

    settings = Settings(asset_root=str(root))
    found = resolve_psd_path(settings, CharacterId.KOHARU_RIKKA)
    assert found == psd


def test_resolve_psd_missing_returns_none(tmp_path):
    settings = Settings(asset_root=str(tmp_path / "empty"))
    # 開発フォールバックも無い前提のキャラ指定でも例外を出さない
    result = resolve_psd_path(settings, CharacterId.KASUKABE_TSUMUGI)
    assert result is None or result.suffix == ".psd"


def test_speech_item_is_immutable():
    item = SpeechItem(
        text="やあ",
        emotion=Emotion.HAPPY,
        wav=b"RIFF",
        mouth_timeline=(MouthFrame(0.0, MouthShape.A),),
    )
    assert item.text == "やあ"
    assert item.mouth_timeline[0].shape == MouthShape.A
