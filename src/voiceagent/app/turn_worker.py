"""会話 1 ターンを処理する worker スレッド。

Claude のストリームを消費し、文単位で「読み上げ整形 → 感情推定 → 音声合成」を行い、
GUI スレッドへ Qt シグナルで結果を渡す。合成（HTTP/COM）はブロッキングのため、
GUI を固めないよう専用スレッドで実行する。
"""

from __future__ import annotations

import asyncio

from PySide6.QtCore import QThread, Signal

from voiceagent.app.speech_item import SpeechItem
from voiceagent.claude.agent_client import AgentClient
from voiceagent.claude.events import AgentDone, AgentError, AgentTextChunk
from voiceagent.config.characters import CharacterConfig
from voiceagent.domain.character import CharacterId
from voiceagent.text.emotion_tagger import infer_emotion
from voiceagent.text.filter import clean_for_speech
from voiceagent.text.segmenter import extract_complete_sentences
from voiceagent.tts.engine_base import EngineUnavailableError
from voiceagent.tts.engine_manager import EngineManager
from voiceagent.tts.lipsync import build_mouth_timeline


class AgentTurnWorker(QThread):
    """1 プロンプト分の応答ストリームを処理するスレッド。"""

    assistant_text = Signal(str)  # 読み上げ用に整形済みの文
    speech_ready = Signal(object)  # SpeechItem
    turn_done = Signal(str)  # session_id
    failed = Signal(str)

    def __init__(
        self,
        agent: AgentClient,
        engines: EngineManager,
        character: CharacterId,
        config: CharacterConfig,
        model_id: str,
        prompt: str,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._agent = agent
        self._engines = engines
        self._character = character
        self._config = config
        self._model_id = model_id
        self._prompt = prompt

    def run(self) -> None:  # QThread エントリ
        try:
            asyncio.run(self._consume())
        except Exception as exc:  # スレッド内の想定外例外を UI へ
            self.failed.emit(str(exc))

    async def _consume(self) -> None:
        buffer = ""
        async for event in self._agent.stream(self._prompt, self._config, self._model_id):
            if isinstance(event, AgentTextChunk):
                buffer += event.text
                complete, buffer = extract_complete_sentences(buffer)
                for sentence in complete:
                    self._speak(sentence)
            elif isinstance(event, AgentDone):
                if buffer.strip():
                    self._speak(buffer)
                    buffer = ""
                self.turn_done.emit(event.session_id or "")
            elif isinstance(event, AgentError):
                self.failed.emit(event.message)

    def _speak(self, sentence: str) -> None:
        cleaned = clean_for_speech(sentence)
        if not cleaned.strip():
            return
        self.assistant_text.emit(cleaned)
        emotion = infer_emotion(cleaned)
        try:
            engine = self._engines.get_engine(self._character)
            utterance = engine.synthesize(cleaned, emotion)
        except EngineUnavailableError as exc:
            self.failed.emit(str(exc))
            return
        timeline = build_mouth_timeline(utterance.phonemes)
        self.speech_ready.emit(
            SpeechItem(text=cleaned, emotion=emotion, wav=utterance.wav, mouth_timeline=timeline)
        )
