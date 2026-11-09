# 台帳の書式

研究プロジェクトの状態は 3 つのファイルに置く。**どれも追記・更新するだけで、過去の記録は消さない**（取り消すときは `status: retracted` などで残す）。

## research.yaml

```yaml
project: so101-tactile-grasp          # rl new が入れる
domain: robotics                       # ml | cv | nlp | robotics | systems
created: 2026-11-09
stage: S1                              # S0〜S7（SKILL.md の表）
question: ""                           # G1 で確定する研究の問い（1 文）
hypotheses: []                         # 反証できる形で。例: "H1: 触覚入力を加えると把持成功率が 10pt 以上上がる"
venue_target: ""                       # 例: CoRL 2027
gates:
  G1: {approved: false, pending: false, decided_at: null, note: ""}
  G2: {approved: false, pending: false, decided_at: null, note: ""}
  G3: {approved: false, pending: false, decided_at: null, note: ""}
  G4: {approved: false, pending: false, decided_at: null, note: ""}
budget:                                # G2 で人が承認した上限
  gpu_usd: 0                           # GPU の合計上限（USD）
  gpu_usd_spent: 0                     # gpu-cloud が runs/ の記録から更新する
  llm_usd_per_night: 10                # 夜間ループ 1 晩あたりの Claude の上限
  max_run_hours: 8                     # 1 回の実行の上限時間
protocol:                              # G2 で固定する評価プロトコル（変えるなら止まって確認）
  test_split: ""
  metrics: []
  seeds: 5
  baselines: []
  robot_trials_per_condition: 0        # 実機評価がある場合
tasks:                                 # 次にやること。夜間ループは先頭の open を 1 つ片付ける
  - {id: T1, title: "", status: open, stage: S1, depends_on: []}
blockers: []                           # 止まった理由。{at, reason, needs: human|tool|budget}
log: []                                # {at, by: human|claude|night-loop, what}
```

ルール
- `stage` は前にしか進めない。戻すときは `log` に理由を書く。
- `gates.<G>.approved: true` は **人の発言を受けてだけ** 立てる。エージェントが自分で立てない。
- `protocol` は G2 の承認後に変えない。変えたいときは `blockers` に書いて止まる。

## claims.yaml

```yaml
claims:
  - id: C1
    text: "Tactile input improves grasp success on transparent objects by 14.2 pt (95% CI 8.1–20.3)."
    strength: strong            # strong | qualified | exploratory
    evidence: [run_20261120_0912_a1b2, run_20261120_1033_c3d4]   # runs/ の run_id
    stats: "Wilson CI, n=50 trials/condition; paired by object"
    eval_type: real_gt          # real_gt | synthetic_proxy | sim_only（ARIS experiment-integrity の区分）
    status: candidate           # candidate | frozen（G3） | retracted
    audit: {by: codex, verdict: "", at: null}
```

ルール
- 論文の数字はここにある主張からだけ書く。`evidence` の run がない主張は `exploratory` 止まり。
- `sim_only` の主張を「実機で」と書かない。`synthetic_proxy` は「代理指標での一致」としか言わない。

## runs/<run_id>/

`run_id` は `run_YYYYMMDD_HHMM_<短いハッシュ>`。1 回の実行につき 1 フォルダ。

| ファイル | 中身 |
|---|---|
| `run.yaml` | 目的（どのタスク・仮説のため）、コマンド、git の commit と差分の有無、seed、データのバージョン、計算資源（クラウド・GPU 種別・時間・費用） |
| `config.yaml` | 実行に使った設定のコピー（Hydra などの最終的な設定） |
| `metrics.json` | 最終指標。`{"metric_name": value, ...}` と `"split": "val" | "test"` |
| `log.txt` | 標準出力（大きければ末尾だけ。全体はクラウドのストレージや W&B） |
| `status` | `queued | running | done | failed | killed` の 1 語 |

ルール
- テストセットでの評価は、G2 で決めた回数だけ。`metrics.json` の `split: test` の数は `rl status` が数えて表示する。
- 失敗した実行も消さない（`status: failed` と理由）。
