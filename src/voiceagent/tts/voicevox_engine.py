"""VOICEVOX エンジン実装（HTTP）。

ヘッドレスな VOICEVOX エンジン (`run.exe`) のローカル HTTP API を叩く。
`/audio_query` の mora 情報から音素タイミングを構築し、音声解析なしで
リップシンク可能な `Utterance` を返す。
"""

from __future__ import annotations

import httpx

from voiceagent.domain.character import CharacterId
from voiceagent.domain.emotion import Emotion
from voiceagent.domain.phoneme import Phoneme
from voiceagent.domain.utterance import Utterance
from voiceagent.tts.engine_base import EngineUnavailableError

_DEFAULT_TIMEOUT = 30.0


def parse_audio_query_phonemes(query: dict) -> tuple[Phoneme, ...]:
    """AudioQuery JSON から音素タイミング列（秒）を構築する。

    speedScale を反映し、prePhonemeLength の無音から開始。各 mora は
    （あれば）子音 + 母音、句間には pause_mora を挿入する。
    """
    speed = float(query.get("speedScale", 1.0)) or 1.0
    t = float(query.get("prePhonemeLength", 0.0)) / speed
    out: list[Phoneme] = []

    def emit(phoneme: str | None, length: float | None) -> None:
        nonlocal t
        if not phoneme or length is None:
            return
        dur = float(length) / speed
        out.append(Phoneme(phoneme=phoneme, start=t, end=t + dur))
        t += dur

    for phrase in query.get("accent_phrases", []):
        for mora in phrase.get("moras", []):
            emit(mora.get("consonant"), mora.get("consonant_length"))
            emit(mora.get("vowel"), mora.get("vowel_length"))
        pause = phrase.get("pause_mora")
        if pause:
            emit(pause.get("vowel", "pau"), pause.get("vowel_length"))
    return tuple(out)


class VoicevoxEngine:
    """VOICEVOX HTTP エンジンのクライアント。"""

    def __init__(
        self,
        *,
        host: str = "127.0.0.1",
        port: int = 50021,
        default_style_id: int = 8,  # 春日部つむぎ ノーマル
        character: CharacterId = CharacterId.KASUKABE_TSUMUGI,
        client: httpx.Client | None = None,
    ) -> None:
        self._base = f"http://{host}:{port}"
        self._default_style_id = default_style_id
        self._character = character
        self._client = client or httpx.Client(timeout=_DEFAULT_TIMEOUT)

    def is_available(self) -> bool:
        try:
            resp = self._client.get(f"{self._base}/version", timeout=2.0)
            return resp.status_code == 200
        except (httpx.HTTPError, OSError):
            return False

    def synthesize(self, text: str, emotion: Emotion = Emotion.NEUTRAL) -> Utterance:
        if not text.strip():
            raise ValueError("text must not be empty")
        style_id = self._default_style_id  # つむぎは単一スタイル。将来 emotion で切替可。
        try:
            query = self._client.post(
                f"{self._base}/audio_query",
                params={"text": text, "speaker": style_id},
            )
            query.raise_for_status()
            audio_query = query.json()

            wav = self._client.post(
                f"{self._base}/synthesis",
                params={"speaker": style_id},
                json=audio_query,
            )
            wav.raise_for_status()
        except httpx.HTTPError as exc:
            raise EngineUnavailableError(f"VOICEVOX request failed: {exc}") from exc

        return Utterance(
            text=text,
            character=self._character,
            emotion=emotion,
            wav=wav.content,
            phonemes=parse_audio_query_phonemes(audio_query),
        )

    def close(self) -> None:
        self._client.close()
