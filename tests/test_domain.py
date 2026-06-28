"""ドメイン value object のテスト。"""

import pytest

from voiceagent.domain import (
    CharacterId,
    Emotion,
    Message,
    Phoneme,
    Role,
    Utterance,
)


def test_emotion_japanese_labels():
    assert Emotion.HAPPY.label_ja == "嬉しい"
    assert Emotion.NEUTRAL.label_ja == "普通"
    assert {e.label_ja for e in Emotion} == {"嬉しい", "普通", "怒り", "哀しみ", "落ち着き"}


def test_character_display_names():
    assert CharacterId.KOHARU_RIKKA.display_name == "小春六花"
    assert CharacterId.KASUKABE_TSUMUGI.display_name == "春日部つむぎ"


def test_phoneme_duration_and_validation():
    p = Phoneme("a", 0.5, 1.25)
    assert p.duration == pytest.approx(0.75)
    with pytest.raises(ValueError):
        Phoneme("a", 1.0, 0.5)
    with pytest.raises(ValueError):
        Phoneme("a", -0.1, 0.5)


def test_message_appended_is_immutable():
    m = Message(Role.ASSISTANT, "こん")
    m2 = m.appended("にちは")
    assert m.text == "こん"  # 元は不変
    assert m2.text == "こんにちは"
    assert m2.created_at == m.created_at


def test_utterance_duration_from_phonemes():
    u = Utterance(
        text="あい",
        character=CharacterId.KASUKABE_TSUMUGI,
        emotion=Emotion.HAPPY,
        wav=b"RIFF....",
        phonemes=(Phoneme("a", 0.0, 0.3), Phoneme("i", 0.3, 0.7)),
    )
    assert u.duration == pytest.approx(0.7)
    empty = Utterance("", CharacterId.KOHARU_RIKKA, Emotion.NEUTRAL, b"")
    assert empty.duration == 0.0
