# セットアップ

本アプリは**音声・立ち絵アセットを同梱していません**（ライセンス上の理由 — 末尾「アセットについて」参照）。
各自で入手・配置してください。

## 1. 前提ソフト

| 用途 | ソフト | 備考 |
|------|--------|------|
| Python | 3.13 以上 | 3.14 で動作確認 |
| 春日部つむぎの音声 | [VOICEVOX](https://voicevox.hiroshiba.jp/) | エンジン (`run.exe`) のみで動作（GUI不要） |
| 小春六花の音声 | [CeVIO AI 小春六花](https://www.ah-soft.com/cevio/rikka/) | 製品購入・インストールが必要（Windows専用） |

## 2. インストール

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

## 3. エンジン/アセットのパス設定

`VoiceAppPath.example.md` を `VoiceAppPath.md` にコピーして、自分の環境のパスに書き換えます
（`VoiceAppPath.md` は環境固有のため gitignore 対象）。`local_settings.json`（自動生成・gitignore対象）でも上書きできます。

```
## VOICEVOX
C:\path\to\VOICEVOX\vv-engine\run.exe

## CeVIO AI
C:\path\to\CeVIO\CeVIO AI
```

## 4. 立ち絵アセットの配置

`local_settings.json` の `asset_root` に立ち絵フォルダのルートを指定し、その下に各キャラのフォルダを置きます。

```
<asset_root>/
  koharu_rikka/      # 小春六花 立ち絵 (PSD / png)
  kasukabe_tsumugi/  # 春日部つむぎ 立ち絵 (PSD)
```

立ち絵の入手元:
- 小春六花 立ち絵: 配布元の規約に従って入手（例: しりんだーふれいる 様 配布素材）
- 春日部つむぎ 公式立ち絵: [公式サイト](https://tsumugi-official.studio.site/top) の規約に従って入手

## 5. 起動

```powershell
voiceagent
# または
python -m voiceagent.app.main
```

---

## アセットについて（重要）

- **春日部つむぎ公式立ち絵は「二次配布」が禁止**されています。本リポジトリには含めず、各自で公式から入手してください。
- 小春六花の立ち絵・音声、CeVIO/VOICEVOX 各製品もそれぞれの規約に従ってください。
- 詳細は [LICENSE-THIRD-PARTY.md](LICENSE-THIRD-PARTY.md) を参照。
