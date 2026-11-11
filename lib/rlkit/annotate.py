"""rl annotate — 手順書の工程の正解（中間表現 IR v0.2）を作る・確かめる・一致を測る。

  rl annotate validate <file.yaml> [--ref other.yaml ...] [--strict] [--verbose]
  rl annotate convert-v01 <v0.1.yaml> --out <v0.2.yaml> [--report report.md]
  rl annotate draft <project> <robot> --manual <path> --out <file.yaml> [--bom <path>] [--model M] [--call]
                    [--dry-run-schema] [--evaluated M1 M2 ..] [--license L]
  rl annotate review <file.yaml> --sheet out.csv [--all]
  rl annotate apply <file.yaml> --sheet reviewed.csv [--out file.yaml] [--reviewer NAME]
  rl annotate sample <file.yaml> [--frac 0.2] [--seed 0] [--out ids.txt] [--blank blank.yaml]
  rl annotate agree <a.yaml> <b.yaml> [--ids ids.txt] [--threshold 0.6] [--boot 2000] [--seed 0] [--drop-unknown] [--json]

スキーマ: lib/rlkit/ir_schema_v0_2.json（projects/robot-assembly-bench/notes/ir-design-2026-11-09.md §2、
taxonomy-draft §9–§10）。手順: skills/research-lab/references/annotation.md。
一致の統計は skills/ml-rigor/scripts/rl_stats.py（kappa・alpha）を呼んで計算する（暗算しない）。
"""
from __future__ import annotations

import argparse
import copy
import csv
import datetime as dt
import hashlib
import inspect
import json
import random
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq

from .common import RL, die, now, resolve_project

SCHEMA_PATH = Path(__file__).with_name("ir_schema_v0_2.json")
RL_STATS = RL / "skills" / "ml-rigor" / "scripts" / "rl_stats.py"

TYPES = ["INS", "PRS", "SNP", "SCR", "HRN", "CBL", "CON", "ADH", "ALN", "SW", "INSP", "OTH", "unknown"]
AXES = ["tool_required", "tool_access", "hold_needed", "fixture_required", "geometric_screen",
        "evaluator_support", "human_required", "execution_outcome"]
ORDINAL = {"hold_needed": ["0", "1", "2+"]}
STANDARD_ATTRS = ["flips", "force", "deformable", "attached_flexible", "zero_position", "joint_motion",
                  "access_clearance", "n_held_parts", "min_part_mm"]
EVAL_SUPPORTED = {"INS", "HRN", "SCR"}
EVAL_UNSUPPORTED = {"PRS", "SNP", "CON", "CBL", "ADH", "ALN"}
SCOPE_OF_TYPE = {"OTH": "manufacturing", "SW": "software", "INSP": "inspect"}
NON_VALUES = {None, "unknown", "not_checked", "not_run"}   # 出所がなくてよい「未判定」の値
SRC_VALUES = ["stated", "cad", "bom", "rule", "sim", "rule+sim", "sim-uncertain", "annotator", "execution", "borrowed[:robot]"]
PLAIN_FIELDS = ["type", "secondary", "fix_state", "from_media_only", "count", "template_of", "optional", "parts_in", "fasteners"]

# ---------------------------------------------------------------- YAML（rl と同じ書式。null と yes/no をはっきり書く）
_AMBIG = {"yes", "no", "on", "off", "true", "false", "y", "n", "null", "~", ""}

yaml = YAML()
yaml.preserve_quotes = True
yaml.width = 4096
yaml.indent(mapping=2, sequence=4, offset=2)
yaml.representer.add_representer(type(None), lambda r, d: r.represent_scalar("tag:yaml.org,2002:null", "null"))


def _repr_str(r, d):
    style = "'" if d.strip().lower() in _AMBIG else None
    return r.represent_scalar("tag:yaml.org,2002:str", d, style=style)


yaml.representer.add_representer(str, _repr_str)


def load_yaml(path: Path):
    with Path(path).open() as f:
        return yaml.load(f)


