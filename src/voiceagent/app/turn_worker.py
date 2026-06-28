"""会話 1 ターンの Claude ストリームを処理する worker スレッド。

Claude のストリームを消費し、文単位で「読み上げ整形 → 感情推定」を行い、
合成依頼（SpeakRequest）を発行する。実際の音声合成は常駐の SynthService が担う
（COM をターンごとのスレッドに束縛しないため）。
"""

from __future__ import annotations

import asyncio

from PySide6.QtCore import QThread, Signal

from voiceagent.app.speech_item import SpeakRequest
from voiceagent.claude.agent_client import AgentClient
from voiceagent.claude.events import AgentDone, AgentError, AgentTextChunk
from voiceagent.config.characters import CharacterConfig
from voiceagent.domain.character import CharacterId
from voiceagent.text.emotion_tagger import infer_emotion
from voiceagent.text.filter import clean_for_speech
from voiceagent.text.segmenter import extract_complete_sentences


class AgentTurnWorker(QThread):
    """1 プロンプト分の応答ストリームを処理するスレッド（Claude のみ）。"""

    assistant_text = Signal(str)  # 読み上げ・表示用に整形済みの文
    speak_request = Signal(object)  # SpeakRequest（合成は SynthService が担当）
    turn_done = Signal(str)  # session_id
    failed = Signal(str)

    def __init__(
        self,
        agent: AgentClient,
        character: CharacterId,
        config: CharacterConfig,
        model_id: str,
        prompt: str,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._agent = agent
        self._character = character
        self._config = config
        self._model_id = model_id
        self._prompt = prompt

    def run(self) -> None:
        try:
            asyncio.run(self._consume())
        except Exception as exc:
            self.failed.emit(str(exc))

    async def _consume(self) -> None:
        buffer = ""
        async for event in self._agent.stream(self._prompt, self._config, self._model_id):
            if isinstance(event, AgentTextChunk):
                buffer += event.text
                complete, buffer = extract_complete_sentences(buffer)
                for sentence in complete:
                    self._emit_sentence(sentence)
            elif isinstance(event, AgentDone):
                if buffer.strip():
                    self._emit_sentence(buffer)
                    buffer = ""
                self.turn_done.emit(event.session_id or "")
            elif isinstance(event, AgentError):
                self.failed.emit(event.message)

    def _emit_sentence(self, sentence: str) -> None:
        cleaned = clean_for_speech(sentence)
        if not cleaned.strip():
            return
        self.assistant_text.emit(cleaned)
        emotion = infer_emotion(cleaned)
        self.speak_request.emit(SpeakRequest(text=cleaned, emotion=emotion, character=self._character))
