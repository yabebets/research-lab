# 工程の正解の注釈（手順書 → IR v0.2）

ロボットの組立手順書から、工程の正解（L1 の型・属性・可否の軸・先行関係）を作る手順。道具は `rl annotate`、スキーマは `lib/rlkit/ir_schema_v0_2.json`（robot-assembly-bench の `notes/ir-design-2026-11-09.md` §2、`notes/taxonomy-draft-2026-11-09.md` §9–§10 に合わせたもの）。統計は `rl_stats.py`（`kappa`・`fleiss`・`alpha`）で計算し、暗算しない。

## 流れ

| 段 | すること | コマンド |
|---|---|---|
| 1. 下書き | LLM に手順書・部品表・規則・スキーマを渡して IR を書かせる。**下書きのモデルは評価する言語モデルと別にする** | `rl annotate draft <project> <robot> --manual m.txt --out a/<robot>.yaml --model M [--call]` |
| 2. 機械の確認 | スキーマと意味のチェック（ID の重複、参照、BOM、必須の辺の閉路、order_only を required にしていないか、出所の欠け、L2↔L1 の対応） | `rl annotate validate a/<robot>.yaml` |
| 3. 人の確認 | 1 行＝L1 × 項目のシートで、全件を ok / change で決める。change には理由を書く | `rl annotate review … --sheet s.csv` → 埋める → `rl annotate apply … --sheet s.csv --reviewer <名前>` |
| 4. 二重注釈 | L1 の 20% を型で層別して選び、2 人目が最初の注釈を見ずに付ける | `rl annotate sample a/<robot>.yaml --frac 0.2 --seed 0 --out ids.txt --blank b/<robot>.yaml` |
| 5. 一致 | 項目ごと（型・fix_state・scope・可否の 8 軸・先行関係の kind と source）に κ と α、ブートストラップの CI | `rl annotate agree a/<robot>.yaml b/<robot>.yaml --ids ids.txt` |
| 6. 規則の改訂 | κ < 0.6 の項目は決め方の文を直し、直した規則で付け直して測り直す。CI の下限が 0.6 未満の項目も記録する | taxonomy の改訂の節に書く |

- `draft` は `--call` を付けなければ、プロンプトの包み（`<out>.prompt/`：prompt.md・rules.md・schema.json・手順書・meta.json）を書くだけで費用はかからない。`--call` は `rlkit.llm` を通して呼び、記録・費用・予算は `rlkit.llm` の決まりに従う
- 確認シートの `draft_value` は書き出したときの値。`apply` は、いまの値がこれと違う行があると何も書き換えずに止まる（シートを作った後にファイルが変わった）
- 人が変えた値は `src: annotator`（本文で確かめたなら `new_src` に `stated` などを書く）。変更は L1 の `review.changes` に、元の値・新しい値・理由・人・日時で残る。理由の一覧は規則の改訂の材料になる
- 2 人目の空欄のファイルは L1 の切り方（ID・l2_refs・parts_in）だけを同じにし、値と辺は空にする。L1 の切り方そのものの一致はこの手順では測らない（切り方の規則は taxonomy §9.1・findings §6）

## 出所（src）の意味

| 値 | 意味 | 評価の入力に使えるか |
|---|---|---|
| `stated` | 手順書の本文に書いてある | 使える |
| `cad` / `bom` | CAD・部品表から読める | 使える |
| `rule` | 型などからの規則で決めた（例：SCR → 工具はドライバー） | 使えない（正解の側） |
| `sim` / `rule+sim` / `sim-uncertain` | シミュレーションの判定。すきま・摩擦を振ると変わるなら sim-uncertain | 使えない |
| `borrowed[:robot]` | 他機種の手順書から借りた（SO-100 のねじ寸法を SO-101 から） | 使えない |
| `annotator` | 人の推論・判断（確認で変えた値もこれ） | 使えない |
| `execution` | 実行して確かめた | 使えない |

- 値が `null`・`unknown`・`not_checked`・`not_run` のときは出所がなくてよい。それ以外の値に出所がなければ `validate` のエラー
- 結果は出所の層ごとに分けて報告する（taxonomy §10.2）。`rule` の正解だけで「能力」を主張しない

## 決まり

1. **下書きのモデル ≠ 評価するモデル。** 一覧は research.yaml の `protocol.evaluated_models`、なければ plan.md の「言語モデルは」の行から読む。同じ系統（`gpt-5` と `gpt-5-mini` など）も断る。会社名（`anthropic`）が登録簿で評価対象に解決される場合も断る。下書きのモデル名は `annotation.drafted_by` と各 L1 の `review.drafted_by` に残る
2. **G2 の前にテストの機種を注釈しない。** スキーマの確かめだけは `--dry-run-schema` で行い、`annotation.dry_run_schema: true` が付いたものは正解に使わない。テストの機種は research.yaml の `protocol.test_split`、なければ plan.md §1 の「テスト」の行
3. **NC ライセンスの開発用データの注釈は配らない**（ToddlerBot は CC BY-NC-SA）。`--license` に NC を含めると `source.redistribution: restricted` を付ける。外に出すなら同じ条件で
4. 本文に書いていないことを `stated` にしない。両手が要るかを人の推論で埋めない（`hold_needed` は sim で決める）。`human_required: yes` は独立の根拠（手順書が人の判断を明記、柔軟物の経路づけ）を `reason` に書けるときだけ
5. 先行関係は L1 の ID で書く。`order_only`（本文の並びだけ）の辺は記録するが正解に入れない（kind は null）。必須の辺（required）に閉路があれば validate のエラー
6. 一致の数字は `rl annotate agree` の出力（rl_stats.py）をそのまま使う。`unknown` も 1 つの値として数える（`--drop-unknown` で欠けにした値も併記できる）。κ が定義できない（全件同じ値）項目は一致率だけを書く

## v0.1 の試し書きからの移行

`rl annotate convert-v01 <v0.1.yaml> --out <v0.2.yaml> --report r.md`。隣り合う placed → fixed を 1 つの L1 にまとめ、L2 の辺を L1 に展開し、辺の kind をメモの言葉から推定する（「逆順も可」「後でも」→ recommended、geometry → required、ただし L2 の辺を複数の L1 の組に広げた場合と「要 CAD」は unknown）。推定したもの・不明にしたものはレポートに全部出る。変換した値はすべて `review.status: draft` で、人の確認の前に正解として使わない。