def dump_yaml(data, path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w") as f:
        yaml.dump(data, f)
    tmp.replace(path)


def F(d: dict) -> CommentedMap:
    """1 行で書く小さな対応（{v, src} や辺）。"""
    m = CommentedMap(d)
    m.fa.set_flow_style()
    return m


def FL(xs) -> CommentedSeq:
    s = CommentedSeq(list(xs))
    s.fa.set_flow_style()
    return s


def to_plain(x):
    """ruamel の型・日付を JSON にできる素の型にする（スキーマの検査用）。"""
    if isinstance(x, dict):
        return {str(k): to_plain(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [to_plain(v) for v in x]
    if isinstance(x, (dt.date, dt.datetime)):
        return x.isoformat()
    if isinstance(x, bool) or x is None:
        return x
    if isinstance(x, int):
        return int(x)
    if isinstance(x, float):
        return float(x)
    if isinstance(x, str):
        return str(x)
    return x


def _norm_model(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


# ---------------------------------------------------------------- validate
class Report:
    def __init__(self):
        self.errors: list[tuple[str, str]] = []
        self.warnings: list[tuple[str, str]] = []

    def err(self, code, msg):
        self.errors.append((code, msg))

    def warn(self, code, msg):
        self.warnings.append((code, msg))


def _schema():
    return json.loads(SCHEMA_PATH.read_text())


def _path_label(doc: dict, path) -> str:
    parts = list(path)
    out = ""
    for i, p in enumerate(parts):
        if isinstance(p, int):
            out += f"[{p}]"
            if i == 1 and isinstance(parts[0], str):
                lst = doc.get(parts[0])
                if isinstance(lst, list) and p < len(lst) and isinstance(lst[p], dict):
                    ident = lst[p].get("id") or (f"{lst[p].get('from')}->{lst[p].get('to')}" if "from" in lst[p] else None)
                    if ident:
                        out += f" ({ident})"
        else:
            out += ("." if out else "") + str(p)
    return out or "(全体)"


def _schema_message(e) -> str:
    v = e.validator
    if v == "required":
        m = re.search(r"'(.+?)' is a required property", e.message)
        return f"必須の項目 {m.group(1) if m else e.message} がない"
    if v == "additionalProperties":
        msg = e.message.split("does not match any of the regexes")[0]
        m = re.findall(r"'([^']+)'", msg)
        return f"知らない項目 {', '.join(m) or e.message}（綴りの誤り？ 拡張なら x_ を前に付ける）"
    if v == "enum":
        return f"値 {e.instance!r} は使えない（使える値: {', '.join(map(repr, e.validator_value))}）"
    if v == "const":
        return f"値 {e.instance!r} は {e.validator_value!r} でなければならない"
    if v == "type":
        return f"型が違う（値 {e.instance!r}、期待する型: {e.validator_value}）"
    if v == "pattern":
        return f"書式が違う（値 {e.instance!r}、期待する形: {e.validator_value}）"
    if v in ("minimum", "exclusiveMinimum"):
        return f"値 {e.instance!r} は {e.validator_value} 以上にする"
    if v == "minLength":
        return "空にできない"
    if v in ("anyOf", "oneOf"):
        if "src" in [str(p) for p in e.absolute_path] or "size_source" in [str(p) for p in e.absolute_path]:
            return f"出所の値 {e.instance!r} は使えない（使える値: {', '.join(SRC_VALUES)}、null）"
        return f"値 {e.instance!r} が許される形のどれにも合わない"
    return e.message


def _ids(lst):
    return [x.get("id") for x in lst if isinstance(x, dict)]


def _variants(doc) -> set:
    out = set()
    for v in doc.get("variants") or []:
        out.add(v if isinstance(v, str) else v.get("id"))
    return out


def _find_cycle(nodes, edges):
    """有向グラフの閉路を 1 つ返す（なければ None）。"""
    adj = {n: [] for n in nodes}
    for a, b in edges:
        adj.setdefault(a, []).append(b)
        adj.setdefault(b, [])
    color = {n: 0 for n in adj}
    parent = {}
    for start in adj:
        if color[start]:
            continue
        stack = [(start, iter(adj[start]))]
        color[start] = 1
        while stack:
            node, it = stack[-1]
            nxt = next(it, None)
            if nxt is None:
                color[node] = 2
                stack.pop()
                continue
            if color[nxt] == 0:
                color[nxt] = 1
                parent[nxt] = node
                stack.append((nxt, iter(adj[nxt])))
            elif color[nxt] == 1:
                cyc = [nxt]
                cur = node
                while cur != nxt:
                    cyc.append(cur)
                    cur = parent[cur]
                cyc.append(nxt)
                return list(reversed(cyc))
    return None


def validate(doc, refs: dict | None = None) -> Report:
    """スキーマ＋意味のチェック。refs: {robot: set(bom_id)}（別機種の部品の確認用）。"""
    import jsonschema

    rep = Report()
    plain = to_plain(doc)
    if not isinstance(plain, dict):
        rep.err("schema", "YAML の一番上が対応（mapping）になっていない")
        return rep
    validator = jsonschema.Draft202012Validator(_schema())
    for e in sorted(validator.iter_errors(plain), key=lambda e: [str(p) for p in e.absolute_path]):
        rep.err("schema", f"{_path_label(plain, e.absolute_path)}: {_schema_message(e)}")

    robot = plain.get("robot")
    bom = [b for b in plain.get("bom") or [] if isinstance(b, dict)]
    secs = [s for s in plain.get("sections") or [] if isinstance(s, dict)]
    steps = [s for s in plain.get("manual_steps") or [] if isinstance(s, dict)]
    l1s = [a for a in plain.get("atomic") or [] if isinstance(a, dict)]
    edges = [e for e in plain.get("precedence") or [] if isinstance(e, dict)]

    # ID の重複
    for name, lst in (("bom", bom), ("sections", secs), ("manual_steps", steps), ("atomic", l1s)):
        seen = set()
        for i in _ids(lst):
            if i in seen:
                rep.err("dup", f"{name}: ID {i} が重複している")
            seen.add(i)
    bom_ids, sec_ids, l2_ids, l1_ids = set(_ids(bom)), set(_ids(secs)), set(_ids(steps)), set(_ids(l1s))
    variants = _variants(plain)

    def check_variant(where, vs):
        if not vs:
            return
        if not variants:
            if any(v != "all" for v in vs):
                rep.warn("variant", f"{where}: variant {list(vs)} があるが、一番上の variants が空")
            return
        for v in vs:
            if v != "all" and v not in variants:
                rep.err("variant", f"{where}: variant {v} が variants にない（{sorted(variants)}）")

    # BOM
    for b in bom:
        w = f"bom ({b.get('id')})"
        if b.get("kind") == "included_with":
            ref = b.get("included_with") or b.get("parent")
            if not ref:
                rep.err("bom", f"{w}: kind: included_with なのに included_with（付属元）がない")
            elif ref not in bom_ids:
                rep.err("bom", f"{w}: included_with {ref} が BOM にない")
        elif b.get("included_with"):
            rep.warn("bom", f"{w}: included_with があるが kind が included_with でない")
        if b.get("parent") and b["parent"] not in bom_ids:
            rep.err("bom", f"{w}: parent {b['parent']} が BOM にない")
        check_variant(w, b.get("variant"))
    # L3 / L2
    for s in steps:
        w = f"manual_steps ({s.get('id')})"
        if s.get("section") and s["section"] not in sec_ids:
            rep.err("ref", f"{w}: section {s['section']} が sections にない")
        check_variant(w, s.get("variant"))

    # L1
    referenced_l2 = set()
    for a in l1s:
        aid = a.get("id")
        w = f"atomic ({aid})"
        refs_l2 = a.get("l2_refs") or []
        for r in refs_l2:
            referenced_l2.add(r)
            if r not in l2_ids:
                rep.err("ref", f"{w}: l2_refs の {r} が manual_steps にない")
        if not refs_l2 and not a.get("source_section"):
            rep.err("coverage", f"{w}: l2_refs が空（番号ステップの外の本文から拾ったなら source_section を書く）")
        t = a.get("template_of")
        if t is not None:
            if t == aid:
                rep.err("ref", f"{w}: template_of が自分自身")
            elif t not in l1_ids:
                rep.err("ref", f"{w}: template_of {t} が atomic にない")
        for p in a.get("parts_in") or []:
            if not isinstance(p, str) or ":" not in p:
                continue
            rb, bid = p.split(":", 1)
            if rb == robot:
                if bid not in bom_ids:
                    rep.err("bom", f"{w}: 部品 {p} が BOM にない")
            elif refs and rb in refs:
                if bid not in refs[rb]:
                    rep.err("bom", f"{w}: 部品 {p} が {rb} の BOM にない")
            else:
                rep.warn("external", f"{w}: 別機種の部品 {p}（--ref {rb}.yaml で確かめられる）")
        if not a.get("parts_in"):
            rep.warn("parts", f"{w}: parts_in が空")
        check_variant(w, a.get("variant"))
        typ = a.get("type")
        if typ == "unknown" and not a.get("from_media_only"):
            rep.warn("media", f"{w}: type が unknown なのに from_media_only が true でない")
        if typ == "SCR" and not a.get("fasteners"):
            rep.warn("fasteners", f"{w}: SCR なのに fasteners がない")
        # 出所
        for k, pv in (a.get("attrs") or {}).items():
            if isinstance(pv, dict) and pv.get("v") not in NON_VALUES and not pv.get("src"):
                rep.err("prov", f"{w}: attrs.{k} = {pv.get('v')!r} に出所（src）がない")
        tool = a.get("tool")
        if isinstance(tool, dict) and tool.get("v") not in NON_VALUES and not tool.get("src"):
            rep.err("prov", f"{w}: tool = {tool.get('v')!r} に出所（src）がない")
        label = a.get("label") or {}
        for ax in AXES + ["summary"]:
            pv = label.get(ax)
            if isinstance(pv, dict) and pv.get("v") not in NON_VALUES and not pv.get("src"):
                rep.err("prov", f"{w}: label.{ax} = {pv.get('v')!r} に出所（src）がない")
        # 規則との食い違い（taxonomy §10.1）
        scope = label.get("scope")
        want_scope = SCOPE_OF_TYPE.get(typ, "assembly") if typ != "unknown" else None
        if scope and want_scope and scope != want_scope:
            rep.warn("rule", f"{w}: type {typ} なのに scope が {scope}（規則では {want_scope}）")
        es = (label.get("evaluator_support") or {}).get("v")
        if es and typ in EVAL_SUPPORTED | EVAL_UNSUPPORTED:
            want = "supported" if typ in EVAL_SUPPORTED else "unsupported"
            if es != want:
                rep.warn("rule", f"{w}: type {typ} の evaluator_support は規則では {want}（いまは {es}）")
        hr = label.get("human_required") or {}
        if hr.get("v") == "yes" and not hr.get("reason"):
            rep.warn("rule", f"{w}: human_required: yes に独立の根拠（reason）がない（評価器が扱えないだけなら unknown）")
        fx = label.get("fixture_required") or {}
        if fx.get("v") == "yes" and (label.get("hold_needed") or {}).get("v") != "2+" and not fx.get("reason"):
            rep.warn("rule", f"{w}: fixture_required: yes だが hold_needed が 2+ でなく、reason もない")
        if (a.get("review") or {}).get("status") == "blank":
            rep.warn("blank", f"{w}: 空欄の L1（2 人目の注釈を待っている）")
    for s in steps:
        if s.get("id") not in referenced_l2:
            rep.warn("coverage", f"manual_steps ({s.get('id')}): どの L1 からも参照されない L2")

    # 先行関係
    seen = set()
    req, rec = [], []
    for e in edges:
        f, t = e.get("from"), e.get("to")
        w = f"precedence ({f}->{t})"
        for end in (f, t):
            if end not in l1_ids:
                rep.err("ref", f"{w}: {end} が atomic にない（辺は L1 の ID で書く）")
        if f == t:
            rep.err("edge", f"{w}: 自分から自分への辺")
        if (f, t) in seen:
            rep.err("dup", f"{w}: 同じ辺が 2 回ある")
        seen.add((f, t))
        kind, source = e.get("kind"), e.get("source")
        if source == "order_only" and kind == "required":
            rep.err("edge", f"{w}: source が order_only（本文の並びだけ）の辺を required にしている（正解に入れない）")
        if kind is None and source != "order_only":
            rep.err("edge", f"{w}: kind が空（required / recommended / unknown のどれかにする）")
        if kind == "unknown":
            rep.warn("edge_unknown", f"{w}: kind が unknown（正解に使う前に required / recommended を決める）")
        if source == "unknown":
            rep.warn("edge_source", f"{w}: source が unknown")
        if kind == "required":
            req.append((f, t))
        elif kind == "recommended":
            rec.append((f, t))
    cyc = _find_cycle(l1_ids, req)
    if cyc:
        rep.err("cycle", "required の辺に閉路がある: " + " -> ".join(cyc))
    else:
        cyc2 = _find_cycle(l1_ids, req + rec)
        if cyc2:
            rep.warn("cycle", "required と recommended を合わせると閉路がある: " + " -> ".join(cyc2))
    return rep


def summary_line(doc) -> str:
    p = to_plain(doc)
    l1s = p.get("atomic") or []
    edges = p.get("precedence") or []
    kinds = {}
    for e in edges:
        k = "order_only" if e.get("source") == "order_only" else (e.get("kind") or "null")
        kinds[k] = kinds.get(k, 0) + 1
    types = {}
    for a in l1s:
        types[a.get("type")] = types.get(a.get("type"), 0) + 1
    tstr = " ".join(f"{k}:{v}" for k, v in sorted(types.items(), key=lambda x: -x[1]))
    kstr = " / ".join(f"{k} {v}" for k, v in sorted(kinds.items()))
    return (f"L2 {len(p.get('manual_steps') or [])}・L1 {len(l1s)}・辺 {len(edges)}（{kstr}）\n"
            f"  型: {tstr}")


def print_report(rep: Report, verbose=False, max_per_code=5):
    print(f"エラー {len(rep.errors)} 件・注意 {len(rep.warnings)} 件")
    if rep.errors:
        print("エラー:")
        for _, m in rep.errors:
            print(f"  - {m}")
    if rep.warnings:
        print("注意:")
        by = {}
        for c, m in rep.warnings:
            by.setdefault(c, []).append(m)
        for c, ms in by.items():
            show = ms if verbose else ms[:max_per_code]
            for m in show:
                print(f"  - {m}")
            if len(ms) > len(show):
                print(f"    （同じ種類がほか {len(ms) - len(show)} 件。--verbose で全部）")


def cmd_validate(a):
    doc = load_yaml(a.file)
    refs = {}
    for r in a.ref or []:
        d = to_plain(load_yaml(r))
        refs[d.get("robot")] = {b.get("id") for b in d.get("bom") or []}
    rep = validate(doc, refs)
    print(f"{a.file}: {summary_line(doc)}")
    print_report(rep, a.verbose)
    if rep.errors or (a.strict and rep.warnings):
        sys.exit(1)


# ---------------------------------------------------------------- convert-v01
REVERSIBLE_KW = ["逆順も可", "後でも", "可逆", "でも付けられる", "でも付く", "前でも", "easier", "後からだと難しい", "already"]
UNCERTAIN_KW = ["要 CAD", "CAD で確認", "なら独立", "確認要", "なら geometry"]
ZERO_KW = ["not to move the motor position", "middle position", "zero position", "center position"]
JOINT_KW = ["by turning the", "turning the shoulder", "rotate the joint"]


def _tool_axis(tool_v: str | None, src: str):
    if tool_v in (None, "none"):
        return F({"v": "none", "src": src})
    s = tool_v.lower()
    hex_ = "hex" in s
    ph = "phillips" in s or "screwdriver" in s
    if hex_ and ph:
        return F({"v": "unknown", "src": src, "reason": "六角とプラスのどちらか本文から決まらない"})
    if hex_:
        return F({"v": "hex", "src": src})
    if ph:
        return F({"v": "screwdriver", "src": src})
    if "plier" in s:
        return F({"v": "pliers", "src": src})
    return F({"v": "other", "src": src, "reason": tool_v})


def _conv_fasteners(fz, rep_unknown, aid):
    if not fz:
        return None
    raw = fz.get("size")
    size, ssrc, notes = None, None, []
    if raw is not None:
        m = re.match(r"^\s*(M\d+(?:\.\d+)?(?:x\d+(?:\.\d+)?)?)", str(raw))
        if m:
            size = m.group(1)
            ssrc = "guess" if any(k in str(raw) for k in ("推定", "?", "guess")) else "manual"
            if str(raw).strip() != size:
                notes.append(f"v0.1 の寸法の欄: {raw}")
        else:
            notes.append(f"v0.1 の寸法の欄: {raw}")
            rep_unknown.append(f"{aid}: ねじの寸法が不明（{raw}）")
    v01src = fz.get("size_source")
    if v01src:
        ssrc = {"so101": "borrowed:so101", "guess": "guess", "none": None, "manual": "manual"}.get(v01src, f"borrowed:{v01src}")
        if size is None and ssrc and ssrc.startswith("borrowed"):
            ssrc = None
    cnt = fz.get("count")
    if not isinstance(cnt, int):
        if cnt is not None:
            notes.append(f"v0.1 の本数の欄: {cnt}")
            rep_unknown.append(f"{aid}: ねじの本数が不明（{cnt}）")
        cnt = None
    out = {"size": size, "count": cnt}
    if fz.get("thread"):
        out["thread"] = fz["thread"]
    if fz.get("nuts"):
        out["nuts"] = F({"size": fz["nuts"].get("size"), "count": fz["nuts"].get("count")})
    out["size_source"] = ssrc
    if fz.get("notes"):
        notes.append(str(fz["notes"]))
    if notes:
        out["notes"] = "；".join(notes)
    return F(out)


def _prov(v, src, **kw):
    d = {"v": v, "src": src if v is not None else None}
    d.update({k: x for k, x in kw.items() if x is not None})
    return F(d)


def _conv_atomic(a, step, robot, step_variant, rep):
    aid = a["id"]
    typ = a.get("type") or "unknown"
    if typ not in TYPES:
        rep["unknowns"].append(f"{aid}: 型 {typ} は v0.2 にない → unknown")
        typ = "unknown"
    text = str(step.get("text") or "")
    tl = text.lower()
    notes = str(a.get("notes") or "")
    attrs = CommentedMap()
    if a.get("flips") is not None:
        attrs["flips"] = _prov(a["flips"], "stated")
    attrs["force"] = _prov(a.get("force"), "annotator")
    flex = a.get("flexible")
    if flex in ("yes", True):
        if typ in ("CBL", "CON"):
            attrs["deformable"] = _prov("yes", "annotator")
        else:
            attrs["deformable"] = _prov("no", "annotator")
            attrs["attached_flexible"] = _prov("yes", "annotator", note="v0.1 の flexible: yes（線が付いた剛体として変換）")
            rep["heuristics"].append(f"{aid}: flexible: yes を attached_flexible に（型 {typ}）")
    elif flex in ("no", False):
        attrs["deformable"] = _prov("no", "annotator")
    if typ == "HRN" and any(k in tl for k in ZERO_KW):
        attrs["zero_position"] = _prov("yes", "stated", note="本文のキーワードから変換（要確認）")
        rep["heuristics"].append(f"{aid}: zero_position: yes（本文のキーワード）")
    if a.get("visibility"):
        attrs["visibility"] = _prov(a["visibility"], "stated")
        if any(k in tl for k in JOINT_KW):
            attrs["joint_motion"] = _prov("yes", "stated", note="本文のキーワードから変換（要確認）")
            rep["heuristics"].append(f"{aid}: joint_motion: yes（本文のキーワード）")
    attrs["access_clearance"] = _prov(None, None)
    attrs["n_held_parts"] = _prov(None, None)
    attrs["min_part_mm"] = _prov(a.get("min_part_mm"), "annotator",
                                 note="v0.1 の値（v0.1 は軸が未定義。v0.2 は最長辺）" if a.get("min_part_mm") is not None else None)
    th = a.get("two_hands")
    if th in ("yes", "no"):
        attrs["two_hands_v01"] = _prov(th, "annotator", note="v0.1 の推論。hold_needed は sim (c) で決める（taxonomy §9.3）")
    # 工具
    t01 = a.get("tool") or {}
    if t01.get("stated"):
        tool = _prov(t01["stated"], "stated")
        tool_v, tool_src = t01["stated"], "stated"
    elif t01.get("inferred"):
        tool = _prov(t01["inferred"], "rule")
        tool_v, tool_src = t01["inferred"], "rule"
    else:
        tool = _prov("none", "rule")
        tool_v, tool_src = None, "rule"
    scope = SCOPE_OF_TYPE.get(typ, "assembly")
    # 可否ラベル（taxonomy §10.1 の軸）
    label = CommentedMap()
    label["tool_required"] = _tool_axis(tool_v, tool_src) if scope == "assembly" else _prov(None, None)
    label["tool_access"] = F({"v": "not_checked", "src": None})
    label["hold_needed"] = F({"v": "unknown", "src": None})
    label["fixture_required"] = F({"v": "unknown", "src": None})
    label["geometric_screen"] = _prov("not_applicable", "rule") if scope != "assembly" else _prov(None, None)
    if typ in EVAL_SUPPORTED:
        label["evaluator_support"] = _prov("supported", "rule")
    elif typ in EVAL_UNSUPPORTED:
        label["evaluator_support"] = _prov("unsupported", "rule")
    else:
        label["evaluator_support"] = _prov(None, None)
    if typ == "CBL":
        label["human_required"] = _prov("yes", "rule", reason="flexible")
    elif scope != "assembly":
        label["human_required"] = _prov(None, None)
    else:
        label["human_required"] = F({"v": "unknown", "src": None})
    label["execution_outcome"] = F({"v": "not_run", "src": None})
    label["scope"] = scope
    fr = a.get("feasibility_rule")
    summ = "X" if scope == "manufacturing" else fr
    if summ == "X" and fr != "X":
        rep["heuristics"].append(f"{aid}: 旧ラベル {fr} → X（OTH は範囲外、taxonomy §9.2）")
    label["summary"] = _prov(summ, "rule", note="v0.1 の機械規則（taxonomy §10 で軸に置き換え済み。参考）")
    # 本体
    l1 = CommentedMap()
    l1["id"] = aid
    l1["l2_refs"] = FL([step["id"]])
    l1["fix_state"] = a.get("fix_state")
    l1["type"] = typ
    l1["secondary"] = FL([s for s in (a.get("secondary") or []) if s in TYPES])
    l1["from_media_only"] = typ == "unknown"
    l1["parts_in"] = FL([p if ":" in str(p) else f"{robot}:{p}" for p in a.get("parts_in") or []])
    cnt = a.get("count")
    if cnt is not None and not isinstance(cnt, int):
        rep["unknowns"].append(f"{aid}: count が不明（{cnt}）")
        notes = (notes + "；" if notes else "") + f"v0.1 の count: {cnt}"
        cnt = None
    l1["count"] = cnt
    m = re.search(r"(S\w+?[a-z])\s*の写し", notes)
    l1["template_of"] = m.group(1) if m else None
    if m:
        rep["heuristics"].append(f"{aid}: template_of: {m.group(1)}（メモの「の写し」から）")
    if step_variant:
        l1["variant"] = FL(step_variant)
    l1["fasteners"] = _conv_fasteners(a.get("fasteners"), rep["unknowns"], aid)
    l1["attrs"] = attrs
    l1["tool"] = tool
    l1["optional"] = bool("任意工程" in notes or "optional フラグ" in notes)
    if l1["optional"]:
        rep["heuristics"].append(f"{aid}: optional: true（メモから）")
    l1["source_section"] = a.get("source_section")
    l1["label"] = label
    l1["review"] = F({"status": "draft", "drafted_by": "v0.1 trial (agent)"})
    l1["notes"] = notes or None
    known = {"id", "type", "secondary", "parts_in", "fasteners", "tool", "two_hands", "flexible", "min_part_mm", "force",
             "precedes_from_text", "feasibility_rule", "notes", "fix_state", "flips", "count", "visibility", "source_section"}
    for k in a:
        if k not in known:
            rep["dropped"].append(f"{aid}: 項目 {k} は変換していない")
    if "写真頼み" in notes or "as shown" in tl or "see photo" in tl:
        rep["media_review"].append(aid)
    return l1


def _edge_kind(source, notes):
    if source == "order_only":
        return None
    if any(k in notes for k in REVERSIBLE_KW):
        return "recommended"
    if source == "geometry":
        return "unknown" if any(k in notes for k in UNCERTAIN_KW) else "required"
    return "unknown"


def convert_v01(src: dict, src_name: str = "") -> tuple[CommentedMap, dict]:
    rep = {"merged": [], "not_merged": [], "dropped": [], "unknowns": [], "heuristics": [], "edges_expanded": [],
           "edges_dropped": [], "edges_unresolved": [], "media_review": [], "kinds": {}}
    robot = src["robot"]
    out = CommentedMap()
    out["ir_version"] = "0.2"
    out["robot"] = robot
    # source
    s01 = dict(src.get("source") or {})
    source = CommentedMap()
    source["url"] = s01.pop("url", "")
    source["fetched"] = str(s01.pop("fetched")) if s01.get("fetched") else None
    source["commit"] = s01.pop("commit_or_version", None)
    source["license"] = s01.pop("license", "unknown")
    source["format"] = s01.pop("format", "numbered_markdown_photos")
    counts = CommentedMap()
    for k, k2 in (("numbered_steps", "numbered_steps"), ("unnumbered_steps", "unnumbered_steps"), ("photos", "photos"), ("videos", "videos")):
        if k in s01:
            v = s01.pop(k)
            counts[k2] = v if isinstance(v, int) else None
    source["counts"] = F(counts)
    source["manual_origin"] = "manual"
    for k, v in s01.items():
        source[k] = to_plain(v)
    out["source"] = source
    # 変種
    seen_v = []
    for row in (src.get("bom") or []):
        if row.get("variant") and row["variant"] not in seen_v:
            seen_v.append(row["variant"])
    for st in (src.get("pre_steps") or []) + (src.get("steps") or []):
        for key in ("variant", "applies_to"):
            if st.get(key) and st[key] not in seen_v:
                seen_v.append(st[key])
    tr = str(src.get("variant_transcribed") or "").replace(" ", "")
    head = tr.split("を主経路")[0] if "を主経路" in tr else ""
    vlist = CommentedSeq()
    if "leader" in seen_v and "follower" not in seen_v and "follower" in robot:
        seen_v.insert(0, "follower")
    for v in seen_v:
        vv = str(v).replace(" ", "")
        if head:
            main = vv in head and f"非{vv}" not in head
        elif vv in robot:
            main = True
        else:
            main = False if seen_v else None
        vlist.append(F({"id": v, "main": main}))
    if vlist:
        rep["heuristics"].append("variants の main: " + ", ".join(f"{x['id']}={x['main']}" for x in vlist) + "（要確認）")
    out["variants"] = vlist
    # BOM
    bom = CommentedSeq()
    for row in src.get("bom") or []:
        b = {"id": row["id"], "name": row.get("name", ""), "qty": row.get("qty")}
        if row.get("variant"):
            b["variant"] = FL([row["variant"]])
        b["kind"] = row.get("kind")
        if row.get("kind") == "included_with":
            b["included_with"] = row.get("parent")
        elif row.get("parent"):
            b["parent"] = row["parent"]
        for k in ("cad", "sim"):
            if row.get(k):
                b[k] = FL([row[k]] if isinstance(row[k], str) else row[k])
        for k in ("size", "file", "notes"):
            if row.get(k) is not None:
                b[k] = str(row[k])
        if row.get("kind") == "subassembly_external":
            m = re.search(r"([\w-]+\.yaml)", str(row.get("notes") or ""))
            b["external_ref"] = m.group(1) if m else None
        for k in row:
            if k not in {"id", "name", "qty", "variant", "kind", "parent", "cad", "sim", "size", "file", "notes"}:
                b[f"x_{k}"] = to_plain(row[k])
        if isinstance(b["qty"], str):
            rep["unknowns"].append(f"BOM {row['id']}: 数量が数でない（{b['qty']}）")
        bom.append(F(b))
    out["bom"] = bom
    # L3
    secs = CommentedSeq()
    for sa in src.get("subassemblies") or []:
        d = {"id": sa["id"], "title": sa.get("manual_section") or sa.get("name") or sa["id"]}
        if sa.get("repeat"):
            d["repeat"] = sa["repeat"]
        nt = []
        if sa.get("manual_section") and sa.get("name"):
            nt.append(f"v0.1 の名前: {sa['name']}")
        if sa.get("parent"):
            nt.append(f"v0.1 の親: {sa['parent']}（v0.2 の L3 は木にしない）")
        if sa.get("notes"):
            nt.append(str(sa["notes"]))
        if nt:
            d["notes"] = "；".join(nt)
        secs.append(F(d))
    if any(sa.get("parent") for sa in src.get("subassemblies") or []):
        rep["dropped"].append("subassemblies の parent（L3 の木）は落とした。サブアセンブリの木は CAD から別に取る（ir-design §1-2）")
    out["sections"] = secs
    # L2 と L1
    steps_in = list(src.get("pre_steps") or []) + list(src.get("steps") or [])
    l2s = CommentedSeq()
    l1s = []
    step_of = {}          # L1 id -> [step id]
    step_l1 = {}          # step id -> [L1 id]
    intra = []            # (from_ref, to_l1, step_id) precedes_from_text
    for st in steps_in:
        sid = st["id"]
        d = CommentedMap()
        d["id"] = sid
        mref = st.get("manual_ref")
        if not mref:
            m = re.match(r"^S(\d+)$", sid)
            mref = f"Step {int(m.group(1))}" if m else None
        d["manual_ref"] = mref
        d["section"] = st.get("subassembly")
        var = st.get("variant") or st.get("applies_to")
        d["variant"] = FL([var] if var else ["all"])
        d["text"] = str(st.get("text") or "")
        med = st.get("media") or {}
        media = {}
        for k, k2 in (("photo", "photos"), ("photos", "photos"), ("figure", "figures"), ("video", "video")):
            if k in med:
                media[k2] = med[k]
        d["media"] = F(media) if media else None
        if st.get("repeat"):
            d["repeat"] = st["repeat"]
        if st.get("notes"):
            d["notes"] = str(st["notes"])
        for k in ("after_text", "after_media"):
            if st.get(k) is not None:
                d[f"x_{k}"] = to_plain(st[k])
        for k in st:
            if k not in {"id", "manual_ref", "text", "media", "subassembly", "repeat", "atomic", "notes", "variant",
                         "applies_to", "after_text", "after_media"}:
                rep["dropped"].append(f"L2 {sid}: 項目 {k} は変換していない")
        l2s.append(d)
        step_l1[sid] = []
        for a in st.get("atomic") or []:
            l1 = _conv_atomic(a, st, robot, [var] if var else None, rep)
            l1s.append(l1)
            step_of[l1["id"]] = [sid]
            step_l1[sid].append(l1["id"])
            for r in a.get("precedes_from_text") or []:
                intra.append((r, l1["id"], sid))
        if not st.get("atomic"):
            rep["unknowns"].append(f"L2 {sid}: L1 がない（{str(st.get('notes') or '本文に手順がない')[:60]}）")
    out["manual_steps"] = l2s
    if "variant_transcribed" in src:
        out["x_variant_transcribed"] = str(src["variant_transcribed"])
    if "summary_counts" in src:
        rep["dropped"].append("一番上の summary_counts は変換していない（集計は validate で出し直す）")
    if "leader_only_steps_summary" in src:
        rep["dropped"].append("一番上の leader_only_steps_summary（leader 専用ステップの要約）は変換していない。leader は別の IR として起こす")

    # placed → fixed の統合（隣り合うときだけ。間に別の L1 があると閉路になる）
    alias = {}
    i = 0
    merged = []
    while i < len(l1s):
        cur = l1s[i]
        if cur.get("fix_state") == "placed":
            nxt = l1s[i + 1] if i + 1 < len(l1s) else None
            later = next((x for x in l1s[i + 1:] if x.get("fix_state") == "fixed"
                          and set(cur["parts_in"]) <= set(x["parts_in"])), None)
            if nxt is not None and later is nxt:
                f = nxt
                f["l2_refs"] = FL(list(dict.fromkeys(list(cur["l2_refs"]) + list(f["l2_refs"]))))
                sec = [s for s in [cur["type"]] + list(cur["secondary"]) + list(f["secondary"]) if s != f["type"]]
                f["secondary"] = FL(list(dict.fromkeys(sec)))
                f["parts_in"] = FL(list(dict.fromkeys(list(f["parts_in"]) + list(cur["parts_in"]))))
                for k, pv in cur["attrs"].items():
                    if k not in f["attrs"] or f["attrs"][k].get("v") is None:
                        f["attrs"][k] = pv
                if cur["label"]["summary"]["v"] != f["label"]["summary"]["v"]:
                    f["label"]["summary"]["note"] = (f["label"]["summary"].get("note") or "") + \
                        f"（統合前: {cur['id']}={cur['label']['summary']['v']}）"
                f["notes"] = "；".join(x for x in [f"{cur['id']}（placed）と統合", cur.get("notes"), f.get("notes")] if x)
                alias[cur["id"]] = f["id"]
                step_of[f["id"]] = list(dict.fromkeys(step_of[cur["id"]] + step_of[f["id"]]))
                for sid in step_of[cur["id"]]:
                    step_l1[sid] = [f["id"] if x == cur["id"] else x for x in step_l1[sid]]
                rep["merged"].append(f"{cur['id']} + {f['id']} → {f['id']}（l2_refs {list(f['l2_refs'])}）")
                i += 1
                continue
            if later is not None:
                rep["not_merged"].append(f"{cur['id']}（placed）と {later['id']}（fixed）: 間に別の L1 があるので統合しない")
            else:
                rep["not_merged"].append(f"{cur['id']}（placed）: 対応する fixed の L1 がない")
        merged.append(cur)
        i += 1
    l1s = merged
    for sid in step_l1:
        step_l1[sid] = list(dict.fromkeys(step_l1[sid]))
    l1_ids = [x["id"] for x in l1s]
    for x in l1s:
        if x["template_of"] in alias:
            x["template_of"] = alias[x["template_of"]]
    out["atomic"] = CommentedSeq(l1s)

    def A(x):
        return alias.get(x, x)

    # ステップ内の先行（L1 → L1）
    intra_pairs = set()
    for r, t, sid in intra:
        if A(r) in step_l1.get(sid, []):
            intra_pairs.add((A(r), A(t)))

    def ends(sid, role):
        ids = step_l1.get(sid, [])
        if role == "from":
            return [x for x in ids if not any((x, y) in intra_pairs for y in ids)]
        return [x for x in ids if not any((y, x) in intra_pairs for y in ids)]

    def resolve(ref, role):
        if A(ref) in l1_ids:
            return [A(ref)], False
        if ref in step_l1:
            e = ends(ref, role)
            return e, len(step_l1[ref]) > 1
        return [], False

    edges = CommentedSeq()
    have = set()
    for e in src.get("precedence_dag") or []:
        f, t, source, nt = e["from"], e["to"], e.get("source", "unknown"), str(e.get("notes") or "")
        fs, fx = resolve(f, "from")
        ts, tx = resolve(t, "to")
        if not fs or not ts:
            rep["edges_unresolved"].append(f"{f}->{t}")
            continue
        kind = _edge_kind(source, nt)
        multi = (fx or tx) and len(fs) * len(ts) > 1
        if multi and kind == "required":
            kind = "unknown"   # L2 の必須を L1 の組に広げると、必須でない組まで required になる
            rep["heuristics"].append(f"{f}->{t}: required を L1 の {len(fs) * len(ts)} 組に展開したので unknown に下げた")
        for fi in fs:
            for ti in ts:
                if fi == ti:
                    rep["edges_dropped"].append(f"{f}->{t}（統合で同じ L1 になった）")
                    continue
                if (fi, ti) in have:
                    continue
                have.add((fi, ti))
                notes = nt
                if fx or tx:
                    notes = (nt + "｜" if nt else "") + f"L2 の辺 {f}->{t} を L1 に展開"
                edges.append(F({"from": fi, "to": ti, "kind": kind, "source": source, "src": "annotator",
                                "notes": notes or None}))
                rep["kinds"][kind or "null(order_only)"] = rep["kinds"].get(kind or "null(order_only)", 0) + 1
        if (fx or tx) and len(fs) * len(ts) > 1:
            rep["edges_expanded"].append(f"{f}->{t} → {len(fs) * len(ts)} 本")
    for r, t, sid in intra:
        fs, _ = resolve(r, "from")
        if not fs:
            rep["edges_unresolved"].append(f"precedes_from_text {r}->{t}")
            continue
        for fi in fs:
            ti = A(t)
            if fi == ti or (fi, ti) in have:
                continue
            have.add((fi, ti))
            edges.append(F({"from": fi, "to": ti, "kind": "unknown", "source": "unknown", "src": "annotator",
                            "notes": "v0.1 の precedes_from_text から（出所は未判定）"}))
            rep["kinds"]["unknown(precedes_from_text)"] = rep["kinds"].get("unknown(precedes_from_text)", 0) + 1
    out["precedence"] = edges
    out["annotation"] = CommentedMap({"drafted_by": "v0.1 trial (agent)", "converted_from": src_name,
                                      "converted_at": now(), "annotators": FL([])})
    return out, rep


def conversion_report_md(name: str, doc, rep: dict, vrep: Report) -> str:
    L = [f"## {name}", "", f"- {summary_line(doc)}".replace("\n  ", "\n- "),
         f"- validate: エラー {len(vrep.errors)} 件・注意 {len(vrep.warnings)} 件",
         f"- 辺の kind（変換の推定）: " + ", ".join(f"{k} {v}" for k, v in sorted(rep["kinds"].items()))]

    def sect(title, items, limit=40):
        if not items:
            return
        L.append("")
        L.append(f"### {title}（{len(items)}）")
        for x in items[:limit]:
            L.append(f"- {x}")
        if len(items) > limit:
            L.append(f"- …ほか {len(items) - limit} 件")
    sect("placed → fixed を 1 つの L1 に統合", rep["merged"])
    sect("統合しなかった placed", rep["not_merged"])
    sect("値が不明で null にしたもの", rep["unknowns"])
    sect("推定で埋めたもの（要確認）", rep["heuristics"])
    sect("L2 の辺を L1 に展開したもの", rep["edges_expanded"])
    sect("落とした辺", rep["edges_dropped"])
    sect("解決できなかった辺", rep["edges_unresolved"])
    sect("写真を見ないと決まらない L1（from_media_only の候補）", rep["media_review"])
    sect("変換していない項目", rep["dropped"])
    if vrep.errors:
        sect("validate のエラー", [m for _, m in vrep.errors])
    return "\n".join(L) + "\n"


def cmd_convert(a):
    src = to_plain(load_yaml(a.file))
    doc, rep = convert_v01(src, str(a.file))
    dump_yaml(doc, a.out)
    vrep = validate(load_yaml(a.out))
    md = conversion_report_md(Path(a.file).name, doc, rep, vrep)
    if a.report:
        Path(a.report).write_text(md)
    print(md)
    print(f"→ {a.out}")


# ---------------------------------------------------------------- draft
RULES_MD = """# 注釈の規則（要約。正本は projects/<p>/notes/taxonomy-draft と ir-design）

## 単位
- L1（原子工程）が主の単位。L2（手順書のステップ）・L3（手順書の節）は索引で、L1 から l2_refs（多対多）で指す
- L1 は「部品 1 つが固定されるごと」。同じ部品の「置く」→「締める」が 2 つの L2 にまたがるなら 1 つの L1 にし、
  l2_refs に両方、fix_state: fixed、type は締める側（SCR など）、secondary に置く側（INS）
- CBL（配線）は経路 1 本ごと、CON（コネクタ）は接続 1 つごと
- 同じ動作の繰り返し（ねじ ×4、モジュール ×3）は count / repeat で持つ。「同じことをもう一度」は template_of で元の L1 を指す
- 本文が「as shown」だけで型が決まらない L1 は type: unknown、from_media_only: true
- 番号ステップの外の本文から拾った L1 は source_section に節の名前を書く

## 型（type）
INS 挿入（すきまあり）／PRS 圧入（本文に tight fit・push・press）／SNP スナップ／SCR ねじ締結（ホーンを別部品にねじ止めも SCR）／
HRN ホーンをスプラインにはめる工程だけ／CBL 配線・ケーブル通し／CON コネクタの接続／ADH 接着・テープ・結束／
ALN 位置決め・調整／SW ソフト／INSP 検査／OTH 製造（3D 印刷・サポート除去。可否の対象外 scope: manufacturing）／unknown

## 属性（attrs）。すべて {v, src}
flips（向きの反転の回数。本文から）・force（low/medium/high）・deformable（部品自体が柔らかい）・attached_flexible（線の付いた剛体）・
zero_position（原点を動かさない指示）・joint_motion（組立中に関節を動かして穴を出す）・access_clearance・n_held_parts（sim で埋める。空欄でよい）・
min_part_mm（最小部品の最長辺）。**両手が要るかを人の推論で埋めない**（sim の hold_needed で決める）

## 可否の軸（label）。すべて {v, src, reason}
tool_required: none/screwdriver/hex/pliers/other/unknown（接合の種類からの規則 src: rule、手順書の明記 src: stated）
tool_access: ok/blocked/not_checked（sim）　hold_needed: 0/1/2+/unknown（sim）
fixture_required: no/yes/unknown（hold_needed が 2+ か向きを変えないと届かないときだけ yes）
geometric_screen: pass/fail/not_applicable/uncertain（sim）
evaluator_support: INS・HRN・SCR は supported、PRS・SNP・CON・CBL・ADH・ALN は unsupported（src: rule）
human_required: yes は独立の根拠（手順書が人の判断を明記、柔軟物の経路づけ）があるときだけ。評価器が扱えないだけなら unknown
execution_outcome: not_run（下書きでは常に）
scope: assembly / software / inspect / manufacturing

## 出所（src）
stated=手順書の本文、cad / bom=CAD・部品表、rule=型などからの規則、sim、borrowed:<robot>=他機種から借用、annotator=人の推論。
**本文に書いていないことを stated にしない。** 分からない値は v: null（または unknown）にして src: null。

## 先行関係（precedence）。L1 の ID で書く
kind: required（幾何で必須）/ recommended（本文が勧める可逆な順）/ unknown
source: text_explicit（after・then・already）/ text_anaphora（定冠詞・指示語で前の成果物を指す）/ geometry / order_only（本文の並びだけ。kind は null）
本文の語順が幾何と逆のことがある（括弧書きの作業が先、ナットがボルトの前）。order_only を required にしない。
"""

SYSTEM_PROMPT = ("あなたはロボットの組立手順書から、工程の正解データ（中間表現 IR v0.2）の下書きを作る注釈者です。"
                 "人が後で全件を確認します。推測で値を埋めず、本文にないことは null か unknown にして、出所（src）を正直に書いてください。")


def _norm_name(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def evaluated_models(proj: Path) -> list[str]:
    """評価する言語モデルの一覧。research.yaml の protocol.evaluated_models、なければ plan.md の「言語モデルは」の行。"""
    led = load_yaml(proj / "research.yaml") or {}
    em = (led.get("protocol") or {}).get("evaluated_models") or led.get("evaluated_models")
    if em:
        return [str(x) for x in em]
    plan = proj / "plan.md"
    if not plan.exists():
        return []
    out = []
    for line in plan.read_text().splitlines():
        if "言語モデルは" not in line:
            continue
        depth, start, seg = 0, None, ""
        for i, ch in enumerate(line):
            if ch in "（(":
                depth += 1
            elif ch in "）)":
                depth -= 1
            elif depth == 0 and ch in "：:" and start is None:
                start = i + 1
            elif depth == 0 and ch == "。" and start is not None:
                seg = line[start:i]
                break
        if start is not None and not seg:
            seg = line[start:]
        depth, cur, parts = 0, "", []
        for ch in seg:
            if ch in "（(":
                depth += 1
            elif ch in "）)":
                depth -= 1
            if depth == 0 and ch in "、,":
                parts.append(cur)
                cur = ""
            else:
                cur += ch
        parts.append(cur)
        for p in parts:
            name = re.split(r"[（(]", p)[0].strip(" *")
            if name:
                out.append(name)
            out += re.findall(r"`([^`]+)`", p)
        if out:
            break
    return out


def model_conflict(model: str, evaluated: list[str]) -> str | None:
    m = _norm_model(model)
    for e in evaluated:
        n = _norm_model(e)
        if n and (m == n or m.startswith(n) or n.startswith(m)):
            return e
    return None


def test_robots(proj: Path) -> list[str]:
    led = load_yaml(proj / "research.yaml") or {}
    ts = (led.get("protocol") or {}).get("test_robots") or (led.get("protocol") or {}).get("test_split")
    if isinstance(ts, list) and ts:
        return [str(x) for x in ts]
    if isinstance(ts, str) and ts.strip():
        return [x.strip() for x in re.split(r"[,、]", ts) if x.strip()]
    plan = proj / "plan.md"
    out = []
    if plan.exists():
        for line in plan.read_text().splitlines():
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= 2 and cells[0] == "テスト":
                out.append(cells[1])
    return out


def is_test_robot(robot: str, tests: list[str]) -> str | None:
    r = _norm_name(robot)
    for t in tests:
        n = _norm_name(t)
        if r and n and (r == n or n.startswith(r) or r.startswith(n)):
            return t
    return None


def _excerpt(path: Path, start_pat: str, end_pat: str | None = None) -> str:
    if not path.exists():
        return ""
    txt = path.read_text()
    m = re.search(start_pat, txt, re.M)
    if not m:
        return ""
    rest = txt[m.start():]
    if end_pat:
        m2 = re.search(end_pat, rest[1:], re.M)
        if m2:
            rest = rest[:m2.start() + 1]
    return rest


def _sha(path_or_text) -> str:
    b = path_or_text.encode() if isinstance(path_or_text, str) else Path(path_or_text).read_bytes()
    return hashlib.sha256(b).hexdigest()


def build_prompt(robot: str, manual_text: str, bom_text: str, rules: str, project_rules: str) -> str:
    return f"""{SYSTEM_PROMPT}

# 作業
機種 `{robot}` の組立手順書（下の「手順書」）から、IR v0.2 の YAML を 1 つ書いてください。
- 一番上: ir_version: "0.2", robot: {robot}, source, variants, bom, sections, manual_steps, atomic, precedence
- 部品は `{robot}:<BOM の ID>` で書く。部品表にない部品は bom に行を足し、notes に「手順書だけに出る」と書く
- 各 L1 に review: {{status: draft}} を付ける
- 出力は ```yaml で囲んだ YAML だけ。説明の文は書かない

# 規則
{rules}

# プロジェクトの分類体系（抜粋。上の規則と食い違うときはこちらが正しい）
{project_rules or "（なし）"}

# スキーマ
同じフォルダの schema.json（JSON Schema）に従うこと。

# 部品表
{bom_text or "（なし。手順書から部品表を起こす）"}

# 手順書
{manual_text}
"""


def _extract_yaml(text: str) -> str:
    m = re.search(r"```ya?ml\s*\n(.*?)```", text, re.S)
    return m.group(1) if m else text


def resolved_model_names(llm, model: str) -> list[str]:
    """登録簿で解決した名前と model_id（会社名 anthropic が評価対象のモデルに解決されることがある）。"""
    out = [model]
    if hasattr(llm, "resolve_model") and hasattr(llm, "load_registry"):
        try:
            key, cfg = llm.resolve_model(model, llm.load_registry())
            out += [key, str(cfg.get("model_id") or ""), str(cfg.get("label") or "")]
        except Exception as e:  # noqa: BLE001
            die(f"下書きのモデル {model} が登録簿で解決できない: {e}")
    return [x for x in out if x]


def _call_llm(llm, prompt: str, model: str, proj: Path, meta: dict):
    """rlkit.llm.call(model, messages, *, system, max_tokens, budget_project, meta) -> Result。
    形の違う版でも動くよう、受け取る引数だけを渡す。返り値は (text, 実際のモデル名の並び, 費用)。"""
    fn = getattr(llm, "call")
    params = inspect.signature(fn).parameters
    cand = {"model": model, "messages": prompt, "prompt": prompt, "system": SYSTEM_PROMPT, "max_tokens": 64000,
            "budget_project": str(proj), "project": str(proj), "meta": meta}
    kw = {k: v for k, v in cand.items() if k in params}
    if "messages" in kw and "prompt" in kw:
        del kw["prompt"]
    res = fn(**kw)
    if isinstance(res, str):
        return res, [], None
    if isinstance(res, dict):
        return res.get("text") or "", [res.get("model_id"), res.get("model_returned")], res.get("cost_usd")
    if getattr(res, "refused", False):
        die(f"下書きのモデルが拒否した（{getattr(res, 'refusal', None)}）。別のモデルに勝手に切り替えない")
    if getattr(res, "error", None):
        die(f"呼び出しに失敗した: {res.error}")
    names = [getattr(res, "model_id", None), getattr(res, "model_returned", None)]
    return getattr(res, "text", "") or "", [x for x in names if x], getattr(res, "cost_usd", None)


def cmd_draft(a):
    proj = resolve_project(a.project)
    led = load_yaml(proj / "research.yaml") or {}
    g2 = bool(((led.get("gates") or {}).get("G2") or {}).get("approved"))
    hit = is_test_robot(a.robot, test_robots(proj))
    if hit and not g2 and not a.dry_run_schema:
        die(f"{a.robot} はテストの機種（{hit}）。G2 の承認前にテスト機種の正解を作らない。"
            "スキーマの確かめだけなら --dry-run-schema（正解には使わない印が付く）")
    evaluated = a.evaluated or evaluated_models(proj)
    if a.model:
        c = model_conflict(a.model, evaluated)
        if c:
            die(f"下書きのモデル {a.model} は評価する言語モデル（{c}）と同じ系統。正解が評価対象に寄るので使わない。評価対象: {evaluated}")
    if a.call and not a.model:
        die("--call には --model が要る（下書きのモデルを記録するため）")
    if a.call and not evaluated:
        die("評価する言語モデルの一覧が見つからない（research.yaml の protocol.evaluated_models か plan.md）。--evaluated で渡す")
    manual = Path(a.manual)
    if manual.suffix.lower() == ".pdf":
        die("PDF はテキストにしてから渡す（例: pdftotext -layout manual.pdf manual.txt）。図だけのページは VLM か人が起こす")
    manual_text = manual.read_text()
    bom_text = Path(a.bom).read_text() if a.bom else ""
    project_rules = _excerpt(proj / "notes" / "taxonomy-draft-2026-11-09.md", r"^## 9\.")
    project_rules += "\n" + _excerpt(proj / "notes" / "ir-design-2026-11-09.md", r"^## 2\.", r"^## 3\.")
    out = Path(a.out)
    pkg = out.with_name(out.stem + ".prompt")
    pkg.mkdir(parents=True, exist_ok=True)
    prompt = build_prompt(a.robot, manual_text, bom_text, RULES_MD, project_rules.strip())
    (pkg / "prompt.md").write_text(prompt)
    (pkg / "rules.md").write_text(RULES_MD + "\n\n" + project_rules)
    shutil.copy(SCHEMA_PATH, pkg / "schema.json")
    shutil.copy(manual, pkg / ("manual" + manual.suffix))
    if a.bom:
        shutil.copy(a.bom, pkg / ("bom" + Path(a.bom).suffix))
    nc = bool(a.license and "NC" in a.license.upper())
    meta = {"project": str(proj), "robot": a.robot, "created": now(), "model": a.model, "evaluated_models": evaluated,
            "g2_approved": g2, "test_robot": hit, "dry_run_schema": bool(a.dry_run_schema), "license": a.license,
            "redistribution": "restricted" if nc else None,
            "sha256": {"manual": _sha(manual), "bom": _sha(a.bom) if a.bom else None, "prompt": _sha(prompt),
                       "schema": _sha(SCHEMA_PATH)}}
    (pkg / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    print(f"プロンプトの包み: {pkg}/（prompt.md・rules.md・schema.json・manual・meta.json）")
    if nc:
        print("注意: NC ライセンスのデータ。注釈は外に出さないか、同じ条件で出す（source.redistribution: restricted）")
    if not a.call:
        print("--call を付けずに実行した。LLM には prompt.md を渡し、返った YAML を "
              f"{out} に保存してから `rl annotate validate {out}` を回す")
        return
    try:
        from rlkit import llm  # 別のエージェントが作っている共通の呼び出し口
    except ImportError:
        print("rlkit.llm が見つからないので、プロンプトの包みだけを書いた（費用はかかっていない）")
        return
    for name in resolved_model_names(llm, a.model):
        c = model_conflict(name, evaluated)
        if c:
            die(f"下書きのモデル {a.model} は登録簿で {name} に解決され、評価する言語モデル（{c}）と同じ系統。使わない")
    text, actual, cost = _call_llm(llm, prompt, a.model, proj,
                                   {"purpose": "annotate-draft", "robot": a.robot, "dry_run_schema": bool(a.dry_run_schema)})
    (pkg / "response.md").write_text(text)
    for name in actual:
        c = model_conflict(name, evaluated)
        if c:
            die(f"応答のモデル {name} が評価対象（{c}）と同じ系統だった。下書きを書き出さない（{pkg / 'response.md'} に控え）")
    if cost is not None:
        print(f"費用: ${cost:.4f}")
    try:
        doc = yaml.load(_extract_yaml(text))
    except Exception as e:  # noqa: BLE001
        die(f"返答の YAML が読めない（{e}）。{pkg / 'response.md'} を見る")
    if not isinstance(doc, dict):
        die(f"返答の YAML の一番上が対応になっていない。{pkg / 'response.md'} を見る")
    doc["ir_version"] = "0.2"
    doc["robot"] = a.robot
    ann = doc.get("annotation") or CommentedMap()
    ann["drafted_by"] = a.model
    if actual:
        ann["drafted_model_id"] = actual[0]
    ann["drafted_at"] = now()
    ann["dry_run_schema"] = bool(a.dry_run_schema)
    doc["annotation"] = ann
    if nc and isinstance(doc.get("source"), dict):
        doc["source"]["redistribution"] = "restricted"
    for l1 in doc.get("atomic") or []:
        if isinstance(l1, dict):
            l1["review"] = F({"status": "draft", "drafted_by": a.model})
    dump_yaml(doc, out)
    rep = validate(doc)
    print(f"下書き: {out}（モデル {a.model}）")
    print_report(rep)


# ---------------------------------------------------------------- review / apply
def enc(v) -> str:
    v = to_plain(v)
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    return json.dumps(v, ensure_ascii=False)


def dec(s: str):
    s = (s or "").strip()
    if s == "" or s.lower() == "null":
        return None
    if s[0] in "[{\"" or s in ("true", "false") or re.fullmatch(r"-?\d+(\.\d+)?", s):
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            return s
    return s


def l1_fields(l1) -> list[str]:
    fs = list(PLAIN_FIELDS) + ["tool"]
    keys = list(STANDARD_ATTRS) + [k for k in (l1.get("attrs") or {}) if k not in STANDARD_ATTRS]
    fs += [f"attrs.{k}" for k in keys]
    fs += [f"label.{ax}" for ax in AXES] + ["label.scope"]
    return fs


def get_field(l1, field):
    """(値, 出所, reason, 出所つきか)"""
    if field in PLAIN_FIELDS:
        return l1.get(field), None, None, False
    if field == "label.scope":
        return (l1.get("label") or {}).get("scope"), None, None, False
    if field == "tool":
        pv = l1.get("tool")
    else:
        top, key = field.split(".", 1)
        pv = (l1.get(top) or {}).get(key)
    if pv is None:
        return None, None, None, True
    return pv.get("v"), pv.get("src"), pv.get("reason"), True


def set_field(l1, field, value, src):
    if field in PLAIN_FIELDS:
        if field in ("secondary", "parts_in") and isinstance(value, list):
            value = FL(value)
        elif field == "fasteners" and isinstance(value, dict):
            value = F(value)
        l1[field] = value
        return
    if field == "label.scope":
        l1.setdefault("label", CommentedMap())["scope"] = value
        return
    if field == "tool":
        holder, key = l1, "tool"
    else:
        top, key = field.split(".", 1)
        if l1.get(top) is None:
            l1[top] = CommentedMap()
        holder = l1[top]
    old = holder.get(key)
    new = F({"v": value, "src": src if value is not None else None})
    if isinstance(old, dict):
        for k in ("reason", "note"):
            if old.get(k) is not None:
                new[k] = old[k]
    holder[key] = new


SHEET_COLS = ["robot", "l1_id", "l2_refs", "l2_text", "field", "draft_value", "draft_src", "draft_reason",
              "decision", "new_value", "new_src", "reason", "reviewer"]
DECISIONS = {"ok": "ok", "accept": "ok", "可": "ok", "承認": "ok", "change": "change", "変更": "change",
             "delete": "delete", "削除": "delete", "add": "add", "追加": "add"}


def cmd_review(a):
    doc = load_yaml(a.file)
    robot = doc.get("robot")
    l2text = {s.get("id"): str(s.get("text") or "") for s in doc.get("manual_steps") or []}
    rows = []
    for l1 in doc.get("atomic") or []:
        st = (l1.get("review") or {}).get("status")
        if st == "reviewed" and not a.all:
            continue
        refs = list(l1.get("l2_refs") or [])
        txt = " / ".join(l2text.get(r, "") for r in refs)[:200]
        for f in l1_fields(l1):
            v, s, r, _ = get_field(l1, f)
            rows.append({"robot": robot, "l1_id": l1.get("id"), "l2_refs": " ".join(refs), "l2_text": txt, "field": f,
                         "draft_value": enc(v), "draft_src": enc(s), "draft_reason": enc(r)})
    for e in doc.get("precedence") or []:
        if (e.get("review") or {}).get("status") == "reviewed" and not a.all:
            continue
        rows.append({"robot": robot, "l1_id": "edge", "l2_refs": "", "l2_text": str(e.get("notes") or "")[:200],
                     "field": f"precedence:{e.get('from')}->{e.get('to')}", "draft_value": enc(e.get("kind")),
                     "draft_src": enc(e.get("source")), "draft_reason": ""})
    with open(a.sheet, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=SHEET_COLS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in SHEET_COLS})
    print(f"確認シート: {a.sheet}（{len(rows)} 行）")
    print("decision に ok / change / delete（辺だけ）/ add（辺を足す行）を書く。change は new_value と reason が要る。"
          "出所つきの項目は new_src を空にすると annotator になる。辺の new_value は kind、new_src は source（4 値）")


def cmd_apply(a):
    path = Path(a.file)
    doc = load_yaml(path)
    by_id = {l1.get("id"): l1 for l1 in doc.get("atomic") or []}
    edges = doc.get("precedence")
    if edges is None:
        edges = doc["precedence"] = CommentedSeq()
    edge_ix = {(e.get("from"), e.get("to")): e for e in edges}
    with open(a.sheet, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    who = a.reviewer
    at = now()
    problems, conflicts = [], []
    decided, total = {}, {}
    n = {"ok": 0, "change": 0, "delete": 0, "add": 0, "pending": 0}
    removed = []
    for i, r in enumerate(rows, start=2):
        dcs_raw = (r.get("decision") or "").strip().lower()
        dcs = DECISIONS.get(dcs_raw, DECISIONS.get((r.get("decision") or "").strip()))
        field = r.get("field") or ""
        rid = r.get("l1_id")
        by = (r.get("reviewer") or who or "annotator").strip()
        reason = (r.get("reason") or "").strip()
        if not field.startswith("precedence:"):
            total[rid] = total.get(rid, 0) + 1
        if not dcs_raw:
            n["pending"] += 1
            continue
        if dcs is None:
            problems.append(f"{i} 行目: decision {r.get('decision')!r} が分からない（ok / change / delete / add）")
            continue
        if dcs in ("change", "delete", "add") and not reason:
            problems.append(f"{i} 行目（{rid} {field}）: {dcs} には reason が要る（規則の改訂に使う）")
            continue
        if field.startswith("precedence:"):
            m = re.match(r"precedence:(.+?)->(.+)$", field)
            if not m:
                problems.append(f"{i} 行目: field {field!r} の形が違う（precedence:FROM->TO）")
                continue
            key = (m.group(1), m.group(2))
            e = edge_ix.get(key)
            if dcs == "add":
                if e is not None:
                    problems.append(f"{i} 行目: 辺 {key} はすでにある（change を使う）")
                    continue
                kind = dec(r.get("new_value"))
                ne = F({"from": key[0], "to": key[1], "kind": kind, "source": (r.get("new_src") or "unknown").strip(),
                        "src": "annotator", "review": F({"status": "reviewed", "reviewed_by": by, "reviewed_at": at}),
                        "notes": f"確認で追加: {reason}"})
                edges.append(ne)
                edge_ix[key] = ne
                n["add"] += 1
                continue
            if e is None:
                problems.append(f"{i} 行目: 辺 {key} がファイルにない")
                continue
            if enc(e.get("kind")) != (r.get("draft_value") or ""):
                conflicts.append(f"{i} 行目: 辺 {key} の kind がシートを作った後に変わっている")
                continue
            if dcs == "delete":
                removed.append(F({"from": key[0], "to": key[1], "kind": e.get("kind"), "source": e.get("source"),
                                  "reason": reason, "by": by, "at": at}))
                edges.remove(e)
                del edge_ix[key]
                n["delete"] += 1
                continue
            rv = CommentedMap({"status": "reviewed", "reviewed_by": by, "reviewed_at": at})
            if dcs == "change":
                new_kind = dec(r.get("new_value"))
                new_src = (r.get("new_src") or "").strip() or e.get("source")
                rv["changes"] = [F({"field": "kind/source", "from": f"{e.get('kind')}/{e.get('source')}",
                                    "to": f"{new_kind}/{new_src}", "reason": reason, "by": by, "at": at})]
                e["kind"] = new_kind
                e["source"] = new_src
                e["src"] = "annotator"
                n["change"] += 1
            else:
                n["ok"] += 1
            e["review"] = rv
            continue
        l1 = by_id.get(rid)
        if l1 is None:
            problems.append(f"{i} 行目: L1 {rid} がファイルにない")
            continue
        cur, _, _, is_prov = get_field(l1, field)
        if enc(cur) != (r.get("draft_value") or ""):
            conflicts.append(f"{i} 行目（{rid} {field}）: シートの draft_value {r.get('draft_value')!r} と"
                             f"いまの値 {enc(cur)!r} が違う（シートを作った後にファイルが変わった）")
            continue
        if dcs == "change":
            new = dec(r.get("new_value"))
            src = ((r.get("new_src") or "").strip() or "annotator") if is_prov else None
            set_field(l1, field, new, src)
            rv = l1.get("review")
            if rv is None or rv.fa.flow_style():
                rv = l1["review"] = CommentedMap(rv or {})   # 変更の記録が付くので 1 行でなく段落で書く
            if rv.get("changes") is None:
                rv["changes"] = CommentedSeq()
            rv["changes"].append(F({"field": field, "from": to_plain(cur), "to": to_plain(new), "reason": reason,
                                    "by": by, "at": at}))
            n["change"] += 1
        elif dcs in ("delete", "add"):
            problems.append(f"{i} 行目（{rid} {field}）: {dcs} は辺の行だけで使える")
            continue
        else:
            n["ok"] += 1
        decided[rid] = decided.get(rid, 0) + 1
    if problems or conflicts:
        for m in conflicts + problems:
            print(f"  - {m}")
        die(f"シートに問題が {len(problems) + len(conflicts)} 件あるので、何も書き換えていない")
    n_rev = 0
    partial = []
    for rid, tot in total.items():
        l1 = by_id.get(rid)
        if l1 is None:
            continue
        if decided.get(rid, 0) == tot:
            rv = l1.get("review")
            if rv is None:
                rv = l1["review"] = CommentedMap()
            rv["status"] = "reviewed"
            rv["reviewed_by"] = who or rv.get("reviewed_by") or "annotator"
            rv["reviewed_at"] = at
            n_rev += 1
        elif decided.get(rid):
            partial.append(rid)
    ann = doc.get("annotation")
    if ann is None:
        ann = doc["annotation"] = CommentedMap()
    if ann.get("review_log") is None:
        ann["review_log"] = CommentedSeq()
    ann["review_log"].append(F({"at": at, "by": who, "sheet": str(a.sheet), **n, "l1_reviewed": n_rev}))
    if removed:
        if ann.get("removed_edges") is None:
            ann["removed_edges"] = CommentedSeq()
        ann["removed_edges"].extend(removed)
    if who:
        lst = ann.get("annotators")
        if lst is None:
            lst = ann["annotators"] = FL([])
        if who not in lst:
            lst.append(who)
    out = Path(a.out) if a.out else path
    if out == path:
        shutil.copy(path, path.with_suffix(path.suffix + ".bak"))
    dump_yaml(doc, out)
    print(f"反映: ok {n['ok']}・変更 {n['change']}・辺の削除 {n['delete']}・辺の追加 {n['add']}・未決 {n['pending']}"
          f" → 確認済みの L1 {n_rev}（途中 {len(partial)}）")
    print(f"→ {out}" + ("（元は .bak に）" if out == path else ""))
    rep = validate(load_yaml(out))
    print_report(rep)
    if rep.errors:
        sys.exit(1)


# ---------------------------------------------------------------- sample
def stratified_sample(doc, frac: float, seed: int) -> tuple[list[str], dict]:
    l1s = [x for x in doc.get("atomic") or [] if (x.get("review") or {}).get("status") != "blank"]
    strata = {}
    for x in l1s:
        strata.setdefault(str(x.get("type")), []).append(x.get("id"))
    N = len(l1s)
    target = max(1, round(frac * N)) if N else 0
    quota = {t: frac * len(v) for t, v in strata.items()}
    alloc = {t: int(q) for t, q in quota.items()}
    if target >= len(strata):
        for t in strata:
            alloc[t] = max(1, alloc[t])
    rest = target - sum(alloc.values())
    order = sorted(strata, key=lambda t: (-(quota[t] - int(quota[t])), t))
    k = 0
    while rest > 0 and order:
        t = order[k % len(order)]
        if alloc[t] < len(strata[t]):
            alloc[t] += 1
            rest -= 1
        k += 1
        if k > 10 * len(order) + target:
            break
    while rest < 0:   # 各層 1 件の下限で目標を超えたら、多い層から減らす
        t = max((t for t in alloc if alloc[t] > 1), key=lambda t: alloc[t] - quota[t], default=None)
        if t is None:
            break
        alloc[t] -= 1
        rest += 1
    rng = random.Random(seed)
    chosen = set()
    for t in sorted(strata):
        chosen.update(rng.sample(strata[t], min(alloc[t], len(strata[t]))))
    ids = [x.get("id") for x in l1s if x.get("id") in chosen]
    return ids, {t: (alloc[t], len(strata[t])) for t in sorted(strata)}


def blank_copy(doc, ids: list[str]):
    out = copy.deepcopy(doc)
    keep = set(ids)
    new = CommentedSeq()
    for l1 in out.get("atomic") or []:
        if l1.get("id") not in keep:
            continue
        b = CommentedMap()
        b["id"] = l1["id"]
        b["l2_refs"] = l1.get("l2_refs")
        b["fix_state"] = None
        b["type"] = "unknown"
        b["secondary"] = FL([])
        b["from_media_only"] = False
        b["parts_in"] = l1.get("parts_in")
        b["count"] = l1.get("count")
        if l1.get("variant"):
            b["variant"] = l1["variant"]
        b["fasteners"] = None
        b["attrs"] = CommentedMap({k: F({"v": None, "src": None}) for k in STANDARD_ATTRS})
        b["tool"] = F({"v": None, "src": None})
        lab = CommentedMap({ax: F({"v": None, "src": None}) for ax in AXES})
        lab["scope"] = "assembly"
        b["label"] = lab
        b["review"] = F({"status": "blank"})
        new.append(b)
    out["atomic"] = new
    out["precedence"] = CommentedSeq()
    ann = out.get("annotation") or CommentedMap()
    out["annotation"] = CommentedMap({"blank": True, "blank_of": ann.get("converted_from") or "",
                                      "note": "2 人目の注釈用。最初の注釈を見ずに埋め、埋めた L1 は review.status を reviewed にする。"
                                              "type の unknown・空の値は仮置き。辺は対象の L1 の間だけを書く"})
    return out


def cmd_sample(a):
    doc = load_yaml(a.file)
    ids, strata = stratified_sample(doc, a.frac, a.seed)
    head = [f"# rl annotate sample {a.file} --frac {a.frac} --seed {a.seed}",
            f"# {len(ids)} 件（型で層別: " + ", ".join(f"{t} {k}/{n}" for t, (k, n) in strata.items()) + "）"]
    text = "\n".join(head + ids) + "\n"
    if a.out:
        Path(a.out).write_text(text)
        print(f"→ {a.out}")
    print(text, end="")
    if a.blank:
        dump_yaml(blank_copy(doc, ids), a.blank)
        print(f"2 人目用の空欄のファイル → {a.blank}")


# ---------------------------------------------------------------- agree
def _rl_stats(sub: str, sub_args: list[str], payload: dict, seed: int) -> dict:
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "in.json"
        p.write_text(json.dumps(payload, ensure_ascii=False))
        cmd = [sys.executable, str(RL_STATS), "--seed", str(seed), "--json", sub, str(p)] + sub_args
        r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        return {"error": (r.stderr or r.stdout).strip()}
    return json.loads(r.stdout)


def _read_ids(path) -> list[str]:
    out = []
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            out.append(line)
    return out


def agreement(da, db, ids=None, threshold=0.6, boot=2000, seed=0, drop_unknown=False) -> dict:
    A = {x.get("id"): x for x in da.get("atomic") or []}
    B = {x.get("id"): x for x in db.get("atomic") or []}
    common = [i for i in A if i in B]
    if ids:
        sel = set(ids)
        common = [i for i in common if i in sel]
    blank = [i for i in common if (A[i].get("review") or {}).get("status") == "blank"
             or (B[i].get("review") or {}).get("status") == "blank"]
    common = [i for i in common if i not in blank]
    rows = []

    def field_row(name, va, vb, ordinal=None):
        n_all = len(va)
        pairs = [(x, y) for x, y in zip(va, vb) if x is not None and y is not None]
        row = {"field": name, "n": len(pairs), "missing": n_all - len(pairs)}
        if len(pairs) < 2:
            row["status"] = "対象なし"
            rows.append(row)
            return
        ka = _rl_stats("kappa", ["--boot", str(boot)], {"a": [p[0] for p in pairs], "b": [p[1] for p in pairs]}, seed)
        al = _rl_stats("alpha", ["--level", "nominal", "--boot", str(boot)],
                       {"data": [[p[0] for p in pairs], [p[1] for p in pairs]]}, seed)
        row.update({"p_observed": ka.get("p_observed"), "kappa": ka.get("kappa"), "ci": ka.get("ci"),
                    "alpha": al.get("alpha"), "error": ka.get("error") or al.get("error")})
        if ordinal:
            op = [(str(x), str(y)) for x, y in pairs if str(x) in ordinal and str(y) in ordinal]
            if len(op) >= 2:
                kw = _rl_stats("kappa", ["--weights", "quadratic", "--boot", str(boot), "--categories", *ordinal],
                               {"a": [p[0] for p in op], "b": [p[1] for p in op]}, seed)
                ao = _rl_stats("alpha", ["--level", "ordinal", "--boot", str(boot), "--categories", *ordinal],
                               {"data": [[p[0] for p in op], [p[1] for p in op]]}, seed)
                row.update({"kappa_quadratic": kw.get("kappa"), "alpha_ordinal": ao.get("alpha"), "n_ordinal": len(op)})
        k = row.get("kappa")
        if row.get("error"):
            row["status"] = "計算できない"
        elif k is None:
            row["status"] = "κ は定義できない（全件同じ値）"
        elif k < threshold:
            row["status"] = f"要改訂（κ<{threshold}）"
        elif row["ci"] and row["ci"][0] is not None and row["ci"][0] < threshold:
            row["status"] = f"注意（CI の下限 <{threshold}）"
        else:
            row["status"] = "OK"
        rows.append(row)

    def val(l1, f):
        v = get_field(l1, f)[0]
        if drop_unknown and v in NON_VALUES:
            return None
        return None if v is None else enc(v)

    for f in ["type", "fix_state", "label.scope"] + [f"label.{ax}" for ax in AXES]:
        ax = f.split(".", 1)[1] if f.startswith("label.") else None
        field_row(f, [val(A[i], f) for i in common], [val(B[i], f) for i in common], ORDINAL.get(ax))
    cs = set(common)

    def edge_map(d):
        out = {}
        for e in d.get("precedence") or []:
            if e.get("from") in cs and e.get("to") in cs:
                out[(e.get("from"), e.get("to"))] = e
        return out
    ea, eb = edge_map(da), edge_map(db)
    keys = sorted(set(ea) | set(eb))

    def ek(e):
        if e is None:
            return "absent"
        return "order_only" if e.get("source") == "order_only" else str(e.get("kind"))
    field_row("precedence.kind（辺の和集合）", [ek(ea.get(k)) for k in keys], [ek(eb.get(k)) for k in keys])
    both = [k for k in keys if k in ea and k in eb]
    field_row("precedence.source（両方にある辺）", [str(ea[k].get("source")) for k in both],
              [str(eb[k].get("source")) for k in both])
    return {"n_common": len(common), "n_blank_excluded": len(blank), "only_a": len([i for i in A if i not in B]),
            "only_b": len([i for i in B if i not in A]), "n_edges_union": len(keys), "threshold": threshold,
            "rows": rows}


def _f(x, nd=2):
    return "—" if x is None else f"{x:.{nd}f}"


def cmd_agree(a):
    da, db = to_plain(load_yaml(a.a)), to_plain(load_yaml(a.b))
    ids = _read_ids(a.ids) if a.ids else None
    res = agreement(da, db, ids, a.threshold, a.boot, a.seed, a.drop_unknown)
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return
    print(f"共通の L1 {res['n_common']}（空欄で除外 {res['n_blank_excluded']}、A だけ {res['only_a']}、B だけ {res['only_b']}）"
          f"・辺の和集合 {res['n_edges_union']}")
    print("| 項目 | n | 欠け | 一致率 | κ | 95% CI | α | 判定 |")
    print("|---|---|---|---|---|---|---|---|")
    for r in res["rows"]:
        ci = r.get("ci") or [None, None]
        extra = ""
        if r.get("kappa_quadratic") is not None:
            extra = f"（順序: κw {_f(r['kappa_quadratic'])}・α {_f(r.get('alpha_ordinal'))}、n={r.get('n_ordinal')}）"
        print(f"| {r['field']} | {r['n']} | {r['missing']} | {_f(r.get('p_observed'))} | {_f(r.get('kappa'))} | "
              f"[{_f(ci[0])}, {_f(ci[1])}] | {_f(r.get('alpha'))} | {r['status']}{extra} |")
    bad = [r["field"] for r in res["rows"] if r["status"].startswith("要改訂")]
    if bad:
        print(f"\nκ < {a.threshold} の項目: {', '.join(bad)} → 決め方の文を直し、直した規則で付け直してから測り直す（taxonomy §6）")
    print("統計は rl_stats.py（Cohen の κ・Krippendorff の α、項目のブートストラップ）で計算した。")


# ---------------------------------------------------------------- main
def main(argv=None):
    ap = argparse.ArgumentParser(prog="rl annotate", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("validate", help="スキーマと意味のチェック")
    p.add_argument("file")
    p.add_argument("--ref", nargs="*", help="別機種の IR（parts_in の <robot>:<id> を確かめる）")
    p.add_argument("--strict", action="store_true", help="注意もエラーとして扱う")
    p.add_argument("--verbose", action="store_true")
    p.set_defaults(fn=cmd_validate)
    p = sub.add_parser("convert-v01", help="v0.1 の試し書きを v0.2 に変換")
    p.add_argument("file"); p.add_argument("--out", required=True); p.add_argument("--report")
    p.set_defaults(fn=cmd_convert)
    p = sub.add_parser("draft", help="LLM の下書きのプロンプトの包みを作る（--call で呼ぶ）")
    p.add_argument("project"); p.add_argument("robot")
    p.add_argument("--manual", required=True); p.add_argument("--out", required=True); p.add_argument("--bom")
    p.add_argument("--model", help="下書きのモデル（評価する言語モデルと別にする）")
    p.add_argument("--call", action="store_true", help="rlkit.llm で LLM を呼ぶ（費用がかかる）")
    p.add_argument("--dry-run-schema", action="store_true", help="G2 前のテスト機種で、スキーマの確かめだけをする")
    p.add_argument("--evaluated", nargs="+", help="評価する言語モデルの一覧（plan.md から読めないとき）")
    p.add_argument("--license", help="手順書のライセンス（NC なら注釈を外に出さない印を付ける）")
    p.set_defaults(fn=cmd_draft)
    p = sub.add_parser("review", help="確認シート（CSV）を書き出す")
    p.add_argument("file"); p.add_argument("--sheet", required=True)
    p.add_argument("--all", action="store_true", help="確認済みの L1 も含める")
    p.set_defaults(fn=cmd_review)
    p = sub.add_parser("apply", help="確認シートの判断を反映する")
    p.add_argument("file"); p.add_argument("--sheet", required=True); p.add_argument("--out"); p.add_argument("--reviewer")
    p.set_defaults(fn=cmd_apply)
    p = sub.add_parser("sample", help="二重注釈の対象を型で層別して選ぶ")
    p.add_argument("file"); p.add_argument("--frac", type=float, default=0.2); p.add_argument("--seed", type=int, default=0)
    p.add_argument("--out"); p.add_argument("--blank", help="2 人目用の空欄のファイル")
    p.set_defaults(fn=cmd_sample)
    p = sub.add_parser("agree", help="2 人の注釈の一致（項目ごとの κ・α）")
    p.add_argument("a"); p.add_argument("b"); p.add_argument("--ids", help="sample の出力（対象の L1）")
    p.add_argument("--threshold", type=float, default=0.6); p.add_argument("--boot", type=int, default=2000)
    p.add_argument("--seed", type=int, default=0); p.add_argument("--json", action="store_true")
    p.add_argument("--drop-unknown", action="store_true", help="unknown・not_checked・not_run を欠けとして扱う（既定は 1 つの値として数える）")
    p.set_defaults(fn=cmd_agree)
    a = ap.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
