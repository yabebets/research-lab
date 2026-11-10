#!/usr/bin/env python3
"""ML・ロボティクス実験の統計（標準ライブラリだけ・決定的）。

モデルの暗算で信頼区間や検定をしないために使う。乱数は --seed で固定（既定 0）。

サブコマンド
  ci       値の平均と 95% ブートストラップ信頼区間（seed 間のばらつき）
  paired   同じ seed / 同じ課題で対になった 2 条件の差（ペアのブートストラップ CI と符号反転の並べ替え検定）
  wilson   成功回数 k / 試行 n の Wilson 信頼区間（実機ロボットの成功率など）
  twoprop  2 条件の成功率の差（Fisher の正確検定、両側）
  iqm      RL など多課題 × 多 seed の IQM（四分位平均）と層別ブートストラップ CI（rliable 方式）
  trials   2 条件の成功率の差を検出するのに必要な 1 条件あたりの試行数（正規近似）
  holm     複数の p 値の Holm 補正
  kappa    2 人の注釈者の一致（Cohen の κ。--weights linear|quadratic で順序尺度の重みつき κ）
  fleiss   3 人以上（各項目を同じ人数が付けた）の一致（Fleiss の κ）
  alpha    欠けのある一致（Krippendorff の α。--level nominal|ordinal|interval）

一致の 3 つは、項目（単位）を復元抽出するブートストラップで CI を出す（--seed で決定的）。
入力は JSON ファイル:
  kappa   {"a": [...], "b": [...], "categories": [順序つきの値, ...]（任意）}  または --a ... --b ...
  fleiss  {"ratings": [[項目 1 の各人の値], ...]}  または {"counts": [[項目 1 の値ごとの人数], ...], "categories": [...]}
  alpha   {"data": [[注釈者 1 の各項目の値], [注釈者 2 ...], ...]}（欠けは null）  または {"units": [[項目 1 の各人の値], ...]}
null・""・"NA" は欠けとして扱う（kappa はその項目を落とし、落とした数を出す）。

例
  rl_stats.py ci 71.2 70.8 72.5 69.9 71.7
  rl_stats.py paired --a 71.2 70.8 72.5 --b 70.1 70.9 71.0
  rl_stats.py wilson 37 50
  rl_stats.py twoprop 37 50 26 50
  rl_stats.py iqm scores.json          # {"task": [seed1, seed2, ...], ...}
  rl_stats.py trials 0.6 0.8 --alpha 0.05 --power 0.8
  rl_stats.py holm 0.01 0.04 0.03
  rl_stats.py kappa --a SCR INS CON --b SCR PRS CON
  rl_stats.py kappa pairs.json --weights quadratic --categories 0 1 2+
  rl_stats.py fleiss ratings.json
  rl_stats.py alpha reliability.json --level ordinal
すべて --json で機械が読める出力にできる。
"""
from __future__ import annotations

import argparse
import json
import math
import random
import statistics
import sys

Z = {0.90: 1.6448536269514722, 0.95: 1.959963984540054, 0.99: 2.5758293035489004}


def _z(conf: float) -> float:
    if conf in Z:
        return Z[conf]
    return statistics.NormalDist().inv_cdf(0.5 + conf / 2)


def _pct(sorted_vals: list[float], q: float) -> float:
    if not sorted_vals:
        return float("nan")
    k = (len(sorted_vals) - 1) * q
    lo, hi = math.floor(k), math.ceil(k)
    if lo == hi:
        return sorted_vals[int(k)]
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (k - lo)


def bootstrap_ci(vals: list[float], stat, n_boot: int, conf: float, rng: random.Random):
    n = len(vals)
    boots = sorted(stat([vals[rng.randrange(n)] for _ in range(n)]) for _ in range(n_boot))
    a = (1 - conf) / 2
    return _pct(boots, a), _pct(boots, 1 - a)


def cmd_ci(args, rng):
    v = args.values
    if len(v) < 2:
        sys.exit("値が 2 つ以上必要です（seed が 1 つでは、ばらつきを測れません）")
    lo, hi = bootstrap_ci(v, statistics.fmean, args.boot, args.conf, rng)
    out = {
        "n": len(v),
        "mean": statistics.fmean(v),
        "std": statistics.stdev(v),
        "sem": statistics.stdev(v) / math.sqrt(len(v)),
        "ci": [lo, hi],
        "conf": args.conf,
        "method": "percentile bootstrap of the mean",
        "warning": "n<5: CI is unreliable; report as preliminary" if len(v) < 5 else None,
    }
    return out


