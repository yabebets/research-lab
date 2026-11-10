"""rl annotate draft の止める仕組み（評価対象と同じモデル、G2 前のテスト機種）と、LLM の呼び出し口。"""
import json
import sys
import types

import pytest

from conftest import FIX
from rlkit import annotate as A

PLAN = """# 実験計画
## 1. 対象とデータ
| 区分 | 機種 | 使い方 |
|---|---|---|
| テスト | OpenArm 1.0 | 手順書 |
| テスト | XLeRobot | 手順書 |
| 開発用 | ToddlerBot | 調整 |
## 2. 比べる計画器
- **言語モデルは 3 つ**（人が決定）：Claude Opus 5.5（`claude-opus-5-5`、主）、GPT-5（比較）、Qwen3-VL（公開の重み）。DeepSeek は外した
"""


@pytest.fixture
def proj(tmp_path):
    p = tmp_path / "proj"
    (p / "notes").mkdir(parents=True)
    (p / "research.yaml").write_text("project: proj\ngates:\n  G2: {approved: false}\nprotocol: {test_split: ''}\n")
    (p / "plan.md").write_text(PLAN)
    (tmp_path / "manual.txt").write_text("Step 1. Place the servo into the base.\n")
    return p


def args(proj, robot, out, **kw):
    d = dict(project=str(proj), robot=robot, manual=str(proj.parent / "manual.txt"), out=str(out), bom=None,
             model=None, call=False, dry_run_schema=False, evaluated=None, license=None)
    d.update(kw)
    return types.SimpleNamespace(**d)


def test_reads_evaluated_models_and_test_robots(proj):
    ev = A.evaluated_models(proj)
    assert ev == ["Claude Opus 5.5", "claude-opus-5-5", "GPT-5", "Qwen3-VL"]   # DeepSeek（外した）は入らない
    assert A.test_robots(proj) == ["OpenArm 1.0", "XLeRobot"]
    assert A.is_test_robot("openarm", A.test_robots(proj)) == "OpenArm 1.0"
    assert A.is_test_robot("toddlerbot", A.test_robots(proj)) is None


@pytest.mark.parametrize("model,bad", [("claude-opus-5-5", True), ("gpt-5-mini", True), ("qwen3-vl-plus", True),
                                       ("claude-sonnet-5", False), ("deepseek-v4", False)])
def test_model_conflict(proj, model, bad):
    assert (A.model_conflict(model, A.evaluated_models(proj)) is not None) == bad


def test_refuses_test_robot_before_g2(proj, tmp_path):
    with pytest.raises(SystemExit):
        A.cmd_draft(args(proj, "openarm", tmp_path / "o.yaml"))
    A.cmd_draft(args(proj, "openarm", tmp_path / "o.yaml", dry_run_schema=True))
    meta = json.loads((tmp_path / "o.prompt" / "meta.json").read_text())
    assert meta["dry_run_schema"] is True and meta["test_robot"] == "OpenArm 1.0"


def test_refuses_evaluated_model(proj, tmp_path):
    with pytest.raises(SystemExit):
        A.cmd_draft(args(proj, "toddlerbot", tmp_path / "t.yaml", model="claude-opus-5-5"))


def test_package_without_call(proj, tmp_path):
    A.cmd_draft(args(proj, "toddlerbot", tmp_path / "t.yaml", model="claude-sonnet-5", license="CC-BY-NC-SA-4.0"))
    pkg = tmp_path / "t.prompt"
    assert {"prompt.md", "rules.md", "schema.json", "meta.json", "manual.txt"} <= {p.name for p in pkg.iterdir()}
    meta = json.loads((pkg / "meta.json").read_text())
    assert meta["redistribution"] == "restricted" and meta["model"] == "claude-sonnet-5"
    assert "Place the servo" in (pkg / "prompt.md").read_text()
    assert not (tmp_path / "t.yaml").exists()


def fake_llm(monkeypatch, text, model_id="claude-sonnet-5", resolve_to=None):
    calls = []

    def call(model, messages, *, system=None, max_tokens, budget_project=None, meta=None):
        calls.append({"model": model, "meta": meta, "budget_project": budget_project})
        return types.SimpleNamespace(text=text, model_id=model_id, model_returned=model_id, cost_usd=0.0,
                                     refused=False, refusal=None, error=None)

    def resolve_model(name, reg):
        return (resolve_to or name), {"model_id": resolve_to or name}

    mod = types.ModuleType("rlkit.llm")
    mod.call = call
    mod.resolve_model = resolve_model
    mod.load_registry = lambda: {}
    import rlkit
    monkeypatch.setitem(sys.modules, "rlkit.llm", mod)
    monkeypatch.setattr(rlkit, "llm", mod, raising=False)
    return calls


def test_call_writes_validated_draft(proj, tmp_path, monkeypatch):
    body = (FIX / "minimal_v02.yaml").read_text().replace("toyarm", "toddlerbot")
    calls = fake_llm(monkeypatch, "前置き\n```yaml\n" + body + "```\n")
    out = tmp_path / "t.yaml"
    A.cmd_draft(args(proj, "toddlerbot", out, model="claude-sonnet-5", call=True))
    d = A.to_plain(A.load_yaml(out))
    assert d["annotation"]["drafted_by"] == "claude-sonnet-5"
    assert all(x["review"] == {"status": "draft", "drafted_by": "claude-sonnet-5"} for x in d["atomic"])
    assert calls[0]["meta"]["purpose"] == "annotate-draft"
    assert A.validate(A.load_yaml(out)).errors == []


def test_call_refuses_alias_resolving_to_evaluated(proj, tmp_path, monkeypatch):
    fake_llm(monkeypatch, "```yaml\nrobot: x\n```", resolve_to="claude-opus-5-5")
    with pytest.raises(SystemExit):
        A.cmd_draft(args(proj, "toddlerbot", tmp_path / "t.yaml", model="anthropic", call=True))
    assert not (tmp_path / "t.yaml").exists()


def test_call_needs_model(proj, tmp_path):
    with pytest.raises(SystemExit):
        A.cmd_draft(args(proj, "toddlerbot", tmp_path / "t.yaml", call=True))
