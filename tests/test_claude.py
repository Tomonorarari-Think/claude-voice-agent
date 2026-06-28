"""Claude レイヤーのテスト（SDK の query をモック）。"""

import pytest
from claude_agent_sdk import AssistantMessage, ResultMessage, TextBlock

from voiceagent.claude import agent_client as ac_module
from voiceagent.claude.agent_client import AgentClient
from voiceagent.claude.events import AgentDone, AgentError, AgentTextChunk
from voiceagent.claude.model_registry import MODELS, default_model, model_by_id
from voiceagent.claude.persona import build_system_prompt
from voiceagent.claude.session_manager import SessionManager
from voiceagent.config.characters import load_character_configs
from voiceagent.domain.character import CharacterId


def _config():
    return load_character_configs()[CharacterId.KASUKABE_TSUMUGI]


def _result(session_id="sess-1", cost=0.01):
    return ResultMessage(
        subtype="success",
        duration_ms=10,
        duration_api_ms=8,
        is_error=False,
        num_turns=1,
        session_id=session_id,
        total_cost_usd=cost,
    )


# --- model_registry / persona / session_manager (純粋) ---------------------


def test_model_registry_defaults_and_lookup():
    assert default_model().id == "claude-opus-4-8"
    assert model_by_id("claude-sonnet-4-6").label == "Sonnet 4.6"
    # 未知 ID でも前方互換で ModelInfo を返す
    assert model_by_id("future-model").id == "future-model"
    assert len(MODELS) >= 3


def test_persona_appends_to_claude_code_preset():
    sp = build_system_prompt(_config())
    assert sp["type"] == "preset"
    assert sp["preset"] == "claude_code"
    assert "春日部つむぎ" in sp["append"]
    assert "音声で読み上げ" in sp["append"]


def test_session_manager_remember_and_new_topic():
    sm = SessionManager()
    assert sm.session_id is None
    sm.remember("abc")
    assert sm.session_id == "abc"
    sm.remember(None)  # None は無視
    assert sm.session_id == "abc"
    sm.new_topic()
    assert sm.session_id is None


# --- AgentClient.stream (query をモック) -----------------------------------


def _patch_query(monkeypatch, messages, capture=None):
    async def fake_query(*, prompt, options):
        if capture is not None:
            capture["prompt"] = prompt
            capture["options"] = options
        for m in messages:
            yield m

    monkeypatch.setattr(ac_module, "query", fake_query)


async def test_stream_yields_text_then_done_and_records_session(monkeypatch):
    msgs = [
        AssistantMessage(content=[TextBlock("こんにちは")], model="claude-opus-4-8"),
        AssistantMessage(content=[TextBlock("元気？")], model="claude-opus-4-8"),
        _result(session_id="s-42", cost=0.02),
    ]
    capture = {}
    _patch_query(monkeypatch, msgs, capture)

    sm = SessionManager()
    client = AgentClient(sm)
    events = [e async for e in client.stream("やあ", _config(), "claude-opus-4-8")]

    texts = [e.text for e in events if isinstance(e, AgentTextChunk)]
    assert texts == ["こんにちは", "元気？"]
    done = [e for e in events if isinstance(e, AgentDone)]
    assert done[0].session_id == "s-42"
    assert done[0].cost_usd == 0.02
    # セッションが記録され、次回 resume に使われる
    assert sm.session_id == "s-42"
    assert capture["options"].model == "claude-opus-4-8"
    assert capture["options"].resume is None  # 初回は resume なし


async def test_stream_uses_resume_on_second_turn(monkeypatch):
    _patch_query(monkeypatch, [_result(session_id="s-1")], capture := {})
    sm = SessionManager()
    sm.remember("s-1")
    client = AgentClient(sm)
    _ = [e async for e in client.stream("続き", _config(), "claude-sonnet-4-6")]
    assert capture["options"].resume == "s-1"
    assert capture["options"].model == "claude-sonnet-4-6"


async def test_stream_emits_error_event_on_exception(monkeypatch):
    async def boom(*, prompt, options):
        raise RuntimeError("CLI not found")
        yield  # pragma: no cover - generator にするため

    monkeypatch.setattr(ac_module, "query", boom)
    client = AgentClient(SessionManager())
    events = [e async for e in client.stream("x", _config(), "claude-opus-4-8")]
    assert any(isinstance(e, AgentError) and "CLI not found" in e.message for e in events)


def test_stream_rejects_empty_prompt():
    client = AgentClient(SessionManager())

    async def run():
        return [e async for e in client.stream("   ", _config(), "claude-opus-4-8")]

    with pytest.raises(ValueError):
        import asyncio

        asyncio.run(run())
