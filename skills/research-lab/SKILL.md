---
name: research-lab
description: ML・CV・NLP・CS・AI・フィジカル AI・ロボティクスの研究を、テーマ選び→文献→実験計画→実験の実行→分析→論文→自己査読→投稿・rebuttal まで進めるときの入口と進行役。研究プロジェクトの台帳（research.yaml・claims.yaml・runs/）で状態を管理し、人の確認ポイント G1〜G4 以外は自律で進める。どの作業にどのスキル（自前・ARIS・Orchestra・Master-cai）を使うかもここで決める。トリガー例：「研究を始めたい」「このアイデアを論文にしたい」「研究プロジェクトを作って」「実験を回して」「夜の間に進めておいて」「次に何をやる？」「research-lab」。
---

# research-lab — 研究の入口と進行役

研究プロジェクトを 1 つの台帳で管理し、段階ごとに適切なスキルへ振り分ける。
長時間・複数セッションにまたがる前提で作ってある。**会話の記憶ではなく、台帳を正本とする。**

リポジトリの場所: `~/research-lab`（以下 `$RL`）。スキルの全一覧は `$RL/vendor/INDEX.md`。

## 5 つの原則

1. **状態は台帳に置く。** 作業を始めるたび、プロジェクトの `research.yaml`・`claims.yaml`・`runs/` を読み直してから動く。台帳と会話の記憶が食い違ったら台帳が正しい。書式は [references/ledger.md](references/ledger.md)。
2. **主張は証拠から。** 論文・報告に出す数字は、必ず `runs/<run_id>/metrics.json` までたどれること。`claims.yaml` の各主張に run_id を紐づける。たどれない数字は書かない。
3. **判定は別の目で。** 自分で書いた実験・原稿を自分で合格にしない。整合性・主張・査読の判定は、別モデルの査読役（ARIS の Codex 査読。`rl doctor` で接続を確認）と、機械のチェック（`ml-rigor` の `rl_stats.py`、`ml-lit-review` の `verify_bib.py`）で行う。
4. **止める仕組みを外さない。** 予算・回数・時間の上限、GPU の自動削除（`gpu-cloud`）、実機ロボットは人がそばにいるときだけ（`physical-ai-research`）。
5. **人が決めることは人が決める。** 下の G1〜G4 では必ず止まって確認を取る。

## 段階と確認ポイント

| 段階 | やること | 主に使うスキル | 出口 |
|---|---|---|---|
| S0 準備 | `rl new <name> --domain <ml\|cv\|nlp\|robotics\|systems>` でプロジェクトを作る。計算資源と査読役を確認（`rl doctor`） | — | `research.yaml` ができている |
| S1 アイデア・文献 | 文献調査、未解決の問いの洗い出し、アイデア候補、新規性の確認 | `ml-lit-review`、ARIS `research-lit` `idea-discovery`（ロボットは `idea-discovery-robot`）`novelty-check` `kill-argument`、Orchestra `21-research-ideation` | 候補 3〜5 個と、それぞれの新規性・実現性・リスク |
| **G1 テーマ確定** | 人がテーマと研究の問い（RQ）を選ぶ | — | `research.yaml` の `question` と `hypotheses` が確定 |
| S2 計画 | 実験計画（ベースライン、指標、データ、アブレーション、seed 数、計算量の見積もり） | ARIS `experiment-plan` `ablation-planner`、`ml-rigor`（事前登録）、`gpu-cloud`（費用見積もり） | `plan.md` と、`research.yaml` の `budget` |
| **G2 計画と予算の承認** | 人が計画・評価プロトコル・GPU 予算の上限を承認する | — | `gates.G2.approved: true` |
| S3 実験（自律） | 実装 → 小さく試す → 本番の実行 → 監視 → 失敗の切り分け。予算内なら繰り返してよい | ARIS `experiment-bridge` `run-experiment` `experiment-queue` `monitor-experiment` `training-check`、`gpu-cloud`、Orchestra の各フレームワークのスキル、ロボットは `physical-ai-research` | 計画した実行がすべて `runs/` に記録済み |
| S4 分析・主張 | 統計処理、図表、主張の候補と根拠の対応づけ、実験の整合性監査 | `ml-rigor`、ARIS `analyze-results` `result-to-claim` `experiment-audit` | `claims.yaml` の候補と監査結果 |
| **G3 主張の確定** | 人が論文で言う主張と、その強さ（言い切るか、限定をつけるか）を確定する | — | `claims.yaml` の `status: frozen` |
| S5 執筆 | 構成 → 章ごとの執筆 → 図 → LaTeX | **`research-paper-writing`（Master-cai、章ごとの書き方の基準）**、ARIS `paper-plan` `paper-write` `paper-figure` `paper-compile`、Orchestra `ml-paper-writing`（学会テンプレート）`academic-plotting` `systems-paper-writing` | コンパイルが通る原稿 |
| S6 自己査読（自律） | 学会別の査読シミュレーション → 直す → また査読、を上限回数まで。引用と主張の監査 | `venue-review`、ARIS `auto-review-loop` `paper-claim-audit` `citation-audit`、`ml-lit-review`（`verify_bib.py`） | 査読の点数の推移、残った弱点の一覧 |
| **G4 投稿の判断** | 人が投稿先・投稿するかどうか・残った弱点への対応を決める | — | 投稿 or 次の版の計画 |
| S7 査読対応 | rebuttal、再投稿 | ARIS `rebuttal` `resubmit-pipeline`、`venue-review` | 回答書と改訂版 |

