"""言語モデルの呼び出しを 1 か所にまとめる（記録・費用・予算・応答のキャッシュ）。

    import sys, pathlib
    sys.path.insert(0, str(pathlib.Path("~/research-lab/lib").expanduser()))
    from rlkit import llm

    r = llm.call("claude-opus-5-5", "この部品表から組立の順序を出して…",
                 system=SYSTEM, images=["renders/so101_iso.png"], max_tokens=16000,
                 effort="high", sample_index=2, budget_project="robot-assembly-bench",
                 meta={"robot": "openarm", "condition": "P-D", "input": "image+bom"})
    if r.refused: ...          # 拒否は結果の一種として記録される（別モデルに切り替えない）
    print(r.text, r.cost_usd)

    # P-E：判定器（Python の関数）を道具として渡す
    checker = llm.Tool("check_sequence", "部品の順序が L1 で成り立つかを返す", SCHEMA, fn=check_sequence)
    lr = llm.tool_loop("gpt-5", prompt, [checker], max_turns=20, max_tokens=16000, ...)

- 1 回の呼び出しごとに 1 行の JSON を残す：$RL_RUN_DIR/llm_calls.jsonl、実行の外なら <project>/notes/llm-logs/<日付>.jsonl。
  要求の本文は <記録の場所>/llm_requests/<sha256>.json（画像は sha256 で参照し、images/ に 1 回だけ保存）
- 予算：research.yaml の budget.llm_usd_cap。プロジェクトの全記録の cost_usd を足し、次の 1 回の最大の見積もりで上限を超えるなら送らない。80% で警告
- 応答のキャッシュ：<project>/.llm_cache/。鍵は（会社・モデル・送った引数・要求の sha256・sample_index）
- API の鍵は環境変数か ant のプロファイルから SDK が読む。記録には鍵も認証のヘッダーも残さない
"""
from __future__ import annotations

import dataclasses
import datetime as dt
import fcntl
import hashlib
import json
import math
import os
import re
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Callable

from .common import RL, load, now
from .llm_providers import anthropic_api, openai_compat

