"""感情推定（ヒューリスティック）。

文のキーワードと記号から共通感情 `Emotion` を推定し、立ち絵の表情と
エンジンの感情パラメータに反映する。軽量・決定的でテストしやすい実装。
将来的に LLM へ感情タグを直接出させる方式に差し替え可能。
"""

from __future__ import annotations

import re

from voiceagent.domain.emotion import Emotion

# 感情ごとのキーワード（部分一致）。優先度はスコアで決める。
_KEYWORDS: dict[Emotion, tuple[str, ...]] = {
    Emotion.HAPPY: (
        "嬉し", "楽し", "やった", "わーい", "わあ", "すごい", "最高", "できた",
        "成功", "ありがとう", "笑", "👍", "🎉", "✨", "！！",
    ),
    Emotion.ANGRY: (
        "怒", "ダメ", "だめ", "許せ", "むかつ", "ふざけ", "いい加減", "もう！",
        "失敗", "エラー", "壊れ", "最悪",
    ),
    Emotion.SAD: (
        "悲し", "つらい", "辛い", "ごめん", "残念", "しょんぼり", "困った",
        "うまくいかない", "わからない", "難しい", "😢", "😭",
    ),
    Emotion.CALM: (
        "なるほど", "そうだね", "ふむ", "了解", "わかった", "落ち着", "大丈夫",
        "ゆっくり", "確認",
    ),
}

_EXCLAIM = re.compile(r"[!！]")


def infer_emotion(text: str, *, default: Emotion = Emotion.NEUTRAL) -> Emotion:
    """テキストから感情を推定する。該当なしは default。"""
    if not text:
        return default

    scores: dict[Emotion, int] = {e: 0 for e in _KEYWORDS}
    for emotion, words in _KEYWORDS.items():
        for w in words:
            if w in text:
                scores[emotion] += 1

    # 感嘆符が多いと喜び/怒り方向を少し後押し（既に該当語がある場合のみ）
    exclaims = len(_EXCLAIM.findall(text))
    if exclaims >= 2:
        if scores[Emotion.HAPPY] > 0:
            scores[Emotion.HAPPY] += 1
        if scores[Emotion.ANGRY] > 0:
            scores[Emotion.ANGRY] += 1

    best = max(scores, key=lambda e: scores[e])
    return best if scores[best] > 0 else default
