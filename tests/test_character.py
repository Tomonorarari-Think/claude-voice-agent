"""立ち絵スロット/口形/表情マッピングのテスト（PSD 非依存の純粋ロジック）。"""

from voiceagent.character.expression_set import ExpressionSet
from voiceagent.character.mouth_map import MouthMap
from voiceagent.character.slots import Layout, Slot, classify_role, slot_for_role
from voiceagent.domain.emotion import Emotion
from voiceagent.domain.phoneme import MouthFrame, MouthShape
from voiceagent.tts.lipsync import shape_at


def _layout():
    return Layout(
        size=(100, 200),
        slots=(
            Slot("mouth", "!口", ("通常", "通常開き", "あ", "い")),
            Slot("eyes", "!目", ("通常", "笑", "閉じ")),
            Slot("brows", "!眉", ("通常", "怒り")),
        ),
        has_flip_layer=True,
    )


def test_classify_role_from_japanese_group_names():
    assert classify_role("!口") == "mouth"
    assert classify_role("!目") == "eyes"
    assert classify_role("!眉") == "brows"
    assert classify_role("!腕") == "arms"
    assert classify_role("!Body") == "body"
    assert classify_role("チーク先") == "other"


def test_slot_for_role():
    layout = _layout()
    assert slot_for_role(layout, "mouth").group_name == "!口"
    assert layout.slot_for_role("eyes").group_name == "!目"
    assert slot_for_role(layout, "arms") is None


def test_slot_resolve_index_by_int_name_and_clamp():
    slot = _layout().slots[0]
    assert slot.resolve_index(1) == 1
    assert slot.resolve_index("あ") == 2  # 完全一致
    assert slot.resolve_index("開き") == 1  # 部分一致 (通常開き)
    assert slot.resolve_index(99) == 3  # クランプ
    assert slot.resolve_index(None, default=2) == 2


def test_mouth_map_two_state_default():
    mm = MouthMap()
    slot = _layout().slots[0]
    assert mm.index_for(MouthShape.CLOSED, slot) == 0
    assert mm.index_for(MouthShape.A, slot) == 1
    assert mm.index_for(MouthShape.O, slot) == 1


def test_mouth_map_from_config_vowels():
    mm = MouthMap.from_config({"closed_index": 0, "open_index": 1, "a_index": 2, "i_index": 3})
    slot = _layout().slots[0]
    assert mm.index_for(MouthShape.CLOSED, slot) == 0
    assert mm.index_for(MouthShape.A, slot) == 2
    assert mm.index_for(MouthShape.I, slot) == 3
    assert mm.index_for(MouthShape.U, slot) == 1  # 未指定 -> open


def test_expression_set_from_config_and_fallback():
    es = ExpressionSet.from_config({"happy": {"eyes": 1, "brows": 0}, "angry": {"brows": 1}})
    assert es.selection_for(Emotion.HAPPY) == {"eyes": 1, "brows": 0}
    assert es.selection_for(Emotion.ANGRY) == {"brows": 1}
    assert es.selection_for(Emotion.SAD) == {}  # 未定義 -> 中立


def test_shape_at_position_lookup():
    frames = (
        MouthFrame(0.0, MouthShape.CLOSED),
        MouthFrame(0.2, MouthShape.A),
        MouthFrame(0.5, MouthShape.CLOSED),
    )
    assert shape_at(frames, 0.0) == MouthShape.CLOSED
    assert shape_at(frames, 0.3) == MouthShape.A
    assert shape_at(frames, 0.9) == MouthShape.CLOSED
    assert shape_at((), 0.1) == MouthShape.CLOSED
