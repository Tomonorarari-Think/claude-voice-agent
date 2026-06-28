"""エンジン実行ファイルのパス解決。

優先順位:
1. 明示引数 / 設定ファイル (local_settings.json)
2. リポジトリ同梱の VoiceAppPath.md（開発者ローカルのデフォルト）
3. 既定の探索パス

VoiceAppPath.md はユーザー環境固有のため、配布時は各自で用意する想定。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_VOICE_APP_PATH_MD = _REPO_ROOT / "VoiceAppPath.md"


@dataclass(frozen=True, slots=True)
class EnginePaths:
    """音声エンジンのパス設定。"""

    voicevox_run_exe: Path | None
    cevio_dir: Path | None
    voicevox_host: str = "127.0.0.1"
    voicevox_port: int = 50021


def _parse_voice_app_md(md_path: Path) -> dict[str, str]:
    """`## 見出し` の次行に書かれたパスを {見出し小文字: パス} で返す。"""
    if not md_path.exists():
        return {}
    result: dict[str, str] = {}
    current: str | None = None
    for raw in md_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        heading = re.match(r"^#{1,6}\s+(.*)$", line)
        if heading:
            current = heading.group(1).strip().lower()
            continue
        if current and line and not line.startswith("#"):
            result.setdefault(current, line)
    return result


def resolve_engine_paths(
    *,
    voicevox_run_exe: str | None = None,
    cevio_dir: str | None = None,
    md_path: Path = _VOICE_APP_PATH_MD,
) -> EnginePaths:
    """明示引数 > VoiceAppPath.md の順でパスを解決する。"""
    parsed = _parse_voice_app_md(md_path)

    vv = voicevox_run_exe or parsed.get("voicevox")
    cevio = cevio_dir or parsed.get("cevio ai")

    return EnginePaths(
        voicevox_run_exe=Path(vv) if vv else None,
        cevio_dir=Path(cevio) if cevio else None,
    )