def cmd_paired(args, rng):
    a, b = args.a, args.b
    if len(a) != len(b):
        sys.exit("--a と --b の数が違います。対になっていない比較なら ci を条件ごとに使ってください")
    d = [x - y for x, y in zip(a, b)]
    n = len(d)
    lo, hi = bootstrap_ci(d, statistics.fmean, args.boot, args.conf, rng)
    obs = abs(statistics.fmean(d))
    if n <= 16:  # 全ての符号の組み合わせで正確に
        cnt = tot = 0
        for mask in range(1 << n):
            s = sum(x if (mask >> i) & 1 else -x for i, x in enumerate(d)) / n
            tot += 1
            cnt += abs(s) >= obs - 1e-12
        p = cnt / tot
        method = "exact sign-flip permutation"
    else:
        cnt = 0
        for _ in range(args.boot):
            s = sum(x if rng.random() < 0.5 else -x for x in d) / n
            cnt += abs(s) >= obs - 1e-12
        p = (cnt + 1) / (args.boot + 1)
        method = "Monte Carlo sign-flip permutation"
    return {
        "n_pairs": n,
        "mean_diff_a_minus_b": statistics.fmean(d),
        "ci": [lo, hi],
        "conf": args.conf,
        "p_two_sided": p,
        "method": method,
        "min_attainable_p": 2 / (1 << n) if n <= 16 else None,
    }


def wilson(k: int, n: int, conf: float):
    if n <= 0 or not 0 <= k <= n:
        sys.exit("0 <= k <= n、n > 0 にしてください")
    z = _z(conf)
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(0.0, c - h), min(1.0, c + h)


def cmd_wilson(args, rng):
    lo, hi = wilson(args.k, args.n, args.conf)
    return {"k": args.k, "n": args.n, "rate": args.k / args.n, "ci": [lo, hi], "conf": args.conf,
            "half_width_pt": (hi - lo) * 50, "method": "Wilson score interval"}


def _logC(n, k):
    return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)


def fisher_two_sided(k1, n1, k2, n2):
    K, N = k1 + k2, n1 + n2
    lo, hi = max(0, K - n2), min(K, n1)
    def pmf(x):
        return math.exp(_logC(n1, x) + _logC(n2, K - x) - _logC(N, K))
    p_obs = pmf(k1)
    return min(1.0, sum(pmf(x) for x in range(lo, hi + 1) if pmf(x) <= p_obs * (1 + 1e-7)))


def cmd_twoprop(args, rng):
    p = fisher_two_sided(args.k1, args.n1, args.k2, args.n2)
    r1, r2 = args.k1 / args.n1, args.k2 / args.n2
    return {"rate1": r1, "rate2": r2, "diff_pt": (r1 - r2) * 100,
            "ci1": list(wilson(args.k1, args.n1, args.conf)), "ci2": list(wilson(args.k2, args.n2, args.conf)),
            "p_two_sided": p, "method": "Fisher exact test (two-sided)"}


def iqm(vals: list[float]) -> float:
    s = sorted(vals)
    n = len(s)
    lo, hi = n * 0.25, n * 0.75
    total = w = 0.0
    for i, x in enumerate(s):  # 端を按分する IQM
        a, b = max(i, lo), min(i + 1, hi)
        if b > a:
            total += x * (b - a)
            w += b - a
    return total / w


def cmd_iqm(args, rng):
    data = json.load(open(args.file))
    tasks = {t: [float(x) for x in v] for t, v in data.items()}
    flat = [x for v in tasks.values() for x in v]
    boots = []
    for _ in range(args.boot):
        sample = []
        for v in tasks.values():  # 課題ごとに seed を復元抽出（層別）
            sample += [v[rng.randrange(len(v))] for _ in v]
        boots.append(iqm(sample))
    boots.sort()
    a = (1 - args.conf) / 2
    return {"tasks": len(tasks), "runs": len(flat), "iqm": iqm(flat), "mean": statistics.fmean(flat),
            "median": statistics.median(flat), "ci": [_pct(boots, a), _pct(boots, 1 - a)], "conf": args.conf,
            "method": "IQM with stratified bootstrap over runs within tasks (Agarwal et al. 2021)"}


