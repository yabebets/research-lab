"""rlkit.llm：記録・費用・予算・キャッシュ・画像・拒否・道具のループ。API は呼ばない。"""
from __future__ import annotations

import base64
import datetime
import json

import pytest

from conftest import FakeAnthropic, FakeOpenAI, anth_resp, make_png, oa_resp, set_cap
from rlkit import llm
from rlkit.llm_providers import IMAGE_REF, openai_compat

REG = llm.load_registry()


def lines(path):
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]


def log_of(project):
    files = list((project / "notes" / "llm-logs").glob("*.jsonl"))
    assert len(files) == 1
    return files[0]


# ───────── 登録簿と引数

def test_registry_has_three_planners():
    for k in ("claude-opus-5-5", "gpt-5", "qwen3-vl-plus"):
        cfg = REG["models"][k]
        assert cfg["images"] is True
        assert cfg["price_source"]["url"] and cfg["price_source"]["checked"]
    assert REG["models"]["claude-opus-5-5"]["model_id"] == "claude-opus-5-5"
    assert llm.resolve_model("anthropic", REG)[0] == "claude-opus-5-5"


@pytest.mark.parametrize("model,param", [("claude-opus-5-5", "temperature"), ("claude-opus-5-5", "top_p"),
                                         ("claude-opus-5-5", "tool_choice"), ("gpt-5", "temperature"),
                                         ("gpt-5", "max_tokens")])
def test_forbidden_params_stop_before_sending(project, model, param):
    fake = FakeAnthropic([]) if model.startswith("claude") else FakeOpenAI([])
    with pytest.raises(ValueError, match=param):
        llm.call(model, "hi", max_tokens=100, params={param: 0.7}, budget_project=project, client=fake)
    assert fake.bodies == []


def test_opus_request_shape(project):
    fake = FakeAnthropic([anth_resp()])
    llm.call("claude-opus-5-5", "plan this", system="You are a planner.", max_tokens=16000, effort="high",
             budget_project=project, client=fake)
    b = fake.bodies[0]
    assert b["model"] == "claude-opus-5-5"
    assert b["thinking"] == {"type": "adaptive"}
    assert b["output_config"] == {"effort": "high"}
    assert b["cache_control"] == {"type": "ephemeral"}
    assert b["system"][0]["cache_control"] == {"type": "ephemeral"}
    for k in ("temperature", "top_p", "top_k", "tool_choice", "fallbacks", "betas"):
        assert k not in b


def test_effort_default_is_sent_explicitly(project):
    fake = FakeAnthropic([anth_resp()])
    llm.call("claude-opus-5-5", "x", max_tokens=100, budget_project=project, client=fake)
    assert fake.bodies[0]["output_config"] == {"effort": "medium"}


def test_prefill_rejected(project):
    with pytest.raises(ValueError, match="prefill"):
        llm.call("claude-opus-5-5", [{"role": "user", "content": "a"}, {"role": "assistant", "content": "{"}],
                 max_tokens=10, budget_project=project, client=FakeAnthropic([]))


def test_gpt5_request_shape(project):
    fake = FakeOpenAI([oa_resp()])
    llm.call("gpt-5", "x", system="sys", max_tokens=5000, effort="high", budget_project=project, client=fake)
    b = fake.bodies[0]
    assert b["max_completion_tokens"] == 5000 and "max_tokens" not in b
    assert b["reasoning_effort"] == "high"
    assert b["messages"][0] == {"role": "developer", "content": "sys"}
    assert "temperature" not in b


# ───────── 画像

