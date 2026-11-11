# rl annotate（工程の正解の注釈）— 作ったものと、本体への反映の案

担当の範囲：`bin/rl-annotate`、`lib/rlkit/annotate.py`、`lib/rlkit/ir_schema_v0_2.json`、`tests/annotate/`、`skills/ml-rigor/scripts/rl_stats.py`（一致の 3 つを追加。既存のサブコマンドは変えていない）、`skills/research-lab/references/annotation.md`（新規）。README・SKILL.md・ledger.md・テンプレート・プロジェクトのファイルは触っていない。コミットしていない。有料の API は呼んでいない。

## 作ったもの

| コマンド | すること |
|---|---|
| `rl annotate validate <file> [--ref other.yaml] [--strict]` | JSON Schema（IR v0.2）＋意味のチェック。ID の重複、L2・L3・BOM・template_of・included_with の参照、`<robot>:<bom_id>`（別機種は `--ref` で確認）、L2↔L1 の対応、出所の欠け、required の辺の閉路（閉路の経路を表示）、order_only を required にしていないか、規則との食い違い（scope・evaluator_support・human_required の根拠）。エラーは日本語で、どの L1 か ID 付き |
| `rl annotate convert-v01 <v0.1> --out <v0.2> [--report r.md]` | ir-trial の v0.1 を v0.2 に。隣り合う placed → fixed を 1 つの L1 に統合、L2 の辺を L1 に展開、辺の kind をメモの言葉から推定、可否を §10.1 の軸に（旧ラベルは summary に参考として）、不明は null。推定・不明・落とした項目をレポートに全部出す |
| `rl annotate draft <project> <robot> --manual m.txt --out f.yaml [--model M] [--call] [--dry-run-schema] [--license L]` | プロンプトの包み（prompt.md・rules.md・schema.json・手順書・meta.json に sha256）を書く。`--call` なら `rlkit.llm.call` で呼ぶ。止める仕組み：評価対象のモデル（plan.md の「言語モデルは」の行か `protocol.evaluated_models`）と同じ系統なら断る（登録簿で解決した名前と応答のモデル名でも確かめる）、G2 前のテスト機種（plan.md §1 の「テスト」の行）は `--dry-run-schema` がなければ断る、NC なら `redistribution: restricted` |
| `rl annotate review <file> --sheet s.csv` | 1 行＝L1 × 項目（型・属性・工具・可否の 8 軸・scope など）と辺 1 本ずつ。下書きの値・出所・根拠と、空の decision / new_value / new_src / reason / reviewer。UTF-8 BOM 付きで Excel でも文字化けしない |
| `rl annotate apply <file> --sheet s.csv [--reviewer R] [--out f]` | ok / change / delete（辺）/ add（辺）を反映。変えた値は `src: annotator`（`new_src` で上書き可）、`review.changes` に元の値・新しい値・理由・人・日時。理由のない変更、シート作成後に変わった値は、何も書き換えずに止まる。上書きのときは `.bak` を残す |
| `rl annotate sample <file> --frac 0.2 --seed 0 [--blank b.yaml]` | 型で層別した二重注釈の対象（各型 1 件以上、残りは比例で最大剰余）。`--blank` で 2 人目用の空欄のファイル（L1 の切り方だけ同じ、値と辺は空） |
| `rl annotate agree a.yaml b.yaml [--ids ids.txt] [--drop-unknown]` | 共通の L1 で、型・fix_state・scope・8 軸・先行関係の kind（辺の和集合、片方にない辺は absent）・source について、一致率・Cohen の κ・95% CI・Krippendorff の α。hold_needed は順序つき（2 次の重みの κ・ordinal α）も。κ < 0.6 は「要改訂」、CI の下限 < 0.6 は「注意」。統計は rl_stats.py を呼ぶ |

rl_stats.py に足したもの：`kappa`（Cohen、`--weights none|linear|quadratic`、`--categories` で順序）、`fleiss`（ratings か counts）、`alpha`（Krippendorff、nominal / ordinal / interval、欠けは null）。どれも項目のブートストラップで CI、`--seed` で決定的。標準ライブラリだけ。

