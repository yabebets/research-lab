# 実験の記録をブログ仕立てにする

runs/ に残した実験を、専門外の人にも読める記事の下書きにする。目的は学習ログと共有。論文ではない（論文は `research-paper-writing`）。
**ここで作るのは下書きまで。** Zenn・Hugging Face・SNS・ブログへの公開は人が決める。

## 流れ

```bash
rl blog new <project> --title "…" --runs <id1>,<id2> --zenn --slug so101-act-first-try   # 下書きを作る
#   --since 2026-11-01 で、その日以降に終わった run を全部。--figs notes/figs/x.png で図を足す
# TODO を埋める（下の書き方）
rl blog check notes/blog/2026-11-10-so101-act-first-try.md    # 点検
rl blog refresh notes/blog/…md                               # run を足した・作り直したあと、表を作り直す
rl blog list <project>
```

下書きは `notes/blog/YYYY-MM-DD-<slug>.md`。雛形は `templates/blog/post.md`。

| 節 | 誰が書くか |
|---|---|
| 何をしたか / なぜやったか / どうやったか（本文） | 書き手（Claude か人）。TODO を埋める |
| どうやったか（設定・コマンド・commit） | **rl blog が run.yaml から作る**（自動の枠） |
| 結果（表） | **rl blog が metrics.json から作る**（自動の枠）。本文の数字の出どころはここだけ |
| 図 | rl blog が run のフォルダの PNG・GIF を並べる。説明の 1 行は書き手 |
| 分かったこと・うまくいかなかったこと / 次にやること | 書き手 |
| 再現の仕方 | rl blog が作る（commit・seed・コマンド）。リポジトリの URL は書き手（公開するかは人） |

自動の枠（`<!-- rl:blog:auto:…:start -->` 〜 `end`）の中は手で直さない。結果の表を手で直すと `rl blog check` がエラーにする。

## 書き方

- **読み手は専門外の人。** 最初の 3 行で「何の話か・自分に関係あるか」が分かるように。専門用語は初出で一言説明する（例：「ACT（Action Chunking with Transformers、動きをまとめて予測する模倣学習の手法）」）
- **話の順番**：何をしたか → なぜ → どうやって → 結果 → 分かったこと・うまくいかなかったこと → 次。冒頭に 1 行のステータス（どこまで進んだか）
- **数字は結果の表からだけ。** 表にある値をそのまま引く（0.62 を「62%」と書くのはよい）。表にない数字（差・倍率・自分で計算した平均）は書かない。必要なら `rl_stats.py` で計算し、その結果を run の metrics.json に残してから `rl blog refresh`。他人の論文の数字は引用（`>`）か脚注（`[^1]`）で出典をつける
- **シミュレーションか実機かを毎回はっきり書く。** シミュレーションの結果は「シミュレーションで」と書く。`--tag sim` の run の結果を「実機で」と書かない。実機の成功率は試行数（n）も書く
- **言える範囲を守る。** seed や試行が少なければ「3 seed だけ」「予備的」と書く。1 回うまくいったことを「できるようになった」と書かない
- **失敗も書く。** うまくいかなかった run・ハマったこと・切り分けの過程は、学習ログとしていちばん役に立つ。表には失敗・中断した run も残る
- **図は run から。** 学習曲線・成功例の GIF などは、実行のときに `$RL_RUN_DIR` に保存しておく（rl blog が拾う）。図ごとに「何を示すか」を 1 行
- **非公開の情報を書かない。** NDA・共同研究の未公開の中身・事業化や出願の計画・人の評価・メールアドレス・手元の絶対パス（ユーザー名が出る）・認証情報。`rl blog check` が目印を警告する（全部は見つけられないので読み直す）
- **データ・モデルのライセンス**を確かめる。NC のデータで学習したモデルの配布や、許可のない画像の転載はしない

## 公開について

- `published: false` のまま渡す。`true` にするのは人だけ（`rl blog check` は `published: true` をエラーにする）
- Zenn・HF・SNS・個人ブログへ出すのは、人がはっきり OK と言ったときだけ。研究の「外への公開」と同じ扱い（`research-lab` の「必ず止まる」）
- `so101-lab` は公開の学習ログ（Zenn と同期、`articles/` と `images/<slug>/`）。ここで書いた下書きを、人があとで so101-lab の `articles/` に移すことがある。移すときは図を `images/<slug>/` にコピーして `/images/<slug>/…` に書き換え、run へのリンクは公開リポジトリの URL か削除にする（このとき表の数字は変えない）
- `--zenn` は Zenn の front matter（`title, emoji, type: "tech", topics, published: false`）で作る。slug は a-z0-9・`-`・`_` の 12〜50 文字が Zenn の決まり
