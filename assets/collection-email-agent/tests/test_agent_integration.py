"""Integration tests for CollectionEmailAgent — LLM is mocked."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "app"))


def _make_llm_response(text: str) -> MagicMock:
    msg = MagicMock()
    msg.content = text
    return msg


def _make_graph(response_text: str) -> MagicMock:
    """Build a mock LangChain agent graph that returns response_text."""
    graph = MagicMock()
    graph.ainvoke = AsyncMock(
        return_value={"messages": [_make_llm_response(response_text)]}
    )
    return graph


class TestCollectionEmailAgentInvoke:
    @pytest.fixture(autouse=True)
    def patch_create_agent(self):
        mock_graph = _make_graph(
            "Subject: Overdue Invoice Reminder\n\nDear Customer,\n\n"
            "Your invoice INV-001 for USD 1,000.00 is overdue by 30 days.\n\n"
            "Please review and send this draft if it meets your requirements."
        )
        with patch("agent.create_agent", return_value=mock_graph):
            yield mock_graph

    async def test_invoke_returns_completed_status(self):
        from agent import CollectionEmailAgent
        agent = CollectionEmailAgent()
        result = await agent.invoke("Draft a collection email for customer CUST001", "ctx-1")
        assert result.status == "completed"

    async def test_invoke_response_contains_draft(self):
        from agent import CollectionEmailAgent
        agent = CollectionEmailAgent()
        result = await agent.invoke("Draft a collection email for customer CUST001", "ctx-2")
        assert "Subject:" in result.message or "invoice" in result.message.lower()

    async def test_stream_yields_processing_then_result(self):
        from agent import CollectionEmailAgent
        agent = CollectionEmailAgent()
        chunks = []
        async for chunk in agent.stream("Draft email for CUST001", "ctx-3"):
            chunks.append(chunk)
        assert len(chunks) >= 2
        assert chunks[0]["is_task_complete"] is False
        assert chunks[0]["content"] == "Processing..."
        assert chunks[-1]["is_task_complete"] is True

    async def test_stream_final_chunk_has_content(self):
        from agent import CollectionEmailAgent
        agent = CollectionEmailAgent()
        last = {}
        async for chunk in agent.stream("Draft email for CUST001", "ctx-4"):
            last = chunk
        assert last["content"] != ""
        assert last["require_user_input"] is False

    async def test_error_in_llm_returns_error_chunk(self):
        from agent import CollectionEmailAgent, AgentResponse

        bad_graph = MagicMock()
        bad_graph.ainvoke = AsyncMock(side_effect=RuntimeError("LLM unavailable"))

        agent = CollectionEmailAgent()
        with patch("agent.create_agent", return_value=bad_graph):
            result = await agent.invoke("Draft email", "ctx-err")

        assert result.status == "completed"
        assert "error" in result.message.lower() or "encountered" in result.message.lower()

    async def test_no_tools_appends_fallback_message(self):
        from agent import CollectionEmailAgent

        captured_prompts = []

        def capturing_create_agent(llm, *, tools, system_prompt, **kw):
            captured_prompts.append(system_prompt)
            return _make_graph("Tools unavailable.")

        agent = CollectionEmailAgent()
        with patch("agent.create_agent", side_effect=capturing_create_agent):
            await agent.invoke("hello", "ctx-notools", tools=[])

        assert captured_prompts
        assert "IMPORTANT" in captured_prompts[-1] or "unavailable" in captured_prompts[-1]

    async def test_thread_ttl_eviction(self):
        """Eviction runs without errors even when threads are expired."""
        import time
        from agent import CollectionEmailAgent, THREAD_TTL_SECONDS

        agent = CollectionEmailAgent()
        agent._last_active["old-thread"] = time.monotonic() - THREAD_TTL_SECONDS - 1

        with patch("agent.create_agent", return_value=_make_graph("ok")):
            result = await agent.invoke("hi", "ctx-new")
        assert "old-thread" not in agent._last_active
        assert result.status == "completed"


class TestAgentResponse:
    def test_dataclass_fields(self):
        from agent import AgentResponse
        r = AgentResponse(status="completed", message="hello")
        assert r.status == "completed"
        assert r.message == "hello"

    def test_input_required_status(self):
        from agent import AgentResponse
        r = AgentResponse(status="input_required", message="need more info")
        assert r.status == "input_required"

    def test_error_status(self):
        from agent import AgentResponse
        r = AgentResponse(status="error", message="something went wrong")
        assert r.status == "error"