def test_image_encoding_per_provider(project, tmp_path):
    png = make_png(tmp_path / "r.png", 64, 32)
    raw = png.read_bytes()
    b64 = base64.standard_b64encode(raw).decode()

    fa = FakeAnthropic([anth_resp()])
    r = llm.call("claude-opus-5-5", "describe", images=[png], max_tokens=100, budget_project=project, client=fa)
    blk = fa.bodies[0]["messages"][0]["content"][0]
    assert blk == {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64}}
    assert fa.bodies[0]["messages"][0]["content"][1] == {"type": "text", "text": "describe"}   # 画像が先

    fo = FakeOpenAI([oa_resp()])
    llm.call("gpt-5", "describe", images=[png], max_tokens=100, budget_project=project, client=fo)
    part = fo.bodies[0]["messages"][0]["content"][0]
    assert part["image_url"]["url"] == f"data:image/png;base64,{b64}"
    assert part["image_url"]["detail"] == "high"

    # 記録の本文には base64 を入れず、画像は 1 回だけ保存
    req = json.loads((project / "notes" / "llm-logs" / "llm_requests" / f"{r.request_sha256}.json").read_text())
    s = json.dumps(req)
    assert b64 not in s and IMAGE_REF in s
    imgs = list((project / "notes" / "llm-logs" / "llm_requests" / "images").iterdir())
    assert len(imgs) == 1 and imgs[0].read_bytes() == raw


def test_image_tokens_estimate():
    opus = REG["models"]["claude-opus-5-5"]["image_tokens"]
    assert llm.image_tokens((1000, 1000), opus) == 1296           # 公式の表の値
    assert llm.image_tokens((3840, 2160), opus) == 4784           # 上限で頭打ち
    assert llm.image_tokens(None, opus) == 4784


# ───────── 記録

def test_log_line_fields_and_no_secrets(project, monkeypatch):
    secret = "sk-ant-api03-SECRETSECRETSECRET-xyz"
    monkeypatch.setenv("ANTHROPIC_API_KEY", secret)
    fake = FakeAnthropic([anth_resp("answer", usage={"input_tokens": 100, "output_tokens": 50,
                                                     "cache_read_input_tokens": 2000,
                                                     "cache_creation_input_tokens": 300})])
    r = llm.call("claude-opus-5-5", "q", max_tokens=1000, sample_index=3, budget_project=project,
                 client=fake, meta={"robot": "openarm", "condition": "P-D"})
    e = lines(log_of(project))[0]
    for k in ("ts", "provider", "model", "model_id", "model_returned", "params", "request_sha256", "request_path",
              "text", "usage", "cost_usd", "latency_s", "stop_reason", "refusal", "cache_hit", "sample_index",
              "error", "meta"):
        assert k in e, k
    assert e["model"] == "claude-opus-5-5" and e["sample_index"] == 3 and e["text"] == "answer"
    assert e["params"]["output_config"] == {"effort": "medium"} and "messages" not in e["params"]
    assert e["usage"] == {"input_tokens": 100, "output_tokens": 50, "cache_read_tokens": 2000,
                          "cache_write_tokens": 300, "cache_write_1h_tokens": 0}
    assert e["cost_usd"] == pytest.approx(r.cost_usd)
    assert (project / e["request_path"]).exists() and (project / e["response_path"]).exists()
    every = "".join(p.read_text() for p in project.rglob("*") if p.is_file() and p.suffix in (".json", ".jsonl"))
    assert secret not in every


def test_scrub():
    assert "sk-ant-abcdefgh12345" not in llm.scrub("key=sk-ant-abcdefgh12345 rest")


def test_run_dir_logging(project, monkeypatch):
    rd = project / "runs" / "run_20261110_0900_ab12"
    rd.mkdir()
    monkeypatch.setenv("RL_RUN_DIR", str(rd))
    llm.call("claude-opus-5-5", "q", max_tokens=100, client=FakeAnthropic([anth_resp()]))   # プロジェクトは run から
    e = lines(rd / "llm_calls.jsonl")[0]
    assert e["run_id"] == rd.name and e["cost_usd"] > 0 and e["model"] == "claude-opus-5-5"
    assert (rd / "llm_requests" / f"{e['request_sha256']}.json").exists()


def test_model_mismatch_flagged(project):
    llm.call("claude-opus-5-5", "q", max_tokens=100, budget_project=project,
             client=FakeAnthropic([anth_resp(model="claude-opus-4-8")]))
    assert lines(log_of(project))[0]["model_mismatch"] is True


# ───────── 費用

