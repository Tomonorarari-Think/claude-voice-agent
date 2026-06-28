"""リップシンク・タイムライン生成のテスト。"""

from voiceagent.domain.phoneme import MouthShape, Phoneme
from voiceagent.tts.lipsync import build_mouth_timeline
from voiceagent.tts.voicevox_engine import parse_audio_query_phonemes


def test_empty_phonemes_gives_empty_timeline():
    assert build_mouth_timeline(()) == ()


def test_vowels_map_to_mouth_shapes():
    phonemes = (
        Phoneme("a", 0.0, 0.2),
        Phoneme("i", 0.2, 0.4),
        Phoneme("u", 0.4, 0.6),
    )
    frames = build_mouth_timeline(phonemes)
    shapes = [f.shape for f in frames]
    assert shapes[:3] == [MouthShape.A, MouthShape.I, MouthShape.U]
    # 末尾に閉口が追加される
    assert frames[-1].shape == MouthShape.CLOSED


def test_consonant_keeps_previous_vowel_shape():
    # k(子音) は直前の母音 a の口形を維持
    phonemes = (
        Phoneme("a", 0.0, 0.2),
        Phoneme("k", 0.2, 0.25),
        Phoneme("a", 0.25, 0.45),
    )
    frames = build_mouth_timeline(phonemes)
    # 連続する A は 1 フレームにまとまる -> [A, CLOSED]
    assert [f.shape for f in frames] == [MouthShape.A, MouthShape.CLOSED]


def test_pause_is_closed_mouth():
    phonemes = (
        Phoneme("a", 0.0, 0.2),
        Phoneme("pau", 0.2, 0.5),
        Phoneme("o", 0.5, 0.7),
    )
    shapes = [f.shape for f in build_mouth_timeline(phonemes)]
    assert MouthShape.CLOSED in shapes
    assert shapes[0] == MouthShape.A
    assert MouthShape.O in shapes


def test_parse_audio_query_phonemes_timing():
    query = {
        "speedScale": 1.0,
        "prePhonemeLength": 0.1,
        "accent_phrases": [
            {
                "moras": [
                    {"text": "コ", "consonant": "k", "consonant_length": 0.05,
                     "vowel": "o", "vowel_length": 0.15},
                    {"text": "ン", "consonant": None, "consonant_length": None,
                     "vowel": "N", "vowel_length": 0.1},
                ],
                "pause_mora": {"vowel": "pau", "vowel_length": 0.2},
            }
        ],
    }
    phonemes = parse_audio_query_phonemes(query)
    # k(0.1-0.15), o(0.15-0.30), N(0.30-0.40), pau(0.40-0.60)
    assert phonemes[0].phoneme == "k"
    assert abs(phonemes[0].start - 0.1) < 1e-9
    assert abs(phonemes[1].start - 0.15) < 1e-9
    assert abs(phonemes[-1].end - 0.60) < 1e-9


def test_parse_audio_query_respects_speed_scale():
    query = {
        "speedScale": 2.0,
        "prePhonemeLength": 0.0,
        "accent_phrases": [
            {"moras": [{"vowel": "a", "vowel_length": 0.4}], "pause_mora": None}
        ],
    }
    phonemes = parse_audio_query_phonemes(query)
    # 2倍速 -> 0.2s
    assert abs(phonemes[0].end - 0.2) < 1e-9
