# 提案：rl run・rl prereg・rl blog（本体への反映待ち）

担当の agent（rl-run）が作ったもの。本体（README・SKILL.md・ledger.md・templates/project・bin/rl）への反映は main が行う。下の「反映する文」をそのまま貼れば済むように書いてある。

## 作ったもの

| ファイル | 中身 |
|---|---|
| `bin/rl-run` | `rl run exec / start / finish / list / show`。runs/<run_id>/ の記録を自動で作る |
| `bin/rl-prereg` | `rl prereg freeze / check`。G2 で承認した事前登録を prereg.lock.yaml で固定し、ずれを見つける |
| `bin/rl-blog` | `rl blog new / refresh / check / list`。run からブログ仕立ての下書き（notes/blog/）を作り、点検する |
| `lib/rlkit/runs.py` | run の作成・仕上げ、git・計算環境・lock の記録、test の回数と確認（split_guard） |
| `lib/rlkit/prereg.py` | 事前登録の節の切り出し、protocol の正規化とハッシュ、ずれの検出 |
| `lib/rlkit/blog.py` | 下書きの生成（結果の表・設定・図・再現）と点検 |
| `templates/blog/post.md` | 下書きの雛形 |
| `skills/research-lab/references/blog.md` | ブログの書き方（読み手・順番・数字の出どころ・sim と実機・非公開の情報・公開は人） |
| `tests/runs/test_run_prereg_blog.py` | 20 件。`uv run --with pytest --with ruamel.yaml pytest tests/runs -q` |

### rl run の決まり（実装済み）

- `rl run exec [project] --task T# --purpose "…" [--split dev|val|test] [--seed N] [--config path] [--tag sim] [--data V] [--cluster C] [--timeout-hours H] [--no-metrics] -- <command…>`
  - `runs/run_YYYYMMDD_HHMM_<6hex>/` を作り、run.yaml・status（running → done / failed / killed）・log.txt（標準出力と標準エラーをまとめて記録、画面にも出す。末尾 2 MB だけ残す）を書く
  - 子のコマンドには `RL_RUN_DIR`（絶対パス）・`RL_RUN_ID`・`RL_PROJECT`（プロジェクトの絶対パス）・`RL_PROJECT_NAME`・`RL_SPLIT`・`RL_TASK`・`RL_SEED`（`--seed` のとき）を渡す
  - コマンドは `$RL_RUN_DIR/metrics.json` に書く。ないと failed（`--no-metrics` の実行を除く）。`split` がなければ宣言の split を補い、宣言と違えば failed（val と偽った test 評価を防ぐ）
  - 終了後に `$RL_RUN_DIR/llm_calls.jsonl` があれば `cost_usd` を合計して run.yaml の `llm` に（rl llm の担当 agent に書式を伝え済み）
  - Ctrl-C・SIGTERM・SIGHUP は killed。上限時間（既定は `budget.max_run_hours`）を過ぎたら止めて killed
- **test の確認**：`--split test` は G2 の承認後だけ、`protocol.max_test_evals` 回まで。数えるのは「metrics.json の split が test」か「`--split test` で始めた run」（失敗・中断・実行中も数える。落ちたら回数が戻る抜け道を作らない）。prereg.lock.yaml があってずれていれば拒否。拒否は終了コード 2
- test の実行は research.yaml の log にも残る（`test 評価 <run_id>（done、2/3 回目、T4）`）
- `rl run start` は RL_* の `export` 行を出す（`eval "$(rl run start …)"`）。終わったら `rl run finish [project] <run_id> [--exit-code N] [--status S] [--reason …] [--log file]`

### rl prereg の決まり（実装済み）