def cmd_trials(args, rng):
    p1, p2 = args.p1, args.p2
    za = _z(1 - args.alpha)
    zb = statistics.NormalDist().inv_cdf(args.power)
    pbar = (p1 + p2) / 2
    n = ((za * math.sqrt(2 * pbar * (1 - pbar)) + zb * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2) / (p1 - p2) ** 2
    return {"p1": p1, "p2": p2, "alpha": args.alpha, "power": args.power, "trials_per_condition": math.ceil(n),
            "method": "two-proportion z-test sample size (normal approximation; use as a lower bound)"}


def cmd_holm(args, rng):
    ps = args.pvalues
    order = sorted(range(len(ps)), key=lambda i: ps[i])
    adj = [0.0] * len(ps)
    running = 0.0
    m = len(ps)
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (m - rank) * ps[i]))
        adj[i] = running
    return {"p": ps, "p_holm": adj, "reject_at_0.05": [x < 0.05 for x in adj]}


# ---------------------------------------------------------------- 注釈者の間の一致
MISSING = {"", "na", "n/a", "null", "nan"}   # "none" は値（工具なし など）として扱う


def _is_missing(x) -> bool:
    if x is None:
        return True
    if isinstance(x, float) and math.isnan(x):
        return True
    return isinstance(x, str) and x.strip().lower() in MISSING


def _norm(x) -> str:
    """値を文字列にそろえる（JSON の 1 と CLI の "1" を同じ値として扱う）。"""
    if isinstance(x, bool):
        return "true" if x else "false"
    if isinstance(x, float) and x.is_integer():
        return str(int(x))
    return str(x).strip()


def _num(s: str):
    try:
        return float(s)
    except ValueError:
        return None


def _categories(values: list[str], given, need_order: bool, what: str) -> list[str]:
    if given:
        cats = [_norm(c) for c in given]
        extra = sorted(set(values) - set(cats))
        if extra:
            sys.exit(f"--categories にない値があります: {extra}")
        return cats
    uniq = sorted(set(values))
    if all(_num(v) is not None for v in uniq):
        return sorted(uniq, key=lambda v: _num(v))
    if need_order:
        sys.exit(f"{what} は値の順序が要ります。--categories で小さい順に並べてください（値: {uniq}）")
    return uniq


def _weight(i: int, j: int, k: int, weights: str) -> float:
    if weights == "none":
        return 0.0 if i == j else 1.0
    if k < 2:
        return 0.0
    d = abs(i - j) / (k - 1)
    return d if weights == "linear" else d * d


def cohen_kappa(a: list[str], b: list[str], cats: list[str], weights: str = "none"):
    """(kappa, p_observed, p_expected)。期待の不一致が 0（全件が同じ値）なら kappa は None。"""
    k, n = len(cats), len(a)
    idx = {c: i for i, c in enumerate(cats)}
    obs = [[0.0] * k for _ in range(k)]
    for x, y in zip(a, b):
        obs[idx[x]][idx[y]] += 1.0 / n
    row = [sum(obs[i]) for i in range(k)]
    col = [sum(obs[i][j] for i in range(k)) for j in range(k)]
    do = sum(_weight(i, j, k, weights) * obs[i][j] for i in range(k) for j in range(k))
    de = sum(_weight(i, j, k, weights) * row[i] * col[j] for i in range(k) for j in range(k))
    po = sum(obs[i][i] for i in range(k))
    pe = sum(row[i] * col[i] for i in range(k))
    kappa = None if de <= 1e-12 else 1.0 - do / de
    return kappa, po, pe


def _boot_stat(n_items: int, fn, n_boot: int, conf: float, rng: random.Random):
    boots, undefined = [], 0
    for _ in range(n_boot):
        s = fn([rng.randrange(n_items) for _ in range(n_items)])
        if s is None:
            undefined += 1
        else:
            boots.append(s)
    boots.sort()
    a = (1 - conf) / 2
    ci = [_pct(boots, a), _pct(boots, 1 - a)] if boots else [None, None]
    return ci, undefined


def _load_json(path):
    with open(path) as f:
        return json.load(f)


