"""Behavior checks for paid-call limits, isolation and cloud agent execution."""

import asyncio
import gc
import importlib
import importlib.util
import json
import sqlite3
import unittest
from unittest.mock import AsyncMock, patch

import httpx
from openai import AsyncOpenAI


def chat_response(text=None, tool=None, arguments="{}"):
    """Chat Completions SSE at the external model HTTP boundary."""
    delta = {"role": "assistant"}
    if tool:
        delta["tool_calls"] = [{
            "index": 0, "id": "call_" + tool, "type": "function",
            "function": {"name": tool, "arguments": arguments},
        }]
    else:
        delta["content"] = text
    chunks = []
    for value, finish in [(delta, None), ({}, "tool_calls" if tool else "stop")]:
        chunks.append("data: " + json.dumps({
            "id": "chatcmpl-fixture", "object": "chat.completion.chunk", "created": 1,
            "model": "deepseek-chat",
            "choices": [{"index": 0, "delta": value, "finish_reason": finish}],
        }, ensure_ascii=False) + "\n\n")
    return httpx.Response(200, text="".join(chunks) + "data: [DONE]\n\n",
                          headers={"Content-Type": "text/event-stream"})


class PortfolioStateTests(unittest.TestCase):
    def setUp(self):
        name = "m13_streamlit.portfolio_backend"
        self.assertIsNotNone(importlib.util.find_spec(name), "cloud backend is not implemented")
        self.backend = importlib.import_module(name)
        self.state = self.backend.PortfolioState()
        self.addCleanup(self.state.close)

    def test_sixth_turn_is_rejected_without_changing_counter(self):
        for _ in range(5):
            self.state.start_turn("杭州天气")
        with self.assertRaises(ValueError):
            self.state.start_turn("再问一次")
        self.assertEqual(self.state.used_turns, 5)

    def test_invalid_input_does_not_consume_quota(self):
        for prompt in ("", "   ", "何" * 301):
            with self.subTest(prompt_length=len(prompt)):
                with self.assertRaises(ValueError):
                    self.state.start_turn(prompt)
        self.assertEqual(self.state.used_turns, 0)
        self.assertEqual(self.state.start_turn("何" * 300), "何" * 300)

    def test_clear_removes_memory_and_agent_but_preserves_quota(self):
        self.state.start_turn("我叫小何")
        self.state.current_agent = "RefundAgent"
        self.state.messages.append({"role": "user", "content": "我叫小何", "logs": []})
        asyncio.run(self.state.session.add_items([{"role": "user", "content": "我叫小何"}]))
        asyncio.run(self.state.clear())
        self.assertEqual(self.state.used_turns, 1)
        self.assertEqual(self.state.messages, [])
        self.assertEqual(self.state.current_agent, "TriageAgent")
        self.assertEqual(asyncio.run(self.state.session.get_items()), [])

    def test_two_visitors_have_independent_history_and_quota(self):
        other = self.backend.PortfolioState()
        self.addCleanup(other.close)
        self.state.start_turn("我叫小何")
        asyncio.run(self.state.session.add_items([{"role": "user", "content": "小何"}]))
        self.assertNotEqual(self.state.session_id, other.session_id)
        self.assertEqual(asyncio.run(other.session.get_items()), [])
        self.assertEqual(other.used_turns, 0)

    def test_unwritable_sqlite_falls_back_to_memory(self):
        real_session = self.backend.SQLiteSession
        def create_session(*args, **kwargs):
            if kwargs.get("db_path") != ":memory:":
                raise sqlite3.OperationalError("read only")
            return real_session(*args, **kwargs)
        with patch.object(self.backend, "SQLiteSession", side_effect=create_session):
            state = self.backend.PortfolioState()
        self.addCleanup(state.close)
        asyncio.run(state.session.add_items([{"role": "user", "content": "杭州"}]))
        self.assertEqual(asyncio.run(state.session.get_items()), [{"role": "user", "content": "杭州"}])
        self.assertTrue(state.memory_only)

    def test_abandoned_visitor_closes_database_and_removes_temp_directory(self):
        state = self.backend.PortfolioState()
        session = state.session
        directory = str(session.db_path)
        del state
        gc.collect()
        with self.assertRaises(RuntimeError):
            asyncio.run(session.get_items())
        from pathlib import Path
        self.assertFalse(Path(directory).parent.exists())