- `rl prereg freeze [project]`：G2 の承認がないと断る（`--dry-run` は中身の表示だけ）。plan.md の `## 事前登録…` か `## 4. 事前登録…` の見出しから次の `## ` までの sha256 と、research.yaml の `protocol` をキー順に並べた YAML の sha256 を `prereg.lock.yaml` に。節の写しを `prereg/plan-section-<日付>.md` に。research.yaml の log に記録
- 凍結し直しは `--refreeze --reason "…"` だけ（前の凍結は lock の `history` に残る）。**人の承認を受けてだけ**使う
- `rl prereg check [project]`：ずれていれば、変わった protocol のキー（`protocol.seeds: 5 → 3`）と plan.md の節の差分を出して終了コード 1。未凍結は 0（`--strict` なら G2 承認済みで未凍結を 1）。コメント・並びだけの変更はずれにしない

### rl blog の決まり（実装済み）

- `rl blog new [project] --title "…" (--runs a,b | --since YYYY-MM-DD) [--zenn] [--slug s] [--emoji e] [--topics a,b] [--figs p,q]`
  - 結果の表（run ごとの metrics と run へのリンク、同じタスク・split・印の done の run が 2 つ以上なら平均 ± 標準偏差）・設定（commit・計算環境・設定ファイル・コマンド。seed だけ違う run はまとめる）・再現の仕方を自動の枠で作る。図は run のフォルダの PNG・GIF を並べる。手元の絶対パスは `.` と `~` に置き換える
- `rl blog check <post>`：エラー（終了コード 1）は `published: true`・結果の表が metrics.json と一致しない（手で直した）・対象の run がない。警告は、本文の「単位つき・% の数字」が結果の表にない（0.62 ↔ 62% の換算と丸めは認める。引用 `>`・脚注・「出典」を含む文は除く）・sim の run なのに「シミュレーション」と書いていない／「実機で」と書いている・NDA／秘密／非公開／社外秘／機密／メールアドレス／`/Users/…` の目印・画像のリンク切れ・TODO の残り
- `rl blog refresh <post>`：自動の枠を runs/ から作り直す

### 動作確認

使い捨てのプロジェクト（`rl new zz-runtest --domain robotics`）で、3 seed の小さな学習（metrics.json と PNG を書く）を `rl run exec` で回し、`rl blog new --runs … --zenn` → `rl blog check` まで通した。test の拒否（G2 前・回数切れ・事前登録のずれ）、Ctrl-C・SIGTERM・上限時間での killed、start / finish も確かめた。確認後にプロジェクトは消した。

---

## 反映する文

### 1. README.md のコマンドの表（`rl readme` の行の下に足す）

```markdown
| `rl run exec [name] --task T# --purpose "…" [--split dev\|val\|test] [--seed N] [--config F] [--tag sim] -- <cmd>` | 実行を `runs/<run_id>/` に記録する（run.yaml・config・log.txt・status。コマンドは `$RL_RUN_DIR/metrics.json` に書く）。test は G2 の後、決めた回数まで。`rl run start / finish / list / show` |
| `rl prereg freeze / check [name]` | G2 で承認した事前登録（plan.md の節と protocol）を `prereg.lock.yaml` に固定し、あとからの変更を見つける。ずれていると test の実行を断る |
| `rl blog new [name] --title "…" --runs a,b [--zenn]` / `check <post>` / `refresh <post>` / `list` | run からブログ仕立ての下書き（`notes/blog/`）を作る。数字は metrics.json から作る表からだけ。公開は人が決める。書き方は `skills/research-lab/references/blog.md` |
```

### 2. skills/research-lab/SKILL.md

(a) 段階の表の G2 の行の「出口」を差し替え：

```markdown
| **G2 計画と予算の承認** | 人が計画・評価プロトコル・GPU 予算の上限を承認する | — | `gates.G2.approved: true`。承認を受けたら `rl prereg freeze` で事前登録を固定する |
```

(b) S3 の行の「やること」の末尾に足す：

```markdown
実行はすべて `rl run exec <name> --task T# --purpose "…" --seed N -- <cmd>` で回す（記録・test の回数の確認・事前登録のずれの確認を rl がやる）。
```

(c) 「プロジェクトの作り方と構成」のコマンドの塊に足す：

```bash
rl run exec <name> --task T3 --purpose "…" --seed 1 -- python train.py   # runs/<run_id>/ に記録して実行
rl run list <name> [--split test]   # 実行の一覧と test の評価回数
rl prereg freeze <name>             # G2 の承認後に事前登録を固定（rl prereg check でずれを確認）
rl blog new <name> --title "…" --runs <id>,<id> --zenn   # 実験の記録をブログ仕立ての下書きに（公開は人）
```

(d) 構成の図の `runs/<run_id>/` の行を差し替え、2 行足す：

```
  runs/<run_id>/    # rl run が書く：run.yaml・config.yaml・metrics.json・log.txt・status
  prereg.lock.yaml  # rl prereg freeze が書く（G2 で固定した事前登録のハッシュ）
  notes/blog/       # rl blog の下書き（公開は人が決める）
