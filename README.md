# VoiceAgent — Claude 対話読み上げデスクトップキャラアプリ

Claude Code の対話を、デスクトップに常駐するキャラクター（**小春六花** / **春日部つむぎ**）が
音声で読み上げるアプリです。透過ウィンドウに立ち絵を表示し、表情変化とリップシンクで
「キャラがそこにいる」体験を目指します。

> ⚠️ 音声・立ち絵アセットは同梱していません。[docs/setup.md](docs/setup.md) と
> [docs/third-party-licenses.md](docs/third-party-licenses.md) を必ず確認してください
> （春日部つむぎ立ち絵は二次配布禁止）。

## 主な機能（開発中）

- Claude Code の Agent 応答をストリーム読み上げ（コード/URL は読まず会話的に整形）
- 音声合成: 小春六花 = CeVIO AI、春日部つむぎ = VOICEVOX（いずれもバックエンドのみで動作）
- PSD 立ち絵の表情変化 + リップシンク + 感情表現
- チャット欄（モデル切替 Opus/Sonnet/Haiku、セッション継続、「新しい話題」）
- 透過・常駐・リサイズ・左右反転対応のデスクトップウィジェット
- （後フェーズ）メモ / アラーム / ポモドーロ / Riot API 戦績

## プロジェクト構成

```
claude-voice-agent/
  src/voiceagent/      アプリ本体（レイヤード構成）
    domain/            不変ドメインモデル
    config/            設定・パス・キャラ定義（TOML）
    claude/            Claude Agent SDK ラッパー
    text/              読み上げ整形フィルタ + 感情推定
    tts/               音声エンジン抽象 + VOICEVOX/CeVIO + リップシンク
    audio/             再生 + タイムライン同期
    character/         PSD ローダ + 表情 + 口形マッピング
    ui/                透過常駐ウィンドウ + チャット UI
    app/               エントリポイント・オーケストレーション
  tests/               ユニットテスト
  docs/                設計・セットアップ・ライセンス・構想
  scripts/             起動・セットアップ用バッチ
  slides/              プロジェクト紹介スライド
```

設計の詳細は [docs/architecture.md](docs/architecture.md) を参照。

## 起動（バッチファイル）

`scripts/` 内のバッチをダブルクリックします。

| ファイル | 用途 |
|----------|------|
| `scripts/setup.bat` | 初回セットアップ（仮想環境作成 + 依存インストール） |
| `scripts/VoiceAgent.bat` | 通常起動（コンソールなしで GUI 起動） |
| `scripts/VoiceAgent-debug.bat` | ログ確認用（コンソール表示。起動しない時はこちら） |

初回は `scripts/setup.bat` → 以降は `scripts/VoiceAgent.bat` をダブルクリック。

## 操作

- **入力**: 画面下部の入力欄（常に最前面）。直上にモデル切替・「新規チャット」・「履歴」表示トグル。
- **メニュー**: **キャラの上で右クリック** → キャラ切替 / 左右反転 / 上半身表示 / チャット履歴の前面切替 / トレイ格納 / 終了。
- **上半身表示**はキャラごとに `upper_body_fraction`（TOML）で範囲を調整できます。
- **移動**: 立ち絵をドラッグ。**リサイズ**: 右下のグリップ。
- 普段はボタンを表示せず、立ち絵と入力欄だけのすっきりした見た目です。

## 開発

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
pytest
```

ブランチ運用は git-flow（`main` / `develop` / `feature/*`）。
