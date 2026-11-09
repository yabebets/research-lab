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

研究のコードと原稿はプロジェクト（`projects/<名前>/`、それぞれ別の Git リポジトリ）に、判断と考えは Plexa の Vault（ロボティクスは `Exp Robotics/`、それ以外は `Research/`）に残す。

## コマンド

| コマンド | すること |
|---|---|
| `rl new <name> --domain ml\|cv\|nlp\|robotics\|systems` | 研究プロジェクトを作る（台帳・計画・ARIS スキルの登録・Codex 査読役の設定） |
| `rl status [name]` | 段階・ゲート・GPU 予算・実行の数・test での評価回数・未完了のタスク・blockers |
| `rl night [name] [--iterations N] [--budget-usd X] [--hours H]` | 夜間ループ（1 回ごとに新しいセッション、上限つき、ゲートで止まる） |
| `rl gpu up <name> <task.yaml> --hours H --usd-per-hour X` | GPU を立てる（G2・上限時間・残り予算を確認してから） |
| `rl gpu down <name> <cluster>` / `rl gpu reap` / `rl gpu status` | 消す・期限切れを消す・一覧 |
| `rl doctor [--clouds]` | ツール・接続の確認 |
| `rl sync` | 上流スキルを更新し、索引を作り直す |

## 構成

```
skills/                    グローバルに登録する自前スキル（rl link）
  research-lab/            入口・進行・台帳・夜間ループ
  ml-rigor/                事前登録・分岐の庭のチェック・統計（scripts/rl_stats.py）
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
templates/                 プロジェクトのひな形・夜間ループのプロンプト・SkyPilot のタスク
evals/                     スキルの評価ハーネス（run_evals.py）
bin/rl                     操作コマンド
scripts/                   vendor-sync.sh・build-index.py
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
