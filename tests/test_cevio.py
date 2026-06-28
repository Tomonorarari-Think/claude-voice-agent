"""CeVIO 音素アダプタのテスト（COM 非依存部分）。"""

from dataclasses import dataclass

from voiceagent.tts.cevio_engine import to_phonemes


@dataclass
class _FakePhoneme:
    Phoneme: str
    StartTime: float
    EndTime: float


class _FakeComArray:
    """CeVIO IPhonemeDataArray2 を模した Length + At(i) の COM 風配列。"""

    def __init__(self, items):
        self._items = items

    @property
    def Length(self):
        return len(self._items)

    def At(self, index):
        return self._items[index]


def test_to_phonemes_normalizes_com_objects():
    raw = [
        _FakePhoneme("k", 0.0, 0.05),
        _FakePhoneme("o", 0.05, 0.2),
        _FakePhoneme("N", 0.2, 0.3),
    ]
    phonemes = to_phonemes(raw)
    assert len(phonemes) == 3
    assert phonemes[0].phoneme == "k"
    assert phonemes[1].start == 0.05
    assert phonemes[2].end == 0.3
    assert phonemes[1].duration > 0


def test_to_phonemes_handles_com_indexed_array():
    # win32com の dynamic dispatch で for が回せない COM 配列を Length/At で走査
    raw = _FakeComArray([_FakePhoneme("a", 0.0, 0.1), _FakePhoneme("i", 0.1, 0.25)])
    phonemes = to_phonemes(raw)
    assert [p.phoneme for p in phonemes] == ["a", "i"]
    assert phonemes[1].end == 0.25
