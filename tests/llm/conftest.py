"""rlkit.llm のテスト用の道具立て。API は呼ばない（偽のクライアントを渡す）。"""
from __future__ import annotations

import struct
import sys
import zlib
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))

from rlkit import llm  # noqa: E402


def make_png(path: Path, w: int = 64, h: int = 32, seed: int = 0) -> Path:
    raw = b"".join(b"\x00" + bytes([(x + y + seed) % 256 for x in range(w)]) for y in range(h))

    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)

    data = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))
    path.write_bytes(data)
    return path


@pytest.fixture
def project(tmp_path, monkeypatch):
    p = tmp_path / "proj"
    (p / "notes").mkdir(parents=True)
    (p / "runs").mkdir()
    (p / "research.yaml").write_text(
        "project: proj\nbudget:\n  gpu_usd: 0\n  llm_usd_cap: 600\n  llm_usd_per_night: 10\n")
    for v in ("RL_RUN_DIR", "RL_PROJECT", "RL_NIGHT", "RL_NIGHT_STARTED_AT"):
        monkeypatch.delenv(v, raising=False)
    llm._WARNED.clear()
    return p


def set_cap(project: Path, cap=None, per_night=10, halt=None):
    lines = ["project: proj", "budget:", f"  llm_usd_per_night: {per_night}"]
    if cap is not None:
        lines.append(f"  llm_usd_cap: {cap}")
    if halt is not None:
        lines.append(f"  llm_halt_ratio: {halt}")
    (project / "research.yaml").write_text("\n".join(lines) + "\n")


# ── 偽の Anthropic クライアント（messages.stream(**body) → get_final_message().to_dict()）

class _Msg:
    def __init__(self, d):
        self._d = d
        self._request_id = "req_fake"

    def to_dict(self):
        return self._d


class _Stream:
    def __init__(self, d):
        self._d = d

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def get_final_message(self):
        return _Msg(self._d)


class FakeAnthropic:
    def __init__(self, responses):
        self.responses = list(responses)
        self.bodies = []
        self.messages = SimpleNamespace(stream=self._stream)

    def _stream(self, **body):
        self.bodies.append(body)
        return _Stream(self.responses.pop(0))


def anth_resp(text="ok", *, stop="end_turn", tool_uses=(), usage=None, model="claude-opus-5-5",
              stop_details=None, thinking=True):
    content = []
    if thinking:
        content.append({"type": "thinking", "thinking": "", "signature": "sig-abc"})
    if text:
        content.append({"type": "text", "text": text})
    for tu in tool_uses:
        content.append({"type": "tool_use", **tu})
    return {"id": "msg_1", "type": "message", "role": "assistant", "model": model, "content": content,
            "stop_reason": stop, "stop_details": stop_details,
            "usage": usage or {"input_tokens": 1000, "output_tokens": 200,
                               "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}}


# ── 偽の OpenAI 互換クライアント（chat.completions.create(**body)）

class _Resp:
    def __init__(self, d):
        self._d = d
        self._request_id = "req_oa"

    def to_dict(self):
        return self._d


class FakeOpenAI:
    def __init__(self, responses=(), raises=None):
        self.responses = list(responses)
        self.bodies = []
        self.raises = raises
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **body):
        self.bodies.append(body)
        if self.raises:
            raise self.raises
        r = self.responses.pop(0)
        if body.get("stream"):
            return iter(r)            # 断片の並び
        return _Resp(r)


def oa_resp(text="ok", *, finish="stop", tool_calls=None, usage=None, model="gpt-5-2025-08-07", refusal=None):
    msg = {"role": "assistant", "content": text, "refusal": refusal}
    if tool_calls:
        msg["tool_calls"] = tool_calls
    return {"id": "chatcmpl-1", "object": "chat.completion", "model": model,
            "choices": [{"index": 0, "message": msg, "finish_reason": finish}],
            "usage": usage or {"prompt_tokens": 1000, "completion_tokens": 100,
                               "prompt_tokens_details": {"cached_tokens": 0}}}
