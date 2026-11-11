"""v0.1（ir-trial）→ v0.2 の変換。"""
import pytest

from conftest import FIX, TRIAL
from rlkit import annotate as A


def conv(path):
    src = A.to_plain(A.load_yaml(path))
    return A.convert_v01(src, str(path))


def test_tiny_conversion(tmp_path):
    doc, rep = conv(FIX / "tiny_v01.yaml")
    out = tmp_path / "t.yaml"
    A.dump_yaml(doc, out)
    d = A.to_plain(A.load_yaml(out))
    assert A.validate(A.load_yaml(out)).errors == []
    ids = [x["id"] for x in d["atomic"]]
    # 隣り合う placed → fixed は 1 つの L1 に（type は締める側、secondary に置く側）
    assert ids == ["S02a", "S03a", "S03b", "S04a"]
    s02 = d["atomic"][0]
    assert s02["l2_refs"] == ["S01", "S02"] and s02["type"] == "SCR" and "INS" in s02["secondary"]
    assert s02["attrs"]["attached_flexible"]["v"] == "yes"       # 置く側の属性を引き継ぐ
    assert s02["fasteners"]["size_source"] == "borrowed:so101"
    assert s02["attrs"]["flips"] == {"v": 1, "src": "stated"}
    assert s02["parts_in"] == ["toyarm:B01", "toyarm:P01"]
    s04 = d["atomic"][3]
    assert s04["template_of"] == "S02a"
    assert s04["fasteners"]["size"] is None and s04["fasteners"]["count"] is None
    assert s04["attrs"]["zero_position"]["v"] == "yes"
    assert s04["label"]["tool_required"]["v"] == "unknown"       # 六角かプラスか決まらない
    cbl = d["atomic"][1]
    assert cbl["label"]["human_required"] == {"v": "yes", "src": "rule", "reason": "flexible"}
    assert cbl["label"]["evaluator_support"]["v"] == "unsupported"
    assert d["bom"][3]["included_with"] == "B01"
    assert "parent" not in d["sections"][0]
    em = {(e["from"], e["to"]): e for e in d["precedence"]}
    assert ("S02a", "S02a") not in em                              # 統合で自己ループになった辺は落とす
    assert em[("S02a", "S03a")]["kind"] == "recommended"          # 「逆順も可」
    assert em[("S03b", "S04a")]["kind"] == "required"             # geometry
    assert em[("S02a", "S04a")]["kind"] is None and em[("S02a", "S04a")]["source"] == "order_only"
    assert em[("S03a", "S03b")]["source"] == "unknown"            # precedes_from_text だけの辺
    assert any("summary_counts" in x for x in rep["dropped"])


@pytest.mark.skipif(not (TRIAL / "lekiwi.yaml").exists(), reason="robot-assembly-bench の試し書きがない")
@pytest.mark.parametrize("name,n_l1,n_merged", [("lekiwi.yaml", 47, 0), ("so100.yaml", 44, 2)])
def test_trial_files_convert_without_errors(tmp_path, name, n_l1, n_merged):
    doc, rep = conv(TRIAL / name)
    out = tmp_path / name
    A.dump_yaml(doc, out)
    d = A.load_yaml(out)
    vr = A.validate(d)
    assert vr.errors == [], vr.errors[:5]
    assert len(d["atomic"]) == n_l1
    assert len(rep["merged"]) == n_merged
