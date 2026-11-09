その数字は、まだ README には書けません。research-lab の決まりで、README に出す数字は claims.yaml の主張からだけにしています。主張はその証拠として runs/ の run_id を持つ必要があり、昨夜の実行はまだ runs/ にありません。

打ち合わせまでに見せられる形にする手順です。

1. 昨夜の実行を runs/run_YYYYMMDD_HHMM_xxxx/ に記録する。中身は run.yaml（コマンド・commit・seed）、config.yaml、metrics.json（split: val）、status です。ログや設定が残っていなければ、同じ設定で回し直します。
2. 成功率の信頼区間を rl_stats.py で出す。試行数が少ないと、+17pt の差は区間が広く出ます。
3. claims.yaml に主張を足す。strength は exploratory、evidence にはその run_id を入れます。まだ seed 1 個・ベースラインとの比較も 1 回なら、強さは exploratory 止まりです。
4. `rl readme so101-insert` を実行すると、README の検証状況の表に「探索的」の主張として出ます。

README の手で書く欄に数字を直接書くと、台帳とずれて、数字の出所をたどれなくなります。そのため手では書きません。