def test_cost_anthropic_with_cache():
    cfg = REG["models"]["claude-opus-5-5"]
    u = {"input_tokens": 1_000_000, "output_tokens": 1_000_000, "cache_read_tokens": 1_000_000,
         "cache_write_tokens": 1_000_000, "cache_write_1h_tokens": 1_000_000}
    assert llm.cost_usd(cfg, u) == pytest.approx(4 + 20 + 0.20 + 5 + 8)


def test_cost_openai_cached_split():
    cfg = REG["models"]["gpt-5"]
    parsed = openai_compat.parse(oa_resp(usage={"prompt_tokens": 30000, "completion_tokens": 2000,
                                                "prompt_tokens_details": {"cached_tokens": 20000},
                                                "completion_tokens_details": {"reasoning_tokens": 1500}}), cfg)
    assert parsed["usage"]["input_tokens"] == 10000 and parsed["usage"]["reasoning_tokens"] == 1500
    assert llm.cost_usd(cfg, parsed["usage"]) == pytest.approx((10000 * 1.25 + 20000 * 0.125 + 2000 * 10) / 1e6)


def test_cost_qwen_tiers():
    cfg = REG["models"]["qwen3-vl-plus"]
    low = llm.cost_usd(cfg, {"input_tokens": 32000, "output_tokens": 1000})
    high = llm.cost_usd(cfg, {"input_tokens": 32001, "output_tokens": 1000})
    assert low == pytest.approx((32000 * 0.2 + 1000 * 1.6) / 1e6)
    assert high == pytest.approx((32001 * 0.3 + 1000 * 2.4) / 1e6)      # 段を超えると全トークンが上の単価
    cached = llm.cost_usd(cfg, {"input_tokens": 10000, "cache_read_tokens": 10000, "output_tokens": 0})
    assert cached == pytest.approx((10000 * 0.2 + 10000 * 0.2 * 0.2) / 1e6)


def test_self_hosted_is_free_and_price_missing_refused(project):
    assert llm.cost_usd(REG["models"]["qwen3-vl-235b-a22b-instruct-vllm"], {"input_tokens": 10**6}) == 0
    reg = json.loads(json.dumps(REG))
    reg["models"]["gpt-5"]["prices"] = {"input": None, "output": None}
    with pytest.raises(llm.LLMError, match="価格"):
        llm.call("gpt-5", "x", max_tokens=10, budget_project=project, client=FakeOpenAI([]), registry=reg)


# ───────── 予算

def _seed_spend(project, usd):
    d = project / "notes" / "llm-logs"
    d.mkdir(parents=True, exist_ok=True)
    (d / "2026-11-01.jsonl").write_text(json.dumps({"ts": "2026-11-01T10:00:00+09:00", "model": "gpt-5",
                                                     "cost_usd": usd, "usage": {}}) + "\n")


def test_budget_refuses_before_sending(project):
    set_cap(project, cap=1.0)
    _seed_spend(project, 0.99)
    fake = FakeAnthropic([anth_resp()])
    with pytest.raises(llm.BudgetExceeded):
        llm.call("claude-opus-5-5", "x", max_tokens=16000, budget_project=project, client=fake)
    assert fake.bodies == []
    refused = lines(project / "notes" / "llm-logs" / f"{datetime.date.today()}.jsonl")
    assert refused[-1]["error"]["type"] == "budget_refused" and refused[-1]["cost_usd"] == 0


def test_budget_warns_at_80_percent(project, capsys):
    set_cap(project, cap=1.0)
    _seed_spend(project, 0.85)
    llm.call("claude-opus-5-5", "x", max_tokens=100, budget_project=project, client=FakeAnthropic([anth_resp()]))
    assert "80%" in capsys.readouterr().err


def test_budget_halt_ratio(project):
    set_cap(project, cap=1.0, halt=0.8)
    _seed_spend(project, 0.79)
    with pytest.raises(llm.BudgetExceeded):
        llm.call("claude-opus-5-5", "x", max_tokens=1000, budget_project=project, client=FakeAnthropic([anth_resp()]))


