"""Claude（公式の anthropic SDK）。

守ること（claude-api スキル、Claude Opus 5.5）:
- モデル ID は claude-opus-5-5 をそのまま（日付を付けない）
- 思考は adaptive のみ（disabled・budget_tokens は 400）。深さは output_config.effort。既定は medium なので常に明示して送る
- temperature / top_p / top_k は送らない（400）。assistant の書き出し（prefill）も 400
- tool_choice は auto（既定）。強制（any / tool）は 400。道具は strict: true
- stop_reason == "refusal" を content より先に見る（HTTP 200 で返る）
- 長い出力に備えて常に streaming（get_final_message）
- 安定した前半（system・部品表・画像）はプロンプトキャッシュに載せる
- server-side fallbacks は使わない（ベンチマークで別モデルに切り替わると比較が壊れる。docs/pending/llm.md）
"""
from __future__ import annotations

from . import as_blocks, blob_for_path, collect_blobs, first_user_index, replace_refs, tool_spec

STOP_MAP = {"end_turn": "end_turn", "max_tokens": "max_tokens", "tool_use": "tool_use",
            "refusal": "refusal", "stop_sequence": "stop_sequence", "pause_turn": "pause_turn"}


def _img(b) -> dict:
    return {"type": "image", "source": {"type": "base64", "media_type": b.media_type, "data": b.ref}}


def build_body(cfg, *, system, messages, images, tools, max_tokens, effort, params, prompt_cache):
    top, blobs = collect_blobs(messages, images)
    if messages and messages[-1].get("role") == "assistant":
        raise ValueError("Claude Opus 5.5 は assistant の書き出し（prefill）を受け付けない（400）。"
                         "形式は system の指示か strict な道具で決める")
    cc = {"type": "ephemeral"}
    if params.get("cache_ttl") == "1h":
        cc["ttl"] = "1h"
    native = []
    fu = first_user_index(messages)
    for i, m in enumerate(messages):
        role = m.get("role")
        if role in ("assistant", "system"):
            # assistant は Result.assistant_message をそのまま（思考のブロックを変えずに返す）。
            # system は会話の途中の指示（Opus 5.5 は対応、ヘッダー不要）
            native.append({"role": role, "content": m["content"]})
            continue
        blocks = [_img(b) for b in top] if i == fu else []
        for blk in as_blocks(m.get("content")):
            t = blk.get("type")
            if t == "image" and "path" in blk:
                blocks.append(_img(blob_for_path(blobs, blk["path"])))
            elif t == "tool_result":
                r = {"type": "tool_result", "tool_use_id": blk["tool_call_id"], "content": blk["content"]}
                if blk.get("is_error"):
                    r["is_error"] = True
                blocks.append(r)
            else:
                blocks.append(blk)
        native.append({"role": "user", "content": blocks})

    body: dict = {"model": cfg["model_id"], "max_tokens": int(max_tokens)}
    if system:
        sblk = {"type": "text", "text": system}
        if prompt_cache:
            sblk["cache_control"] = dict(cc)
        body["system"] = [sblk]
    body["messages"] = native
    thinking = {"type": "adaptive"}
    if params.get("thinking_display"):
        thinking["display"] = params["thinking_display"]
    body["thinking"] = thinking
    if effort is not None:
        body["output_config"] = {"effort": effort}
    if tools:
        out = []
        for t in tools:
            s = tool_spec(t)
            d = {"name": s["name"], "description": s["description"], "input_schema": s["input_schema"]}
            if cfg.get("strict_tools"):
                d["strict"] = True
            out.append(d)
        body["tools"] = out
    if prompt_cache:
        body["cache_control"] = dict(cc)   # 自動のキャッシュ：最後のブロックまでを載せる（道具のループでは毎回前へ進む）
    for k in ("stop_sequences", "metadata"):
        if k in params:
            body[k] = params[k]
    return body, blobs


def materialize(body, blobs):
    return replace_refs(body, lambda sha: blobs[sha].b64())


def make_client(cfg):
    import anthropic
    # 認証は SDK の順序に任せる：ANTHROPIC_API_KEY → ANTHROPIC_AUTH_TOKEN → ant auth login のプロファイル
    return anthropic.Anthropic(timeout=900.0, max_retries=2)


def send(client, body, cfg):
    with client.messages.stream(**body) as stream:
        msg = stream.get_final_message()
    return msg.to_dict(), getattr(msg, "_request_id", None)


def parse(raw: dict, cfg) -> dict:
    content = raw.get("content") or []
    text = "".join(b.get("text", "") for b in content if b.get("type") == "text")
    tool_calls = [{"id": b["id"], "name": b["name"], "input": b.get("input")}
                  for b in content if b.get("type") == "tool_use"]
    sr_raw = raw.get("stop_reason")
    refusal = None
    discarded = None
    if sr_raw == "refusal":
        sd = raw.get("stop_details") or {}
        refusal = {"category": sd.get("category"), "explanation": sd.get("explanation")}
        discarded = text or None      # 途中で止まった出力は完成した答えとして扱わない
        text, tool_calls = "", []
    u = raw.get("usage") or {}
    cc = u.get("cache_creation") or {}
    w1h = cc.get("ephemeral_1h_input_tokens") or 0
    w5m = cc.get("ephemeral_5m_input_tokens")
    if w5m is None:
        w5m = max((u.get("cache_creation_input_tokens") or 0) - w1h, 0)
    usage = {"input_tokens": u.get("input_tokens") or 0,
             "output_tokens": u.get("output_tokens") or 0,
             "cache_read_tokens": u.get("cache_read_input_tokens") or 0,
             "cache_write_tokens": w5m,
             "cache_write_1h_tokens": w1h}
    return {"text": text, "tool_calls": tool_calls,
            "stop_reason": STOP_MAP.get(sr_raw, sr_raw), "stop_reason_raw": sr_raw,
            "refusal": refusal, "discarded_text": discarded, "usage": usage,
            "model_returned": raw.get("model"), "response_id": raw.get("id"),
            "assistant_message": {"role": "assistant", "content": content}}


def refusal_from_error(exc):
    return None
