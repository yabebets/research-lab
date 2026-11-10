"""rl_stats.py の一致の統計を、教科書・独立の実装の値で確かめる。

参照値:
- Cohen の κ: 2×2 の表 (20, 5 / 10, 15) で κ = 0.40（Wikipedia "Cohen's kappa" の例）
- 重みつき κ: scikit-learn の cohen_kappa_score（weights=None/linear/quadratic）で計算した値
- Fleiss の κ: Wikipedia "Fleiss' kappa" の 10 項目 × 14 人の例で κ = 0.210（statsmodels で 0.20993）
- Krippendorff の α: Krippendorff (2011) "Computing Krippendorff's Alpha-Reliability" の 4 人 × 12 項目の例で
  nominal 0.743・ordinal 0.815・interval 0.849、2 人 × 10 項目の 2 値の例で 0.095（krippendorff パッケージでも一致）
"""
import json
import subprocess
import sys

import pytest

from conftest import RL_STATS


def run(*args, payload=None, tmp_path=None):
    cmd = [sys.executable, str(RL_STATS), "--json", "--seed", "0"]
    args = list(args)
    if payload is not None:
        f = tmp_path / "in.json"
        f.write_text(json.dumps(payload))
        args.insert(1, str(f))
    r = subprocess.run(cmd + args, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_cohen_kappa_textbook(tmp_path):
    a = ["y"] * 20 + ["y"] * 5 + ["n"] * 10 + ["n"] * 15
    b = ["y"] * 20 + ["n"] * 5 + ["y"] * 10 + ["n"] * 15
    out = run("kappa", "--boot", "500", payload={"a": a, "b": b}, tmp_path=tmp_path)
    assert out["kappa"] == pytest.approx(0.4, abs=1e-9)
    assert out["p_observed"] == pytest.approx(0.7)
    assert out["p_expected"] == pytest.approx(0.5)
    assert out["ci"][0] < 0.4 < out["ci"][1]


@pytest.mark.parametrize("weights,expected", [("none", 0.4642857142857143), ("linear", 0.6511627906976745),
                                              ("quadratic", 0.810126582278481)])
def test_weighted_kappa_matches_sklearn(tmp_path, weights, expected):
    A = [0, 1, 2, 3, 1, 2, 0, 3, 2, 1, 0, 2, 3, 3, 1]
    B = [0, 2, 2, 3, 1, 1, 0, 2, 2, 1, 1, 2, 3, 2, 0]
    out = run("kappa", "--weights", weights, "--boot", "200", payload={"a": A, "b": B}, tmp_path=tmp_path)
    assert out["kappa"] == pytest.approx(expected, abs=1e-9)


def test_kappa_cli_args_and_missing():
    r = subprocess.run([sys.executable, str(RL_STATS), "--json", "kappa", "--a", "x", "y", "NA", "x",
                        "--b", "x", "y", "y", "y", "--boot", "100"], capture_output=True, text=True)
    out = json.loads(r.stdout)
    assert out["n"] == 3 and out["n_dropped_missing"] == 1


def test_none_is_a_value_not_missing():
    r = subprocess.run([sys.executable, str(RL_STATS), "--json", "kappa", "--a", "none", "hex", "none",
                        "--b", "none", "hex", "hex", "--boot", "50"], capture_output=True, text=True)
    out = json.loads(r.stdout)
    assert out["n"] == 3 and "none" in out["categories"]


def test_kappa_undefined_when_constant():
    r = subprocess.run([sys.executable, str(RL_STATS), "--json", "kappa", "--a", "x", "x", "--b", "x", "x",
                        "--boot", "50"], capture_output=True, text=True)
    out = json.loads(r.stdout)
    assert out["kappa"] is None and out["p_observed"] == 1.0


def test_weighted_kappa_needs_order_for_labels():
    r = subprocess.run([sys.executable, str(RL_STATS), "kappa", "--a", "lo", "hi", "--b", "hi", "hi",
                        "--weights", "linear"], capture_output=True, text=True)
    assert r.returncode != 0 and "--categories" in (r.stderr + r.stdout)


def test_fleiss_textbook(tmp_path):
    counts = [[0, 0, 0, 0, 14], [0, 2, 6, 4, 2], [0, 0, 3, 5, 6], [0, 3, 9, 2, 0], [2, 2, 8, 1, 1],
              [7, 7, 0, 0, 0], [3, 2, 6, 3, 0], [2, 5, 3, 2, 2], [6, 5, 2, 1, 0], [0, 2, 2, 3, 7]]
    out = run("fleiss", "--boot", "300", payload={"counts": counts}, tmp_path=tmp_path)
    assert out["kappa"] == pytest.approx(0.20993070442195522, abs=1e-9)
    assert out["P_bar"] == pytest.approx(0.378, abs=1e-3)
    assert out["Pe_bar"] == pytest.approx(0.213, abs=1e-3)


def test_fleiss_from_ratings_equals_counts(tmp_path):
    ratings = [["a", "a", "b"], ["b", "b", "b"], ["a", "c", "c"], ["c", "c", "c"]]
    counts = [[2, 1, 0], [0, 3, 0], [1, 0, 2], [0, 0, 3]]
    k1 = run("fleiss", "--boot", "50", payload={"ratings": ratings}, tmp_path=tmp_path)["kappa"]
    k2 = run("fleiss", "--boot", "50", payload={"counts": counts}, tmp_path=tmp_path)["kappa"]
    assert k1 == pytest.approx(k2)


KRIPP = [[1, 2, 3, 3, 2, 1, 4, 1, 2, None, None, None],
         [1, 2, 3, 3, 2, 2, 4, 1, 2, 5, None, 3],
         [None, 3, 3, 3, 2, 3, 4, 2, 2, 5, 1, None],
         [1, 2, 3, 3, 2, 4, 4, 1, 2, 5, 1, None]]


@pytest.mark.parametrize("level,expected", [("nominal", 0.743421052631579), ("ordinal", 0.8153875037548814),
                                            ("interval", 0.8491071428571428)])
def test_krippendorff_alpha_textbook(tmp_path, level, expected):
    out = run("alpha", "--level", level, "--boot", "300", payload={"data": KRIPP}, tmp_path=tmp_path)
    assert out["alpha"] == pytest.approx(expected, abs=1e-9)
    assert out["n_pairable_units"] == 11   # 最後の項目は 1 人だけなので数えない


def test_krippendorff_binary_example(tmp_path):
    data = [[0, 1, 0, 0, 0, 0, 0, 0, 1, 0], [1, 1, 1, 0, 0, 1, 0, 0, 0, 0]]
    out = run("alpha", "--boot", "300", payload={"data": data}, tmp_path=tmp_path)
    assert out["alpha"] == pytest.approx(0.095238, abs=1e-5)


def test_alpha_units_form_equals_data_form(tmp_path):
    units = [[r[u] for r in KRIPP] for u in range(12)]
    a = run("alpha", "--boot", "50", payload={"units": units}, tmp_path=tmp_path)["alpha"]
    assert a == pytest.approx(0.743421052631579)


def test_bootstrap_is_deterministic(tmp_path):
    p = {"data": KRIPP}
    a = run("alpha", "--boot", "400", payload=p, tmp_path=tmp_path)["ci"]
    b = run("alpha", "--boot", "400", payload=p, tmp_path=tmp_path)["ci"]
    assert a == b


def test_existing_subcommands_unchanged():
    out = json.loads(subprocess.run([sys.executable, str(RL_STATS), "--json", "wilson", "37", "50"],
                                    capture_output=True, text=True).stdout)
    assert out["rate"] == 0.74 and out["ci"][0] == pytest.approx(0.6045, abs=1e-4)   # 手計算の Wilson 区間
    out = json.loads(subprocess.run([sys.executable, str(RL_STATS), "--json", "holm", "0.01", "0.04", "0.03"],
                                    capture_output=True, text=True).stdout)
    assert out["p_holm"] == pytest.approx([0.03, 0.06, 0.06])
