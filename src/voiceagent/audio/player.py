"""WAV 再生と再生位置トラッキング。

リップシンクは再生位置（経過秒）に同期して口形を切り替えるため、
再生中に `position()` で現在時刻を取得できるようにする。
"""

from __future__ import annotations

import io
import time
import wave
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class DecodedAudio:
    """デコード済み PCM。"""

    samples: np.ndarray  # shape (frames, channels), float32 [-1, 1]
    sample_rate: int

    @property
    def duration(self) -> float:
        return len(self.samples) / self.sample_rate if self.sample_rate else 0.0


def decode_wav(wav_bytes: bytes) -> DecodedAudio:
    """WAV バイト列を float32 PCM へデコードする（16/24/32bit PCM 対応）。"""
    with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
        channels = wf.getnchannels()
        width = wf.getsampwidth()
        rate = wf.getframerate()
        frames = wf.readframes(wf.getnframes())

    if width == 2:
        data = np.frombuffer(frames, dtype="<i2").astype(np.float32) / 32768.0
    elif width == 4:
        data = np.frombuffer(frames, dtype="<i4").astype(np.float32) / 2147483648.0
    elif width == 1:
        data = (np.frombuffer(frames, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
    elif width == 3:  # 24bit packed
        raw = np.frombuffer(frames, dtype=np.uint8).reshape(-1, 3)
        as_int = (raw[:, 0].astype(np.int32)
                  | (raw[:, 1].astype(np.int32) << 8)
                  | (raw[:, 2].astype(np.int32) << 16))
        as_int = np.where(as_int & 0x800000, as_int - 0x1000000, as_int)
        data = as_int.astype(np.float32) / 8388608.0
    else:  # pragma: no cover - 想定外フォーマット
        raise ValueError(f"unsupported sample width: {width} bytes")

    if channels > 1:
        data = data.reshape(-1, channels)
    else:
        data = data.reshape(-1, 1)
    return DecodedAudio(samples=data, sample_rate=rate)


class AudioPlayer:
    """sounddevice による非ブロッキング再生 + 再生位置の追跡。"""

    def __init__(self) -> None:
        self._start_time: float | None = None
        self._duration: float = 0.0

    def play(self, wav_bytes: bytes) -> float:
        """再生を開始し、音声長（秒）を返す。ブロックしない。"""
        import sounddevice as sd  # 遅延 import（テスト環境にデバイス無くても import 可）

        audio = decode_wav(wav_bytes)
        sd.stop()
        sd.play(audio.samples, audio.sample_rate)
        self._start_time = time.monotonic()
        self._duration = audio.duration
        return audio.duration

    def position(self) -> float:
        """再生開始からの経過秒。停止中や未再生は 0。"""
        if self._start_time is None:
            return 0.0
        elapsed = time.monotonic() - self._start_time
        return min(elapsed, self._duration)

    def is_playing(self) -> bool:
        return self._start_time is not None and self.position() < self._duration

    def stop(self) -> None:
        import sounddevice as sd

        sd.stop()
        self._start_time = None
