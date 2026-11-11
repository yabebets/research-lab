# AI 支援・自律研究の OSS(スキル集・フレームワーク・ツール)と取り込み候補

調査日: 2026-11-11。

**数値の出どころ**: 「★」「最終 push」「API ライセンス」は、この日に GitHub Search API(`gh api search/repositories`、`repo:` 指定)で取った値。「README 記載」は同日に GitHub のリポジトリページを WebFetch で読んだ内容(小型モデルによる要約経由なので、取り込み前に LICENSE ファイルを直接確認すること)。API が `NOASSERTION` / `none` を返したものは README の記載を併記した。README を読んでいないものは「メタデータのみ」と書いた。

**ライセンスの読み方(このリポジトリの決まりに合わせて)**: MIT / Apache-2.0 = vendor/ に取り込める。CC BY-SA / CC BY-NC / GPL / AGPL / 独自ライセンス / ライセンスなし = 文章やコードをコピーしない(考え方だけ参考、または外部ツールとして呼ぶ)。

---

## 1. 研究向けの Claude Code スキル集・プラグイン・サブエージェント集(既存 4 上流の最近の変更を含む)

### Takeaway
既存 4 上流のうち動きが大きいのは ARIS(プラグイン化、査読モデルの選択制、`/citation-crosscheck`、Codex CLI の仕様変更への追従)と AERS(採点 CLI と評価ハーネスの整備)。新規で取り込み価値が高いのは、MIT の PaperJury(査読シミュレーション)、ARA(研究成果物の規約と 7 スキル)、claesbackman/AI-research-feedback(論文とコードの突き合わせ)、uditgoenka/autoresearch(汎用の改善ループ)、Apache-2.0 の openai/codex-plugin-cc と huggingface/skills。

### Cited Findings

#### 1-A. 既に使っている上流の現状と最近の変更

| 上流 | API ライセンス | ★ | 最終 push | 最近の変更(README 記載) |
|---|---|---|---|---|
| wanshuiyin/Auto-claude-code-research-in-sleep (ARIS) | MIT | 19,024 | 2026-11-11 | 下記 |
| Orchestra-Research/AI-Research-SKILLs | MIT | 14,454 | 2026-10-11 | 下記 |
| Master-cai/Research-Paper-Writing-Skills | MIT | 8,266 | 2026-06-23 | 日付つきの変更履歴なし(コミット 6 件) |
| brycewang-stanford/Auto-Empirical-Research-Skills (AERS) | NOASSERTION(README バッジは CC BY-SA 4.0) | 4,998 | 2026-11-09 | 下記 |