def test_budget_not_set_and_night_fallback(project, monkeypatch):
    set_cap(project, cap=None, per_night=10)
    with pytest.raises(llm.BudgetNotSet):
        llm.call("claude-opus-5-5", "x", max_tokens=100, budget_project=project, client=FakeAnthropic([anth_resp()]))
    monkeypatch.setenv("RL_NIGHT", "1")
    monkeypatch.setenv("RL_NIGHT_STARTED_AT", "2026-11-05T00:00:00+09:00")
    _seed_spend(project, 50.0)                    # 夜の起点より前なので数えない
    llm.call("claude-opus-5-5", "x", max_tokens=100, budget_project=project, client=FakeAnthropic([anth_resp()]))
    st = llm.budget_status(project)
    assert st["cap"] == 10 and st["spent"] < 1 and "夜間" in st["source"]


def test_budget_sums_runs_and_notes(project):
    _seed_spend(project, 1.5)
    rd = project / "runs" / "run_x"
    rd.mkdir()
    (rd / "llm_calls.jsonl").write_text(json.dumps({"ts": "2026-11-02T00:00:00+09:00", "cost_usd": 2.25}) + "\n"
                                        + '{"ts": "2026-11-02T00:00:01+09:00", "cost_us')   # 書きかけの行は数えない
    st = llm.budget_status(project)
    assert st["spent"] == pytest.approx(3.75) and st["remaining"] == pytest.approx(600 - 3.75)
    s = llm.usage_summary(project)
    assert s["by_run"]["run_x"]["cost_usd"] == pytest.approx(2.25)
    assert s["total"]["calls"] == 2


# ───────── 応答のキャッシュ

def test_cache_keys_distinct_per_sample_and_hit(project):
    fake = FakeAnthropic([anth_resp("s0"), anth_resp("s1")])
    r0 = llm.call("claude-opus-5-5", "same", max_tokens=100, sample_index=0, budget_project=project, client=fake)
    r1 = llm.call("claude-opus-5-5", "same", max_tokens=100, sample_index=1, budget_project=project, client=fake)
    assert len(fake.bodies) == 2 and r0.text == "s0" and r1.text == "s1"
    assert r0.request_sha256 == r1.request_sha256            # 要求は同じ、標本の番号で分ける
    again = llm.call("claude-opus-5-5", "same", max_tokens=100, sample_index=1, budget_project=project, client=fake)
    assert len(fake.bodies) == 2                              # API は呼んでいない
    assert again.cache_hit and again.text == "s1" and again.cost_usd == 0 and again.original_cost_usd == r1.cost_usd
    e = lines(log_of(project))[-1]
    assert e["cache_hit"] is True and e["cost_usd"] == 0
    k = llm.cache_key
    base = ("anthropic", "claude-opus-5-5", {"max_tokens": 1}, "abc")
    assert len({k(*base, 0), k(*base, 1), k("openai", "claude-opus-5-5", {"max_tokens": 1}, "abc", 0),
                k("anthropic", "claude-opus-5-5", {"max_tokens": 2}, "abc", 0)}) == 4


def test_cache_off(project):
    fake = FakeAnthropic([anth_resp("a"), anth_resp("b")])
    llm.call("claude-opus-5-5", "z", max_tokens=100, budget_project=project, client=fake, cache=False)
    llm.call("claude-opus-5-5", "z", max_tokens=100, budget_project=project, client=fake, cache=False)
    assert len(fake.bodies) == 2


# ───────── 拒否

def test_anthropic_refusal_recorded_not_fallen_back(project):
    fake = FakeAnthropic([anth_resp("partial", stop="refusal",
                                    stop_details={"type": "refusal", "category": "bio", "explanation": "x"})])
    r = llm.call("claude-opus-5-5", "x", max_tokens=100, budget_project=project, client=fake)
    assert r.refused and r.refusal["category"] == "bio" and r.text == "" and r.discarded_text == "partial"
    assert "fallbacks" not in fake.bodies[0] and len(fake.bodies) == 1
    assert lines(log_of(project))[0]["refusal"]["category"] == "bio"


