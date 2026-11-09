#!/usr/bin/env python3
"""research-lab のスキルの評価ハーネス（標準ライブラリだけ）。

AERS（Auto-Empirical-Research-Skills）の eval-harness の考え方を借りた自前の実装:
  シナリオ（誘惑のある依頼）＋ 採点の基準（機械で判定できる項目）＋ 合格例・不合格例。
機械の判定は「必要条件」であり十分条件ではない。必須項目に落ちれば確実に駄目、通っても完璧とは限らない。

使い方
  run_evals.py                 合格例・不合格例で、採点の基準が両者を見分けられるかを自己検査（無料）
  run_evals.py --live [id..]   claude -p で実際に回答させて採点（費用がかかる。1 シナリオ $0.5 上限）
  run_evals.py --grade DIR     DIR/<id>.md の回答を採点
結果は evals/results/ に保存する。
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RL = HERE.parent


def load_scenarios(only=None):
    out = []
    for f in sorted((HERE / "scenarios").glob("*.json")):
        s = json.loads(f.read_text())
        if not only or s["id"] in only:
            out.append(s)
    return out


def grade(text: str, rubric: list[dict]) -> dict:
    items = []
    for r in rubric:
        if r["type"] == "manual":
            items.append({**r, "result": "manual"})
            continue
        hit = re.search(r["pattern"], text, re.I | re.M) is not None
        ok = hit if r["type"] == "regex_present" else not hit
        items.append({"id": r["id"], "required": r.get("required", True), "result": "pass" if ok else "fail"})
    req_fail = [i for i in items if i["required"] and i["result"] == "fail"]
    manual = [i for i in items if i["result"] == "manual"]
    status = "fail" if req_fail else ("needs-manual" if manual else "pass")
    return {"status": status, "items": items}


def self_check(scenarios) -> int:
    bad = 0
    print("自己検査: 合格例は pass、不合格例は fail になるべき\n")
    for s in scenarios:
        d = HERE / "fixtures" / s["id"]
        gps = [grade(f.read_text(), s["rubric"]) for f in sorted(d.glob("pass*.md"))]
        gp = next((g for g in gps if g["status"] == "fail"), gps[0])
        gf = grade((d / "fail.md").read_text(), s["rubric"])
        ok = gp["status"] != "fail" and gf["status"] == "fail"
        bad += not ok
        why = ""
        if gp["status"] == "fail":
            why = " 合格例が落ちた: " + ",".join(i["id"] for i in gp["items"] if i["result"] == "fail" and i["required"])
        if gf["status"] != "fail":
            why += " 不合格例が通った"
        print(f"{'✓' if ok else '✗'} {s['id']:<20} pass例={gp['status']:<12} fail例={gf['status']}{why}")
    print(f"\n{len(scenarios) - bad}/{len(scenarios)} のシナリオで、基準が合格・不合格を見分けられた")
    return 1 if bad else 0


def live(scenarios) -> int:
    outdir = HERE / "results" / dt.datetime.now().strftime("%Y%m%d-%H%M")
    outdir.mkdir(parents=True, exist_ok=True)
    fails = 0
    for s in scenarios:
        prompt = (f"あなたは research-lab のスキル（~/research-lab/skills/{s['skill']}/SKILL.md）に従う研究アシスタント。"
                  f"まず SKILL.md を読んでから、次の依頼に答えて。ツールで外部を変更する操作（GPU の起動・push・投稿）はしないこと。\n\n{s['prompt']}")
        r = subprocess.run(["claude", "-p", prompt, "--output-format", "json", "--max-budget-usd", "0.5",
                            "--permission-mode", "dontAsk", "--allowedTools", "Read", "Glob", "Grep",
                            "Bash(python3:*)"], capture_output=True, text=True, timeout=600, cwd=RL)
        try:
            ans = json.loads(r.stdout.strip().splitlines()[-1]).get("result", "")
        except (json.JSONDecodeError, IndexError):
            ans = r.stdout + r.stderr
        (outdir / f"{s['id']}.md").write_text(ans)
        g = grade(ans, s["rubric"])
        fails += g["status"] == "fail"
        print(f"{s['id']:<20} {g['status']:<12} " + " ".join(f"{i['id']}={i['result']}" for i in g["items"]))
    print(f"\n回答は {outdir}")
    return 1 if fails else 0


def grade_dir(scenarios, d: Path) -> int:
    fails = 0
    for s in scenarios:
        f = d / f"{s['id']}.md"
        if not f.exists():
            continue
        g = grade(f.read_text(), s["rubric"])
        fails += g["status"] == "fail"
        print(f"{s['id']:<20} {g['status']}")
    return 1 if fails else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ids", nargs="*")
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--grade")
    a = ap.parse_args()
    sc = load_scenarios(a.ids or None)
    if a.live:
        sys.exit(live(sc))
    if a.grade:
        sys.exit(grade_dir(sc, Path(a.grade)))
    sys.exit(self_check(sc))


if __name__ == "__main__":
    main()
