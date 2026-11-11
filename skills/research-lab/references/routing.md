# 作業 → スキルの対応表

パスは `~/research-lab` からの相対パス。グローバル登録済み（★）以外は SKILL.md を Read して従う。
プロジェクト内では ARIS の主要スキルが `.claude/skills/` に登録されているので `/名前` でも呼べる（◆）。

## 文献・アイデア

| 作業 | スキル |
|---|---|
| 興味の範囲から研究テーマの候補を出す（問いの前） | ★ `research-themes`（条件を聞く → 棚卸し → 交点 → テーマのカード） |
| テーマを論文・プロジェクトの単位に切る（幹・並び・依存・資産） | ★ `research-program`（`notes/program.md`。1 論文 = 1 プロジェクト） |
| 文献を広く集めて整理する | ★ `ml-lit-review` → ◆ ARIS `research-lit`（arXiv / Semantic Scholar / OpenAlex） |
| 1 本の論文をすばやく理解する | ◆ ARIS `alphaxiv`、`arxiv` |
| アイデアを出す（ML 全般） | ◆ ARIS `idea-discovery` `idea-creator`、Orchestra `21-research-ideation/*` |
| アイデアを出す（ロボティクス） | ◆ ARIS `idea-discovery-robot` ＋ ★ `physical-ai-research` |
| 新規性を確かめる | ◆ ARIS `novelty-check` |
| アイデアを潰しにかかる | ◆ ARIS `kill-argument` |
| 研究の問いを磨く | ◆ ARIS `research-refine` `research-refine-pipeline` |
| 研究の背景と動機を Introduction の形で書く（G1 のあと） | `research-lab/references/introduction.md` ＋ ★ `research-paper-writing`（`references/introduction.md`）＋ ★ `ml-lit-review`（出典の確認） |

## 計画・実験

| 作業 | スキル |
|---|---|
| 実験計画（ベースライン・指標・アブレーション） | ◆ ARIS `experiment-plan` `ablation-planner` ＋ ★ `ml-rigor`（事前登録・seed 数・統計） |
| GPU の確保・費用・片付け（RunPod / Lambda） | ★ `gpu-cloud` |
| 計画をコードにする | ◆ ARIS `experiment-bridge` `research-implement-feature` |
| 実行・キュー・監視 | ◆ ARIS `run-experiment` `experiment-queue` `monitor-experiment` `training-check`（`gpu: remote` で `gpu-cloud` の SSH 先を使う） |
| 実行の記録・test の回数・事前登録の固定 | `rl run exec`（runs/<run_id>/ を作る）・`rl prereg freeze / check`（書式は `research-lab/references/ledger.md`） |
| 実験の中で言語モデルを呼ぶ（記録・費用・予算） | `lib/rlkit/llm.py` の `call()`・`tool_loop()`、登録簿は `llm/models.yaml`、確認は `rl llm`。Claude のコードは ★ `claude-api` |
| 手順書・データから正解（ラベル）を作る | `research-lab/references/annotation.md`（`rl annotate`）＋ ★ `ml-rigor`（一致の κ・α） |
| ロボットの公開データ（CAD・手順書・部品表）を使う | `rl robot fetch / link`（`robots/catalog.yaml`）＋ ★ `physical-ai-research` |
| 学習・微調整 | Orchestra `03-fine-tuning/*`（peft、unsloth、axolotl、llama-factory）、`06-post-training/*`（trl、grpo、verl、openrlhf） |
| 分散学習・最適化 | Orchestra `08-distributed-training/*`、`10-optimization/*`（flash-attention、量子化、`ml-training-recipes`） |
| モデル構造・小さく試す | Orchestra `01-model-architecture/*`（nanogpt、litgpt、mamba） |
| 推論・評価 | Orchestra `12-inference-serving/*`（vllm、sglang）、`11-evaluation/*`（lm-evaluation-harness、bigcode） |
| 実験管理 | Orchestra `13-mlops/*`（weights-and-biases、mlflow、tensorboard） |
| CV・マルチモーダル | Orchestra `18-multimodal/*`（clip、segment-anything、llava、stable-diffusion、blip-2） |
| VLA・ロボット方策 | Orchestra `18-multimodal/openpi` `openvla-oft` `cosmos-policy` ＋ ★ `physical-ai-research` |
| 解釈可能性 | Orchestra `04-mechanistic-interpretability/*` |
| 安全性・アラインメント | Orchestra `07-safety-alignment/*` |
| データ処理 | Orchestra `05-data-processing/*` |

## 分析・主張

| 作業 | スキル |
|---|---|
| 統計（seed のばらつき、信頼区間、検定、RL の IQM、実機の成功率、注釈者の一致） | ★ `ml-rigor`（`scripts/rl_stats.py`） |
| 結果の分析・図 | ◆ ARIS `analyze-results`、Orchestra `20-ml-paper-writing/academic-plotting` |
| 結果から言えることの判定 | ◆ ARIS `result-to-claim` |
| 実験の整合性の監査（別モデル） | ◆ ARIS `experiment-audit` `integrity-forensics` |

## 執筆・査読

| 作業 | スキル |
|---|---|
| 章ごとの書き方の基準（Abstract〜Conclusion） | ★ `research-paper-writing`（Master-cai） |
| 構成・下書き・図・コンパイル | ◆ ARIS `paper-plan` `paper-write` `paper-figure` `paper-compile`、Orchestra `20-ml-paper-writing/ml-paper-writing`（学会の LaTeX テンプレート） |
| システム系の論文 | Orchestra `20-ml-paper-writing/systems-paper-writing`、◆ ARIS `writing-systems-papers` |
| 学会別の査読シミュレーション | ★ `venue-review` |
| 査読 → 修正のループ（別モデル） | ◆ ARIS `auto-review-loop` `auto-paper-improvement-loop` |
| 主張と引用の監査 | ◆ ARIS `paper-claim-audit` `citation-audit` `citation-crosscheck`、★ `ml-lit-review`（`verify_bib.py`） |
| 数式・証明 | ◆ ARIS `formula-derivation` `proof-checker` |
| 発表 | ◆ ARIS `paper-slides` `paper-poster-html`、Orchestra `20-ml-paper-writing/presenting-conference-talks` |
| 実験の記録をブログ・Zenn の記事にする（下書きまで。公開は人） | `research-lab/references/blog.md`（`rl blog new / check`） |
| rebuttal・再投稿 | ◆ ARIS `rebuttal` `resubmit-pipeline` ＋ ★ `venue-review` |

## 全体を一気に回すもの（使うときの注意）

- ARIS `research-pipeline`、Orchestra `0-autoresearch-skill` は「アイデアから論文まで」を自律で回す。**このリポジトリでは使うときも G1〜G4 で止める**。各段階の中身の参考として読み、段階の切り替えは `research-lab` の台帳で行う。