MODELS_YAML = RL / "llm" / "models.yaml"
PROVIDERS = {"anthropic": anthropic_api, "openai": openai_compat, "qwen": openai_compat}
WARN_RATIO = 0.8
SECRET_ENVS = ["ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "OPENAI_API_KEY", "DASHSCOPE_API_KEY", "VLLM_API_KEY"]
_KEY_RE = re.compile(r"(sk-ant-[A-Za-z0-9_\-]{8,}|sk-[A-Za-z0-9_\-]{20,})")
_BODY_CONTENT_KEYS = ("messages", "system", "tools")


# ───────────────────────── エラー

class LLMError(RuntimeError):
    pass


class BudgetNotSet(LLMError):
    pass


class BudgetExceeded(LLMError):
    pass


class LLMCallError(LLMError):
    def __init__(self, msg: str, result: "Result"):
        super().__init__(msg)
        self.result = result


# ───────────────────────── 結果

@dataclasses.dataclass
class Result:
    text: str
    tool_calls: list
    stop_reason: str | None
    refusal: dict | None
    usage: dict
    cost_usd: float
    model: str                      # 登録簿の名前（llm/models.yaml の鍵）
    model_id: str                   # 送ったモデル ID
    model_returned: str | None      # 応答が名乗ったモデル
    provider: str
    latency_s: float
    cache_hit: bool
    sample_index: int
    request_sha256: str
    call_id: str
    assistant_message: dict | None = None    # 次の回に会話へそのまま足す形（Claude の思考のブロックを変えずに保つ）
    stop_reason_raw: str | None = None
    discarded_text: str | None = None        # 拒否で途中まで出た文字（答えとして使わない）
    original_cost_usd: float | None = None   # キャッシュから返したとき、元の呼び出しの費用
    est_max_cost_usd: float = 0.0
    error: dict | None = None
    log_path: str | None = None
    meta: dict = dataclasses.field(default_factory=dict)

    @property
    def refused(self) -> bool:
        return self.refusal is not None or self.stop_reason == "refusal"


@dataclasses.dataclass
class Tool:
    """P-E の道具。fn は道具の引数をキーワード引数で受け、文字列か JSON にできる値を返す。"""
    name: str
    description: str
    input_schema: dict
    fn: Callable[..., Any]


@dataclasses.dataclass
class LoopResult:
    final: Result | None
    turns: list
    messages: list
    stopped: str                    # end_turn | refusal | max_tokens | max_turns
    tool_runs: list

    @property
    def cost_usd(self) -> float:
        return round(sum(t.cost_usd for t in self.turns), 8)

    @property
    def text(self) -> str:
        return self.final.text if self.final else ""


# ───────────────────────── 登録簿

def _plain(x):
    return json.loads(json.dumps(x, default=str))


_REG_CACHE: dict = {}


def load_registry(path: Path | None = None) -> dict:
    p = Path(path or MODELS_YAML)
    key = (str(p), p.stat().st_mtime)
    if key not in _REG_CACHE:
        _REG_CACHE[key] = _plain(load(p))
    return _REG_CACHE[key]


def resolve_model(name: str, reg: dict) -> tuple[str, dict]:
    models = reg.get("models") or {}
    if name in models:
        return name, models[name]
    d = (reg.get("defaults") or {}).get(name)
    if d:
        return d, models[d]
    for k, cfg in models.items():
        if cfg.get("model_id") == name:
            return k, cfg
    raise LLMError(f"モデルが登録簿にありません: {name}（llm/models.yaml。登録済み: {', '.join(models)}）")


def check_params(key: str, cfg: dict, params: dict, effort):
    spec = cfg.get("params") or {}
    forbidden = spec.get("forbidden") or {}
    allowed = set(spec.get("allowed") or [])
    for k in params:
        if k in forbidden:
            raise ValueError(f"{key}: {k} は送れません — {forbidden[k]}")
        if k not in allowed:
            raise ValueError(f"{key}: {k} は登録簿の params.allowed にありません（llm/models.yaml に足してから使う）")
    eff = cfg.get("effort")
    if not eff:
        if effort is not None:
            raise ValueError(f"{key}: effort は指定できません（登録簿の effort が null）")
        return None
    if effort is None:
        effort = eff.get("default")      # 既定に任せず、記録のため常に明示して送る
    if effort not in (eff.get("values") or []):
        raise ValueError(f"{key}: effort={effort!r} は使えません（{eff.get('values')}）")
    return effort


def check_tools(key: str, cfg: dict, tools: list):
    if not cfg.get("strict_tools"):
        return
    from .llm_providers import tool_spec
    for t in tools:
        s = tool_spec(t)["input_schema"] or {}
        if s.get("type") != "object" or s.get("additionalProperties") is not False or "required" not in s:
            raise ValueError(f"{key}: 道具 {tool_spec(t)['name']} は strict で送るので、input_schema に "
                             "type: object・additionalProperties: false・required が要ります")


# ───────────────────────── 費用

def _require_price(key: str, cfg: dict):
    p = cfg.get("prices") or {}
    if cfg.get("self_hosted"):
        return
    if not p.get("tiers") and (p.get("input") is None or p.get("output") is None):
        raise LLMError(f"{key}: 価格が登録簿に無いので呼べません（llm/models.yaml の prices と price_source を埋める）")


def _tier(prices: dict, total_in: int) -> dict:
    tiers = prices["tiers"]
    for t in tiers:
        if total_in <= t["max_input_tokens"]:
            return t
    return tiers[-1]


def cost_usd(cfg: dict, usage: dict) -> float:
    """正規化した usage（input_tokens はキャッシュに当たらなかった分）から USD を出す。"""
    if cfg.get("self_hosted"):
        return 0.0
    p = cfg.get("prices") or {}
    i = usage.get("input_tokens") or 0
    o = usage.get("output_tokens") or 0
    cr = usage.get("cache_read_tokens") or 0
    cw = usage.get("cache_write_tokens") or 0
    cw1 = usage.get("cache_write_1h_tokens") or 0
    if p.get("tiers"):
        t = _tier(p, i + cr + cw + cw1)
        ip, op = t["input"], t["output"]
        crp = ip * p.get("cache_read_ratio", 1.0)
        cwp = cw1p = ip
    else:
        ip, op = p["input"], p["output"]
        crp = p["cache_read"] if p.get("cache_read") is not None else ip * p.get("cache_read_ratio", 1.0)
        cwp = p.get("cache_write_5m", ip)
        cw1p = p.get("cache_write_1h", ip)
    return round((i * ip + o * op + cr * crp + cw * cwp + cw1 * cw1p) / 1e6, 8)


def image_tokens(size, spec: dict | None) -> int:
    """予算の見積もり用。課金は応答の usage の実数。"""
    if not spec:
        return 5000
    if size is None:
        return int(spec.get("max_tokens") or 5000)
    w, h = size
    if "tile_px" in spec:                                   # OpenAI の高精細のタイル
        s = min(1.0, spec["fit_px"] / max(w, h))
        w, h = w * s, h * s
        s = min(1.0, spec["short_side_px"] / min(w, h))
        w, h = w * s, h * s
        tiles = math.ceil(w / spec["tile_px"]) * math.ceil(h / spec["tile_px"])
        return int(spec["base_tokens"] + spec["tokens_per_tile"] * tiles)
    le = spec.get("max_long_edge_px")
    if le and max(w, h) > le:
        s = le / max(w, h)
        w, h = w * s, h * s
    t = math.ceil(w / spec["patch_px"]) * math.ceil(h / spec["patch_px"])
    return int(min(t, spec.get("max_tokens") or t))


def estimate_input_tokens(body: dict, blobs: dict, cfg: dict) -> int:
    from .llm_providers import IMAGE_REF
    text = _canon(body)
    n = math.ceil(len(text.encode("utf-8")) / 3)            # 英語なら 1 トークン 約 4 文字。3 バイトで割って多めに見る
    for sha, b in blobs.items():
        n += text.count(IMAGE_REF + sha) * image_tokens(b.size, cfg.get("image_tokens"))
    return n


def estimate_max_cost(cfg: dict, in_tokens: int, max_tokens: int, prompt_cache: bool, params: dict) -> float | None:
    if cfg.get("self_hosted"):
        return 0.0
    p = cfg.get("prices") or {}
    if p.get("tiers"):
        t = _tier(p, in_tokens)
        ip, op = t["input"], t["output"]
    else:
        ip, op = p.get("input"), p.get("output")
        if ip is None or op is None:
            return None                                             # 価格が未登録（call は送る前に止める）
        if prompt_cache and cfg.get("provider") == "anthropic":   # 書き込みは入力より高い
            w = p.get("cache_write_1h") if params.get("cache_ttl") == "1h" else p.get("cache_write_5m")
            ip = max(ip, w or ip)
    return round((in_tokens * ip + int(max_tokens) * op) / 1e6, 8)


# ───────────────────────── 場所

def _canon(obj) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)


