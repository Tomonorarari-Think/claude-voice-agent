"""立ち絵アセット（PSD）のパス解決。

設定の asset_root を優先し、無ければ開発用に同梱フォルダ（素材/, .gitignore 対象）を探す。
配布時はユーザーが asset_root を設定して各自の立ち絵を配置する想定。
"""

from __future__ import annotations

from pathlib import Path

from voiceagent.config.settings import Settings
from voiceagent.domain.character import CharacterId

_REPO_ROOT = Path(__file__).resolve().parents[3]

# 開発用フォールバック（リポジトリには含めないが、ローカルにあれば使う）。
_DEV_FALLBACK: dict[CharacterId, Path] = {
    CharacterId.KOHARU_RIKKA: _REPO_ROOT
    / "素材" / "KoharuRikkaTachie_v1.2" / "KoharuRikka_v1.2.psd",
    CharacterId.KASUKABE_TSUMUGI: _REPO_ROOT
    / "素材" / "春日部つむぎ立ち絵_公式_v2.0" / "春日部つむぎ立ち絵_公式_v2.0.psd",
}


def resolve_psd_path(settings: Settings, character: CharacterId) -> Path | None:
    """キャラの立ち絵 PSD パスを返す。見つからなければ None。"""
    if settings.asset_root:
        char_dir = Path(settings.asset_root) / character.value
        if char_dir.is_dir():
            psds = sorted(char_dir.glob("*.psd"))
            if psds:
                return psds[0]
    fallback = _DEV_FALLBACK.get(character)
    if fallback and fallback.exists():
        return fallback
    return None