def test_openai_refusal_and_content_filter(project):
    cfg = REG["models"]["gpt-5"]
    p = openai_compat.parse(oa_resp(None, refusal="I can't help with that."), cfg)
    assert p["stop_reason"] == "refusal" and p["refusal"]["category"] == "model_refusal"
    p = openai_compat.parse(oa_resp("half", finish="content_filter"), cfg)
    assert p["refusal"]["category"] == "content_filter" and p["text"] == ""


def test_dashscope_inspection_error_is_refusal(project, monkeypatch):
    class Err(Exception):
        status_code = 400
        body = {"code": "data_inspection_failed"}
    monkeypatch.setenv("DASHSCOPE_API_KEY", "dummy-not-used")
    r = llm.call("qwen3-vl-plus", "x", max_tokens=100, budget_project=project, client=FakeOpenAI(raises=Err("bad")))
    assert r.refused and r.refusal["category"] == "data_inspection_failed"


def test_api_error_logged_and_raised(project):
    class Boom(Exception):
        status_code = 500
    with pytest.raises(llm.LLMCallError):
        llm.call("gpt-5", "x", max_tokens=10, budget_project=project, client=FakeOpenAI(raises=Boom("server")))
    e = lines(log_of(project))[0]
    assert e["error"]["type"] == "Boom" and e["cost_usd"] == 0


def test_qwen_stream_accumulates(project):
    chunks = [{"id": "c1", "model": "qwen3-vl-plus", "choices": [{"delta": {"reasoning_content": "hmm"}}]},
              {"choices": [{"delta": {"content": "Hel"}}]},
              {"choices": [{"delta": {"content": "lo", "tool_calls": [
                  {"index": 0, "id": "call_1", "function": {"name": "check", "arguments": "{\"a\":"}}]}}]},
              {"choices": [{"delta": {"tool_calls": [{"index": 0, "function": {"arguments": " 1}"}}]},
                            "finish_reason": "tool_calls"}]},
              {"choices": [], "usage": {"prompt_tokens": 40000, "completion_tokens": 10,
                                        "prompt_tokens_details": {"cached_tokens": 0}}}]
    fake = FakeOpenAI([chunks])
    r = llm.call("qwen3-vl-plus", "x", max_tokens=100, budget_project=project, client=fake)
    assert fake.bodies[0]["stream"] is True and fake.bodies[0]["extra_body"] == {"enable_thinking": True}
    assert r.text == "Hello" and r.tool_calls == [{"id": "call_1", "name": "check", "input": {"a": 1}}]
    assert r.cost_usd == pytest.approx((40000 * 0.3 + 10 * 2.4) / 1e6)


# ───────── 道具のループ（P-E）

SCHEMA = {"type": "object", "properties": {"order": {"type": "array", "items": {"type": "string"}}},
          "required": ["order"], "additionalProperties": False}


def test_tool_loop_anthropic(project):
    calls = []

    def check_sequence(order):
        calls.append(order)
        return {"feasible": order == ["base", "arm"], "first_failure": None}

    fake = FakeAnthropic([
        anth_resp("", stop="tool_use", tool_uses=[{"id": "tu_1", "name": "check_sequence", "input": {"order": ["arm", "base"]}}]),
        anth_resp("", stop="tool_use", tool_uses=[{"id": "tu_2", "name": "check_sequence", "input": {"bad": 1}}]),
        anth_resp("", stop="tool_use", tool_uses=[{"id": "tu_3", "name": "check_sequence", "input": {"order": ["base", "arm"]}}]),
        anth_resp("final: base, arm"),
    ])
    tool = llm.Tool("check_sequence", "L1 の判定", SCHEMA, fn=check_sequence)
    lr = llm.tool_loop("claude-opus-5-5", "plan", [tool], max_turns=10, max_tokens=1000,
                       budget_project=project, client=fake, meta={"condition": "P-E"})
    assert lr.stopped == "end_turn" and lr.text == "final: base, arm" and len(lr.turns) == 4
    assert calls == [["arm", "base"], ["base", "arm"]]            # 形に合わない入力は判定器に渡さない
    assert lr.tool_runs[1]["is_error"] and "余計なキー" in lr.tool_runs[1]["output"]
    b2 = fake.bodies[1]
    assert b2["tools"][0]["strict"] is True and "tool_choice" not in b2
    assert b2["messages"][1]["content"][0] == {"type": "thinking", "thinking": "", "signature": "sig-abc"}  # 思考を変えずに返す
    tr = b2["messages"][2]["content"][0]
    assert tr["type"] == "tool_result" and tr["tool_use_id"] == "tu_1" and json.loads(tr["content"])["feasible"] is False
    assert fake.bodies[2]["messages"][4]["content"][0]["is_error"] is True
    ev = lines(log_of(project))
    assert [e["meta"]["turn"] for e in ev] == [0, 1, 2, 3] and len({e["meta"]["loop_id"] for e in ev}) == 1
    assert lr.cost_usd == pytest.approx(sum(e["cost_usd"] for e in ev))