def cmd_kappa(args, rng):
    if args.file:
        d = _load_json(args.file)
        ra, rb = d["a"], d["b"]
        given = args.categories or d.get("categories")
    else:
        if not args.a or not args.b:
            sys.exit("ファイルか、--a と --b の両方を渡してください")
        ra, rb, given = args.a, args.b, args.categories
    if len(ra) != len(rb):
        sys.exit(f"a と b の数が違います（{len(ra)} と {len(rb)}）。同じ項目を同じ順に並べてください")
    pairs = [(_norm(x), _norm(y)) for x, y in zip(ra, rb) if not (_is_missing(x) or _is_missing(y))]
    dropped = len(ra) - len(pairs)
    if len(pairs) < 2:
        sys.exit("欠けを除いた項目が 2 つ未満です")
    a = [p[0] for p in pairs]
    b = [p[1] for p in pairs]
    cats = _categories(a + b, given, args.weights != "none", "重みつき κ")
    kappa, po, pe = cohen_kappa(a, b, cats, args.weights)
    ci, undef = _boot_stat(len(a), lambda ix: cohen_kappa([a[i] for i in ix], [b[i] for i in ix], cats, args.weights)[0],
                           args.boot, args.conf, rng)
    warn = []
    if kappa is None:
        warn.append("全件が同じ値で κ は定義できない（一致率だけを見る）")
    if len(a) < 30:
        warn.append("n<30: CI が広い。κ の点推定だけで規則の良し悪しを決めない")
    return {"n": len(a), "n_dropped_missing": dropped, "categories": cats, "weights": args.weights,
            "p_observed": po, "p_expected": pe, "kappa": kappa, "ci": ci, "conf": args.conf,
            "n_boot_undefined": undef,
            "method": f"Cohen's kappa ({args.weights} weights); percentile bootstrap over items",
            "warning": "; ".join(warn) or None}


def fleiss_kappa(counts: list[list[float]]):
    """counts: 項目 × 値 の人数。全項目で人数が同じこと。(kappa, P_bar, Pe_bar)。"""
    N = len(counts)
    n = sum(counts[0])
    k = len(counts[0])
    p = [sum(r[j] for r in counts) / (N * n) for j in range(k)]
    P = [(sum(x * x for x in r) - n) / (n * (n - 1)) for r in counts]
    pbar = statistics.fmean(P)
    pe = sum(x * x for x in p)
    kappa = None if 1 - pe <= 1e-12 else (pbar - pe) / (1 - pe)
    return kappa, pbar, pe


def cmd_fleiss(args, rng):
    d = _load_json(args.file)
    if "counts" in d:
        counts = [[float(x) for x in r] for r in d["counts"]]
        cats = [_norm(c) for c in d.get("categories", range(len(counts[0])))]
    else:
        ratings = d["ratings"]
        if any(_is_missing(x) for r in ratings for x in r):
            sys.exit("Fleiss の κ は欠けを扱えません。欠けがあるなら alpha を使ってください")
        vals = [_norm(x) for r in ratings for x in r]
        cats = _categories(vals, args.categories or d.get("categories"), False, "fleiss")
        counts = [[float(sum(1 for x in r if _norm(x) == c)) for c in cats] for r in ratings]
    sizes = {sum(r) for r in counts}
    if len(sizes) != 1:
        sys.exit(f"項目ごとの注釈者の数がそろっていません（{sorted(sizes)}）。欠けがあるなら alpha を使ってください")
    n = sizes.pop()
    if n < 2:
        sys.exit("1 項目あたり 2 人以上の値が要ります")
    kappa, pbar, pe = fleiss_kappa(counts)
    ci, undef = _boot_stat(len(counts), lambda ix: fleiss_kappa([counts[i] for i in ix])[0], args.boot, args.conf, rng)
    return {"n_items": len(counts), "n_raters": int(n), "categories": cats, "P_bar": pbar, "Pe_bar": pe,
            "kappa": kappa, "ci": ci, "conf": args.conf, "n_boot_undefined": undef,
            "method": "Fleiss' kappa; percentile bootstrap over items",
            "warning": "全件が同じ値で κ は定義できない" if kappa is None else None}


def _alpha_units(units, cats, level):
    """units: 各項目の値（欠けなし、2 つ以上）。Krippendorff の α（None は定義できない）。"""
    idx = {c: i for i, c in enumerate(cats)}
    k = len(cats)
    o = [[0.0] * k for _ in range(k)]
    for u in units:
        m = len(u)
        for i, x in enumerate(u):
            for j, y in enumerate(u):
                if i != j:
                    o[idx[x]][idx[y]] += 1.0 / (m - 1)
    nc = [sum(o[c]) for c in range(k)]
    n = sum(nc)
    if n <= 1:
        return None
    if level == "nominal":
        def d2(c, kk):
            return 0.0 if c == kk else 1.0
    elif level == "ordinal":
        cum = [0.0]
        for x in nc:
            cum.append(cum[-1] + x)
        def d2(c, kk):
            lo, hi = min(c, kk), max(c, kk)
            return (cum[hi + 1] - cum[lo] - (nc[lo] + nc[hi]) / 2) ** 2
    else:
        vals = [float(c) for c in cats]
        def d2(c, kk):
            return (vals[c] - vals[kk]) ** 2
    do = sum(o[c][kk] * d2(c, kk) for c in range(k) for kk in range(k))
    de = sum(nc[c] * nc[kk] * d2(c, kk) for c in range(k) for kk in range(k)) / (n - 1)
    if de <= 1e-12:
        return None
    return 1.0 - do / de