def _sha(obj) -> str:
    return hashlib.sha256((obj if isinstance(obj, str) else _canon(obj)).encode("utf-8")).hexdigest()


def _find_up(p: Path) -> Path | None:
    p = p.resolve()
    for q in [p, *p.parents]:
        if (q / "research.yaml").exists():
            return q
    return None


def resolve_project_dir(ref=None, run_dir=None) -> Path:
    if ref:
        cand = Path(str(ref)).expanduser()
        if (cand / "research.yaml").exists():
            return cand.resolve()
        if (RL / "projects" / str(ref) / "research.yaml").exists():
            return RL / "projects" / str(ref)
        raise LLMError(f"プロジェクトが見つかりません: {ref}")
    env = os.environ.get("RL_PROJECT")
    if env and (Path(env) / "research.yaml").exists():
        return Path(env).resolve()
    for start in ([Path(run_dir)] if run_dir else []) + [Path.cwd()]:
        found = _find_up(start)
        if found:
            return found
    raise LLMError("プロジェクトが分かりません（budget_project か RL_PROJECT を指定するか、プロジェクトの中で実行する）")


def log_target(project: Path, run_dir: Path | None) -> tuple[Path, Path]:
    if run_dir:
        d = Path(run_dir)
        return d / "llm_calls.jsonl", d / "llm_requests"
    d = project / "notes" / "llm-logs"
    return d / f"{dt.date.today().isoformat()}.jsonl", d / "llm_requests"


def log_files(project: Path) -> list[Path]:
    return sorted(project.glob("runs/*/llm_calls.jsonl")) + sorted((project / "notes" / "llm-logs").glob("*.jsonl"))


# ───────────────────────── 鍵を残さない

def scrub(s: str) -> str:
    for v in SECRET_ENVS:
        val = os.environ.get(v)
        if val and len(val) >= 8:
            s = s.replace(val, "***")
    return _KEY_RE.sub("***", s)


def _write_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    tmp.write_text(scrub(json.dumps(obj, ensure_ascii=False, indent=1, default=str)))
    tmp.replace(path)


