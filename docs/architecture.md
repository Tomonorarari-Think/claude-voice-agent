# アーキテクチャ

VoiceAgent は「Claude Code の対話を、デスクトップ常駐のキャラが音声で読み上げる」アプリです。
レイヤードアーキテクチャで、エンジン差異や UI フレームワークへの依存を内側に持ち込まないよう設計しています。

## レイヤー構成

```
domain/     不変ドメインモデル（Emotion, CharacterId, Phoneme, MouthShape, Utterance, Message）
config/     設定・エンジン/アセットのパス解決・キャラ定義(TOML)
claude/     Claude Agent SDK ラッパー（ストリーム / セッション継続 / モデル切替 / persona）
text/       読み上げ整形（コード/URL除去）・文分割・感情推定
tts/        音声エンジン抽象 + VOICEVOX(HTTP) / CeVIO(COM) + ヘッドレス起動 + リップシンク
audio/      WAV デコード・再生・再生位置トラッキング
character/  PSD ロード・スロット解決・口形/表情マッピング・フレーム合成
app/        会話オーケストレーション（worker スレッド）・再生器・エントリ
ui/         透過常駐ウィンドウ・立ち絵表示・チャットオーバーレイ
```

依存方向は上から下のみ（`ui`/`app` → 各サービス → `domain`）。`domain` は何にも依存しません。

## 会話 1 ターンのデータフロー

```
ユーザー入力 (ui.ChatOverlay)
   │  submitted(str)
   ▼
app.AppController.send() ──► app.AgentTurnWorker (QThread)
                                  │  claude.AgentClient.stream()  ← persona / model / resume
                                  │     └─ AgentTextChunk をストリーム受信
                                  │  text.extract_complete_sentences() で文確定
                                  │  text.clean_for_speech()  （コード/URL/パス除去）
                                  │  text.infer_emotion()
                                  │  tts.EngineManager.get_engine().synthesize()  （ヘッドレス）
                                  │  tts.build_mouth_timeline()
                                  ▼  signals
        assistant_text(str) ─────────────► ui.ChatOverlay（フェード表示）
        speech_ready(SpeechItem) ────────► app.SpeechPlayer（GUI スレッド）
                                                │  audio.AudioPlayer.play()
                                                │  QTimer 30fps: lipsync.shape_at(pos)
                                                ▼  frame(Emotion, MouthShape)
                                          ui.CharacterView → character.CharacterRenderer.render()
```

ポイント:
- **スレッド分離**: 合成（HTTP/COM はブロッキング）は worker スレッド、再生とフレーム更新は GUI スレッド。橋渡しは Qt シグナル（キュー接続）。
- **文単位ストリーミング**: 文が確定するたびに合成・再生キューへ積むため、応答全体を待たずに喋り始める。
- **エンジン非依存のリップシンク**: VOICEVOX の mora と CeVIO の音素を共通 `Phoneme` 列へ正規化し、`build_mouth_timeline` で口形フレームに変換。

## エンジン統合

| キャラ | エンジン | 接続 | ヘッドレス起動 | 音素タイミング |
|--------|----------|------|----------------|----------------|
| 春日部つむぎ | VOICEVOX | HTTP (`run.exe`) | `run.exe --host --port` をウィンドウなし起動 | AudioQuery の mora 長 |
| 小春六花 | CeVIO AI | COM (RemoteService2) | `ServiceControl2.StartHost(False)` | `Talker2.GetPhonemes()` |

どちらも GUI 本体を起動せずバックエンドのみで動作します（要件: 誤操作で閉じないように）。

## 立ち絵レンダリング

立ち絵 PSD は「`!` 接頭辞グループ＝排他スロット」という慣習を利用します。
役割（口/目/眉）はグループ名のキーワードで解決し、表示する子レイヤーをインデックスで選択します。
レイヤー名はキャラ・配布バージョンで異なるため、`python -m voiceagent.character.inspect_cli <psd>` で
一覧を確認し、キャラ TOML の `[mouth]` / `[expression]` を調整します。

リップシンクは MVP では 2 状態（閉じ / 開き）で確実に動作し、母音 5 形は config で拡張できます。

## 設定とアセット

- コードは MIT。**音声・立ち絵アセットは同梱せず**、`asset_root` 配下に各自配置（[SETUP.md](../SETUP.md)）。
- 春日部つむぎ立ち絵は二次配布禁止（[LICENSE-THIRD-PARTY.md](../LICENSE-THIRD-PARTY.md)）。
- ユーザー固有設定は `local_settings.json`（gitignore 対象）に永続化。

## テスト戦略

- 純粋ロジック（filter / segmenter / emotion / lipsync / slots / mouth_map / config / domain）を
  ユニットテストで担保（53 tests）。
- エンジン/SDK/PSD/GUI は実機スモークで検証（`*/smoke.py`, `inspect_cli`, オフスクリーン起動）。
- COM/HTTP/Qt はモック・フェイク・遅延 import で隔離し、CI でも import 可能に。
