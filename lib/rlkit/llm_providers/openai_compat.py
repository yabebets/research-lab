"""OpenAI の Chat Completions 互換（公式の openai SDK）。GPT-5、DashScope の Qwen3-VL、vLLM で動かす Qwen3-VL。

- GPT-5 は推論モデル：temperature などは送らない、上限は max_completion_tokens、深さは reasoning_effort
- DashScope と vLLM は base_url を替えるだけ。DashScope 独自の引数（enable_thinking など）は extra_body に入れる
- 拒否は message.refusal、finish_reason == content_filter、DashScope の 400 data_inspection_failed
"""
from __future__ import annotations

import os

from . import (as_blocks, blob_for_path, collect_blobs, first_user_index, parse_json_args,
               replace_refs, tool_spec)

STOP_MAP = {"stop": "end_turn", "length": "max_tokens", "tool_calls": "tool_use",
            "function_call": "tool_use", "content_filter": "refusal"}
STD_PARAMS = {"verbosity", "stop", "seed", "prompt_cache_key", "metadata"}


class MissingKey(RuntimeError):
    pass


def _img(b, cfg) -> dict:
    iu = {"url": b.ref}
    if cfg.get("image_detail"):
        iu["detail"] = cfg["image_detail"]
    return {"type": "image_url", "image_url": iu}


def _set_path(body: dict, dotted: str, value):
    cur = body
    parts = dotted.split(".")
    for p in parts[:-1]:
        cur = cur.setdefault(p, {})
    cur[parts[-1]] = value


def build_body(cfg, *, system, messages, images, tools, max_tokens, effort, params, prompt_cache):
    top, blobs = collect_blobs(messages, images)
    srole = cfg.get("system_role") or "system"
    native = []
    if system:
        native.append({"role": srole, "content": system})
    fu = first_user_index(messages)
    for i, m in enumerate(messages):
        role = m.get("role")
        if role == "assistant":
            native.append({k: v for k, v in m.items() if k in ("role", "content", "tool_calls")})
            continue
        if role == "system":
            native.append({"role": srole, "content": m["content"]})
            continue
        parts = [_img(b, cfg) for b in top] if i == fu else []
        tool_msgs = []
        for blk in as_blocks(m.get("content")):
            t = blk.get("type")
            if t == "image" and "path" in blk:
                parts.append(_img(blob_for_path(blobs, blk["path"]), cfg))
            elif t == "tool_result":
                c = blk["content"]
                if blk.get("is_error"):
                    c = f"ERROR: {c}"
                tool_msgs.append({"role": "tool", "tool_call_id": blk["tool_call_id"], "content": c})
            else:
                parts.append(blk)
        native.extend(tool_msgs)          # 道具の結果は assistant の直後に置く
        if parts:
            native.append({"role": "user", "content": parts})

    body: dict = {"model": cfg["model_id"], "messages": native,
                  cfg.get("max_tokens_param") or "max_tokens": int(max_tokens)}
    eff = cfg.get("effort") or None
    if effort is not None and eff:
        value = (eff.get("map") or {}).get(effort, effort)
        _set_path(body, eff["param"], value)
    if tools:
        out = []
        for t in tools:
            s = tool_spec(t)
            fn = {"name": s["name"], "description": s["description"], "parameters": s["input_schema"]}
            if cfg.get("strict_tools"):
                fn["strict"] = True
            out.append({"type": "function", "function": fn})
        body["tools"] = out
    for k, v in params.items():
        if k in STD_PARAMS:
            body[k] = v
        else:
            body.setdefault("extra_body", {})[k] = v
    if cfg.get("stream"):
        body["stream"] = True
        body["stream_options"] = {"include_usage": True}
    return body, blobs


def materialize(body, blobs):
    return replace_refs(body, lambda sha: f"data:{blobs[sha].media_type};base64,{blobs[sha].b64()}")


def make_client(cfg):
    import openai
    envs = cfg.get("api_key_env") or []
    key = next((os.environ[v] for v in envs if os.environ.get(v)), None)
    if not key and not cfg.get("api_key_optional"):
        raise MissingKey(f"{' / '.join(envs)} が未設定です（値は表示しません）")
    base = (os.environ.get(cfg["base_url_env"]) if cfg.get("base_url_env") else None) or cfg.get("base_url")
    return openai.OpenAI(api_key=key or "EMPTY", base_url=base or None, timeout=900.0, max_retries=2)


def _d(x):
    return x.to_dict() if hasattr(x, "to_dict") else x


