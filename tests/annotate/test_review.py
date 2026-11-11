"""確認シートの往復（review → 人が埋める → apply）。"""
import csv
import types

import pytest

from rlkit import annotate as A


def ns(**kw):
    return types.SimpleNamespace(**kw)


def read(p):
    with open(p, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write(p, rows):
    with open(p, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=A.SHEET_COLS)
        w.writeheader()
        w.writerows(rows)


def export(minimal, tmp_path):
    sheet = tmp_path / "sheet.csv"
    A.cmd_review(ns(file=minimal, sheet=sheet, all=False))
    return sheet, read(sheet)


def test_sheet_has_one_row_per_field_and_edge(minimal, tmp_path):
    _, rows = export(minimal, tmp_path)
    a1 = [r for r in rows if r["l1_id"] == "A1"]
    fields = {r["field"] for r in a1}
    assert {"type", "fix_state", "tool", "attrs.force", "label.hold_needed", "label.scope"} <= fields
    assert len(a1) == len(A.l1_fields(A.load_yaml(minimal)["atomic"][0]))
    edges = [r for r in rows if r["field"].startswith("precedence:")]
    assert len(edges) == 4
    force = next(r for r in a1 if r["field"] == "attrs.force")
    assert (force["draft_value"], force["draft_src"]) == ("low", "rule")


def test_all_ok_round_trip_keeps_values(minimal, tmp_path):
    before = A.to_plain(A.load_yaml(minimal))
    sheet, rows = export(minimal, tmp_path)
    for r in rows:
        r["decision"] = "ok"
    write(sheet, rows)
    out = tmp_path / "out.yaml"
    A.cmd_apply(ns(file=minimal, sheet=sheet, out=out, reviewer="r1"))
    after = A.to_plain(A.load_yaml(out))
    for b, a in zip(before["atomic"], after["atomic"]):
        assert a["review"]["status"] == "reviewed" and a["review"]["reviewed_by"] == "r1"
        a.pop("review"); b.pop("review", None)
        assert a == b
    assert all(e["review"]["status"] == "reviewed" for e in after["precedence"])
    assert after["annotation"]["review_log"][0]["ok"] == len(rows)


def test_change_sets_annotator_and_records_reason(minimal, tmp_path):
    sheet, rows = export(minimal, tmp_path)
    for r in rows:
        if r["l1_id"] == "A1":
            r["decision"] = "ok"
            if r["field"] == "label.hold_needed":
                r.update(decision="change", new_value="2+", reason="裏のナットを押さえる")
            if r["field"] == "type":
                r.update(decision="変更", new_value="INS", reason="ねじは別工程")
    write(sheet, rows)
    out = tmp_path / "out.yaml"
    A.cmd_apply(ns(file=minimal, sheet=sheet, out=out, reviewer="r1"))
    a1 = A.to_plain(A.load_yaml(out))["atomic"][0]
    assert a1["label"]["hold_needed"] == {"v": "2+", "src": "annotator"}
    assert a1["type"] == "INS"
    ch = {c["field"]: c for c in a1["review"]["changes"]}
    assert ch["label.hold_needed"]["from"] == "unknown" and ch["label.hold_needed"]["reason"] == "裏のナットを押さえる"
    assert ch["type"]["to"] == "INS"
    assert a1["review"]["status"] == "reviewed"
    a2 = A.to_plain(A.load_yaml(out))["atomic"][1]
    assert (a2.get("review") or {}).get("status") != "reviewed"   # 未決の行が残る L1 は確認済みにしない


def test_new_src_overrides_annotator(minimal, tmp_path):
    sheet, rows = export(minimal, tmp_path)
    r = next(r for r in rows if r["l1_id"] == "A4" and r["field"] == "attrs.flips")
    r.update(decision="change", new_value="1", new_src="stated", reason="本文に 'from the bottom'")
    write(sheet, rows)
    out = tmp_path / "out.yaml"
    A.cmd_apply(ns(file=minimal, sheet=sheet, out=out, reviewer=None))
    assert A.to_plain(A.load_yaml(out))["atomic"][3]["attrs"]["flips"] == {"v": 1, "src": "stated"}


def test_change_without_reason_is_refused(minimal, tmp_path):
    sheet, rows = export(minimal, tmp_path)
    rows[0].update(decision="change", new_value="INS")
    write(sheet, rows)
    with pytest.raises(SystemExit):
        A.cmd_apply(ns(file=minimal, sheet=sheet, out=tmp_path / "o.yaml", reviewer=None))
    assert not (tmp_path / "o.yaml").exists()


def test_conflict_when_file_changed_after_export(minimal, tmp_path):
    sheet, rows = export(minimal, tmp_path)
    for r in rows:
        r["decision"] = "ok"
    write(sheet, rows)
    d = A.load_yaml(minimal)
    d["atomic"][0]["type"] = "PRS"
    A.dump_yaml(d, minimal)
    with pytest.raises(SystemExit):
        A.cmd_apply(ns(file=minimal, sheet=sheet, out=tmp_path / "o.yaml", reviewer=None))


def test_edge_change_delete_add(minimal, tmp_path):
    sheet, rows = export(minimal, tmp_path)
    for r in rows:
        if r["field"] == "precedence:A1->A3":
            r.update(decision="change", new_value="required", new_src="geometry", reason="CAD で確認")
        if r["field"] == "precedence:A3->A4":
            r.update(decision="delete", reason="並びだけで意味がない")
    rows.append({**{k: "" for k in A.SHEET_COLS}, "l1_id": "edge", "field": "precedence:A3->A2",
                 "decision": "add", "new_value": "recommended", "new_src": "text_explicit", "reason": "注記"})
    write(sheet, rows)
    out = tmp_path / "out.yaml"
    A.cmd_apply(ns(file=minimal, sheet=sheet, out=out, reviewer="r2"))
    d = A.to_plain(A.load_yaml(out))
    em = {(e["from"], e["to"]): e for e in d["precedence"]}
    assert em[("A1", "A3")]["kind"] == "required" and em[("A1", "A3")]["source"] == "geometry"
    assert em[("A1", "A3")]["src"] == "annotator"
    assert ("A3", "A4") not in em
    assert d["annotation"]["removed_edges"][0]["reason"] == "並びだけで意味がない"
    assert em[("A3", "A2")]["kind"] == "recommended"


def test_in_place_apply_keeps_backup(minimal, tmp_path):
    sheet, rows = export(minimal, tmp_path)
    rows[0]["decision"] = "ok"
    write(sheet, rows)
    A.cmd_apply(ns(file=minimal, sheet=sheet, out=None, reviewer=None))
    assert minimal.with_suffix(".yaml.bak").exists()