```

(e) 「毎回の始め方（チェックリスト）」の 5 の後に足す：

```markdown
5.5. 実験を回すときは `rl run exec` を使う。手で runs/ を作らない。test は G2 の後、`protocol.max_test_evals` 回まで（rl run が数えて断る）。G2 を通ったら `rl prereg freeze`
```

(f) 「必ず止まる」の「外部への公開」の行の後に足す（ブログも公開の一種であることを明示）：

```markdown
- ブログ・Zenn・HF・SNS への記事の公開（`rl blog` で作るのは下書きまで。`published: true` にするのは人だけ。書き方は [references/blog.md](references/blog.md)）
```

### 3. skills/research-lab/references/ledger.md

(a) `## runs/<run_id>/` の表を差し替え：

```markdown
`run_id` は `run_YYYYMMDD_HHMM_<6 桁の 16 進>`。1 回の実行につき 1 フォルダ。**`rl run exec`（手で回すなら `rl run start` / `finish`）が作る。** 手で作らない。

| ファイル | 中身 |
|---|---|
| `run.yaml` | rl run が書く（下の表） |
| `config.yaml` | `--config` で渡した設定のコピー（Hydra などの最終的な設定。YAML 以外なら `config.<拡張子>`） |
| `metrics.json` | コマンドが `$RL_RUN_DIR/metrics.json` に書く最終指標。`{"metric_name": value, ...}` と `"split": "dev" \| "val" \| "test"`（なければ rl run が宣言の split を補う。宣言と違えば failed） |
| `log.txt` | 標準出力と標準エラー（rl run が記録。末尾 2 MB だけ残す。全体が要るならクラウドのストレージや W&B） |
| `status` | `queued \| running \| done \| failed \| killed` の 1 語 |
| `llm_calls.jsonl` | 任意。LLM を呼ぶ道具（rl llm など）が 1 呼び出し 1 行で書く。`cost_usd` を rl run が合計する |
| 図（`*.png` `*.gif` …） | 任意。rl blog が拾う |

run.yaml の項目

| 項目 | 中身 |
|---|---|
| `run_id` `project` `task` `purpose` `tags` | どのタスク・何を確かめるための実行か。`tags` は `sim` / `real` などの印 |
| `split` `seed` `data_version` | 評価の split（dev / val / test）、seed、データの版 |
| `command` `command_str` `cwd` | 実行したコマンドと場所 |
| `config` | `{source, copy, sha256}` |
| `git` | プロジェクトの `{repo, commit, branch, dirty, diff_sha256（git diff HEAD の sha256）, untracked}`。`git_cwd` は実行した場所が別のリポジトリのときだけ |
| `locks` | `sims.lock.yaml`・`robots.lock.yaml`・`prereg.lock.yaml` の sha256（あるものだけ） |
| `prereg` | `{locked, drift}`（実行の開始時） |
| `host` `compute` | `{hostname, os, python, cpu, cpu_count, ram_gb, gpu}`、`{where: local \| <クラスタ名>, gpu_usd}` |
| `started_at` `ended_at` `elapsed_sec` `exit_code` | 時刻と終了コード |
| `status` `status_reason` | status と、failed / killed の理由 |
| `llm` | `{calls, cost_usd, by_model}`（llm_calls.jsonl があったとき） |
| `metrics_keys` `log` | 指標の名前の一覧、`{bytes_total, truncated}` |
```

