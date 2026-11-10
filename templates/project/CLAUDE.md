# {{PROJECT}} — 研究プロジェクト

このプロジェクトは `research-lab` スキルで進める（{{RL}}/skills/research-lab/SKILL.md）。
作業を始めるたび、`research.yaml` → `claims.yaml` → `runs/` の順に読み直すこと。台帳が正本。

- 分野: {{DOMAIN}}
- 人の確認ポイント: G1 テーマ / G2 計画と予算 / G3 主張 / G4 投稿。`approved` はエージェントが自分で立てない
- 数字は runs/<run_id>/metrics.json にたどれるものだけを書く
- 実験は `rl run exec <名前> --task T# --purpose "…" --seed N -- <コマンド>` で回す。コマンドは `$RL_RUN_DIR/metrics.json` に指標を書く。test は G2 の後、決めた回数まで
- 実験の中で言語モデルを呼ぶときは {{RL}}/lib/rlkit/llm.py の `call()`・`tool_loop()` を使う（記録・費用・予算。上限は research.yaml の `budget.llm_usd_cap`）
- 統計は {{RL}}/skills/ml-rigor/scripts/rl_stats.py で計算する
- 引用は {{RL}}/skills/ml-lit-review/scripts/verify_bib.py で確かめる
- 実機ロボットを動かす操作は、人がそばにいると確認できたときだけ
- 外部への公開（投稿・arXiv・公開リポジトリへの push・SNS）はしない
- ブログの下書きは `rl blog new`（{{RL}}/skills/research-lab/references/blog.md）。公開は人が決める

## 計算環境（ARIS の run-experiment が読む）
<!-- rl gpu up が立てたクラスタを使う。クラスタ名は rl gpu status で確認 -->
## Remote Server
- gpu: remote
- SSH: `ssh <rl gpu up が表示したクラスタ名>`
- Code dir: `~/sky_workdir`
- code_sync: rsync
- wandb: false

## Local
{{LOCAL}}