def cmd_alpha(args, rng):
    d = _load_json(args.file)
    if "units" in d:
        units_raw = d["units"]
    elif "data" in d:
        data = d["data"]
        L = {len(r) for r in data}
        if len(L) != 1:
            sys.exit("data の行（注釈者）の長さがそろっていません。欠けは null で埋めてください")
        units_raw = [[r[u] for r in data] for u in range(L.pop())]
    else:
        sys.exit('JSON に "data"（注釈者 × 項目）か "units"（項目 × 注釈者）が要ります')
    units = [[_norm(x) for x in u if not _is_missing(x)] for u in units_raw]
    pairable = [u for u in units if len(u) >= 2]
    if len(pairable) < 2:
        sys.exit("2 人以上が値を付けた項目が 2 つ未満です")
    vals = [x for u in pairable for x in u]
    if args.level == "interval" and any(_num(v) is None for v in vals):
        sys.exit("interval は数値だけを扱えます")
    cats = _categories(vals, args.categories or d.get("categories"), args.level == "ordinal", "ordinal の α")
    alpha = _alpha_units(pairable, cats, args.level)
    ci, undef = _boot_stat(len(pairable), lambda ix: _alpha_units([pairable[i] for i in ix], cats, args.level),
                           args.boot, args.conf, rng)
    return {"n_units": len(units), "n_pairable_units": len(pairable), "n_values": len(vals), "categories": cats,
            "level": args.level, "alpha": alpha, "ci": ci, "conf": args.conf, "n_boot_undefined": undef,
            "method": f"Krippendorff's alpha ({args.level}); percentile bootstrap over units",
            "warning": "値のばらつきがなく α は定義できない" if alpha is None else None}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--json", action="store_true", help="JSON で出力")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p, boot=True):
        p.add_argument("--conf", type=float, default=0.95)
        if boot:
            p.add_argument("--boot", type=int, default=10000)

    p = sub.add_parser("ci"); p.add_argument("values", type=float, nargs="+"); common(p)
    p = sub.add_parser("paired"); p.add_argument("--a", type=float, nargs="+", required=True)
    p.add_argument("--b", type=float, nargs="+", required=True); common(p)
    p = sub.add_parser("wilson"); p.add_argument("k", type=int); p.add_argument("n", type=int); common(p, False)
    p = sub.add_parser("twoprop")
    for x in ("k1", "n1", "k2", "n2"):
        p.add_argument(x, type=int)
    common(p, False)
    p = sub.add_parser("iqm"); p.add_argument("file"); common(p)
    p = sub.add_parser("trials"); p.add_argument("p1", type=float); p.add_argument("p2", type=float)
    p.add_argument("--alpha", type=float, default=0.05); p.add_argument("--power", type=float, default=0.8)
    p = sub.add_parser("holm"); p.add_argument("pvalues", type=float, nargs="+")
    p = sub.add_parser("kappa"); p.add_argument("file", nargs="?")
    p.add_argument("--a", nargs="+"); p.add_argument("--b", nargs="+")
    p.add_argument("--weights", choices=["none", "linear", "quadratic"], default="none")
    p.add_argument("--categories", nargs="+", help="値の順序（小さい順）。重みつきで値が数でないときに要る")
    common(p)
    p = sub.add_parser("fleiss"); p.add_argument("file"); p.add_argument("--categories", nargs="+"); common(p)
    p = sub.add_parser("alpha"); p.add_argument("file")
    p.add_argument("--level", choices=["nominal", "ordinal", "interval"], default="nominal")
    p.add_argument("--categories", nargs="+", help="ordinal の値の順序（小さい順）"); common(p)

    args = ap.parse_args()
    rng = random.Random(args.seed)
    out = globals()[f"cmd_{args.cmd}"](args, rng)
    if args.json:
        print(json.dumps(out, ensure_ascii=False))
    else:
        for k, v in out.items():
            if v is None:
                continue
            if isinstance(v, float):
                v = round(v, 4)
            elif isinstance(v, list):
                v = [round(x, 4) if isinstance(x, float) else x for x in v]
            print(f"{k}: {v}")


if __name__ == "__main__":
    main()