def _append_jsonl(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    line = scrub(json.dumps(obj, ensure_ascii=False, default=str)) + "\n"
    with path.open("a", encoding="utf-8") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            f.write(line)
            f.flush()
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


# ───────────────────────── 記録を読む（予算・集計）

class _LogReader:
    """記録のファイルを追記された分だけ読み直す（毎回すべてを読まない）。"""

    def __init__(self):
        self._files: dict[str, dict] = {}
        self._lock = threading.Lock()

    def rows(self, path: Path) -> list[dict]:
        key = str(Path(path).resolve())
        with self._lock:
            st = self._files.setdefault(key, {"offset": 0, "rows": []})
            try:
                size = Path(path).stat().st_size
            except FileNotFoundError:
                return []
            if size < st["offset"]:
                st["offset"], st["rows"] = 0, []
            if size > st["offset"]:
                with open(path, "rb") as f:
                    f.seek(st["offset"])
                    chunk = f.read()
                end = chunk.rfind(b"\n") + 1               # 書きかけの行は次に回す
                for line in chunk[:end].splitlines():
                    if line.strip():
                        try:
                            st["rows"].append(_summarize(json.loads(line), Path(path)))
                        except json.JSONDecodeError:
                            continue
                st["offset"] += end
            return list(st["rows"])


def _summarize(e: dict, path: Path) -> dict:
    u = e.get("usage") or {}
    run = e.get("run_id") or (path.parent.name if path.parent.name != "llm-logs" else f"notes:{path.stem}")
    return {"ts": e.get("ts"), "model": e.get("model"), "provider": e.get("provider"), "run": run,
            "day": (e.get("ts") or "")[:10], "cost": float(e.get("cost_usd") or 0.0),
            "cache_hit": bool(e.get("cache_hit")), "error": bool(e.get("error")),
            "refused": bool(e.get("refusal")),
            "input_tokens": u.get("input_tokens") or 0, "output_tokens": u.get("output_tokens") or 0,
            "cache_read_tokens": u.get("cache_read_tokens") or 0,
            "cache_write_tokens": (u.get("cache_write_tokens") or 0) + (u.get("cache_write_1h_tokens") or 0)}


_READER = _LogReader()


def _all_rows(project: Path, extra=()) -> list[dict]:
    seen, out = set(), []
    for f in [*log_files(project), *extra]:
        k = str(Path(f).resolve())
        if k in seen:
            continue
        seen.add(k)
        out.extend(_READER.rows(Path(f)))
    return out


def _parse_ts(s):
    try:
        t = dt.datetime.fromisoformat(s)
    except (TypeError, ValueError):
        return None
    return t if t.tzinfo else t.astimezone()


def budget_status(project, extra=()) -> dict:
    project = resolve_project_dir(project) if not isinstance(project, Path) else project
    led = load(project / "research.yaml") or {}
    b = led.get("budget") or {}
    cap, source, since = b.get("llm_usd_cap"), "budget.llm_usd_cap", None
    if cap is None and os.environ.get("RL_NIGHT"):
        cap, source = b.get("llm_usd_per_night"), "budget.llm_usd_per_night（夜間ループ）"
        since = os.environ.get("RL_NIGHT_STARTED_AT") or dt.datetime.combine(dt.date.today(), dt.time()).astimezone().isoformat()
    rows = _all_rows(project, extra)
    if since:
        s = _parse_ts(since)
        rows = [r for r in rows if (_parse_ts(r["ts"]) or s) >= s]
    spent = round(sum(r["cost"] for r in rows), 6)
    cap = float(cap) if cap is not None else None
    return {"project": project.name, "cap": cap, "spent": spent,
            "remaining": round(cap - spent, 6) if cap is not None else None,
            "source": source if cap is not None else None, "since": since,
            "halt_ratio": b.get("llm_halt_ratio"), "calls": len(rows)}


_WARNED: set = set()


def _check_budget(project: Path, est: float, extra) -> dict:
    st = budget_status(project, extra)
    if st["cap"] is None:
        raise BudgetNotSet("research.yaml の budget.llm_usd_cap が未設定です（G2 で人が決める上限）。"
                           "夜間ループの中だけは RL_NIGHT=1 で budget.llm_usd_per_night を使う")
    limit = st["cap"] * float(st["halt_ratio"] or 1.0)
    if st["spent"] + est > limit:
        raise BudgetExceeded(f"予算を超えるので送りません：使用 ${st['spent']:.2f} + この回の最大の見積もり ${est:.2f} > "
                             f"上限 ${limit:.2f}（{st['source']}" + (f" × {st['halt_ratio']}" if st["halt_ratio"] else "") + "）")
    if st["spent"] + est >= WARN_RATIO * st["cap"] and str(project) not in _WARNED:
        _WARNED.add(str(project))
        print(f"rl llm: 警告 — 言語モデルの予算の {int(WARN_RATIO * 100)}% に達しました"
              f"（使用 ${st['spent']:.2f} / 上限 ${st['cap']:.2f}）。plan.md の決まりに従い、止まって相談する", file=sys.stderr)
    return st


def usage_summary(project: Path) -> dict:
    rows = _all_rows(project)

    def agg(keyf):
        out: dict[str, dict] = {}
        for r in rows:
            a = out.setdefault(keyf(r) or "-", {"calls": 0, "api_calls": 0, "cache_hits": 0, "errors": 0, "refusals": 0,
                                                "input_tokens": 0, "output_tokens": 0, "cache_read_tokens": 0,
                                                "cache_write_tokens": 0, "cost_usd": 0.0})
            a["calls"] += 1
            a["cache_hits"] += r["cache_hit"]
            a["errors"] += r["error"]
            a["refusals"] += r["refused"]
            a["api_calls"] += not r["cache_hit"] and not r["error"]
            for k in ("input_tokens", "output_tokens", "cache_read_tokens", "cache_write_tokens"):
                a[k] += r[k]
            a["cost_usd"] = round(a["cost_usd"] + r["cost"], 6)
        return dict(sorted(out.items()))
    return {"total": agg(lambda r: "total").get("total", {}), "by_model": agg(lambda r: r["model"]),
            "by_run": agg(lambda r: r["run"]), "by_day": agg(lambda r: r["day"])}


# ───────────────────────── 応答のキャッシュ

def cache_key(provider: str, model_id: str, sent_params: dict, request_sha: str, sample_index: int) -> str:
    return _sha({"v": 1, "provider": provider, "model": model_id, "params": sent_params,
                 "request": request_sha, "sample_index": int(sample_index)})


def _cache_path(project: Path, key: str) -> Path:
    return project / ".llm_cache" / key[:2] / f"{key}.json"


def _cache_get(project: Path, key: str):
    p = _cache_path(project, key)
    if p.exists():
        try:
            return json.loads(p.read_text())
        except json.JSONDecodeError:
            return None
    return None


# ───────────────────────── クライアント

_CLIENTS: dict = {}
_CLIENTS_LOCK = threading.Lock()


def _client_for(key: str, cfg: dict, prov):
    with _CLIENTS_LOCK:
        if key not in _CLIENTS:
            _CLIENTS[key] = prov.make_client(cfg)
        return _CLIENTS[key]


def key_status(cfg: dict) -> str:
    """鍵があるかだけを返す（値は出さない）。"""
    envs = cfg.get("api_key_env") or []
    have = [v for v in envs if os.environ.get(v)]
    if have:
        return f"{have[0]}: あり"
    if cfg.get("provider") == "anthropic":
        prof = Path(os.environ.get("ANTHROPIC_CONFIG_DIR", "~/.config/anthropic")).expanduser() / "credentials"
        if prof.exists() and any(prof.iterdir()):
            return "ant のプロファイル: あり"
        return "なし（ANTHROPIC_API_KEY か `ant auth login`）"
    if cfg.get("api_key_optional"):
        return "不要（任意）"
    return f"{' / '.join(envs)}: なし"


# ───────────────────────── 呼び出し

def prepare(model: str, messages, *, system=None, images=None, tools=None, max_tokens: int,
            effort=None, params=None, prompt_cache=True, registry=None) -> dict:
    """送る要求を組み立てる（通信しない）。rl llm ping --dry-run もこれを使う。"""
    reg = registry or load_registry()
    key, cfg = resolve_model(model, reg)
    prov = PROVIDERS[cfg["provider"]]
    params = dict(params or {})
    effort = check_params(key, cfg, params, effort)
    msgs = [{"role": "user", "content": messages}] if isinstance(messages, str) else [dict(m) for m in messages]
    has_img = bool(images) or any(isinstance(m.get("content"), list) and any(
        isinstance(b, dict) and b.get("type") == "image" for b in m["content"]) for m in msgs)
    if has_img and not cfg.get("images"):
        raise ValueError(f"{key} は画像を読めません")
    tool_list = list(tools or [])
    check_tools(key, cfg, tool_list)
    body, blobs = prov.build_body(cfg, system=system, messages=msgs, images=images, tools=tool_list,
                                  max_tokens=max_tokens, effort=effort, params=params, prompt_cache=prompt_cache)
    request_sha = _sha({"provider": cfg["provider"], "model": cfg["model_id"], "body": body})
    sent = {k: v for k, v in body.items() if k not in _BODY_CONTENT_KEYS}
    if tool_list:
        sent["tools"] = [t["name"] if "name" in t else t["function"]["name"] for t in body["tools"]]
    est_in = estimate_input_tokens(body, blobs, cfg)
    return {"key": key, "cfg": cfg, "prov": prov, "body": body, "blobs": blobs, "request_sha256": request_sha,
            "sent_params": sent, "est_input_tokens": est_in,
            "est_max_cost_usd": estimate_max_cost(cfg, est_in, max_tokens, prompt_cache, params),
            "images": [{"sha256": b.sha256, "path": b.path, "size": b.size, "media_type": b.media_type}
                       for b in blobs.values()]}


def call(model: str, messages, *, system: str | None = None, images=None, tools=None, max_tokens: int,
         effort: str | None = None, params: dict | None = None, run_dir=None, sample_index: int = 0,
         cache: bool = True, prompt_cache: bool = True, budget_project=None, meta: dict | None = None,
         client=None, registry=None) -> Result:
    """1 回呼ぶ。model は登録簿の名前（claude-opus-5-5 / gpt-5 / qwen3-vl-plus …）か会社名（anthropic / openai / qwen）。

    messages は文字列か [{"role": "user"|"assistant"|"system", "content": 文字列かブロックの並び}]。
    ブロックは {"type": "text"}、{"type": "image", "path": ...}、{"type": "tool_result", "tool_call_id", "content", "is_error"}。
    assistant には前の Result.assistant_message をそのまま入れる。images（パスの並び）は最初の user の先頭に入る。
    sample_index は同じ要求を何度目に取ったか（キャッシュの鍵に入るので、標本どうしがぶつからない）。
    """
    pr = prepare(model, messages, system=system, images=images, tools=tools, max_tokens=max_tokens,
                 effort=effort, params=params, prompt_cache=prompt_cache, registry=registry)
    key, cfg, prov, body, blobs = pr["key"], pr["cfg"], pr["prov"], pr["body"], pr["blobs"]
    _require_price(key, cfg)
    rd = run_dir or os.environ.get("RL_RUN_DIR") or None
    rd = Path(rd) if rd else None
    project = resolve_project_dir(budget_project, rd)
    log_file, store = log_target(project, rd)
    ckey = cache_key(cfg["provider"], cfg["model_id"], pr["sent_params"], pr["request_sha256"], sample_index)
    call_id = f"{dt.datetime.now().strftime('%Y%m%dT%H%M%S')}-{uuid.uuid4().hex[:8]}"
    req_path = store / f"{pr['request_sha256']}.json"
    resp_path = store.parent / "llm_responses" / f"{call_id}.json"
    meta = dict(meta or {})

    def rel(p: Path) -> str:
        try:
            return str(p.relative_to(project))
        except ValueError:
            return str(p)

    def save_request():
        if not req_path.exists():
            _write_json(req_path, {"provider": cfg["provider"], "model": cfg["model_id"], "registry_key": key,
                                   "request_sha256": pr["request_sha256"], "body": body})
        for b in blobs.values():
            ip = store / "images" / f"{b.sha256}{b.ext}"
            if not ip.exists():
                ip.parent.mkdir(parents=True, exist_ok=True)
                ip.write_bytes(b.data)

    def entry(res: Result, extra: dict) -> dict:
        e = {"ts": now(), "call_id": call_id, "project": project.name,
             "run_id": rd.name if rd else None, "provider": cfg["provider"], "model": key,
             "model_id": cfg["model_id"], "model_returned": res.model_returned,
             "model_mismatch": bool(res.model_returned) and not str(res.model_returned).startswith(cfg["model_id"]),
             "params": pr["sent_params"], "images": pr["images"], "request_sha256": pr["request_sha256"],
             "request_path": rel(req_path), "sample_index": sample_index, "cache_key": ckey,
             "cache_hit": res.cache_hit, "text": res.text, "tool_calls": res.tool_calls,
             "stop_reason": res.stop_reason, "stop_reason_raw": res.stop_reason_raw, "refusal": res.refusal,
             "discarded_text": res.discarded_text, "usage": res.usage, "cost_usd": res.cost_usd,
             "original_cost_usd": res.original_cost_usd, "est_input_tokens": pr["est_input_tokens"],
             "est_max_cost_usd": pr["est_max_cost_usd"], "latency_s": res.latency_s, "error": res.error,
             "meta": meta}
        e.update(extra)
        return e

    def make(parsed: dict, **kw) -> Result:
        return Result(text=parsed["text"], tool_calls=parsed["tool_calls"], stop_reason=parsed["stop_reason"],
                      refusal=parsed["refusal"], usage=parsed["usage"], model=key, model_id=cfg["model_id"],
                      model_returned=parsed.get("model_returned"), provider=cfg["provider"],
                      sample_index=sample_index, request_sha256=pr["request_sha256"], call_id=call_id,
                      assistant_message=parsed.get("assistant_message"), stop_reason_raw=parsed.get("stop_reason_raw"),
                      discarded_text=parsed.get("discarded_text"), est_max_cost_usd=pr["est_max_cost_usd"],
                      log_path=str(log_file), meta=meta, **kw)

    empty = {"text": "", "tool_calls": [], "stop_reason": None, "refusal": None, "usage": {}}

    # 1) 応答のキャッシュ（同じ要求・同じ標本の番号なら API を呼ばない。費用 0 として記録）
    if cache:
        hit = _cache_get(project, ckey)
        if hit:
            parsed = prov.parse(hit["raw"], cfg)
            res = make(parsed, cost_usd=0.0, latency_s=0.0, cache_hit=True,
                       original_cost_usd=cost_usd(cfg, parsed["usage"]))
            save_request()
            _append_jsonl(log_file, entry(res, {"cached_call_id": hit.get("call_id"),
                                                "provider_request_id": hit.get("provider_request_id")}))
            return res

    # 2) 予算（送る前に、最大の見積もりで確かめる）
    try:
        st = _check_budget(project, pr["est_max_cost_usd"], [log_file])
    except (BudgetNotSet, BudgetExceeded) as e:
        res = make(empty, cost_usd=0.0, latency_s=0.0, cache_hit=False,
                   error={"type": "budget_refused", "message": str(e)})
        save_request()
        _append_jsonl(log_file, entry(res, {}))
        raise

    # 3) 送る
    cl = client or _client_for(key, cfg, prov)
    wire = prov.materialize(body, blobs)
    save_request()
    t0 = time.monotonic()
    try:
        raw, rid = prov.send(cl, wire, cfg)
    except Exception as e:  # noqa: BLE001 — 記録してから投げ直す（再試行は SDK が 429・5xx・接続の失敗で行う）
        lat = round(time.monotonic() - t0, 3)
        ref = prov.refusal_from_error(e)
        err = {"type": type(e).__name__, "status": getattr(e, "status_code", None), "message": scrub(str(e))[:2000]}
        if ref is None:
            res = make(empty, cost_usd=0.0, latency_s=lat, cache_hit=False, error=err)
            _append_jsonl(log_file, entry(res, {"budget": {"cap": st["cap"], "spent_before": st["spent"]}}))
            raise LLMCallError(f"{key} の呼び出しに失敗: {err['type']} {err['message'][:300]}", res) from e
        parsed = dict(empty, stop_reason="refusal", refusal=ref, stop_reason_raw="error")
        res = make(parsed, cost_usd=0.0, latency_s=lat, cache_hit=False)
        _append_jsonl(log_file, entry(res, {"refusal_error": err,
                                            "budget": {"cap": st["cap"], "spent_before": st["spent"]}}))
        return res
    lat = round(time.monotonic() - t0, 3)
    parsed = prov.parse(raw, cfg)
    res = make(parsed, cost_usd=cost_usd(cfg, parsed["usage"]), latency_s=lat, cache_hit=False)
    _write_json(resp_path, {"call_id": call_id, "provider_request_id": rid, "raw": raw})
    if cache:
        _write_json(_cache_path(project, ckey), {"call_id": call_id, "created": now(), "model": key,
                                                 "request_sha256": pr["request_sha256"],
                                                 "sample_index": sample_index, "provider_request_id": rid, "raw": raw})
    if res.model_returned and not str(res.model_returned).startswith(cfg["model_id"]):
        print(f"rl llm: 警告 — {cfg['model_id']} を頼んだが応答は {res.model_returned}（記録に model_mismatch）", file=sys.stderr)
    _append_jsonl(log_file, entry(res, {"provider_request_id": rid, "response_id": parsed.get("response_id"),
                                        "response_path": rel(resp_path),
                                        "budget": {"cap": st["cap"], "spent_before": st["spent"]}}))
    return res


# ───────────────────────── 道具のループ（P-E）

def _validate(schema: dict, value, path="$") -> list[str]:
    """JSON Schema の小さな部分集合（type・required・additionalProperties・properties・items・enum）。"""
    errs: list[str] = []
    if not isinstance(schema, dict):
        return errs
    t = schema.get("type")
    types = {"object": dict, "array": list, "string": str, "boolean": bool, "integer": int, "number": (int, float)}
    if t in types:
        ok = isinstance(value, types[t]) and not (t in ("integer", "number") and isinstance(value, bool))
        if not ok:
            return [f"{path}: {t} ではありません"]
    if "enum" in schema and value not in schema["enum"]:
        errs.append(f"{path}: {schema['enum']} のどれでもありません")
    if t == "object" and isinstance(value, dict):
        props = schema.get("properties") or {}
        for r in schema.get("required") or []:
            if r not in value:
                errs.append(f"{path}.{r}: 必須です")
        if schema.get("additionalProperties") is False:
            for k in value:
                if k not in props:
                    errs.append(f"{path}.{k}: 余計なキーです")
        for k, v in value.items():
            if k in props:
                errs.extend(_validate(props[k], v, f"{path}.{k}"))
    if t == "array" and isinstance(value, list) and "items" in schema:
        for i, v in enumerate(value):
            errs.extend(_validate(schema["items"], v, f"{path}[{i}]"))
    return errs


def _run_tool(by_name: dict, tc: dict) -> tuple[str, bool]:
    t = by_name.get(tc.get("name"))
    if t is None:
        return f"道具 {tc.get('name')!r} はありません。使える道具: {', '.join(by_name)}", True
    if tc.get("input_error"):
        return tc["input_error"], True
    args = tc.get("input") if isinstance(tc.get("input"), dict) else None
    if args is None:
        return "道具の引数は JSON のオブジェクトにしてください", True
    errs = _validate(t.input_schema, args)
    if errs:
        return "引数が道具の形に合いません: " + "; ".join(errs), True
    try:
        out = t.fn(**args)
    except Exception as e:  # noqa: BLE001 — 判定器の例外はモデルに返す（ループは止めない）
        return f"{type(e).__name__}: {e}", True
    return (out if isinstance(out, str) else json.dumps(out, ensure_ascii=False, default=str)), False


def tool_loop(model: str, messages, tools: list, *, max_turns: int = 20, sample_index: int = 0,
              meta: dict | None = None, images=None, **kw) -> LoopResult:
    """道具を呼ばなくなるか、拒否・出力の打ち切り・max_turns まで回す。1 回ごとに call() が記録する。"""
    history = [{"role": "user", "content": messages}] if isinstance(messages, str) else [dict(m) for m in messages]
    loop_id = _sha({"model": model, "messages": history, "images": [str(x) for x in images or []],
                    "tools": [t.name for t in tools], "sample_index": sample_index})[:16]
    by_name = {t.name: t for t in tools}
    turns, runs = [], []
    stopped = "max_turns"
    for turn in range(max_turns):
        r = call(model, history, tools=tools, images=images, sample_index=sample_index,
                 meta={**(meta or {}), "loop_id": loop_id, "turn": turn}, **kw)
        turns.append(r)
        if r.refused:
            stopped = "refusal"
            break
        if r.stop_reason == "max_tokens":
            stopped = "max_tokens"          # 途中で切れた道具の引数は実行しない
            break
        if not r.tool_calls:
            stopped = r.stop_reason or "end_turn"
            break
        history.append(r.assistant_message)
        results = []
        for tc in r.tool_calls:
            out, is_err = _run_tool(by_name, tc)
            runs.append({"turn": turn, "id": tc.get("id"), "name": tc.get("name"), "input": tc.get("input"),
                         "output": out, "is_error": is_err})
            results.append({"type": "tool_result", "tool_call_id": tc.get("id"), "content": out, "is_error": is_err})
        history.append({"role": "user", "content": results})   # 並列の呼び出しの結果は 1 つの user にまとめる
    return LoopResult(final=turns[-1] if turns else None, turns=turns, messages=history,
                      stopped=stopped, tool_runs=runs)