テスト：`uv run --with pytest --with ruamel.yaml --with jsonschema pytest tests/annotate -q` → 63 件すべて通る。教科書の値で確かめた（Cohen の κ 0.40、重みつき κ は scikit-learn と一致、Fleiss の κ 0.2099、Krippendorff の α 0.743 / 0.815 / 0.849 と 2 値の例 0.095、krippendorff パッケージでも一致）。スキーマの違反・閉路・シートの往復・下書きの止める仕組み（偽の `rlkit.llm` で）も。`python3 evals/run_evals.py` は 9/9 のまま。

途中で見つけた不具合：rl_stats.py の欠けの扱いで、文字列 `none` を欠けにしていた（`tool_required: none` が黙って落ちる）。直した（`none` は値として扱う）。

### 決めたこと（スキーマで設計メモにないもの）
- 辺の `kind` に `unknown` を足した（変換や下書きで決まらない辺）。`order_only` の辺は `kind: null` を許し、required ならエラー。`source` にも `unknown`
- `src` の値：`stated / cad / bom / rule / sim / rule+sim / sim-uncertain / annotator / execution / borrowed[:robot]`。下書き・確認の状態は出所と分けて `review.status`（draft / reviewed / blank）に持つ
- `label` は §10.1 の 8 軸＋`scope`（assembly / software / inspect / manufacturing）＋`summary`（旧ラベル、派生の要約）。`hold_needed` は `0 / 1 / 2+ / unknown`
- 未判定の値（null・unknown・not_checked・not_run）は出所がなくてよい
- 拡張は `x_` を前に付ける（知らない項目は綴りの誤りとしてエラー）

## 試し書き 2 機種の変換レポート

出力は scratch に置いた（プロジェクトのファイルは読んだだけ）：
- `<作業用の一時フォルダ>/annotate/lekiwi.v02.yaml`、レポート `…/annotate/lekiwi.report.md`
- `<作業用の一時フォルダ>/annotate/so100.v02.yaml`、レポート `…/annotate/so100.report.md`

| | LeKiwi | SO-100 follower |
|---|---|---|
| L2 / L1 | 20 / 47（v0.1 と同じ） | 28 / 44（v0.1 の 45＋準備 1 から、統合で −2） |
| validate | エラー 0・注意 44 | エラー 0・注意 53 |
| placed → fixed の統合 | なし | S03a+S04a → S04a、S07b+S08a → S08a |
| 統合しなかった placed | — | S09a↔S11a、S18a↔S20a（間に別の L1。統合すると閉路になる） |
| 辺（変換後） | 55：required 8・recommended 2・unknown 32・order_only 13 | 59：required 3・recommended 2・unknown 38・order_only 16 |
| L2 の辺を L1 に展開 | 13 本の辺（例 S06→S08 は 4 組） | 13 本 |
| required から unknown に下げた | 2（S10→S11、S08→SX2a：複数の L1 の組に広がるため） | 5（S06→S07、S12→S14、S16→S17、S24→S25、S25→S26） |

変換できなかった・人が決める必要があるもの
- **辺の kind の大半が unknown**（LeKiwi 32/55、SO-100 38/59）。v0.1 は required / recommended を区別していなかった。text_explicit・text_anaphora の辺は全部 unknown、precedes_from_text だけにある辺（LeKiwi 12、SO-100 14）は source も unknown。確認で決める
- **ねじの寸法・本数の不明**：LeKiwi 8 つの L1（S07a・S08v5a・SX1b・SX1c・S13b・S15c・S15d・S17d）、SO-100 3 つ（S13a・S18c・S27a）。BOM の数量が数でない行：LeKiwi F07、SO-100 A03・A04
- **count が不明**：LeKiwi S08v5b（配線図に依存）
- **両手**：v0.1 の `two_hands` は `attrs.two_hands_v01`（annotator）に残しただけで、`hold_needed` は unknown（§9.3：sim で決める）
- **可否の軸**：tool_access・hold_needed・fixture_required・geometric_screen は sim の前なので未判定。human_required は CBL だけ yes（reason: flexible）、他は unknown
- **変種の主経路**：LeKiwi は `variant_transcribed` の文から 12V・Option1 を main と推定、SO-100 は follower を main（要確認）
- **キーワードで埋めた属性（要確認）**：SO-100 S06a/S06b の zero_position、S08a の joint_motion、LeKiwi S13c の optional、S17a/S17b の template_of（メモの「の写し」）
- **写真を見ないと決まらない L1 の候補**（from_media_only）：LeKiwi 7、SO-100 6。いまは type が unknown の L1 だけを from_media_only: true にした
- **落としたもの**：L3 の木（subassemblies の parent）、summary_counts（validate が出し直す）、SO-100 の leader 専用ステップの要約（leader は別の IR に）。SO-100 S00g（leader のギア外し、動画のみ）は L1 なしの L2 として残り、validate の注意に出る
- 旧ラベルの変更：OTH（3D 印刷・サポート除去）は summary を X に（LeKiwi SX1a・S15a、SO-100 S00a）

