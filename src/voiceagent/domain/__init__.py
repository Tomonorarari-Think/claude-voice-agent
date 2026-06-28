"""不変ドメインモデル。全レイヤーで共有する value object 群。"""

from voiceagent.domain.character import CharacterId, EngineKind
from voiceagent.domain.emotion import Emotion
from voiceagent.domain.message import Message, Role
from voiceagent.domain.phoneme import MouthFrame, MouthShape, Phoneme
from voiceagent.domain.utterance import Utterance

__all__ = [
    "CharacterId",
    "EngineKind",
    "Emotion",
    "Message",
    "Role",
    "MouthFrame",
    "MouthShape",
    "Phoneme",
    "Utterance",
]