- **ARIS**: README の変更履歴(2026 年)。9/7 既定の査読モデルを `gpt-6-astra` に変更。9/10 codex-cli 0.154 が `codex mcp-server` を廃止したため、自前の `codex exec` ブリッジを同梱。9/16 Claude Code プラグイン化。9/28 arXiv がリクエストを拒否したときに実在論文を「幻覚引用」と誤判定しないよう修正(拒否は "verify pending" 扱い)、ARIS-Code v0.4.28。10/5 Grok と Gemini/Antigravity の MCP ブリッジ。10/7 `/lean-formalize`(数学の主張を Lean で検証)。10/19 査読者を Codex / Gemini / Grok / Claude Code から選択可能に、`/citation-crosscheck`(手元の .bib と取り直した書誌の比較)、並列作業の上限ルール。11/1 Goal Pulse(長い Codex Goal に 30 分ごとの催促)と Model Worker MCP(本文の下書きを別モデルに任せる)。11/4 Absent Author(AI 支援論文の著者セルフチェックと査読側スクリーニング用の証拠カタログと 2 スキル)。スキル数は README 内で 82 と 83 の両方の記載がある。ライセンスは MIT。— [ARIS README](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep)(ページ前半 10 万文字のみ読了)
- **Orchestra AI-Research-SKILLs**: 最新は v1.7.1(2026 年 6 月)、98 スキル・23 カテゴリ。v1.7.x でスキル数の記載ずれを直し、記載数とディスク上のスキルが食い違うと CI が落ちる「drift guard」を追加、依存バージョンを固定。v1.6.0(4 月)で Agent-Native Research Artifact カテゴリ(ARA Compiler / Research Manager / Rigor Reviewer)を追加。v1.4.0(3 月)で Autoresearch オーケストレーション(文献調査から執筆までの 2 重ループ)。インストールは `npx @orchestra-research/ai-research-skills` か Claude Code マーケットプレイス。MIT。— [Orchestra README](https://github.com/Orchestra-Research/AI-Research-SKILLs)。6 月以降のマージ PR は model-merging スキルへの追記、Qoder 対応など小粒 — GitHub Search API(merged PR 一覧、2026-11-11)
- **Master-cai**: スキルは `research-paper-writing/` の 1 パッケージ(SKILL.md、references/、agents/openai.yaml)。Codex / Claude Code / Gemini のスキルディレクトリにコピーして使う。MIT。— [Master-cai README](https://github.com/Master-cai/Research-Paper-Writing-Skills)
- **AERS**: README バッジは "License: CC BY-SA 4.0"。同梱コレクションは上流のスナップショットで、ライセンスと出所は `docs/LICENSE_AUDIT.md` にあると記載。78 コレクション・1,151 スキル(リポジトリ説明文の「23,000+」とは食い違う)。2026 年の変更: 6 月 プラグインマーケットプレイスと全体ルーター、7 月 初タグ v2026.07、8 月 `aers-score` CLI と外部スコアボード(自己申告でなく同じ採点器で再計算)、9 月 段階的検索とルーティング評価、p-hacking lab、10 月 de-AIGC の強化。検証用に数値ベンチ 19 課題、行動評価シナリオ 42 件(ルーブリック 217 項目)、合格/不合格フィクスチャつき 9 件。— [AERS README](https://github.com/brycewang-stanford/Auto-Empirical-Research-Skills)
- **ARS (Imbad0202/academic-research-skills)**: ★56,479、最終 push 2026-11-11、API は NOASSERTION、README は CC BY-NC 4.0。最新 v3.24.2(2026-11-06)。Deep Research(8 モード)、Academic Paper(11 モード)、Reviewer(6 モード)、10 段のパイプライン、SR-Screener。必須の整合性ゲート(段 2.5 と 4.5)、Semantic Scholar による引用確認、決定的な 4 索引の引用ゲート(v3.11)、任意の claim 監査(`ARS_CLAIM_AUDIT=1`)。v3.24.0 で査読レターに「推薦文献の実在確認」と「査読者の主張と原稿の突き合わせ」を助言扱いで追加(精度は未測定と明記)。v3.24.2 で実験ロックに「理由つきの null 結果」を記録可能に。— [ARS README](https://github.com/Imbad0202/academic-research-skills)

#### 1-B. Anthropic・OpenAI・Hugging Face の公式

| リポジトリ | API ライセンス | ★ | 最終 push | 内容 |
|---|---|---|---|---|
| anthropics/skills | none(README: 多くは Apache-2.0、要スキル別確認) | 192,859 | 2026-11-06 | Agent Skills の公式例。docx/pdf/pptx/xlsx、skill 作成用テンプレート、spec へのリンク。研究専用スキルはなし — [README](https://github.com/anthropics/skills) |
| anthropics/claude-plugins-official | Apache-2.0(プラグインごとに LICENSE を確認と明記) | 46,855 | 2026-11-11 | `plugins/` に 41 個。研究に関係しそうな名前: `ralph-loop`、`skill-creator`、`math-proof`、`math-olympiad`、`code-review`、`pr-review-toolkit`、`hookify`、`session-report`、`claude-md-management` — [README](https://github.com/anthropics/claude-plugins-official)、[plugins/](https://github.com/anthropics/claude-plugins-official/tree/main/plugins) |
| anthropics/knowledge-work-plugins | Apache-2.0 | 35,427 | 2026-11-11 | 11 プラグイン。研究寄りは `data`(SQL・統計分析・可視化・検証)と `bio-research`(PubMed、bioRxiv、ChEMBL などのコネクタ) — [README](https://github.com/anthropics/knowledge-work-plugins) |
| anthropics/life-sciences | none(README にライセンス記載なし) | 647 | 2026-11-09 | スキルのみのマーケットプレイスに変更済み(MCP は撤去)。`scientific-problem-selection`(Fischbach & Walsh, Cell 2024 に基づく課題選びとリスク評価)など 4 スキル — [README](https://github.com/anthropics/life-sciences) |
| openai/codex-plugin-cc | Apache-2.0 | 35,052 | 2026-07-08 | Claude Code から Codex を呼ぶ公式プラグイン。`/codex:review`、`/codex:adversarial-review`(焦点指定可、読み取り専用)、`/codex:rescue`、`/codex:transfer`、`/codex:status|result|cancel`。Stop フックで Codex に応答を査読させる「review gate」(使用量を急速に消費しうると警告) — [README](https://github.com/openai/codex-plugin-cc) |
| huggingface/skills | Apache-2.0 | 11,335 | 2026-11-11 | `huggingface-trackio`、`huggingface-llm-trainer`、`huggingface-vision-trainer`、`trl-training`、`huggingface-community-evals`(inspect-ai / lighteval)、`huggingface-papers`(論文ページを markdown で取得)、`huggingface-paper-publisher`、`hf-mem` など — [README](https://github.com/huggingface/skills) |

#### 1-C. 新規の研究スキル集(README を確認したもの)

- **K-Dense-AI/scientific-agent-skills**(旧 claude-scientific-skills。README に "Claude Scientific Skills is now Scientific Agent Skills")。MIT、★56,819、最終 push 2026-11-09。177 スキル、v2.72.0。各スキルの SKILL.md に個別の `license` 欄があり、リポジトリの MIT と異なる場合があると明記。ML 系(PyTorch Lightning、Transformers、SB3、SHAP、PyMC ほか)、Literature Review、Paper Lookup、Citation Management、Peer Review、Statistical Analysis、Statistical Power、Experimental Design、Hypothesis Generation(仮説を「候補」ラベルのまま保つ)。インストールは `npx skills add` / `gh skill install` ほか。— [README](https://github.com/K-Dense-AI/scientific-agent-skills)
- **Spark-To-Paper-Skills/paperjury**。MIT、★1,218、最終 push 2026-08-14、v1.0.0。投稿前の査読ストレステスト。分野別査読者 3 名(2〜4)が全文を独立に読み、弱点には原文の引用が必須。網羅監査、重複統合、争点は隔離した陪審 5 名(割れたら 12 名)で採決し、定足数と多数決はコードが適用。各指摘は valid-fixable / author-required / invalid-drop の 3 種に決着。各ラウンドは前ラウンドの結果を見ない(アンカリング防止)。パッチには凍結アンカーと段落ごとの編集上限。匿名化漏れ・余白・ページ数の決定的チェック。著者自身の報告として、保留 12 本で F1 0.519→0.656(arXiv 2606.16322)。— [README](https://github.com/Spark-To-Paper-Skills/paperjury)
- **ARA-Labs/Agent-Native-Research-Artifact**。MIT、★709、最終 push 2026-10-11。研究成果物の規約: `PAPER.md`(索引)、`logic/`(claims.md、experiments.md、related_work.md)、`src/`(configs、environment.md)、`trace/exploration_tree.yaml`(行き止まりも残す研究 DAG)、`evidence/`。出所タグ(user / ai-suggested / ai-executed / user-revised)。7 スキル: research-manager、compiler(既存の論文・リポジトリを ARA 化)、rigor-reviewer、research-visualizer、research-foresight、context-drop、research-fuzzer(自己反駁を通らないと結論を出せない、別リポジトリ)。`npx @ara-commons/ara-skills`。論文は arXiv:2604.24658。— [README](https://github.com/ARA-Labs/Agent-Native-Research-Artifact)
- **claesbackman/AI-research-feedback**。MIT、★559、最終 push 2026-10-28。`review-paper`(複数の専門エージェントを並列に走らせ、優先度つきの 1 本の報告に統合)、`review-paper-checks`(機械的な整合性確認)、`review-paper-code`(論文の主張と分析コードの一致: 表、変数、サンプル制限、クラスタリング、固定効果、パス、シード、実行順)、`audit-analysis`(変更された分析コードを文脈の空いたサブエージェントで敵対的に監査。指摘にはファイル・行・引用が必須)、`review-pap`(事前分析計画)。— [README](https://github.com/claesbackman/AI-research-feedback)
- **Galaxy-Dawn/claude-scholar**。MIT、★6,031、最終 push 2026-10-19。CS/AI 研究者向けの半自動アシスタント。スキル(research-ideation、results-analysis、citation-verification、ml-paper-writing、paper-self-review、review-response ほか)、エージェント(literature-reviewer、paper-miner、rebuttal-writer ほか)、フック(プロンプト前に関連スキルを提案する `skill-forced-eval.js`、`session-summary.js`、危険コマンドを止める `security-guard.js`)。Zotero MCP 連携(`/zotero-review`、`/zotero-notes`)と Obsidian のプロジェクト別ナレッジベース(Sources / Knowledge / Experiments / Results / Writing / Daily / Maps、`/kb-*` コマンド)。2026-05-13 に evidence-gated な研究ワークフローを追加。— [README](https://github.com/Galaxy-Dawn/claude-scholar)
- **uditgoenka/autoresearch**。MIT、★6,829、最終 push 2026-10-31、バッジは v2.3.0。Karpathy の autoresearch を汎用化した Claude Code スキル/プラグイン。原則: 反復回数は既定で上限あり、1 反復 1 変更、機械的な指標のみ、検証前にコミットして失敗は自動で revert、同点なら単純な方、git 履歴と結果ログを記憶に使う、停滞時は最良コミットから文脈の新しい枝を分岐。サブコマンド 13 個(plan、probe、predict、reason ほか)。— [README](https://github.com/uditgoenka/autoresearch)
- **dzhng/skills** の `auto-research`。MIT、★1,487、最終 push 2026-11-10。速い 1 課題から始め、仮説を小さな束で試し、良くなるにつれて課題範囲を広げる(以前の課題は回帰チェックになる)。評価器・指標・ベースライン・必要改善幅が不明なら実験前に質問する。「評価に通ること」と「改善目標を満たすこと」を別要件として扱う。出力は最良の検証済み成果物と「parameter-effect map」。同リポジトリに `eval-skills`、`write-skills`、`audit-decisions` もある。— [README](https://github.com/dzhng/skills)
- **jordan-gibbs/hyperresearch**。MIT、★4,571、最終 push 2026-11-09。Claude Code / Codex 用のディープリサーチ・ハーネス。markdown のボールト(「Markdown is truth, SQLite is cache」)、16 段のパイプライン、約 17 のサブエージェント役、批評者 4 名が並列に草稿を攻撃、パッチ役と仕上げ役は Read と Edit だけに制限(全面書き直しを防ぐ)、引用文の一致確認・撤回確認・cite-check が最終ゲート、マニフェストで再開可能。`pip install hyperresearch`、プラグインマーケットプレイスでも配布。DRACO 77.7 という主張は 10 課題・自社計測。— [README](https://github.com/jordan-gibbs/hyperresearch)

#### 1-D. メタデータのみ確認(README 未読。GitHub Search API、2026-11-11)

| リポジトリ | API ライセンス | ★ | 最終 push | 説明文の要点 |
|---|---|---|---|---|
| K-Dense-AI/claude-scientific-writer | MIT | 2,570 | 2026-11-11 | 汎用の科学論文ライター |
| K-Dense-AI/k-dense-byok | MIT | 1,439 | 2026-10-16 | デスクトップの AI co-scientist |
| zLanqing/codex-claude-academic-skills | MIT | 5,883 | 2026-05-14 | 文献読解・論文執筆・科学計算の 3 スキル |
| Weizhena/Deep-Research-skills | MIT | 2,530 | 2026-08-23 | 人が途中で制御する構造化ディープリサーチ |
| Haojae/scipilot-figure-skill | MIT | 2,812 | 2026-06-15 | 出版品質の図スキル |
| dwzhu-pku/PaperBanana | Apache-2.0 | 7,623 | 2026-11-03 | 学術イラストの自動生成 |
| appautomaton/latex-arxiv-SKILL | MIT | 487 | 2026-09-13 | arXiv 向けレビュー論文のハーネス(BibTeX 検証を含む説明文) |
| Aperivue/medsci-skills | MIT | 377 | 2026-11-10 | 医学研究: 文献検索、報告ガイドラインと引用の確認、統計、図 |
| 917Dhj/DeepPaperNote | MIT | 1,348 | 2026-11-10 | 論文 1 本を Obsidian ノートにし、既存ノートへリンク |
| Noi1r/beamer-skill | MIT | 374 | 2026-08-12 | Beamer スライドの作成・コンパイル・レビュー |
| alirezarezvani/claude-skills | MIT | 29,631 | 2026-11-11 | 汎用 410 スキル |
| obra/superpowers | MIT | 316,054 | 2026-11-03 | スキルによる開発方法論 |
| ai4s-research/open-science | NOASSERTION | 2,088 | 2026-11-11 | ローカル優先の AI 研究ワークベンチ(デスクトップ) |
| ComposioHQ/awesome-claude-skills | none | 79,246 | 2026-09-18 | スキルの一覧 |
| BehiSecc/awesome-claude-skills | none | 10,400 | 2026-11-02 | スキルの一覧 |

### Inferences
- ARIS が 9 月に「`codex mcp-server` 廃止 → `codex exec` ブリッジ同梱」に動いたので、Codex を MCP 経由で査読者にしている手順は同じ破損を受けている可能性がある。自前スキル側の呼び出し方を確認する価値がある(公式の openai/codex-plugin-cc に寄せる選択肢もある)。
- ARIS の「arXiv に拒否されたら未検証ではなく verify pending」は、`verify_bib.py` にもそのまま当てはまる失敗パターン(ネットワーク拒否を幻覚と誤判定)。
- PaperJury の「採決・停止条件・パッチ適用はコード、読解と判断はモデル」という分担は、「統計・引用の確認はスクリプトで行う」というこのリポジトリの方針と同じ向きで、MIT なので vendor/ に取り込みやすい。
- AERS と ARS は評価・整合性ゲートの設計が進んでいるが、CC BY-SA / CC BY-NC なので文章はコピー不可。参考にできる考え方: AERS の「外部申告を同じ採点器で再計算」「記載数と実体の drift guard」(後者は MIT の Orchestra にも同等の実装がある)、ARS の「理由つき null 結果を記録できる実験ロック」「査読者の主張を原稿と突き合わせる」。
- K-Dense は MIT だがスキルごとに別ライセンスがありうるので、取り込みは `vendor/manifest.tsv` でスキル単位に絞り、各 SKILL.md の `license` 欄を確認するのが安全。

### Gaps
- anthropics/claude-plugins-official の各プラグイン(`ralph-loop`、`math-proof` など)の中身とプラグイン別ライセンスは未確認(ディレクトリ名のみ確認)。
- anthropics/skills のどのスキルが Apache-2.0 でどれがそうでないかは README からは特定できなかった(`THIRD_PARTY_NOTICES.md` とスキル別フォルダの確認が必要)。
- ARIS README の後半 10 万文字(スキル一覧の詳細)は未読。
- 1-D の表は説明文だけで、品質・中身は未評価。

---

## 2. 自律研究フレームワーク(OSS、保守状況、ライセンス)

### Takeaway
2026 年に動いている Apache-2.0 / MIT の本命は、SakanaAI/AI-Scientist-v3(コーディングエージェントを研究者として駆動、Apache-2.0)、ShinkaEvolve、OpenEvolve、DeepScientist、EvoScientist、AutoResearchClaw、AIDE、gpt-researcher。AI-Scientist v1/v2 は独自ライセンス、HKUDS/AI-Researcher はライセンスなし、Denario は GPL-3.0 で、いずれもコピー不可。

### Cited Findings

| プロジェクト | API ライセンス | ★ | 最終 push | 形態 | 要点 |
|---|---|---|---|---|---|
| SakanaAI/AI-Scientist-v3 | Apache-2.0 | 683 | 2026-10-18 | Python CLI `agsci` | 下記 |
| SakanaAI/AI-Scientist-v2 | NOASSERTION | 7,497 | 2025-12-19 | Python | 下記 |
| SakanaAI/AI-Scientist | NOASSERTION | 14,984 | 2025-12-19 | Python | v2 と同系統の独自ライセンス(v2 README で確認。v1 は未読) |
| karpathy/autoresearch | none(README は "MIT"、LICENSE ファイルなし) | 99,787 | 2026-03-26 | 3 ファイル | 下記 |
| algorithmicsuperintelligence/openevolve | Apache-2.0 | 7,760 | 2026-11-08 | pip `openevolve`、Docker | 下記 |
| SakanaAI/ShinkaEvolve | Apache-2.0 | 1,506 | 2026-11-10 | pip `shinka-evolve` + スキル 4 個 | 下記 |
| WecoAI/aideml (AIDE) | MIT | 1,619 | 2026-10-16 | pip `aideml`、CLI `aide` | 下記 |
| HKUDS/AI-Researcher | none(README にも LICENSE なし) | 5,880 | 2025-10-16 | Python + Docker + Gradio | 文献調査→アイデア→実装→執筆。NeurIPS 2025 — [README](https://github.com/HKUDS/AI-Researcher) |
| SamuelSchmidgall/AgentLaboratory | MIT | 5,929 | 2025-08-20 | Python | 2025-08 以降 push なし(メタデータのみ) |
| ResearAI/DeepScientist | Apache-2.0 | 3,413 | 2026-06-28 | npm `@researai/deepscientist`、CLI `ds` | 下記 |
| Denario-AI/Denario(旧 AstroPilot) | GPL-3.0 | 620 | 2026-10-02 | pip `denario` | 下記 |
| EvoScientist/EvoScientist | Apache-2.0 | 4,945 | 2026-11-11 | pip、CLI `EvoSci` | 下記 |
| aiming-lab/AutoResearchClaw | MIT | 14,858 | 2026-08-19 | pip(ソース)、CLI `researchclaw` | 下記 |
| Future-House/paper-qa | Apache-2.0 | 9,583 | 2026-11-09 | pip、CLI `pqa` | 3 章 |
| Future-House/aviary | Apache-2.0 | 287 | 2026-11-11 | Python(エージェント用 gym) | メタデータのみ |
| Future-House/ldp | Apache-2.0 | 139 | 2026-11-11 | Python | メタデータのみ |
| Future-House/robin | Apache-2.0 | 757 | 2026-04-21 | Python | 下記 |
| assafelovic/gpt-researcher | Apache-2.0 | 30,627 | 2026-11-09 | Python | メタデータのみ |
| stanford-oval/storm | MIT | 31,854 | 2025-09-30 | Python | 2025-09 以降 push なし(メタデータのみ) |
| langchain-ai/open_deep_research | MIT | 12,678 | 2026-08-10 | Python | **archived = true** |
| dzhng/deep-research | MIT | 19,891 | 2026-04-11 | TypeScript | メタデータのみ |
| bytedance/deer-flow | MIT | 85,246 | 2026-11-11 | ハーネス | メタデータのみ |
| microsoft/RD-Agent | MIT | 15,333 | 2026-10-21 | Python | メタデータのみ |
| MiroMindAI/MiroThinker | Apache-2.0 | 8,452 | 2026-07-06 | Python | メタデータのみ |
| EvoMap/AutoResearch | Apache-2.0 | 3,092 | 2026-09-16 | — | 「アイデアから論文用の証拠まで」(メタデータのみ) |
| Kaimen-Inc/Co-Scientist | Apache-2.0 | 289 | 2026-08-03 | — | Google Co-Scientist の再実装(メタデータのみ) |
| jimmc414/Kosmos | none | 607 | 2026-10-09 | — | Claude Code で駆動する Kosmos の実装(メタデータのみ、ライセンスなし) |
| davebcn87/pi-autoresearch | MIT | 8,232 | 2026-10-07 | pi 拡張 | 下記 |
| drivelineresearch/autoresearch-claude-code | MIT | 350 | 2026-09-07 | Claude Code スキル | pi-autoresearch の移植(メタデータのみ) |
| HKUDS/DeepCode | MIT | 16,837 | 2026-11-02 | — | メタデータのみ |

(出どころ: 各行の ★・push・API ライセンスは GitHub Search API、2026-11-11)

- **AI-Scientist-v3**("The Agentic Scientist")。`task.md` を渡すと、コーディングエージェントが案を出し、実験し、課題のルーブリックで採点し、反復する。その後ベースラインとアブレーション、**封印された最終評価**、事後分析、論文執筆。`claude` / `codex` / `cursor` / `opencode` / `gemini` / `pi` を Headless CLI 経由で切り替え(`agent.name=<agent>`)。各フェーズは Docker コンテナで動き、run ローカルの課題スナップショットだけを読む。フェーズが失敗しても run を捨てず "degraded" と報告。コマンドは `agsci run / doctor / inspect / review / investigate`。arXiv 2610.18933。リリースタグなし、main にコミット 8 件。— [README](https://github.com/SakanaAI/AI-Scientist-v3)
- **AI-Scientist-v2**。ライセンスは "The AI Scientist Source Code License"(Responsible AI License の派生)。成果の原稿で AI 使用を明確に開示する義務がある。エージェント的な木探索と実験管理エージェント。— [README](https://github.com/SakanaAI/AI-Scientist-v2)
- **karpathy/autoresearch**。`prepare.py`(固定、エージェントは触らない)、`train.py`(エージェントが編集する唯一のファイル)、`program.md`(人が育てる指示書。README は軽量な「skill」と呼ぶ)。1 回の学習は壁時計でちょうど 5 分、指標は `val_bpb`。約 12 実験/時。README のライセンス節は "MIT" だが LICENSE ファイルはページ上に見当たらない。— [README](https://github.com/karpathy/autoresearch)
- **OpenEvolve**。MAP-Elites、島モデル、LLM アンサンブル(OpenAI 互換 API に加え Claude Code / Copilot / Codex の CLI も可)、評価器の出力とエラーを次世代のプロンプトに戻す artifact feedback、全コンポーネントにシード。— [README](https://github.com/algorithmicsuperintelligence/openevolve)。`codelion/openevolve` は Search API の `repo:` 指定で返らず、現行の場所は algorithmicsuperintelligence 配下 — GitHub Search API(2026-11-11)
- **ShinkaEvolve**。2026 年の更新: 1 月 ICLR 2026 採択、2 月 エージェントスキル `shinka-setup` / `shinka-convert` / `shinka-run` / `shinka-inspect`(`npx skills add SakanaAI/ShinkaEvolve --skill '*'`)、3 月 `ShinkaEvolveRunner` に統合・PyPI 配布、5 月 サブスクリプションの CLI を変異モデルに使う `headless/claude`、`headless/codex@...`。非同期評価で 5〜10 倍のスループットと主張。Slurm 対応。— [README](https://github.com/SakanaAI/ShinkaEvolve)
- **AIDE**。目標と指標を自然言語で渡す(`aide data_dir=… goal=… eval=…`)。各 Python スクリプトがノードの木探索。`best_solution.py` と `tree_plot.html` を出力。商用の後継は Weco(CLI あり)。— [README](https://github.com/WecoAI/aideml)
- **DeepScientist**。ICLR 2026。Codex / Claude Code / Kimi Code / OpenCode の CLI を包む「ローカル優先の自律研究スタジオ」。各 quest は Git リポジトリで、ブランチと worktree が研究ルート。Findings Memory、失敗経路を資産として保存、人がいつでも一時停止・編集・再開。v1.6.0(5/12 の更新で告知)。引用と AI 使用の開示は「依頼」であってライセンス条件ではないと記載。— [README](https://github.com/ResearAI/DeepScientist)
- **Denario**。データ記述→アイデア→手法→結果→LaTeX 論文。AG2 と LangGraph、解析バックエンドは cmbagent(Apache-2.0)。本体は GPLv3。— [README](https://github.com/Denario-AI/Denario)
- **EvoScientist**。v0.4.2(2026-11-06)。サブエージェント 6 種、毎ターン記憶を蒸留して知識グラフにリンク、繰り返しパターンからスキル案を作り人が `/autoskills` で確認、スケジュール実行、MCP 追加(`EvoSci mcp add`)。— [README](https://github.com/EvoScientist/EvoScientist)
- **AutoResearchClaw**。23 段・8 フェーズ、段 5・9・20 が承認ゲート。段 15 で PROCEED / REFINE / PIVOT の判断。引用検証は 4 層(arXiv ID → CrossRef/DataCite DOI → Semantic Scholar の題名照合 → LLM の関連度採点)で、通らない文献は削除。v0.5.0(2026-05-19)。— [README](https://github.com/aiming-lab/AutoResearchClaw)
- **Robin**。病名から実験アッセイと治療候補を生成・順位づけ。文献エージェント(Crow / Falcon)に `EDISON_API_KEY`(有料クレジット)が必要。main にコミット 8 件。— [README](https://github.com/Future-House/robin)
- **pi-autoresearch**。`init_experiment` / `run_experiment` / `log_experiment`。`.auto/prompt.md`(新しいエージェントが再開できるセッション文書)、`.auto/log.jsonl`(追記のみ)、`.auto/measure.sh`(`METRIC name=number` を出力)、`.auto/checks.sh`(正しさの確認。失敗すると keep を止める)。3 回以上の実行後、指標の中央絶対偏差(MAD)をノイズの見積もりにして「最良の改善幅 ÷ MAD」を信頼度として表示(2.0 倍以上で実質的、1.0 未満はノイズ内。助言のみ)。— [README](https://github.com/davebcn87/pi-autoresearch)
- 一覧: webfuse-com/awesome-autoresearch(NOASSERTION、★2,592、2026-09-21)、WecoAI/awesome-autoresearch(CC0-1.0、★1,077)、yibie/awesome-autoresearch(none、★795、2026-11-11)、ResearAI/Awesome-AI-Scientist(Apache-2.0、★317、2025-10-31)— GitHub Search API(2026-11-11)

### Inferences
- AI-Scientist-v3 は「自前のエージェント基盤を持たず、既存のコーディングエージェント CLI を研究者として駆動する」設計で、DeepScientist・ShinkaEvolve の headless バックエンド・OpenEvolve の CLI 対応と同じ方向。スキル集中心のこのリポジトリと相性がよく、Apache-2.0 なので「封印された最終評価」「フェーズごとのコンテナと課題スナップショット」「degraded 報告」は取り込み・模倣の候補。ただしコミット 8 件・タグなしで成熟度は低い。
- pi-autoresearch の MAD 信頼度は、短時間実験のノイズと改善を区別する軽い仕組みで、`rl_stats.py` に載せやすい(モデルの暗算にしない方針にも合う)。MIT。
- ShinkaEvolve のスキル 4 個(Apache-2.0)は、SkyPilot 上の評価と組み合わせる進化探索の入口としてそのまま vendor 候補。
- AgentLaboratory(2025-08)、STORM(2025-09)、HKUDS/AI-Researcher(2025-10)、AI-Scientist v1/v2(2025-12)、open_deep_research(archived)は 2026 年後半に動きがなく、優先度は低い。

### Gaps
- AI-Scientist v1 の LICENSE 本文、karpathy/autoresearch の LICENSE ファイルの有無は直接確認していない(README 記載のみ)。
- gpt-researcher、RD-Agent、deer-flow、Kosmos、EvoMap/AutoResearch、Kaimen Co-Scientist は README 未読。
- FutureHouse の他のエージェント(Edison プラットフォーム側)は OSS の範囲を確認していない。

---

## 3. 文献検索と引用検証(エージェントから呼べるもの)

### Takeaway
引用検証は、LLM を使わない決定的な CI ゲートの citegate(MIT)と、PDF/LaTeX/BibTeX を広く受ける refchecker(MIT)が取り込み候補。検索は openags/paper-search-mcp(MIT、約 20 ソース)、blazickjp/arxiv-mcp-server(Apache-2.0)、54yyyu/zotero-mcp(本体 MIT)が実用的。hallucinator は AGPL-3.0 なのでコピー不可。

### Cited Findings

| ツール | API ライセンス | ★ | 最終 push | 形態 |
|---|---|---|---|---|
| chrisyangsong/citegate | MIT | 101 | 2026-08-30 | pip CLI、GitHub Action、pre-commit |
| markrussinovich/refchecker | MIT | 568 | 2026-10-27 | pip CLI、Web UI、デスクトップ、HTTP API |
| gianlucasb/hallucinator | NOASSERTION(README: AGPL-3.0) | 398 | 2026-09-23 | Rust TUI/CLI、Python バインディング |
| openags/paper-search-mcp | MIT | 3,061 | 2026-10-02 | MCP、CLI `paper-search`、Claude Code スキル |
| blazickjp/arxiv-mcp-server | Apache-2.0 | 3,271 | 2026-10-08 | MCP(`uvx arxiv-mcp-server`) |
| 54yyyu/zotero-mcp | MIT(`plugin/` は AGPL-3.0-or-later) | 5,858 | 2026-11-10 | MCP、`zotero-cli`、スキル |
| cookjohn/zotero-mcp | MIT | 1,276 | 2026-11-08 | Zotero 内プラグイン(メタデータのみ) |
| Future-House/paper-qa | Apache-2.0 | 9,583 | 2026-11-09 | pip、CLI `pqa` |
| wp-a/nature-academic-search | MIT | 384 | 2026-10-01 | スキル + MCP(CrossRef、PubMed、arXiv、OpenAlex、Europe PMC。メタデータのみ) |
| oksure/openalex-research-mcp | MIT | 60 | 2026-10-01 | MCP(メタデータのみ) |
| zongmin-yu/semantic-scholar-fastmcp-mcp-server | MIT | 166 | 2026-03-20 | MCP(メタデータのみ) |
| lstudlo/ScholarMCP | MIT | 33 | 2026-09-23 | MCP(メタデータのみ) |

(出どころ: GitHub Search API、2026-11-11)

- **citegate**。BibTeX の各エントリに `verified` / `not-found` / `retracted` / `mismatch` / `unverifiable`(ビルドを落とさない)/ `error` の判定。DOI があれば項目ごとに比較、なければあいまい検索。Crossref と OpenAlex、DOI なしは DBLP にフォールバック。撤回は OpenAlex のフラグと Crossref の更新記録(Retraction Watch を含む)。**検証に LLM を使わない**。失敗時は非ゼロ終了。週次で再検証して撤回時に issue を立てる例(`examples/retraction-monitor.yml`)、`--only retractions`。— [README](https://github.com/chrisyangsong/citegate)
- **refchecker**。Semantic Scholar、OpenAlex、CrossRef、DBLP、ACL Anthology で照合。入力は arXiv ID/URL、PDF、.tex、.bib/.bbl、テキスト。LLM は任意(抽出の改善と、疑わしい文献の Web 検索つき深掘り)。`--no-llm` で正規表現と構造チェックのみ。`pip install academic-refchecker`。— [README](https://github.com/markrussinovich/refchecker)
- **hallucinator**。PDF から文献を抜き、CrossRef、arXiv、Semantic Scholar、ACL Anthology、Europe PMC、PubMed、OpenAlex などで照合。フラグは「確認の手がかりであって判定ではない」と明記。DBLP はボット対策でオンライン API が壊れておりオフライン DB を推奨。AGPL-3.0。— [README](https://github.com/gianlucasb/hallucinator)
- **paper-search-mcp**。arXiv、PubMed、bioRxiv、medRxiv、Semantic Scholar、Crossref、OpenAlex、CORE、Europe PMC、dblp、OpenReview など約 20 ソース。Google Scholar は不安定、Sci-Hub は任意で既定は無効。CLI は JSON 出力。— [README](https://github.com/openags/paper-search-mcp)
- **arxiv-mcp-server** v0.8.2。19 ツール。`get_paper_latex_section`(元の LaTeX を節単位で読む)、`export_citations`(arXiv メタデータから BibTeX)、`citation_graph`(Semantic Scholar)、`watch_topic` / `check_alerts`(トピック監視)。同名の無関係な npm パッケージがあるので npm/npx で入れないよう警告。— [README](https://github.com/blazickjp/arxiv-mcp-server)
- **zotero-mcp**(54yyyu)。検索(意味検索を含む)、全文・PDF ページ範囲の読み取り、注釈、DOI/URL/BibTeX での追加、重複統合。任意で Scite の引用集計と撤回アラート。`zotero-mcp install-skill`。— [README](https://github.com/54yyyu/zotero-mcp)
- **paper-qa**。2025 年 12 月から CalVer(例 `v2025.12.17`)。エージェント的 RAG、メタデータは Semantic Scholar / Crossref / Unpaywall / OpenAlex、撤回確認、マルチモーダル解析。引用のたどり(citation traversal)はまだリポジトリにないと FAQ に記載。MCP の記載なし。— [README](https://github.com/Future-House/paper-qa)
- スキル集に組み込まれた引用検証(1・2 章で既出): ARIS `/citation-crosscheck`、AutoResearchClaw の 4 層検証、ARS の 4 索引ゲートと claim 監査、hyperresearch の引用文一致確認と撤回確認。

### Inferences
- `verify_bib.py` の比較対象として citegate が最も近い(決定的、LLM なし、終了コードで落とす)。判定に `unverifiable`(落とさない)と `error` を分けている点、撤回の監視、DOI なしのあいまい照合は、評価シナリオの合格例・不合格例に足せる失敗パターン。
- 「API に拒否された = 文献が存在しない」ではない、という扱いを ARIS(verify pending)、citegate(unverifiable / error)、hallucinator(lead, not a verdict)が独立に採用している。
- arxiv-mcp-server の LaTeX 節読みは、PDF 抽出で数式や表が崩れる問題を避けられ、引用した主張を原文と突き合わせる用途に向く。

### Gaps
- Semantic Scholar / OpenAlex 専用 MCP は小規模なものしか見つからず(★200 未満)、公式提供の有無は確認していない。
- alphaXiv や Exa などホスト型の検索 MCP は調べていない。
- 各ツールの検出精度(偽陽性・偽陰性率)の独立した評価は見つけていない。

---

## 4. エージェントの永続的な知識・記憶と長時間ループ

### Takeaway
記憶は qmd(MIT、ローカルのハイブリッド検索 + MCP + Claude Code プラグイン)と beads(MIT、Dolt 上の依存グラフつき課題管理)が定番で、どちらも 2026 年後半も更新されている。実験トラッカーは W&B 公式 MCP(MIT)と trackio(MIT、CLI の JSON 出力とアラート)がエージェントから読める。Paseo は schedule(新しいエージェントを定期起動)と heartbeat(同じ会話を定期的に起こす)を CLI で分けている。

### Cited Findings

| ツール | API ライセンス | ★ | 最終 push | 形態 |
|---|---|---|---|---|
| tobi/qmd | MIT | 31,050 | 2026-10-15 | npm `@tobilu/qmd`、MCP、Claude Code プラグイン |
| gastownhall/beads | MIT | 28,671 | 2026-11-10 | Go CLI `bd`、プラグイン、`beads-mcp` |
| getpaseo/paseo | NOASSERTION(README: Apache-2.0) | 23,794 | 2026-11-11 | デーモン + CLI + スキル |
| letta-ai/letta | Apache-2.0 | 25,417 | 2026-10-18 | 状態を持つエージェントの基盤(メタデータのみ) |
| thedotmack/claude-mem | Apache-2.0 | 116,069 | 2026-11-11 | セッション横断の文脈保存(メタデータのみ) |
| kepano/obsidian-skills | MIT | 51,641 | 2026-09-15 | Obsidian CLI・Bases・JSON Canvas 用スキル(メタデータのみ) |
| AgriciDaniel/claude-obsidian | MIT | 16,341 | 2026-10-25 | Obsidian + Claude Code の第二の脳(メタデータのみ) |
| eugeniughelbur/obsidian-second-brain | MIT | 5,282 | 2026-11-10 | Obsidian ボールトを記憶に(メタデータのみ) |
| Astro-Han/karpathy-llm-wiki | MIT | 2,726 | 2026-07-23 | Karpathy 式 LLM wiki のスキル(メタデータのみ) |
| atomicstrata/llm-wiki-compiler | MIT | 2,252 | 2026-11-11 | 生ソース→相互リンク wiki(メタデータのみ) |
| wandb/wandb-mcp-server | MIT | 72 | 2026-11-07 | MCP(ホスト型 / ローカル) |
| gradio-app/trackio | MIT | 1,775 | 2026-11-10 | Python ライブラリ + CLI |
| mlflow/mlflow | Apache-2.0 | 28,761 | 2026-11-11 | Python |

(出どころ: GitHub Search API、2026-11-11)

- **qmd**。`search`(BM25、SQLite FTS5)、`vsearch`(ベクトル)、`query`(BM25 + ベクトル + LLM のクエリ拡張 + リランク)。MCP ツールは `query` / `get` / `multi_get` / `status` / `metadata`、stdio か `qmd mcp --http`(localhost:8181)。プラグインは `claude plugin marketplace add tobi/qmd`。ローカル GGUF モデル 3 個(embeddinggemma-300M、qwen3-reranker-0.6b、クエリ拡張 1.7B)。`QMD_EMBED_MODEL` で多言語の埋め込みに差し替え可。— [README](https://github.com/tobi/qmd)
- **beads**。"Distributed graph issue tracker for AI agents, powered by Dolt"。`bd ready`(ブロッカーのない課題)、`bd update <id> --claim`(原子的な着手)、古い完了課題を要約する "memory decay"、`bd remember` / `bd prime`。`.beads/issues.jsonl` は書き出し用で正本ではない。`bd setup claude` がフックと設定を入れる。`go install` のパスは今も `github.com/steveyegge/beads` を指す。— [README](https://github.com/gastownhall/beads)。`steveyegge/beads` は Search API の `repo:` 指定で返らず、現行は gastownhall 配下 — GitHub Search API(2026-11-11)
- **Paseo**。ローカルのデーモンがコーディングエージェント(Claude Code、Codex、Copilot、OpenCode、Pi ほか)を管理。README の License 節は Apache-2.0。スキルは `npx skills add getpaseo/paseo` で `paseo-handoff`、`paseo-advisor`(作業を委ねずに第二意見)、`paseo-committee`(対照的な 2 エージェントで原因分析と計画)。— [README](https://github.com/getpaseo/paseo)。同梱スキル文書の構文: `paseo schedule create --cron "*/15 * * * *" "ping main build"`、`paseo heartbeat create --cron "*/15 * * * *" "check the build"`、`paseo send <agent-id> "<follow-up>"`(`--behavior steer|interrupt`)。サブエージェントを作った後はポーリングせず `notifyOnFinish` の通知を待つ。— [skills/paseo/SKILL.md](https://github.com/getpaseo/paseo/blob/main/skills/paseo/SKILL.md)
- Paseo の schedule は「この間隔で、このプロンプトを、このリポジトリで」新しいエージェントを起動する。heartbeat は現在の会話を続ける(`PASEO_AGENT_ID` が必要)。`paseo loop run` はワーカーを起動して出力を検証し、完了まで繰り返す。— Web 検索の要約([paseo.sh/docs/schedules](https://paseo.sh/docs/schedules)、[paseo.sh/docs/orchestration](https://paseo.sh/docs/orchestration)。paseo.sh はこのセッションから直接は読めず、検索結果の要約のみ)
- **wandb-mcp-server**(公式)。run 系: `query_wandb_tool`、`get_run_history_tool`、`compare_runs_tool`、`diagnose_run_tool`、`summarize_evaluation_tool`。Weave トレース系、レポート作成、`log_analysis_to_wandb`。読み取り専用モードあり。ホスト型は `https://mcp.withwandb.com/mcp`、ローカルは `uvx`(リリースタグ固定)。— [README](https://github.com/wandb/wandb-mcp-server)
- **trackio**。`wandb.init/log/finish` 互換。ローカル SQLite(Parquet に凍結可)。`trackio get alerts --project ... --json`、`trackio query project`(読み取り専用 SQL)。エージェントがアラートを上げ、Slack / Discord の webhook に送れる。ベータで DB スキーマは変わりうる。README に MCP サーバーの記載はない。— [README](https://github.com/gradio-app/trackio)。Claude Code などから使うスキルは `huggingface-trackio` — [huggingface/skills](https://github.com/huggingface/skills)
- **MLflow**。README は OpenTelemetry と MCP に「ネイティブ統合」と書き、Claude Code をトレース連携先に挙げるが、MCP サーバーのコマンドは README からは確認できなかった。— [README](https://github.com/mlflow/mlflow)
- 研究用の記憶をスキル集の側で持つ例(既出): claude-scholar の Obsidian プロジェクト KB、hyperresearch の markdown ボールト、ARIS `/research-wiki`、DeepScientist の Findings Memory、EvoScientist の記憶グラフと AutoSkills、Claude Code 公式の `ralph-loop` プラグイン。

### Inferences
- Paseo の「schedule = 毎回まっさらなエージェント」「heartbeat = 同じ会話を起こす」「loop = ワーカー + 検証役」の 3 区分は、長時間の実験監視を設計するときの語彙としてそのまま使える。SkyPilot ジョブの監視は heartbeat、日次の文献巡回は schedule に当たる。
- trackio は CLI が JSON を返し、SQL で直接読めるので、MCP を足さなくても「統計はスクリプトで」という方針のまま `rl_stats.py` から読める。W&B を使うなら公式 MCP の読み取り専用モードが安全側。
- 「markdown が正本、索引はキャッシュ」(hyperresearch)と qmd の組み合わせは、Obsidian + qmd の構成と同じ考え方で、`projects/<名前>/` ごとのノートに当てはめやすい。

### Gaps
- Paseo の API ライセンスは NOASSERTION、README は Apache-2.0。LICENSE ファイル本文は未確認で、取り込む前に確認が必要。paseo.sh のドキュメントは直接読めていない(許可ドメイン外)。
- qmd と beads の最新バージョン番号は確認できなかった(Releases 欄が取得できず)。
- Letta、claude-mem、obsidian-skills、LLM wiki 系は README 未読。
- MLflow の MCP サーバーとエージェント用スキルの有無は未確認。

---

## 5. 再現性と実験監査(エージェントによる)

### Takeaway
ベンチマークは OpenAI の PaperBench(MIT、frontier-evals 内)と、その拡張 2 件(いずれも MIT、2026-10 更新)が中心。日常の研究で使える「論文とコードの突き合わせ」は、claesbackman の `review-paper-code` / `audit-analysis` と ARA の rigor-reviewer(どちらも MIT のスキル)が最も近く、専用の成熟したツールは少ない。

### Cited Findings

| プロジェクト | API ライセンス | ★ | 最終 push | 内容 |
|---|---|---|---|---|
| openai/frontier-evals | MIT | 1,340 | 2026-10-12 | PaperBench、SWE-Lancer、EVMbench |
| pipelinelabai/paperbench-expanded | MIT | 50 | 2026-10-09 | PaperBench を ML 以外へ拡張 |
| UniPat-AI/PaperBenchX | MIT | 46 | 2026-10-08 | 12 分野の論文再現ベンチ(メタデータのみ) |
| openai/mle-bench | NOASSERTION | 1,794 | 2026-04-24 | ML エンジニアリングのベンチ(メタデータのみ) |
| METR/RE-Bench | NOASSERTION | 171 | 2026-10-20 | **archived = true**(メタデータのみ) |
| siegelz/core-bench | MIT | 80 | 2025-11-23 | 計算再現性のベンチ(メタデータのみ) |
| allenai/asta-bench | Apache-2.0 | 143 | 2026-11-10 | メタデータのみ |
| going-doer/Paper2Code | Apache-2.0 | 5,018 | 2026-03-25 | 論文からコード生成(メタデータのみ) |
| zzp1221/Research-Assistant-Agent | MIT | 193 | 2026-11-10 | 再現 + claim-evidence グラフ |
| ARA-Labs/Agent-Native-Research-Artifact | MIT | 709 | 2026-10-11 | 1 章 |
| AmberLJC/ara-paperbench | CC-BY-4.0 | 5 | 2026-07-09 | PaperBench 論文の ARA 化 32 件(メタデータのみ) |
| claesbackman/AI-research-feedback | MIT | 559 | 2026-10-28 | 1 章 |
| SocialCatalystLab/ape-papers | none | 444 | 2026-04-10 | 政策評価の自動化の実験(メタデータのみ) |

(出どころ: GitHub Search API、2026-11-11)

- **frontier-evals**。PaperBench は最先端 AI 論文のエンドツーエンド再現(arXiv 2504.01848)、コードは `project/paperbench`。リポジトリは MIT。— [README](https://github.com/openai/frontier-evals)
- **paperbench-expanded**。93 課題・12 研究領域(公開 12、非公開 81)。Harbor で実行(`run.py check` → `run` → `summary`)。計算で確かめられる性質は決定的チェック、モデル判断が要る部分は固定の審査モデル。課題ごとに `tests/rubric.json`(重みつき基準)。**欠測やインフラ起因のスコアは 0 点に数えず**、網羅率と失敗数を併記する。「報告は証拠を説明できるが、証拠の代わりにはならない」。10 構成中の最良で完全再現 13 課題(13.98%)、部分点 59.08%(同プロジェクトの報告)。— [README](https://github.com/pipelinelabai/paperbench-expanded)
- **Research-Assistant-Agent** v0.9.0。層つきルーブリックを凍結し、論文の各主張と判定基準を run の実成果物に結びつけて網羅率を計算。結果は completed / partial / smoke / blocked / failed / needs review で表示(「ノードが終わった = 成功」としない、モック結果を本実験として出さない)。リポジトリのリビジョン固定、EnvironmentManifest、`manifest.json` と `checksums.sha256` つきの書き出し。Windows デスクトップ、Docker Compose、ソースの 3 形態。— [README](https://github.com/zzp1221/Research-Assistant-Agent)
- 自律研究フレームワーク側の監査機構(2 章で既出): AI-Scientist-v3 の封印された最終評価、ARS の実験ロックと来歴の取り込み(ARS 自身が「手続きが実行されたこと・生データの真正性・再現性は保証しない」と明記)。

### Inferences
- 取り込みやすい「監査の型」は 3 つ。(a) 主張→証拠の結びつけと網羅率(ARA の `claims.md` と `evidence/`、Research-Assistant-Agent)。(b) 結果の状態ラベルを成功/失敗の 2 値にしない(smoke / partial / blocked)。(c) 欠測を 0 点扱いにしない(paperbench-expanded)。いずれも MIT で、評価シナリオの合格例・不合格例に落とし込める。
- `audit-analysis` の「文脈の空いたサブエージェントで、指摘にはファイル・行・引用を必須にする」は、Codex を別モデル査読者にする構成に上乗せできる。
- PaperBench 系はベンチマークであって日常の道具ではないが、ルーブリックの形式(重みつきの木、`rubric.json`)は自前スキルの評価(`evals/run_evals.py`)の参考になる。

### Gaps
- PaperBench 本体のルーブリック・審査器・Code-Dev 版の現状は `project/paperbench` の README を読んでおらず未確認。
- 「論文の数値と実行ログの数値を自動で照合する」専用の成熟した OSS は、今回の検索では見つからなかった(スキル内の手順としては存在)。
- mle-bench と RE-Bench のライセンス本文(API は NOASSERTION)は未確認。
