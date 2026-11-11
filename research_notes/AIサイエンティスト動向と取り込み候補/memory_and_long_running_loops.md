# 長時間・自己改善ループとプロジェクト横断の知識管理（研究自動化への適用、2025–2026）

調査日: 2026-11-11。出典の確度を各項目に付けた。
- 【一次】= 原典（Anthropic の記事・公式ドキュメント・arXiv 本文）を取得して確認
- 【要旨】= arXiv の abstract だけ確認
- 【二次】= 検索結果の要約のみ（原典は未取得。数値・細部は未検証）

ネットワーク制約で取得できなかったもの: paseo.sh（許可ドメイン外）。Paseo の記述はすべて【二次】。

## Q1. Anthropic は長時間エージェントとハーネス設計に何を勧めているか（2025–2026）

### Takeaway
一貫した主張は「状態はコンテキストではなくファイルと git に置き、各セッションは空の状態から決まった手順で復元し、完了判定は生成役と別の検証（E2E テスト・別エージェントの評価）に委ねる」。ハーネスの各部品は「モデルが単独でできないこと」への仮定なので、モデル更新のたびに外せるか試すことも勧めている。

### Cited Findings

**Effective harnesses for long-running agents（2025-11-26）【一次】**
- 2 種類のプロンプトを使い分ける。初回だけ動く initializer agent が環境を整え（`init.sh`、進捗ログ、最初の git commit、機能一覧）、以降の coding agent は毎回 1 機能だけ進めて、きれいな状態と構造化した更新を残す — [Anthropic](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- ファイル: `feature_list.json`（全機能を最初は failing で列挙。項目は category / description / 検証手順 steps / `passes: false`。coding agent が変えてよいのは `passes` だけ）、`claude-progress.txt`（各セッションの作業ログ）、`init.sh`（サーバ起動と基本 E2E 確認） — [Anthropic](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- セッション開始の定型手順: (1) `pwd` (2) git log と進捗ファイルを読む (3) 機能一覧から最優先の未完了項目を選ぶ (4) `init.sh` で起動し、新しい作業の前に基本 E2E テストを回して前セッションの壊れを検出 — [Anthropic](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- 失敗モードと対策の対応: 「早すぎる完了宣言」→構造化した機能一覧と 1 件ずつの作業、「壊れた/未記録の状態を残す」→開始時に読んでテスト・終了時に commit と進捗更新、「未検証で完了扱い」→人間のユーザーと同じ経路（ブラウザ自動化）で検証してから passing、「起動方法の探索で浪費」→`init.sh` — [Anthropic](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- Claude は単体テストや `curl` だけで完了扱いにしがちで、ブラウザ自動化（Puppeteer MCP）で改善した。ただしネイティブの alert モーダルは見えず、そこに依存する機能はバグが多かった — [Anthropic](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- 未解決として明記: 単一汎用エージェントとマルチエージェントのどちらがよいか、Web 開発以外（科学研究・金融モデリングなど）に一般化するか — [Anthropic](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)

**Harness design for long-running application development（2026-03-24、Prithvi Rajasekaran）【一次】**
- planner（1–4 文の依頼を仕様に展開。技術詳細は高レベルに留め、上流の誤りが連鎖しないようにする）／generator（スプリント単位で実装、git 使用）／evaluator（Playwright MCP で実アプリを操作。基準ごとに下限があり、1 つでも割ればスプリント不合格）の 3 役 — [Anthropic](https://www.anthropic.com/engineering/harness-design-long-running-apps)
- sprint contract: コードを書く前に generator が「完了の定義と検証方法」を提案し、evaluator と合意するまで往復する。エージェント間のやりとりはファイル経由 — [Anthropic](https://www.anthropic.com/engineering/harness-design-long-running-apps)
- compaction と context reset の違い: 「While compaction preserves continuity, it doesn't give the agent a clean slate.」Sonnet 4.5 は "context anxiety" を示したので reset（新規エージェント＋構造化した引き継ぎ）が必須だったが、Opus 4.5 ではほぼ解消し reset を外した — [Anthropic](https://www.anthropic.com/engineering/harness-design-long-running-apps)
- 評価役の弱点: 「Out of the box, Claude is a poor QA agent.」実際の問題を見つけても自分を説得して合格にする、表面的にしか試さない。対策は評価ログを読んで人の判断とのずれを見つけ、QA プロンプトを数回改訂すること。主観評価は採点内訳つき few-shot で採点のぶれを抑えた — [Anthropic](https://www.anthropic.com/engineering/harness-design-long-running-apps)
- 費用の実例: レトロゲーム作成で単独実行 20 分・$9（壊れた成果物）に対しフルハーネス 6 時間・$200。Opus 4.6 での DAW 作成は約 3 時間 50 分・$124.70 — [Anthropic](https://www.anthropic.com/engineering/harness-design-long-running-apps)
- Opus 4.6 ではスプリント構造を外し、評価は最後の 1 回に変更。planner と evaluator は残した（planner なしだと generator が範囲を小さく見積もる）。evaluator は「It is worth the cost when the task sits beyond what the current model does reliably solo.」 — [Anthropic](https://www.anthropic.com/engineering/harness-design-long-running-apps)
- 原則: 各部品は「encodes an assumption about what the model can't do on its own」。モデルが良くなるたびに仮定を検証し直す — [Anthropic](https://www.anthropic.com/engineering/harness-design-long-running-apps)

**Effective context engineering for AI agents（2025-09-29）【一次】**
- コンテキストは「a finite resource with diminishing marginal returns」。目標は「the smallest possible set of high-signal tokens」。窓が埋まるほど想起精度が落ちる（context rot） — [Anthropic](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- just-in-time 取得: 軽い識別子（ファイルパス、保存済みクエリ、リンク）だけ持ち、必要時にツールで読む。Claude Code は CLAUDE.md だけ先読みし、残りは glob/grep のハイブリッド — [Anthropic](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- 長時間向けの 3 手法と向き: compaction（往復の多い作業。まず recall を最大化してから precision を上げる。最軽量は古いツール結果の消去）、structured note-taking（NOTES.md や ToDo を窓の外に持つ。節目のはっきりした反復開発向き）、sub-agent（各自は数万トークン使い、1,000–2,000 トークン程度の要約を返す。並列探索が効く調査向き） — [Anthropic](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)

**How we built our multi-agent research system（2025-06-13）【一次】**
- オーケストレータ＋並列サブエージェント構成が、内部の調査評価で単一エージェントを 90.2% 上回った。トークン消費はチャット比でエージェント約 4 倍、マルチエージェント約 15 倍。BrowseComp では 3 要因で性能分散の 95% を説明し、トークン使用量だけで約 80% — [Anthropic](https://www.anthropic.com/engineering/multi-agent-research-system)
- 委任には「an objective, an output format, guidance on the tools and sources to use, and clear task boundaries」が必要。曖昧だと作業が重複する — [Anthropic](https://www.anthropic.com/engineering/multi-agent-research-system)
- リードは計画をメモリに保存する（20 万トークン超で切り詰められるため）。サブエージェントは成果を外部に保存し「lightweight references」だけ返す — [Anthropic](https://www.anthropic.com/engineering/multi-agent-research-system)
- 運用: 失敗時は最初からではなく失敗点から再開。再試行ロジックと定期チェックポイントという決定的な安全策を併用。評価は約 20 件の小標本から始め、状態を持つエージェントは途中経過でなく最終状態で評価 — [Anthropic](https://www.anthropic.com/engineering/multi-agent-research-system)

**Memory tool（API、`memory_20250818`）【一次】**
- クライアント側で実装するファイル操作ツール（view / create / str_replace / insert / delete / rename）。`/memories` 配下に限定する。有効にすると API が次の指示をシステムプロンプトに自動追加する — [Claude Platform docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool)
  ```
  IMPORTANT: ALWAYS VIEW YOUR MEMORY DIRECTORY BEFORE DOING ANYTHING ELSE.
  MEMORY PROTOCOL:
  1. Use the `view` command of your `memory` tool to check for earlier progress.
  2. ... (work on the task) ...
     - As you make progress, record status / progress / thoughts etc in your memory.
  ASSUME INTERRUPTION: Your context window might be reset at any moment, so you risk losing any progress that is not recorded in your memory directory.
  ```
- 散らかり対策の追加プロンプト例:「always try to keep its content up-to-date, coherent and organized. You can rename or delete files that are no longer relevant. Do not create new files unless necessary.」 — [Claude Platform docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool)
- 「Multisession software development pattern」として同じ型を公式化: 初回セッションが進捗ログ・機能チェックリスト・起動スクリプトへの参照を用意 → 以降は開始時に読む → 終了前に進捗ログを更新。「Mark a feature complete only after end-to-end verification confirms it works, not when the code is written.」 — [Claude Platform docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool)
- 運用上の注意: ファイルサイズに上限を設ける、長く参照されないメモリは定期削除、パストラバーサル検証、機微情報の書き込み検査。compaction と併用し「memory preserves the information that must survive summarization」 — [Claude Platform docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool)

**Claude Code: メモリ・スケジュール・headless・hooks【一次】**
- auto memory は `~/.claude/projects/<project>/memory/` に `MEMORY.md`（索引、1 行 1 件）＋トピック別ファイル。セッション開始時に読むのは `MEMORY.md` の先頭 200 行または 25KB まで。リポジトリ単位（worktree 間で共有）でマシンローカル、クラウド環境とは共有されない。`autoMemoryDirectory` で場所を変えられる。CLAUDE.md は 200 行未満が目安 — [Claude Code docs: memory](https://code.claude.com/docs/en/memory)
- CLAUDE.md と auto memory はどちらも「context, not enforced configuration」。確実に止めたい操作は PreToolUse hook を使う — [Claude Code docs: memory](https://code.claude.com/docs/en/memory)
- スケジュールは 3 種: クラウド（旧称 routines。マシン不要、毎回リポジトリを新規 clone、最短 1 時間間隔、既定で auto mode）、Desktop（ローカルファイル可）、`/loop`（セッション内、最短 1 分、定期タスクは 7 日で失効、取りこぼした発火の追い実行なし、1 セッション 50 件まで） — [Claude Code docs: scheduled tasks](https://code.claude.com/docs/en/scheduled-tasks)
- クラウドのスケジュールタスクは実行ごとに新しいセッションで開き、既定ブランチから始めて `claude/` 接頭辞のブランチに push する。トリガーはスケジュール・API（HTTP POST）・GitHub イベント。研究プレビュー扱い — [Claude Code docs: routines](https://code.claude.com/docs/en/routines)
- `/loop` を間隔なしで使うと Claude が 1 分–1 時間の待ち時間を毎回選び、完了時は自分でループを止められる。条件達成まで回し続ける用途は `/goal`、ポーリングの代わりに Monitor ツールやチャンネル（イベント駆動）が案内されている — [Claude Code docs: scheduled tasks](https://code.claude.com/docs/en/scheduled-tasks)
- headless（`claude -p`）: `--output-format json` の結果に `total_cost_usd` とモデル別内訳が入る（クライアント側の推定値で請求と異なりうる）。`--max-budget-usd` に達すると残りのバックグラウンド作業も止まる。無人実行では `--permission-prompts none` で「確認待ち」を拒否に変えられる。SIGTERM は終了コード 143 で実行中の Bash のプロセスツリーを止め、SessionEnd hook を走らせる。`--bare` は hooks・skills・auto memory・CLAUDE.md を読まない（hooks が必要な実行には使わない） — [Claude Code docs: headless](https://code.claude.com/docs/en/headless)
- hooks: `Stop` は exit 2 または `decision: "block"` で停止を差し止めて続行させられ、`continue: false` は無条件に止める。`PreToolUse` は `permissionDecision: "deny"` でツール呼び出しを拒否できる（タイムアウト時に止めたいなら `onFailure: "block"`）。`PostToolBatch` の exit 2 はエージェントループを止める。型は command / http / mcp_tool / prompt / agent（agent は experimental） — [Claude Code docs: hooks](https://code.claude.com/docs/en/hooks)

### Inferences
- 依頼元の構成（毎回新規セッション・承認ゲート・台帳ファイル）は Anthropic の「initializer / worker ＋ 進捗ファイル」型と同型。足りない可能性が高いのは (a) 開始時に前回の成果を**再検証する**手順（`init.sh` 相当の smoke test）、(b) 「合格にしてよいのは誰か」の分離（worker は `passes` 以外を書き換えない・評価は別役）、(c) 実験前に完了定義を合意する sprint contract 相当。
- 機能一覧を JSON にして「変えてよい欄」を 1 つに絞る設計は、台帳の「状態欄だけ更新可・過去行は追記のみ」にそのまま移せる。
- 研究ループの「test oracle」は Web 開発の E2E テストほど明確でない。Anthropic 自身が科学研究への一般化を未解決としているので、ここは AI サイエンティスト系（Q2・Q4）の検証段階設計で補う必要がある。
- 予算上限は `--max-budget-usd`（API 費用）しか公式手段がなく、GPU 費用は自前のラッパーで数える必要がある。

### Gaps
- Agent Skills の記事（スキルの段階的開示など）と subagent の持続メモリ設定の詳細は今回取得していない。
- `/goal` と Monitor ツール、チャンネルの個別ページは未読（scheduled-tasks ページからの言及のみ）。
- The Decoder が伝える「memory tool＋context editing で 39% 改善、context editing 単独で 29%」は【二次】で、Anthropic の原典では未確認 — [The Decoder](https://the-decoder.com/?p=27732)

## Q2. AI サイエンティスト系は長い実行のあいだ状態をどう保つか

### Takeaway
どの系も「生ログをそのまま次に渡さない」。Kosmos は要約を構造化した world model に集約して次サイクルの課題をそこから生成し、DeepScientist は発見を段階（Idea → Implement → Progress）つきのレコードで持ち、AIDE / AI Scientist-v2 は解の木（ノード＝コード＋結果）を持って要約演算子で必要部分だけプロンプトに入れる。Sage-Taiyi は「何が確立され、次の探索に何を意味するか」を別レベルの Cognitive State として明示する。

### Cited Findings

**Kosmos（Edison Scientific / FutureHouse、arXiv 2511.02824、2025-11-04）【一次】**
- 各サイクルで文献検索とデータ解析のタスクを最大 10 件実行し、その出力の要約で world model を更新、次に world model に問い合わせて次サイクルのタスクを提案する。この文脈管理で既存系の 8 倍の反復数を回せたとする — [arXiv HTML](https://arxiv.org/html/2511.02824v2)
- 1 実行あたり平均でデータ解析エージェント 166 回・文献レビュー 36 回のロールアウト、コード約 42,000 行、論文 1,500 本。最大 12 時間 — [arXiv HTML](https://arxiv.org/html/2511.02824v2)
- 報告書の各記述と図は、文献か解析ノートブック（Jupyter）のどちらかを必ず引用する。world model に集約しているので全主張が出所に辿れる — [arXiv HTML](https://arxiv.org/html/2511.02824v2)
- 独立した科学者の評価で記述の 79.4% が正確。内訳はデータ解析 85.5%、文献 82.1% に対し、**統合（synthesis）記述は 57.9%** — [arXiv HTML](https://arxiv.org/html/2511.02824v2)
- 価値ある発見の数はサイクル数に対しほぼ線形（20 サイクルまで、協力者の評価） — [arXiv abs](https://arxiv.org/abs/2511.02824)

**DeepScientist（Westlake、arXiv 2509.26603、2025-09-30、ICLR 2026 掲載は【二次】）【一次】**
- Findings Memory は数千件の構造化レコードで、人の知識（論文・コード）と自系の過去の発見の両方を持つ。文脈長の制約には別の検索モデルで Top-K を選んで対応 — [arXiv HTML](https://arxiv.org/html/2509.26603v1)
- レコードは段階を持つ。未検証の仮説は Idea Finding として作られ、LLM レビュアー（代理モデル）が Findings Memory 全体を踏まえて utility / quality / exploration value を 0–100 の整数で採点する。UCB の獲得関数で選ばれたものが Implement Finding に昇格して実験され、ログと結果がレコードに書き戻される。ベースラインを超えたものだけ Progress Finding に昇格し、追加の分析実験（アブレーション、別データセット）と報告作成に進む — [arXiv HTML](https://arxiv.org/html/2509.26603v1)
- 昇格しなかった案も Findings Memory に残し、以降の探索の材料にする — [arXiv HTML](https://arxiv.org/html/2509.26603v1)
- 規模: 5,000 超のアイデア → 約 1,100 を実験 → 21 が SOTA 超え。20,000 GPU 時間超。失敗試行の標本を専門家が分析したところ**約 60% は実装エラーで早期終了**、残り 40% の大半は改善なしか悪化。全 5,000 件を素直に試せば 100,000 GPU 時間超が必要だったと試算 — [arXiv HTML](https://arxiv.org/html/2509.26603v1)
- 完全無人ではない: 「Three human experts supervise the process to verify outputs and filter out hallucinations.」開始点の SOTA 手法は人手で再現し、実行ログとテストスクリプトを残して渡している — [arXiv HTML](https://arxiv.org/html/2509.26603v1)

**AI Scientist v1 / v2（Sakana、arXiv 2408.06292 / 2504.08066）**
- v2 は実験進行マネージャが 4 段階（予備調査 → ハイパラ調整 → 研究計画の実行 → アブレーション）を管理し、**各段階に明示的な停止条件**がある（段階 1 は動く原型ができたら、段階 2 は学習曲線が収束し 2 つ以上のデータセットで成功したら）。各段階の完了時にチェックポイントを記録し、最良ノードを次段階の根にする — [arXiv HTML](https://arxiv.org/html/2504.08066v1)【一次】
- 木のノードは実行結果で buggy / non-buggy に分類。buggy は保存したエラー情報でデバッグ、non-buggy は改良。ハイパラノードは試行済み設定の記録を持ち重複実験を防ぐ。段階の終わりに最良実験の replication ノードを複数回し、aggregation ノードが平均と標準偏差をまとめる — [arXiv HTML](https://arxiv.org/html/2504.08066v1)【一次】
- v1 は人が書いたコードテンプレートに依存し、実験は直線的な仮説検証だった（v2 論文による整理） — [arXiv HTML](https://arxiv.org/html/2504.08066v1)【一次】

**AIDE（Weco、arXiv 2502.13138）【一次】**
- 状態は解の木（各ノード＝スクリプトと評価スコア）。プロンプトを短く保つため要約演算子が木から「各改良試行の高レベルな案と指標」だけを取り出す。探索方針は、初期案が規定数に達するまで drafting、デバッグ深さの上限内なら debugging、それ以外は最良の non-buggy 解を improving — [arXiv HTML](https://arxiv.org/html/2502.13138v1)

**Sage-Taiyi（上海 AI Lab、arXiv 2611.12762、2026-11-09）【一次・ただし自己報告のベンチマーク】**
- オブジェクトレベル（Target Tree＝探索目標、Idea Graph＝アイデアの生成と改良、検証結果が戻る Evidence State）とメタレベル（課題固有の Cognitive State、再利用する Cognitive Repertoire＝方法論的ヒューリスティクスと Cognitive Operators）を分ける。monitoring が探索結果から Cognitive State を更新し、control がその状態を使って次の目標と方法を選ぶ — [arXiv HTML](https://arxiv.org/html/2611.12762)
- 動機として明記: 反復だけでは「findings from different branches are retained with their evidence and applicability conditions」も、それが後の方法選択に効くことも保証されない — [arXiv HTML](https://arxiv.org/html/2611.12762)
- 自作の Taiyi-Bench（50 論文由来の 265 課題）で Overall 54.0、最強ベースラインの AI Scientist-v2 は 47.9 — [arXiv abs](https://arxiv.org/abs/2611.12762)

**Karpathy autoresearch（2026-03）**
- 構成は 3 ファイル: `prepare.py`（固定、触らない）、`train.py`（エージェントが編集する唯一のファイル）、`program.md`（人が編集するエージェント向け指示）。学習は壁時計で固定 5 分、指標は val_bpb（低いほど良い）。「modifies the code, trains for 5 minutes, checks if the result improved, keeps or discards, and repeats」 — [GitHub README](https://github.com/karpathy/autoresearch)【一次】
- 結果ログは `results.tsv` に commit / val_bpb / memory / status（keep・discard・crash）/ description を記録し、discard は git で巻き戻すがログには残す、という記述は解説記事由来で README には書式の記載がない — [解説](https://programmerraja.is-a.dev/notes/AI-ML/Research/Auto-Research)【二次】

### Inferences
- 台帳の 1 行に最低限ほしい欄は、各系の共通部分から「段階（案/実行済/検証済）・根拠への参照（コミット、ノートブック、ログのパス）・採点（期待効用と不確かさ）・失敗理由の種別（実装エラーか仮説の否定か）」。DeepScientist の 60% が実装エラーという数字は、「実装失敗」と「仮説が否定された」を台帳で区別しないと、良い案を誤って棄却済みにする危険を示す。
- Kosmos の統合記述 57.9% は、個々の実験結果より「複数結果をまとめた解釈」が最も誤りやすいことを示す。朝の要約レポートのうち統合・解釈の部分を人の承認ゲートの重点対象にする根拠になる。
- 「次に何をやるかは world model / Cognitive State から生成する」設計は、新規セッションに生ログを渡さず要約状態だけ渡す現行方針と整合する。Sage-Taiyi の「発見に適用条件を付けて保持」は台帳の欄として取り込める。

### Gaps
- Kosmos の world model の内部スキーマ（何の実体をどう構造化するか）は本文の該当箇所を抽出できておらず未確認。
- AI Scientist v1 の「アイデアアーカイブ」（生成済みアイデアを次の生成の文脈に入れる仕組み）は今回原文で確認していない。
- AIDE の「journal」という呼称は論文本文の抽出では確認できず（実装側の用語の可能性）。未検証。
- Sage-Taiyi は公開 2 日後の時点で第三者の再現なし。

## Q3. 「生の実験ログ → 検証済みの知見」への昇格と、プロジェクト横断の教訓共有

### Takeaway
効果の証拠がある設計は共通して、(1) 軌跡そのものではなく蒸留した小さな項目を保存し、(2) 失敗からも教訓を取り、(3) 全面書き直しではなく項目単位の差分更新にし、(4) 取り出す件数を絞る。逆に、全面書き直しによる崩壊、件数を増やすほど下がる成績、誤った・古い記憶の追従、記憶の汚染が失敗モードとして報告されている。証拠の大半は Web 操作・コーディング・QA ベンチマークで、研究自動化での直接の検証は DeepScientist の主張程度しかない。

### Cited Findings

**ReasoningBank（Google、arXiv 2509.25140）【一次】**
- 記憶項目は title（戦略の短い識別子）/ description（1 文要約）/ content（蒸留した推論手順・判断理由）の 3 要素。成功・失敗の判定は正解ラベルなしの LLM-as-judge による自己判定 — [arXiv HTML](https://arxiv.org/html/2509.25140v1)
- 保存は JSON で、各エントリは課題クエリ・元の軌跡・記憶項目を持つ。統合は最小限で、新項目を追記するだけ（剪定・統合なし。merging や forgetting は今後の課題と明記） — [arXiv HTML](https://arxiv.org/html/2509.25140v1)
- 利用時のプロンプトは、各ステップで「記憶項目を使うかどうかをまず明示的に議論してから行動する」よう求める — [arXiv HTML](https://arxiv.org/html/2509.25140v1)
- 効果: 相対改善は最大 34.2%、操作ステップは 16.0% 減。失敗軌跡を加えると、成功のみから作る手法（AWM）は成績が下がったが ReasoningBank は上がった — [arXiv HTML](https://arxiv.org/html/2509.25140v1)
- **取り出し件数は 1 件が最良**: WebArena-Shopping で記憶なし 39.0 → 1 件で 49.7、件数を増やすと 46.0、45.5、44.4 と低下。「excessive experiences may introduce conflicts or noise」 — [arXiv HTML](https://arxiv.org/html/2509.25140v1)

**ACE: Agentic Context Engineering（Stanford ほか、arXiv 2510.04618）【一次】**
- Generator / Reflector / Curator の 3 役。文脈は箇条書き項目の集まりで、各項目は一意 ID と「helpful / harmful とマークされた回数」のカウンタを持つ。Generator がどの項目が役立ったか・誤導したかを印付けし、Reflector が修正案を出す — [arXiv HTML](https://arxiv.org/html/2510.04618v1)
- 全面書き直しをやめ、局所的な delta 更新と grow-and-refine（追加しつつ重複を除く）にする — [arXiv HTML](https://arxiv.org/html/2510.04618v1)
- **context collapse の実測**: 全面書き直し方式で、ステップ 60 に 18,282 トークン・精度 66.7 だった文脈が、次のステップで 122 トークンに崩れ精度 57.1（適応なしの基準 63.7 より悪い） — [arXiv HTML](https://arxiv.org/html/2510.04618v1)
- 効果: エージェント課題で +10.6%、金融で +8.6%。正解ラベルなしでも実行フィードバックで適応できる — [arXiv abs](https://arxiv.org/abs/2510.04618)
- 限界: Reflector が弱いと文脈が「noisy or even harmful」になる。簡潔な高レベル指示のほうが効く課題もある — [arXiv HTML](https://arxiv.org/html/2510.04618v1)

**その他の記憶手法【要旨】**
- Agent Workflow Memory: 過去の経験から再利用できる手順（workflow）を誘導して選択的に与える。Mind2Web で 24.6%、WebArena で 51.1% の相対改善 — [arXiv abs](https://arxiv.org/abs/2409.07429)
- Dynamic Cheatsheet: 推論時に自己編集する持続メモリ。全文記録ではなく「concise, transferable snippets」を保持。検証済みコードの再利用で算術系課題がほぼ満点に — [arXiv abs](https://arxiv.org/abs/2504.07952)
- A-MEM: Zettelkasten 方式。新しい記憶に文脈説明・キーワード・タグを付け、既存の記憶とリンクし、新規追加が既存記憶の記述更新を引き起こす（memory evolution） — [arXiv abs](https://arxiv.org/abs/2502.12110)
- Mem0: 会話から要点を抽出・統合・検索。LOCOMO で OpenAI の記憶機能に対し LLM 判定指標で 26% 相対改善、全文脈方式に比べ p95 遅延 91% 減・トークン費用 90% 超減 — [arXiv abs](https://arxiv.org/abs/2504.19413)

**Karpathy「LLM Wiki」（gist、2026-04-04）【一次】**
- 3 層: raw sources（不変。LLM は読むだけ）、wiki（LLM が全面的に所有する markdown。要約、実体・概念ページ、比較）、schema（CLAUDE.md / AGENTS.md。構造・規約・手順を定義し、人と LLM で育てる） — [gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
- 操作: ingest（1 ソースで 10–15 ページに波及しうる。1 件ずつが好み）、query（良い回答は新ページとして wiki に書き戻す）、lint（矛盾、古い主張、孤立ページ、相互参照の欠落、データの穴を定期検査） — [gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
- `index.md` は分類別の目録（リンク＋1 行要約）で、ingest のたびに更新し、質問時に最初に読む。約 100 ソース・数百ページ規模なら埋め込み検索なしで足りるとする。`log.md` は追記専用の時系列で、`## [2026-04-02] ingest | Article Title` のように接頭辞を揃え grep / tail で扱えるようにする — [gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
- 道具は任意: qmd（BM25＋ベクトルのハイブリッド検索と LLM 再ランク、CLI と MCP）、Obsidian（閲覧とグラフ表示）、git で履歴管理 — [gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)

**失敗モードと攻撃面**
- Claude Code の auto memory も肥大に上限を置く: `MEMORY.md` が 200 行 / 25KB に近づくと、1 行 1 件に保つ・詳細はトピックファイルへ移す・古い項目を統合または削除するよう促す — [Claude Code docs](https://code.claude.com/docs/en/memory)【一次】
- MemoryGraft（arXiv 2512.16962）: 長期記憶に少数の偽の「成功体験」を植えると、検索された過去事例を模倣する性質のためセッションをまたいで挙動が誘導される — [arXiv](https://arxiv.org/abs/2512.16962)【二次】
- STALE（arXiv 2605.06527）: 後の観測が明示的な否定なしに以前の記憶を無効にする「Implicit Conflict」を扱う — [arXiv](https://arxiv.org/pdf/2605.06527)【二次】
- The Compliance Trap（2607.10608）: 記憶由来の誤りを Entry–Propagation–Recovery で分析し、課題に対して誤った記憶でも最初の判断点で採用してしまうことが主因とする — [alphaXiv](https://www.alphaxiv.org/abs/2607.10608.md)【二次】

### Inferences
- 昇格の型は「生ログ（不変）→ プロジェクト台帳の段階つきレコード → 再現・アブレーションを通ったものだけ横断の知識ベースへ」の 3 層にするのが、LLM Wiki の raw/wiki 分離と DeepScientist の段階昇格の両方に合う。横断側の各項目には ACE 式の ID と「役立った/誤導した」カウンタ、適用条件、出所（プロジェクトとコミット）、最終確認日を持たせると、古い・誤った教訓を lint で落とせる。
- 横断知識ベースの更新は追記と項目単位の編集に限り、LLM に全体を書き直させない（context collapse の実測が根拠）。
- 新規セッションに注入する教訓は少数に絞る（ReasoningBank で 1 件が最良）。全部を先読みさせるより、索引 1 枚＋必要時に検索のほうが Anthropic の just-in-time 方針とも合う。
- 記憶への書き込み経路は攻撃面でもある。Web や上流リポジトリから読んだ文面が「成功体験」として横断知識に入らないよう、昇格を人の承認ゲートかスクリプト検証（数値の再計算）に通す設計が妥当。
- 「失敗からの教訓」は、失敗理由が実装バグか仮説の否定かを区別して書かないと、誤った否定的教訓が他プロジェクトに広がる（DeepScientist の 60% 実装エラーと ReasoningBank の失敗活用を合わせた推論）。

### Gaps
- Obsidian vault＋qmd を研究ループの横断メモリに使った実践報告で、効果を測ったものは見つからなかった。gist 自体も「パターンの記述で実装ではない」と断っている。日本語（note / Zenn）の実践記事は今回の検索では拾えていない。
- 記憶機構が**研究の成果**（発見数や再現率）を上げるという対照実験は未発見。DeepScientist の「並列資源と発見数がほぼ線形、共有 Findings Memory の効果」は著者の主張で、メモリの有無を比べたアブレーションは確認していない。
- 「experience-following」を最初に分析した論文（Xiong ら）は原典を特定できていない。Obsessive Experience Poisoning の「精度 90% 超 → 約 40%」は【二次】で未検証 — [alphaXiv](https://www.alphaxiv.org/overview/2605.18930)

## Q4. 自動実験における探索制御と予算配分

### Takeaway
公開されている系の主流は「安い評価で広くふるい、有望なものだけ高い検証に昇格」（多段忠実度）と、木探索＋デバッグ深さ上限。配分則として明示されているのは DeepScientist の UCB と、固定時間予算で比較可能性を確保する autoresearch。探索戦略は演算子（draft / debug / improve）との組み合わせで効き方が変わる、というのが比較研究の結論。

### Cited Findings
- DeepScientist: 発見を Bayesian Optimization として定式化。LLM レビュアーの 3 点評価を UCB に入れて「活用（utility・quality）と探索（exploration value）」を釣り合わせ、選ばれた 1 件だけ実実験に進める。5,000 → 1,100 → 21 の漏斗 — [arXiv HTML](https://arxiv.org/html/2509.26603v1)【一次】
- 「its inherent success rate for innovation remains exceptionally low, making effective validation and filtering the new bottleneck」 — [arXiv HTML](https://arxiv.org/html/2509.26603v1)【一次】
- AI Scientist-v2: 段階ごとの停止条件、buggy ノード優先のデバッグ、non-buggy 間は LLM が指標・学習の挙動・図の質で評価する best-first、段階末の複数回 replication で平均と標準偏差を出す — [arXiv HTML](https://arxiv.org/html/2504.08066v1)【一次】
- AIDE: 「diverse な初期案を一定数 → 最良を改良し続ける」「壊れた解へのデバッグ回数を制限する」という実用的ヒューリスティクス — [arXiv HTML](https://arxiv.org/html/2502.13138v1)【一次】
- AIRA（Meta、arXiv 2507.02554）: 研究エージェントを「探索方針 × 演算子集合」として定式化し、Greedy / MCTS / Evolutionary を比較。両者の組み合わせが決定的で、最良の組で MLE-bench lite のメダル率が 39.6% → 47.7% — [arXiv abs](https://arxiv.org/abs/2507.02554)【要旨】
- autoresearch: 全実験を同じ 5 分の壁時計予算にすることで、何を変えても直接比較できるようにする。一晩で約 100 実験 — [GitHub README](https://github.com/karpathy/autoresearch)【一次】
- ReasoningBank の MaTTS: 1 課題に計算を多く割いて多様な試行を作り、その対比から質の高い記憶を合成する（記憶とテスト時スケーリングの相乗） — [arXiv abs](https://arxiv.org/abs/2509.25140)【要旨】
- Anthropic の sprint contract は、実行前に「完了の定義と検証方法」を生成役と評価役で合意する点で、事前登録に最も近い公開パターン — [Anthropic](https://www.anthropic.com/engineering/harness-design-long-running-apps)【一次】
- Lambda の実例: Claude Code に実験トラッカーを与え、約 2 日半で 90 個のアイデアにまたがる 468 実験を、プリエンプティブルなキュー（並列 8 ジョブ上限）で実行。API 費用は約 $1,200 — [Lambda blog](https://lambda.ai/blog/what-happens-when-claude-code-gets-an-experiment-tracker)【二次】

### Inferences
- GPU 予算上限のある一晩ループには 3 段の漏斗が合う: (1) 案出しと LLM 採点（GPU 0）、(2) 固定の短時間予算での smoke 実験（全案同じ時間で比較可能に）、(3) 通過したものだけ複数シードの本実験。各段の通過基準と打ち切り基準を実行前に台帳へ書く（＝事前登録）と、sprint contract と同じ効果が得られる。
- UCB の探索項は「不確かさ」の代理として LLM の自己採点を使っており、較正されている保証はない。採点と実結果の対応を台帳で追えば、採点の較正自体を定期点検できる。
- デバッグ深さ上限（AIDE）と「実装エラー 60%」（DeepScientist）を合わせると、kill 基準は「実装失敗 N 回で保留（棄却ではない）」と「仮説否定で棄却」を分けるべき。

### Gaps
- successive halving / Hyperband を LLM 研究エージェントの案選別に明示的に使った公開例は見つからなかった（多段忠実度の考え方は DeepScientist・AI Scientist-v2 に含まれるが、名前を挙げた採用例は未確認）。
- 仮説の事前登録を自動研究ループに組み込んで効果を測った研究は未発見。上の sprint contract は類推。
- AIRA の各探索戦略の詳細な勝敗条件は abstract しか読んでおらず未確認。

## Q5. 無人ループの運用上の安全策

### Takeaway
一次情報で確認できた手段は、Claude Code 側の決定的な制御（費用上限フラグ、確認待ちを拒否に変える設定、hooks による停止/拒否、スケジュールタスクの失効と分離）まで。GPU のアイドル監視・異常検知停止・通知は実践者のブログ頼みで、共通の教訓は「クラッシュ検知だけでは足りず、進捗の停滞を検知する」「終了コードを信用しない」「上限は自前で数える」。

### Cited Findings

**公式の制御手段【一次】**
- `--max-budget-usd` で API 費用に上限。到達時は残りのバックグラウンド作業も止める。`total_cost_usd` は JSON 出力で取れるがクライアント側の推定値 — [Claude Code docs: headless](https://code.claude.com/docs/en/headless)
- `--permission-prompts none`: 誰も答えられない実行で、確認が必要な操作を待たずに拒否し、Claude に再試行しないよう伝える。拒否は結果の `permission_denials` に列挙される — [Claude Code docs: headless](https://code.claude.com/docs/en/headless)
- `claude -p` は成功で 0、実行失敗で非 0 を返す。SIGTERM で 143、実行中の Bash のプロセスツリーを終了させ SessionEnd hook を実行 — [Claude Code docs: headless](https://code.claude.com/docs/en/headless)
- `-p` はフォルダの信頼確認なしにプロジェクトの `.claude/settings.json` の hooks と `.mcp.json` のサーバを実行する（`--bare` なら読まない） — [Claude Code docs: headless](https://code.claude.com/docs/en/headless)
- hooks: PreToolUse で危険なコマンドを deny、Stop で停止の差し止めまたは `continue: false` による強制停止、Notification（`permission_prompt`・`idle_prompt`）で外部通知の起点、http 型でイベントを外部に POST — [Claude Code docs: hooks](https://code.claude.com/docs/en/hooks)
- `/loop` の定期タスクは作成 7 日後に自動失効（「This bounds how long a forgotten loop can run」）。自己ペースのループは再スケジュールも停止もせずに終わると約 20 分後に 1 回だけ予備の起床を入れ、それでも再スケジュールしなければ終了 — [Claude Code docs: scheduled tasks](https://code.claude.com/docs/en/scheduled-tasks)
- クラウドのスケジュールタスクは auto mode（分類器が操作を許可/拒否）で始まり、拒否が閾値まで重なると確認プロンプトを出して人の回答を待つ。push 先は既定で `claude/` 接頭辞ブランチに限られ、GitHub のブランチ保護で制御する — [Claude Code docs: routines](https://code.claude.com/docs/en/routines)

**Heartbeat と Schedule の区別（Paseo）【二次・paseo.sh は取得不可】**
- schedule の対象は 3 通り: 毎回新しいエージェント（日次ジョブや監視向け）、既存のエージェント（継続性）、スケジュールを作った自分自身（エージェント内からの heartbeat）。heartbeat は現在の会話を続け、schedule は独立した cron 型の仕事向き — [Paseo docs: schedules](https://paseo.sh/docs/schedules)、[Paseo docs: orchestration](https://paseo.sh/docs/orchestration)
- 第三の選択肢として loop スキル: worker を起動 → 検証 → 完了か上限到達まで繰り返す。各反復に worker / verifier の組が要るなら loop、各発火が独立した新しいエージェントと作業場所を作るべきなら schedule — [paseo-loop skill](https://claudeskills.info/skills/getpaseo/paseo/paseo-loop/)
- 同じ区別は Claude Code にもある: `/loop`（同じ会話を続ける＝heartbeat 相当）とクラウド/デスクトップのスケジュールタスク（毎回新規セッション） — [Claude Code docs: scheduled tasks](https://code.claude.com/docs/en/scheduled-tasks)【一次】

**実践者の報告【二次・ブログ。細部はバージョン依存】**
- スクリプトが失敗しても Claude がエラーを報告して終了コード 0 で終わる場合があり、単純な再起動ループでは失敗を見逃す。繰り返しクラッシュを診断する watchdog を追加した — [Medium](https://medium.com/@evekhm/running-claude-code-autonomously-overnight-what-breaks-and-how-to-fix-it-3bee3bd958b5)
- heartbeat 型の生存確認はクラッシュは拾うが、同じ失敗するテストを 50 回再試行するループは見逃すため、進捗確認にもとづく停滞警告を足した — [NightShift](https://godmodeai2025.github.io/NightShift/)
- ターン数・費用の上限は `claude -p` に効くもので対話セッションには効かず、費用は上限を超えうるので余裕を持たせる — [DEV Community](https://dev.to/gabrielanhaia/leaving-claude-code-running-overnight-8-settings-to-check-before-you-walk-away-2gfb)
- $6,000 の事例は、起きるたびに約 80 万トークンの会話履歴を作り直す設計が原因と報じられている — [MakeUseOf](https://www.makeuseof.com/someone-left-claude-code-running-overnight-and-it-cost-6000/)
- クラウド GPU 側のアイドル自動停止を長時間実行の前に設定しておく — [Saturn Cloud](https://saturncloud.io/blog/run-claude-code-on-a-cloud-gpu-in-10-minutes-no-root-workarounds-required/)

**AI サイエンティスト系の安全策【一次】**
- DeepScientist のコーディングエージェントはサンドボックス内で全権限を持って動く。全体は人間 3 名が出力検証と幻覚の除去のために監督 — [arXiv HTML](https://arxiv.org/html/2509.26603v1)

### Inferences
- 「毎回新規セッション」は Paseo の schedule 型で、文脈の汚れと暴走の持ち越しを防げる反面、毎回の読み込みコストが効く。開始時に読む量（台帳の要約＋索引）を固定の上限に収めることが費用対策として最重要（$6,000 事例の逆を行く）。一晩のなかで同じ実験の完了待ちをするだけなら heartbeat 型（`/loop` や Monitor）のほうが安い。
- 終了コードが信用できないという報告と公式の「成功 0 / 失敗 非 0」は食い違う。ラッパー側は終了コードではなく、台帳に規定の行が増えたか・GPU ジョブが実際に動いているかという**成果物**で各反復の成否を判定するのが安全。
- 見張るべき信号は 3 つに分けられる: 生存（プロセスが居る）、進捗（台帳が進む・同じ失敗の反復でない）、資源（GPU が確保されたまま利用率 0 でない・予算残）。停止条件は LLM の判断でなくスクリプト（hook かラッパー）で実装する。
- プロジェクトの `.claude/settings.json` の hooks は `-p` で無確認に実行されるので、ループが取り込む外部リポジトリ（vendor など）由来の設定が混ざらないよう作業ディレクトリを分ける。

### Gaps
- GPU のアイドル監視（確保中なのに利用率 0 が続いたら解放・通知）と、損失の発散など異常検知での自動停止を、研究用の Claude Code ループで実装して公開した信頼できる事例は見つからなかった。
- Paseo の heartbeat の制約（`--cron` 必須かどうか）は文書間で食い違いがあるという検索要約のみ。原典未確認。
- 「サブスクリプションではセッション単位の費用上限フラグがない」という主張はブログ由来で、現行版での真偽は未確認 — [runvouch blog](https://runvouch.com/blog/claude-code-cron-unexpected-api-bill-runaway-cost-overnight)
- 人への通知の具体的な設計（何を・いつ・どの経路で）を比較した資料は未発見。
