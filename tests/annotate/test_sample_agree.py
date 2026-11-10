"""二重注釈の対象の選び方と、一致の表。"""
import types

from rlkit import annotate as A


def big_doc(n_per_type):
    d = A.load_yaml(__import__("conftest").FIX / "minimal_v02.yaml")
    base = d["atomic"][1]
    out = []
    k = 0
    for t, n in n_per_type.items():
        for _ in range(n):
            x = A.copy.deepcopy(base)
            k += 1
            x["id"] = f"L{k:03d}"
            x["type"] = t
            out.append(x)
    d["atomic"] = out
    d["precedence"] = []
    return d


def test_sample_is_deterministic_and_stratified():
    d = big_doc({"SCR": 50, "HRN": 30, "CON": 15, "CBL": 5})
    ids1, strata = A.stratified_sample(d, 0.2, 0)
    ids2, _ = A.stratified_sample(d, 0.2, 0)
    ids3, _ = A.stratified_sample(d, 0.2, 1)
    assert ids1 == ids2 and ids1 != ids3
    assert len(ids1) == 20
    assert strata == {"CBL": (1, 5), "CON": (3, 15), "HRN": (6, 30), "SCR": (10, 50)}


def test_sample_keeps_every_type_when_possible():
    d = big_doc({"SCR": 40, "HRN": 5, "unknown": 1, "OTH": 1})
    ids, strata = A.stratified_sample(d, 0.2, 0)
    assert len(ids) == round(0.2 * 47)
    assert all(k >= 1 for k, _ in strata.values())


def test_blank_copy_hides_first_annotation(minimal):
    d = A.load_yaml(minimal)
    b = A.to_plain(A.blank_copy(d, ["A1", "A3"]))
    assert [x["id"] for x in b["atomic"]] == ["A1", "A3"]
    assert all(x["review"]["status"] == "blank" and x["label"]["human_required"]["v"] is None for x in b["atomic"])
    assert b["atomic"][0]["parts_in"] == ["toyarm:B01", "toyarm:P01"]   # L1 の切り方は同じにする
    assert b["precedence"] == []
    assert A.validate(A.blank_copy(d, ["A1", "A3"])).errors == []


def test_agree_identical_is_perfect(minimal):
    d = A.to_plain(A.load_yaml(minimal))
    res = A.agreement(d, d, boot=200)
    rows = {r["field"]: r for r in res["rows"]}
    assert res["n_common"] == 4
    assert rows["type"]["kappa"] == 1.0 and rows["type"]["status"] == "OK"
    assert rows["precedence.kind（辺の和集合）"]["p_observed"] == 1.0


def test_agree_flags_low_kappa(minimal):
    a = A.to_plain(A.load_yaml(minimal))
    b = A.copy.deepcopy(a)
    for x, t in zip(b["atomic"], ["SCR", "SCR", "HRN", "CON"]):   # 型を入れ替える
        x["type"] = t
    b["precedence"][0]["kind"] = "recommended"
    b["precedence"].append({"from": "A2", "to": "A3", "kind": "required", "source": "geometry"})
    res = A.agreement(a, b, boot=200)
    rows = {r["field"]: r for r in res["rows"]}
    assert rows["type"]["kappa"] < 0.6 and rows["type"]["status"].startswith("要改訂")
    pk = rows["precedence.kind（辺の和集合）"]
    assert pk["n"] == 5 and abs(pk["p_observed"] - 0.6) < 1e-9   # 5 本中 3 本が一致（片方にない辺は absent という値として数える）


def test_agree_excludes_blank_and_uses_ids(minimal):
    a = A.to_plain(A.load_yaml(minimal))
    b = A.to_plain(A.blank_copy(A.load_yaml(minimal), ["A1"]))
    res = A.agreement(a, b, boot=50)
    assert res["n_common"] == 0 and res["n_blank_excluded"] == 1
    res = A.agreement(a, a, ids=["A1", "A2"], boot=50)
    assert res["n_common"] == 2


def test_agree_ordinal_axis_reports_weighted(minimal):
    a = A.to_plain(A.load_yaml(minimal))
    b = A.copy.deepcopy(a)
    vals_a, vals_b = [0, 1, "2+", 1], [0, "2+", "2+", 1]
    for x, y, va, vb in zip(a["atomic"], b["atomic"], vals_a, vals_b):
        x["label"]["hold_needed"] = {"v": va, "src": "sim"}
        y["label"]["hold_needed"] = {"v": vb, "src": "sim"}
    rows = {r["field"]: r for r in A.agreement(a, b, boot=50)["rows"]}
    h = rows["label.hold_needed"]
    assert h["n_ordinal"] == 4 and h["kappa_quadratic"] > h["kappa"]


def test_agree_drop_unknown(minimal):
    d = A.to_plain(A.load_yaml(minimal))
    rows = {r["field"]: r for r in A.agreement(d, d, boot=50, drop_unknown=True)["rows"]}
    assert rows["label.tool_access"]["status"] == "対象なし"   # not_checked は欠けになる
