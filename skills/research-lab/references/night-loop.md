# 夜間ループ（rl night）

## 仕組み

```
rl night <project> [--iterations 20] [--budget-usd 10] [--hours 8]
```

1. プロジェクトに移動し、`flock` 相当のロックで二重起動を防ぐ
2. 1 回ごとに `claude -p` を新しいセッションで起動する（会話を持ち越さない）
   - 渡すプロンプトは `templates/night-prompt.md`（台帳を読む → 先頭の open タスクを 1 つ → 台帳を更新）
   - `--max-budget-usd` で 1 回あたりの費用、`timeout` で 1 回あたりの時間を制限
   - `--permission-mode dontAsk` と許可ツールの一覧で、許可していない操作は聞かずに拒否
3. 終わるたびに `research.yaml` を見て、次のどれかなら止まる
   - `gates.*.pending: true` が立った（人の判断待ち）
   - `blockers` が増えた
   - open のタスクがない
   - 合計の費用・回数・時間が上限に達した
4. ログは `<project>/.night/<日時>/iter-NN.log`、要約は `<project>/.night/<日時>/summary.md`

## どこで回すか

- 手元の Mac で回すなら `caffeinate -i rl night ...`（スリープ防止）
- 手元のマシンが重いときは、設定の `compute.worker_host`（`rl config compute.worker_host`）の tmux で回す（`ssh <host>`、`tmux new -s night`）。GPU の実験自体は RunPod / Lambda で動くので、ループ役はどこでもよい
- GPU は `gpu-cloud` が上限時間と自動削除つきで立てる。ループが途中で落ちても、`rl gpu reap` が期限切れの GPU を消す

## 夜間ループでやらないこと

- G1〜G4 の承認、評価プロトコルの変更、実機ロボットの操作、外部への公開、データの削除
- ARIS の `auto-review-loop`・`experiment-queue`・`experiment-audit` などを、毎回最初から呼び直すこと（中に自分のループや判定を持っている）。ループは「終わったか」を確認して次のタスクへ進めるだけ
- 失敗した同じ手を 3 回以上繰り返すこと（3 回目で blockers に書いて止まる）

## 朝の確認

```
rl status <project>      # 段階・ゲート・費用・未完了タスク・blockers・最新の実行
```

`summary.md` を読み、`gates.*.pending` があれば判断する。
