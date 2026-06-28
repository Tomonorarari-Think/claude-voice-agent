"""音声デコードのテスト。"""

import io
import wave

import numpy as np

from voiceagent.audio.player import decode_wav


def _make_wav(samples: np.ndarray, rate: int, channels: int) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        pcm = (samples * 32767).astype("<i2").tobytes()
        wf.writeframes(pcm)
    return buf.getvalue()


def test_decode_mono_16bit():
    rate = 24000
    sig = np.sin(np.linspace(0, np.pi, rate)).astype(np.float32)  # 1秒
    wav = _make_wav(sig, rate, 1)
    decoded = decode_wav(wav)
    assert decoded.sample_rate == rate
    assert decoded.samples.shape == (rate, 1)
    assert abs(decoded.duration - 1.0) < 1e-3
    assert decoded.samples.max() <= 1.0 and decoded.samples.min() >= -1.0


def test_decode_stereo_shape():
    rate = 8000
    stereo = np.zeros((rate, 2), dtype=np.float32)
    wav = _make_wav(stereo, rate, 2)
    decoded = decode_wav(wav)
    assert decoded.samples.shape == (rate, 2)
