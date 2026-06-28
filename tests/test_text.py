"""テキスト整形・文分割・感情推定のテスト。"""

from voiceagent.domain.emotion import Emotion
from voiceagent.text.emotion_tagger import infer_emotion
from voiceagent.text.filter import clean_for_speech
from voiceagent.text.segmenter import extract_complete_sentences, split_sentences


# --- filter ---------------------------------------------------------------


def test_removes_fenced_code_block():
    text = "これを実行します。\n```python\nprint('hello')\n```\n完了しました。"
    out = clean_for_speech(text)
    assert "print" not in out
    assert "これを実行します。" in out
    assert "完了しました。" in out


def test_removes_urls():
    out = clean_for_speech("詳しくは https://example.com/docs を見てね。")
    assert "http" not in out
    assert "example.com" not in out
    assert "詳しくは" in out


def test_keeps_link_text_drops_url():
    out = clean_for_speech("[公式ドキュメント](https://example.com)を参照。")
    assert "公式ドキュメント" in out
    assert "example.com" not in out


def test_removes_file_paths():
    out = clean_for_speech("ファイル src/voiceagent/app/main.py を編集しました。")
    assert "main.py" not in out
    assert "src/voiceagent" not in out
    assert "編集しました" in out


def test_windows_path_removed():
    out = clean_for_speech("設定は C:\\Users\\foo\\config.toml にあります。")
    assert "C:\\" not in out
    assert "config.toml" not in out


def test_inline_code_symbolic_removed_plain_kept():
    out = clean_for_speech("`npm` を使います。`const x = foo()` は省略。")
    assert "npm" in out  # 平易な短語は残す
    assert "const x" not in out  # 記号を含むコードは除去


def test_strips_markdown_markers():
    text = "# 見出し\n- 項目1\n- 項目2\n**強調**された言葉。"
    out = clean_for_speech(text)
    assert "#" not in out
    assert "**" not in out
    assert "見出し" in out
    assert "強調" in out


# --- segmenter ------------------------------------------------------------


def test_split_sentences_japanese():
    s = split_sentences("こんにちは。元気ですか？今日はいい天気！")
    assert s == ["こんにちは。", "元気ですか？", "今日はいい天気！"]


def test_split_sentences_handles_newlines():
    s = split_sentences("一行目\n二行目です。")
    assert "一行目" in s[0]
    assert s[-1].endswith("。")


def test_extract_complete_sentences_streaming():
    complete, rest = extract_complete_sentences("やあ。元気？まだ途中")
    assert complete == ["やあ。", "元気？"]
    assert rest == "まだ途中"

    # 残りに続きを足すと次の文が確定する
    complete2, rest2 = extract_complete_sentences(rest + "だよ。")
    assert complete2 == ["まだ途中だよ。"]
    assert rest2 == ""


# --- emotion_tagger -------------------------------------------------------


def test_emotion_happy():
    assert infer_emotion("やったー！できたよ！") == Emotion.HAPPY


def test_emotion_angry():
    assert infer_emotion("もう最悪、エラーで壊れた。") == Emotion.ANGRY


def test_emotion_sad():
    assert infer_emotion("ごめん、うまくいかなくて残念。") == Emotion.SAD


def test_emotion_calm():
    assert infer_emotion("なるほど、了解だよ。") == Emotion.CALM


def test_emotion_default_neutral():
    assert infer_emotion("これは普通の文です。") == Emotion.NEUTRAL
    assert infer_emotion("") == Emotion.NEUTRAL
