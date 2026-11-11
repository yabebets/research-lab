# research-lab

ML・CV・NLP・CS・AI・フィジカル AI・ロボティクスの研究を、テーマ選びから実験・論文・査読対応まで進めるための Claude Code のスキル一式。

- **土台**：論文の書き方は [Master-cai/Research-Paper-Writing-Skills](https://github.com/Master-cai/Research-Paper-Writing-Skills)（浙江大学の彭思达教授の研究ノートを元にしたもの）
- **実験と査読の流れ**：[ARIS](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep)（別モデルの査読ループ、実験の実行と監査、主張と結果の照合）
- **ML のフレームワーク**：[Orchestra AI-Research-SKILLs](https://github.com/Orchestra-Research/AI-Research-SKILLs)（学習・微調整・分散・推論・評価・VLA）
- **自前で足したもの**：全体の進行と台帳、人の確認ポイント、夜間ループ、RunPod / Lambda の GPU 管理、ML 版の厳密さチェックと統計、ロボティクス（LeRobot / SO-ARM101）、学会別の査読、引用の実在確認、スキルの評価ハーネス（考え方は [AERS](https://github.com/brycewang-stanford/Auto-Empirical-Research-Skills) から）

## 使い方

### 最初に 1 回

```bash
~/research-lab/bin/rl link        # 自前スキルを ~/.claude/skills に登録、rl を ~/.local/bin に
cp config.example.yaml config.yaml  # 記録先・資料の控え・手元のロボット・計算環境を書く（git の管理外）
rl doctor                         # 足りないものを表示
```

GPU（RunPod / Lambda）を使うなら、SkyPilot を入れて鍵を設定する（手順は `skills/gpu-cloud/SKILL.md`）。
Codex を査読役にするので、`codex login` を済ませておく。

### 研究の流れ

1. Claude Code で「〇〇の研究を始めたい」と頼む → `research-lab` スキルが `rl new <名前> --domain robotics` でプロジェクトを作り、文献調査とアイデア出しを進める
2. **G1**：テーマと研究の問いを人が選ぶ
3. 実験計画と GPU 予算の案が出る → **G2**：人が承認する
4. `rl night <名前>` を回して寝る → 承認した予算の範囲で、実験・分析・自己査読が進む。朝は `rl status <名前>`
5. **G3**：論文で言う主張を人が確定する → 執筆と査読シミュレーションのループ
6. **G4**：投稿するかを人が決める

研究のコードと原稿はプロジェクト（`projects/<名前>/`、それぞれ別の Git リポジトリ）に、判断と考えはノートに残す。記録先・手元のロボット・計算環境は `config.yaml` に書く（`cp config.example.yaml config.yaml` で作り、`rl config` で確認）。

## コマンド

| コマンド | すること |
|---|---|
| `rl new <name> --domain ml\|cv\|nlp\|robotics\|systems` | 研究プロジェクトを作る（台帳・計画・ARIS スキルの登録・Codex 査読役の設定） |
| `rl status [name]` | 段階・ゲート・GPU 予算・実行の数・test での評価回数・未完了のタスク・blockers |
| `rl sim list / setup <tool..> / check / launch <tool> [--model M] [--dry-run]` | シミュレーターと道具（`sims/catalog.yaml`：MuJoCo・モデル集・Drake・干渉の判定・STEP の読み込み・ASAP・Fabrica・LeRobot・SkyPilot、借りた GPU で動かす Isaac Lab・Isaac Gym・ManiSkill・Genesis・MJX・MuJoCo Warp・openpi・OpenVLA-OFT・Cosmos Policy）をプロジェクトに入れ、版を `sims.lock.yaml` に残し、動作を確かめ、起動する。Python の版が合わない道具（Drake 1.58 は 3.12）は別の venv に入れる |
| `rl sim setup/check --worker`・`rl sim run [--worker] [--tool T] -- <cmd>`・`rl sim colab [tool..]` | 同じ版を dev-worker（offload）に入れて確かめる・プロジェクトの venv で手元か Worker で実行する・同じ版を入れる Colab のノートブック（試し用。結果は論文に使わない）を書く |
| `rl robot list / fetch <robot> / link <robot> --project P / check / migrate --project P [--apply]` | ロボットの公開データ（CAD・手順書・部品表。`robots/catalog.yaml`）を共有のキャッシュ（`.cache/robots/`）に版と sha256 つきで取り、プロジェクトからリンクで使う。版は `robots.lock.yaml` に残る。ログイン・登録が要るものは取らない |
| `rl program new / list / status / link / readme / check` | 研究プログラム（`programs/<name>/` の program.md と program.yaml）を作り、論文とプロジェクトを両方の台帳で紐づけ、系統ごとの状況を表示する。`rl new <name> --program <prog> --paper <ID>` で作るときに紐づける |
| `rl readme [name] [--check]` | プロジェクトの README の「検証状況」（問い・仮説・主張と証拠・次にやること）を台帳から書き直す。書き方は `skills/research-lab/references/readme.md` |
| `rl run exec [name] --task T# --purpose "…" [--split dev\|val\|test] [--seed N] [--config F] [--tag sim] -- <cmd>` | 実行を `runs/<run_id>/` に記録する（run.yaml・config・log.txt・status。コマンドは `$RL_RUN_DIR/metrics.json` に書く）。test は G2 の後、決めた回数まで。`rl run start / finish / list / show` |
| `rl prereg freeze / check [name]` | G2 で承認した事前登録（plan.md の節と protocol）を `prereg.lock.yaml` に固定し、あとからの変更を見つける。ずれていると test の実行を断る |
| `rl blog new [name] --title "…" --runs a,b [--zenn]` / `check <post>` / `refresh <post>` / `list` | run からブログ仕立ての下書き（`notes/blog/`）を作る。数字は metrics.json から作る表からだけ。公開は人が決める。書き方は `skills/research-lab/references/blog.md` |
| `rl llm models / ping <model> --dry-run / usage [name] / budget [name]` | 言語モデルの登録簿（`llm/models.yaml`：価格と出典・送れない引数）、送る要求の確認（通信しない）、使った額（モデル別・実行別・日別）、上限と残り。呼び出しは `lib/rlkit/llm.py` の `call()`・`tool_loop()` から。1 回ごとに記録し、`budget.llm_usd_cap` を超える呼び出しは送らない |
| `rl annotate validate / convert-v01 / draft / review / apply / sample / agree` | 手順書の工程の正解（IR v0.2）を作る。LLM の下書き（評価する言語モデルと別のモデル、G2 前のテスト機種は断る）→ 確認シートで人が全件を決める → 20% を二重に付けて項目ごとの κ・α。手順は `skills/research-lab/references/annotation.md`、スキーマは `lib/rlkit/ir_schema_v0_2.json` |
| `rl night [name] [--iterations N] [--budget-usd X] [--hours H]` | 夜間ループ（1 回ごとに新しいセッション、上限つき、ゲートで止まる） |
| `rl gpu up <name> <task.yaml> --hours H --usd-per-hour X` | GPU を立てる（G2・上限時間・残り予算を確認してから） |
| `rl gpu down <name> <cluster>` / `rl gpu reap` / `rl gpu status` | 消す・期限切れを消す・一覧 |
| `rl doctor [--clouds]` | ツール・接続の確認 |
| `rl config [key]` | 手元の設定（記録先・資料の控え・ロボット・計算環境）を表示。例：`rl config robot.repo` |
| `rl sync` | 上流スキルを更新し、索引を作り直す |

## 構成

```
skills/                    グローバルに登録する自前スキル（rl link）
  research-lab/            入口・進行・台帳・夜間ループ
  research-themes/         興味の範囲 → テーマの候補（条件から出発、カード 3〜5 枚）
  research-program/        テーマ → 論文・プロジェクトの単位（幹・並び・依存・資産、notes/program.md）
  ml-rigor/                事前登録・分岐の庭のチェック・統計（scripts/rl_stats.py。注釈者の一致 kappa・fleiss・alpha も）
  gpu-cloud/               RunPod / Lambda（SkyPilot）・予算・自動削除
  physical-ai-research/    ロボティクス・VLA・sim2real・実機評価・安全
  venue-review/            学会別の査読シミュレーション
  ml-lit-review/           文献調査・引用の実在確認（scripts/verify_bib.py）
  research-paper-writing → vendor/research-paper-writing（Master-cai）
vendor/                    上流（git subtree。手で直さない）
  manifest.tsv             取り込む上流のディレクトリ一覧
  INDEX.md / index.json    全スキルの索引（scripts/build-index.py が作る）
  research-paper-writing/  Master-cai
  aris/{skills,tools,mcp-servers}/
  orchestra/<カテゴリ>/    研究に関係する 19 カテゴリ
templates/                 プロジェクトのひな形・夜間ループのプロンプト・SkyPilot のタスク・ブログの下書き
evals/                     スキルの評価ハーネス（run_evals.py）
bin/rl                     操作コマンド（bin/rl-<name> は rl <name> で呼べる追加のコマンド）
lib/rlkit/                 追加コマンドと研究コードが共有する部品（runs.py・prereg.py・blog.py・llm.py・annotate.py・robots.py）
tests/                     追加コマンドのテスト（pytest）
config.example.yaml        手元の設定の例（コピーして config.yaml にする。config.yaml は管理外）
scripts/                   vendor-sync.sh・build-index.py
sims/catalog.yaml          シミュレーターと道具の一覧（rl sim が読む）
robots/catalog.yaml        ロボットの公開データの一覧（取得元・版・ライセンス・派生物。rl robot が読む。データは入れない）
robots/sums/               取得したファイルの一覧と sha256 の控え
llm/models.yaml            言語モデルの登録簿（価格・出典・使える引数）
.cache/robots/             ロボットのデータの共有キャッシュ（<robot>/<version>/{raw,derived}。git の管理外・公開しない）
programs/                  研究プログラム（系統・論文の並び。このリポジトリでは管理しない）
projects/                  研究プロジェクト（このリポジトリでは管理しない）
```

## 上流の更新

```bash
rl sync                    # vendor/manifest.tsv の全部
rl sync aris-skills        # 1 つだけ
```

`git subtree split` で必要なディレクトリだけを切り出して取り込んでいる。`--squash` は使わない。取り込む範囲を変えるときは `vendor/manifest.tsv` に行を足して `rl sync <name>`。

## スキルの評価

```bash
python3 evals/run_evals.py            # 採点の基準が合格例・不合格例を見分けられるか（無料）
python3 evals/run_evals.py --live     # 実際に Claude に答えさせて採点（費用がかかる）
```

スキルを直したら回す。シナリオは `evals/scenarios/`、合格例・不合格例は `evals/fixtures/`。

## ライセンス

自前の部分は MIT。`vendor/` の下は各上流のライセンス（[THIRD_PARTY.md](THIRD_PARTY.md)）。
