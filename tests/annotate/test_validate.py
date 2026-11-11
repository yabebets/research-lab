"""rl annotate validate：スキーマと意味のチェック。"""
import copy

from rlkit.annotate import convert_v01, load_yaml, to_plain, validate


def errs(doc):
    return [m for _, m in validate(doc).errors]


def test_minimal_is_valid(minimal):
    rep = validate(load_yaml(minimal))
    assert rep.errors == []


def test_missing_required_field_in_japanese(minimal):
    d = load_yaml(minimal)
    del d["atomic"][0]["type"]
    e = errs(d)
    assert any("atomic[0] (A1)" in m and "必須の項目 type がない" in m for m in e)


def test_bad_enum_and_unknown_key(minimal):
    d = load_yaml(minimal)
    d["atomic"][1]["type"] = "SCREW"
    d["atomic"][1]["colour"] = "red"
    e = errs(d)
    assert any("'SCREW' は使えない" in m for m in e)
    assert any("知らない項目 colour" in m and "x_" in m for m in e)
    d["atomic"][1]["type"] = "HRN"
    del d["atomic"][1]["colour"]
    d["atomic"][1]["x_colour"] = "red"   # 拡張は x_ で許す
    assert errs(d) == []


def test_bad_src_value(minimal):
    d = load_yaml(minimal)
    d["atomic"][0]["attrs"]["force"]["src"] = "guess"
    assert any("出所の値 'guess' は使えない" in m for m in errs(d))
    d["atomic"][0]["attrs"]["force"]["src"] = "borrowed:so101"
    assert errs(d) == []


def test_missing_provenance(minimal):
    d = load_yaml(minimal)
    d["atomic"][0]["attrs"]["force"]["src"] = None
    d["atomic"][0]["label"]["tool_required"]["src"] = None
    e = errs(d)
    assert any("attrs.force" in m and "出所" in m for m in e)
    assert any("label.tool_required" in m and "出所" in m for m in e)
    # 未判定の値（unknown・not_checked）は出所がなくてよい
    d = load_yaml(minimal)
    assert d["atomic"][0]["label"]["hold_needed"]["v"] == "unknown"
    assert errs(d) == []


def test_required_cycle_detected(minimal):
    d = load_yaml(minimal)
    d["precedence"].append({"from": "A4", "to": "A1", "kind": "required", "source": "geometry"})
    e = errs(d)
    assert any("閉路" in m and "A1" in m and "A4" in m for m in e)


def test_recommended_cycle_is_only_warning(minimal):
    d = load_yaml(minimal)
    d["precedence"].append({"from": "A4", "to": "A1", "kind": "recommended", "source": "text_explicit"})
    rep = validate(d)
    assert rep.errors == []
    assert any(c == "cycle" for c, _ in rep.warnings)


def test_order_only_cannot_be_required(minimal):
    d = load_yaml(minimal)
    d["precedence"][3]["kind"] = "required"
    assert any("order_only" in m for m in errs(d))


def test_kind_null_only_for_order_only(minimal):
    d = load_yaml(minimal)
    d["precedence"][0]["kind"] = None
    assert any("kind が空" in m for m in errs(d))


def test_refs_resolve(minimal):
    d = load_yaml(minimal)
    d["atomic"][0]["parts_in"].append("toyarm:P99")
    d["atomic"][1]["l2_refs"] = ["S09"]
    d["precedence"][0]["to"] = "A9"
    d["bom"][1]["included_with"] = "B77"
    d["manual_steps"][0]["section"] = "SEC9"
    d["atomic"][2]["template_of"] = "A8"
    e = errs(d)
    for frag in ("P99 が BOM にない", "S09 が manual_steps にない", "A9 が atomic にない", "B77 が BOM にない",
                 "SEC9 が sections にない", "template_of A8"):
        assert any(frag in m for m in e), frag


def test_duplicate_ids_and_edges(minimal):
    d = load_yaml(minimal)
    d["atomic"][3]["id"] = "A1"
    d["precedence"].append(dict(d["precedence"][2]))
    e = errs(d)
    assert any("ID A1 が重複" in m for m in e)
    assert any("同じ辺が 2 回" in m for m in e)


def test_coverage(minimal):
    d = load_yaml(minimal)
    d["manual_steps"].append({"id": "S04", "text": "Clean up."})
    rep = validate(d)
    assert any("S04" in m and "参照されない" in m for _, m in rep.warnings)
    d["atomic"][2]["l2_refs"] = []
    assert any("l2_refs が空" in m for m in errs(d))
    d["atomic"][2]["source_section"] = "Configure the motors"
    assert not any("l2_refs が空" in m for m in errs(d))


def test_external_part_ref(minimal, tmp_path):
    d = load_yaml(minimal)
    d["atomic"][3]["parts_in"].append("so101:B21")
    rep = validate(d)
    assert rep.errors == [] and any("so101:B21" in m for _, m in rep.warnings)
    rep = validate(d, refs={"so101": {"B01"}})
    assert any("so101 の BOM にない" in m for _, m in rep.errors)


def test_rule_warnings(minimal):
    d = load_yaml(minimal)
    d["atomic"][2]["label"]["human_required"] = {"v": "yes", "src": "rule", "reason": None}
    d["atomic"][2]["label"]["evaluator_support"]["v"] = "supported"
    rep = validate(d)
    ws = [m for _, m in rep.warnings]
    assert any("独立の根拠" in m for m in ws)
    assert any("evaluator_support は規則では unsupported" in m for m in ws)


def test_variant_must_be_declared(minimal):
    d = load_yaml(minimal)
    d["manual_steps"][0]["variant"] = ["12V"]
    assert any("variant 12V が variants にない" in m for m in errs(d))