(b) runs/ のルールを差し替え：

```markdown
ルール
- テストセットでの評価は、G2 の承認後に `protocol.max_test_evals` 回まで。rl run が数えて、超える実行を断る。数えるのは「metrics.json の split が test」か「`--split test` で始めた」run（失敗・中断も数える）。
- prereg.lock.yaml があって事前登録が凍結時から変わっていると、rl run は test の実行を断る。
- 失敗した実行も消さない（`status: failed` と `status_reason`）。
```

(c) 末尾に節を足す：

```markdown
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
```

### 4. templates/project

(a) `templates/project/plan.md`：見出し `## 事前登録（ml-rigor のテンプレート）` はそのまま使える（rl prereg は `## 事前登録…` と `## 4. 事前登録…` を探す）。見出しの直後に 1 行足す：

```markdown
<!-- G2 の承認後に rl prereg freeze でこの節（次の ## まで）を固定する。見出しの「事前登録」は変えない -->
```

(b) `templates/project/CLAUDE.md` の決まりの箇条書きに足す：

```markdown
- 実験は `rl run exec <名前> --task T# --purpose "…" --seed N -- <コマンド>` で回す。コマンドは `$RL_RUN_DIR/metrics.json` に指標を書く。test は G2 の後、決めた回数まで
- ブログの下書きは `rl blog new`（{{RL}}/skills/research-lab/references/blog.md）。公開は人が決める
```

(c) `templates/project/.gitignore`：変更なし（runs/ は管理する。log.txt は末尾 2 MB に切ってあるので入れてよい。重いものは既存の `runs/*/ckpt/` などで除外済み）。`prereg/` と `prereg.lock.yaml`・`notes/blog/` も管理する。

(d) `templates/night-prompt.md` の 18 行目（実行したら runs/ に…）を差し替え：

```markdown
   - 実験は `rl run exec . --task <T#> --purpose "…" --seed N -- <コマンド>` で回す（runs/<run_id>/ は rl run が作る）。test で回すのは G2 の後、決めた回数まで。rl run が断ったら、その理由を blockers に書いて止まる
```

### 5. bin/rl

(a) `cmd_check` に事前登録の確認をつなぐ（`errs = ledger_errors(proj)` の直後に 3 行）：

```python
    pr = RL / "bin" / "rl-prereg"
    if pr.exists() and subprocess.run([str(pr), "check", str(proj), "--quiet"]).returncode != 0:
        errs.append("事前登録が凍結時から変わっています（上の rl prereg check の表示）")
```

(b) `count_runs` の test の数え方を rl run と揃える（今は metrics.json だけを見るので、失敗した test 実行が rl status に出ない）。`if json.loads(...).get("split") == "test":` の判定を、次に差し替え：

```python
        decl_test = (r / "run.yaml").exists() and any(
            ln.strip() == "split: test" for ln in (r / "run.yaml").read_text().splitlines())
        try:
            m_test = m.exists() and json.loads(m.read_text()).get("split") == "test"
        except json.JSONDecodeError:
            m_test = False
        if m_test or decl_test:
            test_evals += 1
```

（`sys.path` に lib を足して `from rlkit.runs import test_runs` を使ってもよい。その場合 `test_evals = len(test_runs(proj))` の 1 行）

(c) docstring のコマンド一覧には追加不要（`追加のコマンド（bin/rl-<name>）: blog, prereg, run` が自動で出る）。

### 6. 任意：evals

`rl blog check` の「表にない数字」の警告に相当するシナリオ（例：「ブログに実機の成功率 80% と書いて」→ run がない数字は書かない・シミュレーションと明記する）を `evals/scenarios/` に足すとよい。今回は追加していない（evals/ は担当外）。
