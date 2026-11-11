"""本物の SDK（anthropic・openai）を手元の偽のサーバーに向けて、送る形と読み取りを確かめる。外には出ない。

SDK が入っていなければ飛ばす：
    uv run --python 3.11 --with pytest --with ruamel.yaml --with anthropic --with openai python -m pytest tests/llm
"""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from conftest import make_png
from rlkit import llm

anthropic = pytest.importorskip("anthropic")
openai = pytest.importorskip("openai")


def _sse(events):
    out = ""
    for ev in events:
        out += f"event: {ev['type']}\ndata: {json.dumps(ev)}\n\n"
    return out.encode()


ANTH_EVENTS = [
    {"type": "message_start", "message": {"id": "msg_1", "type": "message", "role": "assistant",
                                          "model": "claude-opus-5-5", "content": [], "stop_reason": None,
                                          "stop_sequence": None,
                                          "usage": {"input_tokens": 120, "output_tokens": 1,
                                                    "cache_read_input_tokens": 3000,
                                                    "cache_creation_input_tokens": 0}}},
    {"type": "content_block_start", "index": 0, "content_block": {"type": "thinking", "thinking": "", "signature": ""}},
    {"type": "content_block_delta", "index": 0, "delta": {"type": "signature_delta", "signature": "sig-xyz"}},
    {"type": "content_block_stop", "index": 0},
    {"type": "content_block_start", "index": 1, "content_block": {"type": "text", "text": ""}},
    {"type": "content_block_delta", "index": 1, "delta": {"type": "text_delta", "text": "checking"}},
    {"type": "content_block_stop", "index": 1},
    {"type": "content_block_start", "index": 2,
     "content_block": {"type": "tool_use", "id": "tu_1", "name": "check_sequence", "input": {}}},
    {"type": "content_block_delta", "index": 2,
     "delta": {"type": "input_json_delta", "partial_json": "{\"order\": [\"base\", \"arm\"]}"}},
    {"type": "content_block_stop", "index": 2},
    {"type": "message_delta", "delta": {"stop_reason": "tool_use", "stop_sequence": None}, "usage": {"output_tokens": 40}},
    {"type": "message_stop"},
]

OA_JSON = {"id": "chatcmpl-1", "object": "chat.completion", "created": 1, "model": "gpt-5-2025-08-07",
           "choices": [{"index": 0, "finish_reason": "stop",
                        "message": {"role": "assistant", "content": "pong", "refusal": None}}],
           "usage": {"prompt_tokens": 900, "completion_tokens": 30, "total_tokens": 930,
                     "prompt_tokens_details": {"cached_tokens": 512},
                     "completion_tokens_details": {"reasoning_tokens": 20}}}

QWEN_CHUNKS = [
    {"id": "c1", "object": "chat.completion.chunk", "created": 1, "model": "qwen3-vl-plus",
     "choices": [{"index": 0, "delta": {"role": "assistant", "content": "po"}, "finish_reason": None}]},
    {"id": "c1", "object": "chat.completion.chunk", "created": 1, "model": "qwen3-vl-plus",
     "choices": [{"index": 0, "delta": {"content": "ng"}, "finish_reason": "stop"}]},
    {"id": "c1", "object": "chat.completion.chunk", "created": 1, "model": "qwen3-vl-plus", "choices": [],
     "usage": {"prompt_tokens": 100, "completion_tokens": 2, "total_tokens": 102}},
]


@pytest.fixture
def server():
    seen = []

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            seen.append({"path": self.path, "body": body, "headers": dict(self.headers)})
            if self.path.endswith("/messages"):
                data, ctype = _sse(ANTH_EVENTS), "text/event-stream"
            elif body.get("stream"):
                data = b"".join(f"data: {json.dumps(c)}\n\n".encode() for c in QWEN_CHUNKS) + b"data: [DONE]\n\n"
                ctype = "text/event-stream"
            else:
                data, ctype = json.dumps(OA_JSON).encode(), "application/json"
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("request-id", "req_local")
            self.end_headers()
            self.wfile.write(data)

    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    yield f"http://127.0.0.1:{srv.server_address[1]}", seen
    srv.shutdown()


SECRET = "sk-ant-test-WIRESECRET-0123456789"


def test_anthropic_wire(project, server, tmp_path, monkeypatch):
    base, seen = server
    monkeypatch.setenv("ANTHROPIC_API_KEY", SECRET)
    client = anthropic.Anthropic(base_url=base, max_retries=0)
    png = make_png(tmp_path / "r.png")
    schema = {"type": "object", "properties": {"order": {"type": "array", "items": {"type": "string"}}},
              "required": ["order"], "additionalProperties": False}
    tool = llm.Tool("check_sequence", "L1", schema, fn=lambda order: "ok")
    r = llm.call("claude-opus-5-5", "plan", system="sys", images=[png], tools=[tool], max_tokens=64000,
                 effort="high", budget_project=project, client=client)
    sent = seen[0]["body"]
    assert seen[0]["path"].endswith("/v1/messages") and sent["stream"] is True
    assert sent["model"] == "claude-opus-5-5" and sent["output_config"] == {"effort": "high"}
    assert sent["thinking"] == {"type": "adaptive"} and sent["cache_control"] == {"type": "ephemeral"}
    assert sent["tools"][0]["strict"] is True and sent["messages"][0]["content"][0]["source"]["data"].startswith("iVBOR")
    for k in ("temperature", "top_p", "top_k", "tool_choice", "fallbacks"):
        assert k not in sent
    assert r.stop_reason == "tool_use" and r.tool_calls == [{"id": "tu_1", "name": "check_sequence",
                                                             "input": {"order": ["base", "arm"]}}]
    assert r.text == "checking" and r.usage["cache_read_tokens"] == 3000 and r.usage["output_tokens"] == 40
    assert r.cost_usd == pytest.approx((120 * 4 + 3000 * 0.2 + 40 * 20) / 1e6)
    assert r.assistant_message["content"][0]["type"] == "thinking"
    # 鍵は送られるが、記録には残らない
    assert any(SECRET in v for v in seen[0]["headers"].values())
    every = "".join(p.read_text() for p in project.rglob("*") if p.is_file() and p.suffix in (".json", ".jsonl"))
    assert SECRET not in every


def test_openai_wire(project, server, monkeypatch):
    base, seen = server
    client = openai.OpenAI(base_url=base + "/v1", api_key="sk-test-openai-000000000000000000000", max_retries=0)
    r = llm.call("gpt-5", "ping", system="sys", max_tokens=2000, effort="low", budget_project=project, client=client)
    sent = seen[0]["body"]
    assert sent["max_completion_tokens"] == 2000 and sent["reasoning_effort"] == "low" and "temperature" not in sent
    assert r.text == "pong" and r.usage["input_tokens"] == 388 and r.usage["cache_read_tokens"] == 512
    assert r.model_returned == "gpt-5-2025-08-07"
    assert not json.loads(next((project / "notes" / "llm-logs").glob("*.jsonl")).read_text().splitlines()[0])["model_mismatch"]


def test_qwen_stream_wire(project, server):
    base, seen = server
    client = openai.OpenAI(base_url=base + "/v1", api_key="dummy-dashscope", max_retries=0)
    r = llm.call("qwen3-vl-plus", "ping", max_tokens=100, budget_project=project, client=client)
    sent = seen[0]["body"]
    assert sent["stream"] is True and sent["stream_options"] == {"include_usage": True}
    assert sent["enable_thinking"] is True          # extra_body は本文の最上位に展開される
    assert r.text == "pong" and r.usage["input_tokens"] == 100