## 本体への反映の案（このエージェントは触っていない）

### README.md のコマンドの表（`rl config` の行の前に足す）

```markdown
| `rl annotate validate / convert-v01 / draft / review / apply / sample / agree` | 手順書の工程の正解（IR v0.2）を作る。LLM の下書き（評価する言語モデルと別のモデル、G2 前のテスト機種は断る）→ 確認シートで人が全件を決める → 20% を二重に付けて項目ごとの κ・α。手順は `skills/research-lab/references/annotation.md`、スキーマは `lib/rlkit/ir_schema_v0_2.json` |
```

構成の節の `skills/` の下の `ml-rigor/` の行を次に：

```markdown
  ml-rigor/                事前登録・分岐の庭のチェック・統計（scripts/rl_stats.py。注釈者の一致 kappa・fleiss・alpha も）
```

### skills/research-lab/SKILL.md

1. 「プロジェクトの作り方と構成」のコードブロック、`rl readme <name>` の行の後に：

```bash
rl annotate validate notes/annotations/<robot>.yaml   # 工程の正解（IR v0.2）の確認。作り方は references/annotation.md
```

2. 段階の表の S2 の行の「主に使うスキル」の末尾に `、工程の正解を作るなら [references/annotation.md](references/annotation.md)（G2 の前はテストの機種を注釈しない）` を足す。S3 の行の「やること」に `工程の正解の注釈（下書き → 人の確認 → 20% の二重注釈 → κ）` を足す

3. 「作業 → スキルの早見表」の箇条書きの「統計・評価の厳密さは `ml-rigor`。」の後に：

```markdown
- 手順書・データから正解（ラベル）を作る作業は [references/annotation.md](references/annotation.md)（`rl annotate`）。下書きのモデルは評価するモデルと別にし、二重注釈の一致は `rl annotate agree`（rl_stats.py）で出す。
```

### skills/ml-rigor/SKILL.md の「統計の決まりごと」の表（`holm` の行の後に足す）

```markdown
| 注釈者 2 人の一致（正解のラベル） | Cohen の κ と項目のブートストラップの CI。順序のある値は 2 次の重みの κ。κ < 0.6 の項目は決め方を直す | `kappa --a ... --b ...` か `kappa pairs.json [--weights quadratic --categories 0 1 2+]` |
| 注釈者 3 人以上（全項目を同じ人数） | Fleiss の κ | `fleiss ratings.json` |
| 欠けのある一致・順序や間隔の尺度 | Krippendorff の α（nominal / ordinal / interval） | `alpha data.json --level ordinal` |
```

書き方の決まりに 1 行足す：

```markdown
- 注釈の一致は項目ごとに κ（または α）・CI・n を表にする。全件が同じ値で κ が定義できない項目は一致率だけを書き、「一致した」と書かない。
```

### ledger.md（任意）
research.yaml の `protocol` に `evaluated_models: [...]` と `test_robots: [...]` を書けるようにすると、`rl annotate draft` は plan.md の文を読まずにそれを使う（いまは plan.md の行から読む。読めなければ `--evaluated` を求めて止まる）。