def test_tool_loop_stops_on_refusal_and_max_turns(project):
    tool = llm.Tool("check_sequence", "d", SCHEMA, fn=lambda order: "ok")
    fake = FakeAnthropic([anth_resp("", stop="refusal", stop_details={"category": "cyber"})])
    lr = llm.tool_loop("claude-opus-5-5", "p", [tool], max_tokens=100, budget_project=project, client=fake)
    assert lr.stopped == "refusal"
    tu = {"id": "t", "name": "check_sequence", "input": {"order": []}}
    fake = FakeAnthropic([anth_resp("", stop="tool_use", tool_uses=[tu]) for _ in range(3)])
    lr = llm.tool_loop("claude-opus-5-5", "p2", [tool], max_turns=3, max_tokens=100, budget_project=project, client=fake)
    assert lr.stopped == "max_turns" and len(lr.turns) == 3


def test_tool_loop_openai_messages(project):
    tool = llm.Tool("check_sequence", "d", SCHEMA, fn=lambda order: {"ok": True})
    tc = [{"id": "call_9", "type": "function", "function": {"name": "check_sequence", "arguments": "{\"order\":[\"a\"]}"}}]
    fake = FakeOpenAI([oa_resp(None, finish="tool_calls", tool_calls=tc), oa_resp("done")])
    lr = llm.tool_loop("gpt-5", "p", [tool], max_tokens=100, budget_project=project, client=fake)
    msgs = fake.bodies[1]["messages"]
    assert msgs[1]["tool_calls"][0]["id"] == "call_9"
    assert msgs[2] == {"role": "tool", "tool_call_id": "call_9", "content": "{\"ok\": true}"}
    assert lr.text == "done"


def test_strict_tool_schema_required(project):
    bad = llm.Tool("t", "d", {"type": "object", "properties": {}}, fn=lambda: "x")
    with pytest.raises(ValueError, match="additionalProperties"):
        llm.call("claude-opus-5-5", "x", tools=[bad], max_tokens=10, budget_project=project, client=FakeAnthropic([]))


def test_tool_loop_replays_from_cache(project):
    tool = llm.Tool("check_sequence", "d", SCHEMA, fn=lambda order: "ok")
    tu = {"id": "t1", "name": "check_sequence", "input": {"order": ["a"]}}
    fake = FakeAnthropic([anth_resp("", stop="tool_use", tool_uses=[tu]), anth_resp("end")])
    a = llm.tool_loop("claude-opus-5-5", "p", [tool], max_tokens=100, budget_project=project, client=fake)
    b = llm.tool_loop("claude-opus-5-5", "p", [tool], max_tokens=100, budget_project=project, client=fake)
    assert len(fake.bodies) == 2 and b.text == a.text and b.cost_usd == 0


# ───────── dry-run

def test_prepare_dry_run_has_refs_not_base64(tmp_path):
    png = make_png(tmp_path / "x.png", 100, 50)
    pr = llm.prepare("claude-opus-5-5", "hello", images=[png], max_tokens=1000)
    s = json.dumps(pr["body"])
    assert IMAGE_REF in s and base64.standard_b64encode(png.read_bytes()).decode() not in s
    assert pr["est_max_cost_usd"] > 0 and pr["images"][0]["size"] == (100, 50)
