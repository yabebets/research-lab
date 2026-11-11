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
program:                               # 任意。研究プログラム（programs/<name>/program.yaml）に紐づける。rl program link か rl new --program --paper が書く
  name: ""                             # プログラム名（programs/ のフォルダ名）
  paper_id: ""                         # program.yaml の論文 ID（P1, P2', B1 …）
  depends_on: []                       # 先に終わっている必要がある他のプロジェクト名
gates:
  G1: {approved: false, pending: false, decided_at: null, note: ""}
  G2: {approved: false, pending: false, decided_at: null, note: ""}
  G3: {approved: false, pending: false, decided_at: null, note: ""}
  G4: {approved: false, pending: false, decided_at: null, note: ""}
budget:                                # G2 で人が承認した上限
  gpu_usd: 0                           # GPU の合計上限（USD）
  gpu_usd_spent: 0                     # gpu-cloud が runs/ の記録から更新する
  llm_usd_cap: null                    # 実験で呼ぶ言語モデルの API の合計上限（USD）。null の間は rl llm が送らない
  llm_halt_ratio: null                 # 任意。例 0.8 なら上限の 80% で送らなくなる（止まって相談）
  llm_usd_per_night: 10                # 夜間ループ 1 晩あたりの Claude の上限（llm_usd_cap が無いとき夜間ループの中だけ代わりに使う）
  max_run_hours: 8                     # 1 回の実行の上限時間
protocol:                              # G2 で固定する評価プロトコル（変えるなら止まって確認）
  test_split: ""
  metrics: []
  seeds: 5
  baselines: []
  max_test_evals: 3                    # test での評価の上限回数（rl run が数えて断る）
  robot_trials_per_condition: 0        # 実機評価がある場合
  evaluated_models: []                 # 任意。評価する言語モデル（rl annotate draft が下書きのモデルと同じ系統を断るのに使う。なければ plan.md の行から読む）
  test_robots: []                      # 任意。テストの機種（G2 の前は rl annotate draft が注釈を断る。なければ test_split か plan.md の「テスト」の行から読む）
tasks:                                 # 次にやること。夜間ループは先頭の open を 1 つ片付ける
  - {id: T1, title: "", status: open, stage: S1, depends_on: []}
blockers: []                           # 止まった理由。{at, reason, needs: human|tool|budget}
log: []                                # {at, by: human|claude|night-loop, what}
```

ルール
- `stage` は前にしか進めない。戻すときは `log` に理由を書く。
- `gates.<G>.approved: true` は **人の発言を受けてだけ** 立てる。エージェントが自分で立てない。
- `protocol` は G2 の承認後に変えない。変えたいときは `blockers` に書いて止まる。
- 言語モデルの API の使った額は台帳に書かない。`rl llm budget` が runs/ と notes/llm-logs/ の記録から数える。

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

`run_id` は `run_YYYYMMDD_HHMM_<6 桁の 16 進>`。1 回の実行につき 1 フォルダ。**`rl run exec`（手で回すなら `rl run start` / `finish`）が作る。** 手で作らない。

| ファイル | 中身 |
|---|---|
| `run.yaml` | rl run が書く（下の表） |
| `config.yaml` | `--config` で渡した設定のコピー（Hydra などの最終的な設定。YAML 以外なら `config.<拡張子>`） |
| `metrics.json` | コマンドが `$RL_RUN_DIR/metrics.json` に書く最終指標。`{"metric_name": value, ...}` と `"split": "dev" \| "val" \| "test"`（なければ rl run が宣言の split を補う。宣言と違えば failed） |
| `log.txt` | 標準出力と標準エラー（rl run が記録。末尾 2 MB だけ残す。全体が要るならクラウドのストレージや W&B） |
| `status` | `queued \| running \| done \| failed \| killed` の 1 語 |
| `llm_calls.jsonl`・`llm_requests/`・`llm_responses/` | 任意。言語モデルの呼び出しの記録（rlkit.llm が書く。1 行 1 回、要求の本文は sha256 の名前で、画像は 1 回だけ）。`cost_usd` を rl run が合計する |
| 図（`*.png` `*.gif` …） | 任意。rl blog が拾う |

run.yaml の項目

| 項目 | 中身 |
|---|---|
| `run_id` `project` `task` `purpose` `tags` | どのタスク・何を確かめるための実行か。`tags` は `sim` / `real` などの印 |
| `split` `seed` `data_version` | 評価の split（dev / val / test）、seed、データの版 |
| `command` `command_str` `cwd` | 実行したコマンドと場所 |
| `config` | `{source, copy, sha256}` |
| `git` | プロジェクトの `{repo, commit, branch, dirty, diff_sha256（git diff HEAD の sha256）, untracked}`。`git_cwd` は実行した場所が別のリポジトリのときだけ |
| `locks` | `sims.lock.yaml`・`robots.lock.yaml`・`container.lock.yaml`・`prereg.lock.yaml` の sha256（あるものだけ） |
| `prereg` | `{locked, drift}`（実行の開始時） |
| `host` `compute` | `{hostname, os, python, cpu, cpu_count, ram_gb, gpu}`、`{where: local \| <クラスタ名>, gpu_usd}` |
| `container` | コンテナのイメージで回したときの指紋。ホストの rl run がコンテナを起動したとき（コマンドが `docker run … IMAGE`、または包みのスクリプトを使うときの環境変数 `RL_IMAGE`）は `{inside: false, launcher, via, image, id, repo_digests, os_arch, engine}`（`docker image inspect` の ID）。rl run 自身がコンテナの中なら `{inside: true, image, id, repo_digest, info}`（起動する側が渡す環境変数 `RL_IMAGE_ID`・`RL_IMAGE_TAG` と、イメージの中の `/etc/rl-image.json` の sha256）。どちらでもなければ null。本番の評価はイメージを固めて回す（`ml-rigor` の references/reproducibility.md） |
| `started_at` `ended_at` `elapsed_sec` `exit_code` | 時刻と終了コード |
| `status` `status_reason` | status と、failed / killed の理由 |
| `llm` | `{calls, cost_usd, by_model}`（llm_calls.jsonl があったとき） |
| `metrics_keys` `log` | 指標の名前の一覧、`{bytes_total, truncated}` |

ルール
- テストセットでの評価は、G2 の承認後に `protocol.max_test_evals` 回まで。rl run が数えて、超える実行を断る。数えるのは「metrics.json の split が test」か「`--split test` で始めた」run（失敗・中断も数える）。`rl status` も同じ数え方で表示する。
- prereg.lock.yaml があって事前登録が凍結時から変わっていると、rl run は test の実行を断る。
- 失敗した実行も消さない（`status: failed` と `status_reason`）。

## prereg.lock.yaml

G2 の承認後に `rl prereg freeze` が書く。手で直さない。

| 項目 | 中身 |
|---|---|
| `frozen_at` `frozen_by` `gate` | 凍結した時刻、G2 の承認の状態 |
| `plan` | plan.md の `## 事前登録…`（または `## 4. 事前登録…`）の節の `{heading, sha256, git_commit, git_dirty, copy}`。`copy` は節の写し（`prereg/plan-section-<日付>.md`） |
| `protocol` | research.yaml の `protocol` をキー順に並べた YAML の `sha256` と、その中身（`frozen`） |
| `history` | 凍結し直した記録（`rl prereg freeze --refreeze --reason "…"`。人の承認を受けてだけ） |

ルール
- `rl prereg check` が 1 を返したら（事前登録が変わっている）、元に戻すか、blockers に書いて人に確認する。エージェントが自分で凍結し直さない。