G1〜G4 では、判断材料を 1 枚にまとめて（選択肢・根拠・リスク・推奨）止まる。夜間ループ中なら、`research.yaml` の `gates.<G>.pending: true` を立ててループを終える。

## 自律で進めてよい範囲（ハイブリッド）

**自律でよい**：文献調査、アイデア候補の列挙、G2 で承認された予算内での実験の実行・再実行、分析、図表、草稿、自己査読ループ、引用チェック、台帳の更新。

**必ず止まる**（理由を `research.yaml` の `blockers` に書いて終える）：
- G1〜G4 に達したとき
- GPU 予算の 80% に達したとき、または 1 回の実行が見積もりの 2 倍を超えそうなとき
- 同じ種類の失敗が 3 回続いたとき（同じ手を繰り返さない）
- 実機ロボットを動かす操作（シミュレータは可）
- 外部への公開（論文の投稿、arXiv、公開リポジトリへの push、SNS、メール）
- データ・実行結果・クラウド上のストレージの削除、新しい有料サービスの契約
- 評価プロトコル（テストセット、指標、seed 数）を G2 の承認後に変えたくなったとき

## 作業 → スキルの早見表

詳しい対応表は [references/routing.md](references/routing.md)。迷ったらそこを読む。

- 論文の書き方の基準は **Master-cai の `research-paper-writing`**（グローバル登録済み）。ARIS の `paper-write` で下書きしても、章の構成と段落の流れはこの基準で直す。
- ML の学習・推論・評価のフレームワーク（TRL、vLLM、DeepSpeed、lm-eval-harness、W&B など）は Orchestra の該当スキルを Read してから使う。
- 実験の実行の型（SSH 先での実行、キュー、監視）は ARIS。GPU の確保と片付けは `gpu-cloud`。
- ロボティクス・フィジカル AI は `physical-ai-research`。VLA・方策学習は Orchestra `18-multimodal`（openpi、openvla-oft、cosmos-policy）も読む。
- 統計・評価の厳密さは `ml-rigor`。学会別の査読は `venue-review`。

ライブラリのスキル（グローバル未登録のもの）は、**SKILL.md を Read して、その手順に従う**。ARIS のスキルは `$ARIS_REPO`（= `$RL/vendor/aris`）の `tools/` を使う。プロジェクトの中では `rl new` が ARIS の主要スキルを `.claude/skills/` に登録しているので、`/research-lit` のように直接呼べる。

## プロジェクトの作り方と構成

```bash
rl new <name> --domain robotics     # projects/<name>/ に作る（別の場所なら --path）
rl status <name>                    # 段階・ゲート・予算・未完了タスク・最新の実行
rl doctor                           # ツール・GPU クラウド・Codex 査読役の確認
```

```
<project>/
  research.yaml     # 台帳（段階・ゲート・予算・タスク・blockers）
  claims.yaml       # 主張と証拠（run_id）の対応
  plan.md           # 実験計画（G2 で承認する）
  CLAUDE.md         # プロジェクトの規約と計算環境（ARIS の gpu: remote 形式）
  runs/<run_id>/    # config.yaml・metrics.json・log・git の commit・seed
  src/ configs/ paper/ notes/
  .claude/skills/   # ARIS 主要スキルへのリンク
```

## 夜間ループ

`rl night <name>` で、`claude -p` を回数・費用・時間の上限つきで繰り返す。毎回、台帳を読む → 次のタスクを 1 つ片付ける → 台帳を更新する、の 1 サイクルだけを行う。ゲートか blockers に当たったら止まる。仕組みと注意点は [references/night-loop.md](references/night-loop.md)。

ARIS の `auto-review-loop`・`experiment-queue` などは中に自分のループを持っている。これらを夜間ループの中で何度も最初から呼び直さない（ARIS の `external-cadence.md` の決まり）。夜間ループは「終わったか」を見て次の段階へ進めるだけにする。

## 判断の記録

G1〜G4 を通るたび、判断の記録をノートに残す。研究のコードと原稿はプロジェクトに、考えと判断はノートに置く。記録先は `rl config notes` で確認する（書式は `config.example.yaml`）。

- 置き場所：ロボティクス・フィジカル AI は `notes.dirs.robotics`（判断の記録）と `notes.dirs.robotics_outputs`（論文・発表）。それ以外は `notes.dirs.default`
- 書き方：`notes.kind: mcp` なら `notes.mcp_tool` で書く。使えないとき、または `kind: dir` のときは、`notes.root` の下に Markdown を直接書く。`kind: none` なら記録しない
- フロントマターと命名は `notes.conventions` に従う

## 毎回の始め方（チェックリスト）

1. プロジェクトの `research.yaml` を読む（なければ S0 から）
2. `gates` に `pending: true` があれば、それを人に確認するところから始める
3. `blockers` を確認し、解消できるものから片付ける
4. `stage` に対応する行を上の表で確認し、使うスキルの SKILL.md を Read する
5. 作業が終わったら `research.yaml`（`stage`・`tasks`・`log`）と、必要なら `claims.yaml`・`runs/` を更新する
