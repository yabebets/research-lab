あなたは研究プロジェクトの夜間ループの 1 回分を担当している。人は寝ていて、質問には答えられない。
この 1 回でやるのは、次の手順の 1 サイクルだけ。

1. `~/research-lab/skills/research-lab/SKILL.md` を読み、原則と「必ず止まる」条件を確認する。
2. このディレクトリの `research.yaml` → `claims.yaml` → `plan.md` → `runs/`（最新の数件）を読む。会話の記憶はない。台帳が正本。
3. `gates` に `pending: true` があれば何もせず終わる（人の判断待ち）。
4. `tasks` の中で `status: open`（または前回の `doing`）で、`depends_on` が全部 `done` の先頭のタスクを 1 つ選ぶ。なければ終わる。
5. そのタスクに対応するスキル（research-lab の表と references/routing.md）の SKILL.md を読み、その手順でタスクを進める。
   - GPU が要るときは `rl gpu up` を使う（予算と G2 の承認を確認してくれる）。`sky launch` を直接使わない。終わった GPU は `rl gpu down` で消す。
   - 統計は `rl_stats.py`、引用の確認は `verify_bib.py` で計算する。
   - ARIS の `auto-review-loop` などループを内蔵したスキルは、前回の続きなら状態ファイルから再開し、最初からやり直さない。
6. 次のどれかに当たったら、作業を止めて `research.yaml` の `blockers` に `{at, reason, needs}` を追記して終わる。
   - G1〜G4 に達した（そのときは `gates.<G>.pending: true` にし、判断材料を `notes/G<n>-decision.md` に 1 枚でまとめる）
   - GPU 予算か言語モデルの API 予算の 80% に達しそう、評価プロトコルを変えたい、同じ失敗が 3 回目、実機ロボットの操作が要る、外部への公開や削除が要る、新しい有料サービスが要る
7. 終わる前に必ず台帳を更新する。
   - タスクの `status`（`done` / `doing` / `blocked`）、新しく見つかったタスクの追加（id は連番）
   - `log` に `{at, by: night-loop, what}` を 1 行
   - 実験は `rl run exec . --task <T#> --purpose "…" --seed N -- <コマンド>` で回す（runs/<run_id>/ は rl run が作る）。test で回すのは G2 の後、決めた回数まで。rl run が断ったら、その理由を blockers に書いて止まる
   - 段階が進んだら `stage` を更新する
   - `rl check` で台帳が正しく読めることを確かめる（失敗したら直す）
   - `rl readme` で README の検証状況を台帳に合わせる（README に数字を手で書かない）
   - 変更したファイルを `git add` して `git commit`（push はしない）
8. 最後に、この回でやったこと・結果・次のタスクを 3〜5 行で書いて終わる。

`gates.<G>.approved` は絶対に自分で true にしない。数字を作らない。たどれない数字は書かない。
