"""利用可能なモデルの定義。チャット欄のモデル切替に使う。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ModelInfo:
    """切替可能なモデル 1 件。"""

    id: str
    label: str
    note: str = ""


# 最新の Claude モデル（2026 時点）。深い推論=Opus、標準=Sonnet、軽量高速=Haiku。
MODELS: tuple[ModelInfo, ...] = (
    ModelInfo("claude-opus-4-8", "Opus 4.8", "最も賢い・深い推論"),
    ModelInfo("claude-sonnet-4-6", "Sonnet 4.6", "バランス型"),
    ModelInfo("claude-haiku-4-5-20251001", "Haiku 4.5", "高速・軽量"),
)

_BY_ID = {m.id: m for m in MODELS}


def default_model() -> ModelInfo:
    return MODELS[0]


def model_by_id(model_id: str) -> ModelInfo:
    """ID からモデルを引く。未知の ID はそのまま ModelInfo 化して返す（前方互換）。"""
    return _BY_ID.get(model_id, ModelInfo(model_id, model_id))
