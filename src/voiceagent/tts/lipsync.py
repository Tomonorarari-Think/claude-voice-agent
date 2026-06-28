"""リップシンク: 音素タイムライン -> 口形タイムライン。

VOICEVOX(mora) と CeVIO(GetPhonemes) のどちらも `Phoneme` 列へ正規化済みなので、
本モジュールはエンジン非依存で口形 (MouthShape) のフレーム列を生成する。
音声波形は解析しない（タイミングベース）。
"""

from __future__ import annotations

from voiceagent.domain.phoneme import MouthFrame, MouthShape, Phoneme

# 母音 -> 口形。日本語の音素表記（VOICEVOX/CeVIO とも母音は a/i/u/e/o）。
_VOWEL_SHAPES: dict[str, MouthShape] = {
    "a": MouthShape.A,
    "i": MouthShape.I,
    "u": MouthShape.U,
    "e": MouthShape.E,
    "o": MouthShape.O,
}

# 無音・休符・撥音として扱う音素（閉口）。
_CLOSED_PHONEMES = frozenset({"sil", "pau", "cl", "sp", "", "N", "n"})


def _shape_for(phoneme: str) -> MouthShape | None:
    """音素 1 つを口形へ。母音以外は None（直前の形を保つ判断に使う）。"""
    p = phoneme.strip().lower()
    if p in _CLOSED_PHONEMES or phoneme in _CLOSED_PHONEMES:
        return MouthShape.CLOSED
    # 末尾の母音で判定（例: "ky" は子音なので None、"a" は A）
    if p in _VOWEL_SHAPES:
        return _VOWEL_SHAPES[p]
    last = p[-1:] if p else ""
    return _VOWEL_SHAPES.get(last)


def build_mouth_timeline(
    phonemes: tuple[Phoneme, ...] | list[Phoneme],
    *,
    min_frame_sec: float = 0.03,
) -> tuple[MouthFrame, ...]:
    """音素列から口形フレーム列を構築する。

    - 母音はその口形、子音は直前の母音口形を維持、無音/休符は閉口。
    - 連続する同一口形はまとめる。
    - `min_frame_sec` 未満の極短フレームは直前へ吸収して立ち絵のチラつきを防ぐ。
    """
    if not phonemes:
        return ()

    frames: list[MouthFrame] = []
    prev_shape = MouthShape.CLOSED
    for ph in phonemes:
        shape = _shape_for(ph.phoneme)
        if shape is None:
            shape = prev_shape  # 子音: 直前の口形を維持
        prev_shape = shape

        if frames and frames[-1].shape == shape:
            continue  # 同一口形は継続（フレームを増やさない）
        if frames and (ph.start - frames[-1].start) < min_frame_sec:
            # 直前フレームが極端に短い -> 上書きして吸収
            frames[-1] = MouthFrame(start=frames[-1].start, shape=shape)
            continue
        frames.append(MouthFrame(start=ph.start, shape=shape))

    # 末尾に閉口を追加（発話終了で口を閉じる）
    end = phonemes[-1].end
    if frames and frames[-1].shape != MouthShape.CLOSED:
        frames.append(MouthFrame(start=end, shape=MouthShape.CLOSED))
    return tuple(frames)
