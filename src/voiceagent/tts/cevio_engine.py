"""CeVIO AI エンジン実装（COM / RemoteService2）。

`ServiceControl2.StartHost(False)` で GUI なしのバックエンドを起動し、
`Talker2` で小春六花を喋らせる。`OutputWaveToFile` で WAV を取得、
`GetPhonemes` で音素タイミングを取得してリップシンクに使う。

COM は Windows 専用かつ CeVIO AI 製品のインストールが前提のため、
`win32com` は遅延 import する（非 Windows / 未インストール環境でも本モジュールは import 可能）。
"""

from __future__ import annotations

import tempfile
import threading
from pathlib import Path
from typing import Any, Protocol

from voiceagent.config.characters import CharacterConfig
from voiceagent.domain.character import CharacterId
from voiceagent.domain.emotion import Emotion
from voiceagent.domain.phoneme import Phoneme
from voiceagent.domain.utterance import Utterance
from voiceagent.tts.engine_base import EngineUnavailableError

_PROGID_CONTROL = "CeVIO.Talk.RemoteService2.ServiceControl2"
_PROGID_TALKER = "CeVIO.Talk.RemoteService2.Talker2"


class _RawPhoneme(Protocol):
    StartTime: float
    EndTime: float
    Phoneme: str


def _iter_com_array(raw: Any) -> Any:
    """CeVIO の COM 配列 (IPhonemeDataArray2 等) と通常の iterable を統一的に走査する。

    win32com の dynamic dispatch は `IPhonemeDataArray2` を直接 for で回せない
    （"does not support enumeration"）。`.Length` + `.At(i)` / `.Count` + `.Item(i)`
    を持つ COM 配列はインデックスで取り出す。
    """
    length_attr = getattr(raw, "Length", None)
    if length_attr is not None and hasattr(raw, "At"):
        for i in range(int(length_attr)):
            yield raw.At(i)
        return
    count_attr = getattr(raw, "Count", None)
    if count_attr is not None and hasattr(raw, "Item"):
        for i in range(int(count_attr)):
            yield raw.Item(i)
        return
    yield from raw  # 通常の iterable（テストのフェイク等）


def to_phonemes(raw_list: Any) -> tuple[Phoneme, ...]:
    """`GetPhonemes()` の結果（StartTime/EndTime/Phoneme を持つ列）を正規化する。

    純粋関数。COM 配列でも通常の iterable（テストのフェイク）でも扱える。
    """
    out: list[Phoneme] = []
    for item in _iter_com_array(raw_list):
        out.append(
            Phoneme(
                phoneme=str(item.Phoneme),
                start=float(item.StartTime),
                end=float(item.EndTime),
            )
        )
    return tuple(out)


class CevioEngine:
    """CeVIO AI (RemoteService2) クライアント。"""

    def __init__(
        self,
        config: CharacterConfig,
        *,
        character: CharacterId = CharacterId.KOHARU_RIKKA,
        volume: int = 100,
    ) -> None:
        self._config = config
        self._character = character
        self._volume = volume
        # COM オブジェクトは生成したスレッドに束縛されるため、スレッドごとに保持する。
        # （会話ターンごとに別 worker スレッドで合成されるため、共有すると
        #  クロススレッド呼び出しで失敗する＝キャラ切替後に読み上げが止まる原因）
        self._local = threading.local()

    # --- COM ライフサイクル（スレッドローカル） -------------------------------

    def _talker(self) -> Any:
        talker = getattr(self._local, "talker", None)
        if talker is not None:
            return talker
        try:
            import pythoncom  # type: ignore
            import win32com.client  # type: ignore
        except ImportError as exc:  # pragma: no cover - 非 Windows
            raise EngineUnavailableError("pywin32 / CeVIO COM が利用できません") from exc

        try:
            pythoncom.CoInitialize()  # この worker スレッドを STA 初期化
            control = win32com.client.Dispatch(_PROGID_CONTROL)
            result = control.StartHost(False)  # 起動済みなら即時戻る
            if int(result) < 0:
                raise EngineUnavailableError(f"CeVIO StartHost failed: code={result}")
            talker = win32com.client.Dispatch(_PROGID_TALKER)
            talker.Cast = self._config.cevio_cast
            talker.Volume = self._volume
        except EngineUnavailableError:
            raise
        except Exception as exc:  # pragma: no cover - COM 実機依存
            raise EngineUnavailableError(f"CeVIO 初期化に失敗: {exc}") from exc

        self._local.talker = talker
        return talker

    def is_available(self) -> bool:
        try:
            return self._talker() is not None
        except EngineUnavailableError:
            return False

    # --- 感情マッピング -------------------------------------------------------

    def _apply_emotion(self, talker: Any, emotion: Emotion) -> None:
        value = self._config.cevio_value_for(emotion)
        try:
            talker.Components.ByName(emotion.label_ja).Value = value
        except Exception:  # pragma: no cover - キャストに該当感情が無い場合
            pass

    # --- 合成 -----------------------------------------------------------------

    def synthesize(self, text: str, emotion: Emotion = Emotion.NEUTRAL) -> Utterance:
        if not text.strip():
            raise ValueError("text must not be empty")
        talker = self._talker()

        self._apply_emotion(talker, emotion)
        try:
            phonemes = to_phonemes(talker.GetPhonemes(text))
            with tempfile.TemporaryDirectory() as tmp:
                wav_path = Path(tmp) / "out.wav"
                ok = talker.OutputWaveToFile(text, str(wav_path))
                if not ok or not wav_path.exists():
                    raise EngineUnavailableError("CeVIO OutputWaveToFile が失敗しました")
                wav = wav_path.read_bytes()
        except EngineUnavailableError:
            raise
        except Exception as exc:  # pragma: no cover - COM 実機依存
            raise EngineUnavailableError(f"CeVIO 合成に失敗: {exc}") from exc

        return Utterance(
            text=text,
            character=self._character,
            emotion=emotion,
            wav=wav,
            phonemes=phonemes,
        )

    def close(self) -> None:
        # StartHost したホストは他プロセスでも使う可能性があるため CloseHost はしない。
        self._local = threading.local()