class PortfolioAgentTests(unittest.TestCase):
    setUp = PortfolioStateTests.setUp
    def execute(self, prompt, responses, api_key="fixture-key"):
        requests = []
        def handler(request):
            requests.append(json.loads(request.content))
            if not responses:
                raise AssertionError("unexpected paid model call")
            return responses.pop(0)
        client = AsyncOpenAI(api_key=api_key, base_url="https://fixture.invalid",
                             max_retries=0,
                             http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
        text_updates, agent_updates = [], []
        with patch.object(self.backend, "AsyncOpenAI", return_value=client):
            result = asyncio.run(self.backend.run_turn(
                self.state, prompt, api_key, on_text=text_updates.append,
                on_agent=agent_updates.append))
        return result, requests, text_updates, agent_updates

    def test_refund_handoff_and_tool_result_reach_final_answer(self):
        result, requests, updates, agents = self.execute("我想退票", [
            chat_response(tool="transfer_to_refundagent"),
            chat_response(tool="execute_refund"),
            chat_response("模拟退款申请已提交，小何。"),
        ])
        self.assertTrue(result["success"])
        self.assertEqual(result["content"], "模拟退款申请已提交，小何。")
        self.assertIn("RefundAgent", agents)
        self.assertEqual(self.state.current_agent, "RefundAgent")
        self.assertIn("execute_refund", " ".join(result["logs"]))
        self.assertIn("模拟", " ".join(result["logs"]))
        self.assertTrue(updates)
        self.assertEqual(len(requests), 3)
        self.assertTrue(all(r["max_tokens"] == 600 for r in requests))
        self.assertEqual(self.state.used_turns, 1)

    def test_weather_tool_requires_no_mcp_and_labels_fixed_data(self):
        result, requests, _, _ = self.execute("杭州天气", [
            chat_response(tool="get_weather", arguments='{"city":"杭州"}'),
            chat_response("杭州的模拟天气：晴，25℃，风力3级。"),
        ])
        self.assertTrue(result["success"])
        self.assertIn("get_weather", " ".join(result["logs"]))
        outputs = [m["content"] for m in requests[-1]["messages"] if m["role"] == "tool"]
        self.assertIn("教学固定数据", " ".join(outputs))
        self.assertIn("杭州", " ".join(outputs))

    def test_api_error_is_sanitized_and_consumes_one_attempt(self):
        result, _, _, _ = self.execute("你好", [
            httpx.Response(401, json={"error": {"message": "secret fixture-key", "type": "invalid_key"}}),
        ])
        self.assertFalse(result["success"])
        self.assertNotIn("fixture-key", str(result))
        self.assertEqual(self.state.used_turns, 1)
        self.assertEqual(asyncio.run(self.state.session.get_items()), [])
        self.assertEqual(self.state.messages[0]["content"], "你好")

    def test_exhausted_state_does_not_reach_model(self):
        for _ in range(5):
            self.state.start_turn("你好")
        with self.assertRaises(ValueError):
            self.execute("第六轮", [])

    def test_change_agent_seat_tool(self):
        result, _, _, agents = self.execute("我想改签", [
            chat_response(tool="transfer_to_changeagent"),
            chat_response(tool="check_seat"),
            chat_response("模拟查询：明日尚有余票，尚未改签。"),
        ])
        self.assertTrue(result["success"])
        self.assertIn("ChangeAgent", agents)
        self.assertIn("check_seat", " ".join(result["logs"]))

    def test_failed_history_read_returns_safe_message_and_recovers_storage(self):
        with patch.object(self.state.session, "get_items",
                          new=AsyncMock(side_effect=sqlite3.OperationalError("locked"))):
            result, requests, _, _ = self.execute("你好", [])
        self.assertFalse(result["success"])
        self.assertNotIn("locked", str(result))
        self.assertEqual(requests, [])
        self.assertEqual(self.state.used_turns, 1)
        self.assertEqual(len(self.state.messages), 2)


if __name__ == "__main__":
    unittest.main()
