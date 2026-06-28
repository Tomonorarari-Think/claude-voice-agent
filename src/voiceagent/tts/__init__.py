"""音声合成レイヤー。エンジン抽象 + VOICEVOX/CeVIO 実装 + リップシンク。"""

from voiceagent.tts.engine_base import EngineUnavailableError, VoiceEngine
from voiceagent.tts.lipsync import build_mouth_timeline

__all__ = ["VoiceEngine", "EngineUnavailableError", "build_mouth_timeline"]
