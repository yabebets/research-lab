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

例
  rl_stats.py ci 71.2 70.8 72.5 69.9 71.7
  rl_stats.py paired --a 71.2 70.8 72.5 --b 70.1 70.9 71.0
  rl_stats.py wilson 37 50
  rl_stats.py twoprop 37 50 26 50
  rl_stats.py iqm scores.json          # {"task": [seed1, seed2, ...], ...}
  rl_stats.py trials 0.6 0.8 --alpha 0.05 --power 0.8
  rl_stats.py holm 0.01 0.04 0.03
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
