"""キャラ定義のロード。data/characters/*.toml を読み込む。

各キャラの口調(persona)・エンジン設定・感情マッピングを宣言的に定義し、
コード変更なしで調整できるようにする。立ち絵画像の実体はリポジトリ外
（SETUP.md 参照）で、ここではキー名のみを保持する。
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from voiceagent.domain.character import CharacterId, EngineKind
from voiceagent.domain.emotion import Emotion

_DATA_DIR = Path(__file__).resolve().parent / "characters"


@dataclass(frozen=True, slots=True)
class CharacterConfig:
    """1 キャラの全設定（不変）。"""

    character: CharacterId
    engine: EngineKind
    persona: str
    # VOICEVOX: 感情 -> style_id / CeVIO: 感情 -> 感情コンポーネント値(0-100) のマップ
    emotion_engine_params: dict[Emotion, int]
    # 感情 -> 表情画像キー（character/expression_set が解決する）
    emotion_expressions: dict[Emotion, str]
    cevio_cast: str | None = None
    voicevox_default_style_id: int | None = None
    # 立ち絵レイヤー設定（PSD レンダリング用、任意）
    mouth_config: dict = field(default_factory=dict)
    expression_config: dict[str, dict] = field(default_factory=dict)

    def style_id_for(self, emotion: Emotion) -> int | None:
        """VOICEVOX 用。感情に対応する style_id（無ければデフォルト）。"""
        return self.emotion_engine_params.get(emotion, self.voicevox_default_style_id or 0)

    def cevio_value_for(self, emotion: Emotion) -> int:
        """CeVIO 用。感情コンポーネント値（0-100、無ければ中庸 50）。"""
        return self.emotion_engine_params.get(emotion, 50)


def _emotion_map(raw: dict[str, int]) -> dict[Emotion, int]:
    return {Emotion(k): int(v) for k, v in raw.items()}


def _expr_map(raw: dict[str, str]) -> dict[Emotion, str]:
    return {Emotion(k): str(v) for k, v in raw.items()}


def load_character_configs(data_dir: Path = _DATA_DIR) -> dict[CharacterId, CharacterConfig]:
    """data_dir 内の全 *.toml を読み、CharacterId -> CharacterConfig を返す。"""
    configs: dict[CharacterId, CharacterConfig] = {}
    for toml_path in sorted(data_dir.glob("*.toml")):
        raw = tomllib.loads(toml_path.read_text(encoding="utf-8"))
        char = CharacterId(raw["character"])
        configs[char] = CharacterConfig(
            character=char,
            engine=EngineKind(raw["engine"]),
            persona=raw["persona"].strip(),
            emotion_engine_params=_emotion_map(raw.get("emotion_engine_params", {})),
            emotion_expressions=_expr_map(raw.get("emotion_expressions", {})),
            cevio_cast=raw.get("cevio_cast"),
            voicevox_default_style_id=raw.get("voicevox_default_style_id"),
            mouth_config=raw.get("mouth", {}),
            expression_config=raw.get("expression", {}),
        )
    return configs
