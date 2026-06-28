"""TTS スモークテスト CLI。

実エンジン（VOICEVOX / CeVIO）で 1 文を合成・再生し、音素タイムラインと
リップシンク用の口形フレームを標準出力に表示する。

使い方:
    python -m voiceagent.tts.smoke --character kasukabe_tsumugi --text "こんにちは"
    python -m voiceagent.tts.smoke --character koharu_rikka --text "おはよう" --emotion happy
"""

from __future__ import annotations

import argparse
import time

from voiceagent.audio.player import AudioPlayer
from voiceagent.config.characters import load_character_configs
from voiceagent.config.paths import resolve_engine_paths
from voiceagent.domain.character import CharacterId
from voiceagent.domain.emotion import Emotion
from voiceagent.tts.engine_manager import EngineManager
from voiceagent.tts.lipsync import build_mouth_timeline


def main() -> int:
    parser = argparse.ArgumentParser(description="VoiceAgent TTS smoke test")
    parser.add_argument(
        "--character",
        default=CharacterId.KASUKABE_TSUMUGI.value,
        choices=[c.value for c in CharacterId],
    )
    parser.add_argument("--text", default="こんにちは、今日はいい天気ですね。")
    parser.add_argument(
        "--emotion", default=Emotion.NEUTRAL.value, choices=[e.value for e in Emotion]
    )
    parser.add_argument("--no-play", action="store_true", help="再生せずタイムラインのみ表示")
    args = parser.parse_args()

    character = CharacterId(args.character)
    emotion = Emotion(args.emotion)
    manager = EngineManager(resolve_engine_paths(), load_character_configs())

    try:
        engine = manager.get_engine(character)
        print(f"[engine] {character.display_name} で合成中: {args.text!r} ({emotion.value})")
        utterance = engine.synthesize(args.text, emotion)
        print(f"[result] wav={len(utterance.wav)} bytes, duration={utterance.duration:.2f}s")

        print("[phonemes]")
        for ph in utterance.phonemes:
            print(f"  {ph.start:6.3f}-{ph.end:6.3f}  {ph.phoneme}")

        print("[mouth timeline]")
        for frame in build_mouth_timeline(utterance.phonemes):
            print(f"  {frame.start:6.3f}  {frame.shape.value}")

        if not args.no_play:
            player = AudioPlayer()
            dur = player.play(utterance.wav)
            print(f"[play] {dur:.2f}s 再生中...")
            while player.is_playing():
                time.sleep(0.05)
    finally:
        manager.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