def accumulate(chunks) -> dict:
    """stream=True の断片を、stream なしの応答と同じ形の dict にまとめる。"""
    rid = model = fr = None
    usage = None
    content, reasoning, refusal = [], [], []
    calls: dict[int, dict] = {}
    for ch in chunks:
        d = _d(ch)
        rid = d.get("id") or rid
        model = d.get("model") or model
        if d.get("usage"):
            usage = d["usage"]
        for c in d.get("choices") or []:
            delta = c.get("delta") or {}
            content.append(delta.get("content") or "")
            reasoning.append(delta.get("reasoning_content") or "")
            refusal.append(delta.get("refusal") or "")
            for tc in delta.get("tool_calls") or []:
                slot = calls.setdefault(tc.get("index", 0),
                                        {"id": None, "type": "function", "function": {"name": "", "arguments": ""}})
                if tc.get("id"):
                    slot["id"] = tc["id"]
                f = tc.get("function") or {}
                slot["function"]["name"] += f.get("name") or ""
                slot["function"]["arguments"] += f.get("arguments") or ""
            if c.get("finish_reason"):
                fr = c["finish_reason"]
    msg = {"role": "assistant", "content": "".join(content) or None}
    if calls:
        msg["tool_calls"] = [calls[i] for i in sorted(calls)]
    if "".join(reasoning):
        msg["reasoning_content"] = "".join(reasoning)
    if "".join(refusal):
        msg["refusal"] = "".join(refusal)
    return {"id": rid, "model": model, "object": "chat.completion", "streamed": True,
            "choices": [{"index": 0, "message": msg, "finish_reason": fr}], "usage": usage or {}}


def send(client, body, cfg):
    resp = client.chat.completions.create(**body)
    rid = getattr(resp, "_request_id", None)
    if body.get("stream"):
        return accumulate(resp), rid
    return _d(resp), rid


def parse(raw: dict, cfg) -> dict:
    ch = (raw.get("choices") or [{}])[0]
    msg = ch.get("message") or {}
    text = msg.get("content") or ""
    if isinstance(text, list):
        text = "".join(p.get("text", "") for p in text if isinstance(p, dict))
    tool_calls = []
    for tc in msg.get("tool_calls") or []:
        f = tc.get("function") or {}
        args, err = parse_json_args(f.get("arguments"))
        call = {"id": tc.get("id"), "name": f.get("name"), "input": args}
        if err:
            call["input_error"] = err
            call["raw_arguments"] = f.get("arguments")
        tool_calls.append(call)
    fr = ch.get("finish_reason")
    sr = STOP_MAP.get(fr, fr)
    refusal = None
    if msg.get("refusal"):
        refusal = {"category": "model_refusal", "explanation": msg["refusal"]}
        sr = "refusal"
    elif fr == "content_filter":
        refusal = {"category": "content_filter", "explanation": None}
    discarded = None
    if refusal:
        discarded = text or None
        text, tool_calls = "", []
    u = raw.get("usage") or {}
    pt = u.get("prompt_tokens") or 0
    cached = (u.get("prompt_tokens_details") or {}).get("cached_tokens") or 0
    usage = {"input_tokens": max(pt - cached, 0),
             "output_tokens": u.get("completion_tokens") or 0,
             "cache_read_tokens": cached, "cache_write_tokens": 0, "cache_write_1h_tokens": 0}
    rt = (u.get("completion_tokens_details") or {}).get("reasoning_tokens")
    if rt is not None:
        usage["reasoning_tokens"] = rt
    am = {"role": "assistant", "content": msg.get("content")}
    if msg.get("tool_calls"):
        am["tool_calls"] = [{"id": tc.get("id"), "type": "function",
                             "function": {"name": (tc.get("function") or {}).get("name"),
                                          "arguments": (tc.get("function") or {}).get("arguments")}}
                            for tc in msg["tool_calls"]]
    return {"text": text, "tool_calls": tool_calls, "stop_reason": sr, "stop_reason_raw": fr,
            "refusal": refusal, "discarded_text": discarded, "usage": usage,
            "model_returned": raw.get("model"), "response_id": raw.get("id"),
            "assistant_message": am}


def refusal_from_error(exc):
    """DashScope は内容の検査に掛かると HTTP 400 の data_inspection_failed を返す。拒否として記録する。"""
    status = getattr(exc, "status_code", None)
    s = str(exc)
    body = getattr(exc, "body", None)
    code = body.get("code") if isinstance(body, dict) else None
    if status == 400 and ("data_inspection_failed" in s or code == "data_inspection_failed"):
        return {"category": "data_inspection_failed", "explanation": s[:500]}
    return None
