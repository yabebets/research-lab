# research-lab — このリポジトリで作業するときの決まり

研究のスキル一式を開発・保守するリポジトリ。研究そのものは `projects/<名前>/`（別リポジトリ）で行う。

- `vendor/` は上流の git subtree。**手で直さない**。直したいときは自前の skills/ 側に上書きの手順を書くか、上流に PR を出す
- 上流の更新は `rl sync`（`--squash` は使わない）。取り込む範囲は `vendor/manifest.tsv`
- スキルを足したら `python3 scripts/build-index.py` で索引を作り直し、`rl link` で登録する
- スキルを直したら `python3 evals/run_evals.py` を回す。新しい失敗パターンを見つけたら、シナリオと合格例・不合格例を足す
- 統計・引用の確認はスクリプト（`rl_stats.py`・`verify_bib.py`）で行い、モデルの暗算にしない
- AERS（CC BY-SA）と ARS（CC BY-NC）の文章はコピーしない（考え方だけを参考にする）。MIT の上流は vendor/ に取り込んでよい
- 文章は日本語。ユーザー向けの文書は短く、です・ます調でなくてよい（既存のスキルの書き方に合わせる）
