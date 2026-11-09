# スキル索引（自動生成）

`python3 scripts/build-index.py` が作る。手で直さない。
ここにあるスキルは、`research-lab` スキルの指示で **SKILL.md を Read して従う** ライブラリ。
グローバルに登録しているのは `skills/` の自前スキルと research-paper-writing だけ。
研究プロジェクトの中では、`rl new` が ARIS の主要スキルをプロジェクト用に登録する。

## research-lab（自前）（8）

- **gpu-cloud** — RunPod・Lambda の GPU を SkyPilot で立て、研究プロジェクトの予算の範囲で実験を回し、使い終わったら必ず消すためのスキル。費用の見積もり、G2 で承認した予算の確認、上限時間とアイドル時の自動削除、消し忘れの掃除（rl gpu reap）、ARIS の run-experiment（gpu: remote）との接続を扱う。トリガー例：「GPU で学習を回して」「RunPod で」「Lambda で」「費用を見積もって」「GPU が残っていないか確認して」「クラウドの GPU を片付けて」。  
  `skills/gpu-cloud/SKILL.md`
- **ml-lit-review** — ML・CV・NLP・ロボティクスの文献調査と引用の検証。arXiv・Semantic Scholar・OpenAlex で集め、関連研究の比較表（手法・課題・データ・指標・結果・コード）と空白の地図を作り、BibTeX の全エントリを scripts/verify_bib.py で実在確認する（捏造・誤記の検出）。トリガー例：「関連研究を調べて」「この分野のサーベイ」「新規性があるか確かめて」「related work を書く材料」「参考文献をチェックして」「bib が正しいか確認して」。  
  `skills/ml-lit-review/SKILL.md`
- **ml-rigor** — ML・CV・NLP・RL・ロボティクスの実験の厳密さを守るスキル。実験計画の事前登録（主指標・テストセット・seed 数・ベースラインの調整予算）、結果を良く見せる「分岐の庭」（seed 選び・チェックポイント選び・テストセットでの調整・ベンチマークの取捨・汚染）の検出、統計（seed 間の信頼区間、ペア比較、RL の IQM、実機の成功率の Wilson 区間と必要試行数）を scripts/rl_stats.py で機械的に計算する。トリガー例：「実験計画を立てて」「この結果は有意？」「seed は何個必要？」「ロボットの評価は何回やればいい？」「結果を盛っていないかチェックして」「主張を確定する前に監査して」。  
  `skills/ml-rigor/SKILL.md`
- **physical-ai-research** — フィジカル AI・ロボティクス研究（模倣学習・VLA・強化学習・sim2real・操作・移動）を進めるスキル。LeRobot と SO-ARM101、MuJoCo / ManiSkill / Isaac Lab / LIBERO などのシミュレータとベンチマーク、方策（ACT・Diffusion Policy・SmolVLA・π0/openpi・OpenVLA-OFT・GR00T）の選び方、データ収録、実機評価のプロトコル（試行数・判定基準・順番）、実機の安全ルール、CoRL・RSS・ICRA・IROS 向けの書き方を扱う。トリガー例：「ロボットの研究テーマを考えて」「SO-101 で実験したい」「VLA を微調整したい」「sim2real」「実機評価の設計」「成功率を何回測ればいい？」。  
  `skills/physical-ai-research/SKILL.md`
- **research-lab** — ML・CV・NLP・CS・AI・フィジカル AI・ロボティクスの研究を、テーマ選び→文献→実験計画→実験の実行→分析→論文→自己査読→投稿・rebuttal まで進めるときの入口と進行役。研究プロジェクトの台帳（research.yaml・claims.yaml・runs/）で状態を管理し、人の確認ポイント G1〜G4 以外は自律で進める。どの作業にどのスキル（自前・ARIS・Orchestra・Master-cai）を使うかもここで決める。トリガー例：「研究を始めたい」「このアイデアを論文にしたい」「研究プロジェクトを作って」「実験を回して」「夜の間に進めておいて」「次に何をやる？」「research-lab」。  
  `skills/research-lab/SKILL.md`
- **research-program** — 大きな研究テーマ（1〜3 個）を、論文・研究プロジェクトの単位にどう切り分けて、どの順に進めるかを整理するスキル。幹（長期の問い）と論文の並び、各論文が答える 1 つの主張、論文の間の依存関係、積み上がる資産（データ・部品・ツール・評価手順）、投稿先と時期、潰れたときの逃げ道を notes/program.md にまとめ、research-lab のプロジェクト（1 プロジェクト = 1 論文）に対応づける。複数の興味を掛け合わせて 1 つの研究にするときの切り方も扱う。トリガー例：「研究プログラムを作って」「何本の論文に分ける？」「論文の順番を決めたい」「このテーマをプロジェクトに切って」「研究の全体像を整理して」「先を越されたので計画を組み直したい」。  
  `skills/research-program/SKILL.md`
- **research-themes** — 興味のある分野を人と話しながら、研究テーマの候補（3〜5 個）に落とし込むスキル。研究の問いの前の段階を受け持つ。手法ではなく、ゴール・強み・制約・現場への近さから出発し、興味どうしの交点を探して、テーマごとに「問い・なぜ今・空白の仮説・積み上がるもの・リスク・競合の感触」のカードにまとめる。トリガー例：「研究テーマを一緒に考えたい」「興味はあるが問いがない」「この分野で何をやればいい？」「ゼロベースで研究を考え直したい」「研究プログラムの前の相談」。  
  `skills/research-themes/SKILL.md`
- **venue-review** — 投稿先の学会の査読基準で原稿を査読シミュレーションし、直すべき点を優先度つきで出すスキル。NeurIPS・ICLR・ICML（ML）、CVPR・ICCV・ECCV（CV）、ACL・EMNLP・NAACL（ARR、NLP）、CoRL・RSS・ICRA・IROS・RA-L（ロボティクス）、MLSys・OSDI など（システム）の必須チェックリストと評価項目を扱い、別モデル（Codex）の査読と組み合わせる。トリガー例：「この論文を NeurIPS 基準で査読して」「CoRL に出せる？」「reviewer 目線で弱点を出して」「投稿前チェック」「rebuttal の準備」。  
  `skills/venue-review/SKILL.md`

## Master-cai / Research-Paper-Writing-Skills（1）

- **research-paper-writing** — Improve academic paper writing quality for ML/CV/NLP-style papers with clear section structure, paragraph flow, and reviewer-facing presentation. Use when drafting or revising Abstract, Introduction, Related Work, Method, Experiments, or Conclusion; polishing figures/tables; checking claim-support alignment; or performing self-review before submission.  
  `vendor/research-paper-writing/SKILL.md`

## ARIS / Auto-claude-code-research-in-sleep（87）

- **ablation-planner** — Use when main results pass result-to-claim (claim_supported=yes or partial) and ablation studies are needed for paper submission.  
  `vendor/aris/skills/ablation-planner/SKILL.md`
- **alphaxiv** — Quick single-paper lookup via AlphaXiv LLM-optimized summaries with tiered source fallback. Use when user says "explain this paper", "summarize paper", pastes an arXiv/AlphaXiv URL, or provides a bare arXiv ID for quick understanding - not for broad literature search.  
  `vendor/aris/skills/alphaxiv/SKILL.md`
- **analyze-results** — Analyze ML experiment results, compute statistics, generate comparison tables and insights. Use when user says "analyze results", "compare", or needs to interpret experimental data.  
  `vendor/aris/skills/analyze-results/SKILL.md`
- **arxiv** — Search, download, and summarize academic papers from arXiv. Use when user says "search arxiv", "download paper", "fetch arxiv", "arxiv search", "get paper pdf", or wants to find and save papers from arXiv to the local paper library.  
  `vendor/aris/skills/arxiv/SKILL.md`
- **auto-paper-improvement-loop** — Autonomously improve a generated paper via GPT-6-Astra xhigh review → implement fixes → recompile, for 2 rounds. Use when user says \"改论文\", \"improve paper\", \"论文润色循环\", \"auto improve\", or wants to iteratively polish a generated paper.  
  `vendor/aris/skills/auto-paper-improvement-loop/SKILL.md`
- **auto-review-loop** — Autonomous multi-round research review loop. In Copilot CLI it defaults to the native complementary rubber-duck subagent with host-event model evidence; elsewhere it uses Codex, while explicit external reviewer overrides remain available. Implements fixes and re-reviews until a policy-approved positive assessment or max rounds is reached.  
  `vendor/aris/skills/auto-review-loop/SKILL.md`
- **auto-review-loop-llm** — Autonomous research review loop using any OpenAI-compatible LLM API. Configure via llm-chat MCP server or environment variables. Trigger with "auto review loop llm" or "llm review".  
  `vendor/aris/skills/auto-review-loop-llm/SKILL.md`
- **auto-review-loop-minimax** — Autonomous multi-round research review loop using MiniMax API. Use when you want to use MiniMax instead of Codex MCP for external review. Trigger with "auto review loop minimax" or "minimax review".  
  `vendor/aris/skills/auto-review-loop-minimax/SKILL.md`
- **citation-audit** — Zero-context verification that every bibliographic entry in the paper is real, correctly attributed, and used in a context the cited paper actually supports — catching hallucinated authors, wrong years, fabricated venues, version mismatches, and wrong-context citations. Use when user says \"审查引用\", \"check citations\", \"citation audit\", \"verify references\", \"引用核对\", or before submission to en  
  `vendor/aris/skills/citation-audit/SKILL.md`
- **citation-crosscheck** — Double-blind bibliographic cross-check: one agent extracts each cited entry verbatim from the local .bib, a second independently re-fetches the same paper's record from the web while blind to the .bib, and a third extractor emits a mechanical field-by-field delta to catch dropped/re-ordered authors, wrong years, wrong venues, and bad DOIs/arXiv ids. The main agent (never a shard) assigns the MATCH  
  `vendor/aris/skills/citation-crosscheck/SKILL.md`
- **claims-drafting** — Draft patent claims for an invention. Use when user says \"撰写权利要求\", \"draft claims\", \"写权利要求书\", \"claim drafting\", or wants to create patent claims. The core skill of the patent pipeline.  
  `vendor/aris/skills/claims-drafting/SKILL.md`
- **comm-lit-review** — Communications-domain literature review with Claude-style knowledge-base-first retrieval. Use when the task is about communications, wireless, networking, satellite/NTN, Wi-Fi, cellular, transport protocols, congestion control, routing, scheduling, MAC/PHY, rate adaptation, channel estimation, beamforming, or communication-system research and the user wants papers, related work, a survey, or a lan  
  `vendor/aris/skills/comm-lit-review/SKILL.md`
- **deepxiv** — Search and progressively read open-access academic papers through DeepXiv. Use when the user wants layered paper access, section-level reading, trending papers, or DeepXiv-backed literature retrieval.  
  `vendor/aris/skills/deepxiv/SKILL.md`
- **dse-loop** — Autonomous design space exploration loop for computer architecture and EDA. Runs a program, analyzes results, tunes parameters, and iterates until objective is met or timeout. Use when user says \"DSE\", \"design space exploration\", \"sweep parameters\", \"optimize\", \"find best config\", or wants iterative parameter tuning.  
  `vendor/aris/skills/dse-loop/SKILL.md`
- **embodiment-description** — Write detailed embodiment descriptions for patent specifications. Use when user says \"撰写实施例\", \"write embodiment\", \"实施例描述\", \"detailed description\", or wants to describe how to practice an invention.  
  `vendor/aris/skills/embodiment-description/SKILL.md`
- **exa-search** — AI-powered web search via Exa with content extraction. Use when user says "exa search", "web search with content", "find similar pages", or needs broad web results beyond academic databases (arXiv, Semantic Scholar).  
  `vendor/aris/skills/exa-search/SKILL.md`
- **experiment-audit** — Audit experiment integrity before claiming results. Uses cross-model review (external reviewer backend) to check for fake ground truth, score normalization fraud, phantom results, and insufficient scope. Use when user says \"审计实验\", \"check experiment integrity\", \"audit results\", \"实验诚实度\", or after experiments complete before writing claims.  
  `vendor/aris/skills/experiment-audit/SKILL.md`
- **experiment-bridge** — Workflow 1.5: Bridge between idea discovery and auto review. Reads EXPERIMENT_PLAN.md, implements experiment code, deploys to GPU, collects initial results. Use when user says \"实现实验\", \"implement experiments\", \"bridge\", \"从计划到跑实验\", \"deploy the plan\", or has an experiment plan ready to execute.  
  `vendor/aris/skills/experiment-bridge/SKILL.md`
- **experiment-plan** — Turn a refined research proposal or method idea into a detailed, claim-driven experiment roadmap. Use after `research-refine`, or when the user asks for a detailed experiment plan, ablation matrix, evaluation protocol, run order, compute budget, or paper-ready validation that supports the core problem, novelty, simplicity, and any LLM / VLM / Diffusion / RL-based contribution.  
  `vendor/aris/skills/experiment-plan/SKILL.md`
- **experiment-queue** — SSH job queue for multi-seed/multi-config ML experiments with OOM-aware retry, stale-screen cleanup, and wave-transition race prevention. Use when user says "batch experiments", "队列实验", "run grid", "multi-seed sweep", "auto-chain experiments", or when /run-experiment is insufficient for 10+ jobs that need orchestration.  
  `vendor/aris/skills/experiment-queue/SKILL.md`
- **feishu-notify** — Send notifications to Feishu/Lark. Internal utility used by other skills, or manually via /feishu-notify. Use when user says \"发飞书\", \"notify feishu\", or other skills need to send status updates.  
  `vendor/aris/skills/feishu-notify/SKILL.md`
- **figure-description** — Process user-provided patent figures and generate formal drawing descriptions. Use when user says \"附图处理\", \"figure description\", \"附图说明\", \"drawings description\", or wants to describe patent figures with reference numerals.  
  `vendor/aris/skills/figure-description/SKILL.md`
- **figure-spec** — Generate deterministic publication-quality architecture, workflow, and pipeline diagrams from structured JSON (FigureSpec) into editable SVG. Use when user says \"架构图\", \"workflow 图\", \"pipeline 图\", \"确定性矢量图\", \"figure spec\", \"draw architecture\", or needs precise, editable, publication-ready vector diagrams. Preferred over AI illustration for formal architecture/workflow figures.  
  `vendor/aris/skills/figure-spec/SKILL.md`
- **firecrawl-search** — Web search and page scraping via Firecrawl, returning full-page markdown. Use when user says "firecrawl search", "firecrawl scrape" or "/firecrawl-search".  
  `vendor/aris/skills/firecrawl-search/SKILL.md`
- **formula-derivation** — Structures and derives research formulas when the user wants to 推导公式, build a theory line, organize assumptions, turn scattered equations into a coherent derivation, or rewrite theory notes into a paper-ready formula document. Use when the derivation target is not yet fully fixed, the main object still needs to be chosen, or the user needs a coherent derivation package rather than a finished theor  
  `vendor/aris/skills/formula-derivation/SKILL.md`
- **gemini-search** — Search research papers via Gemini for broad literature discovery. Use when user says "gemini search", "gemini papers", "search with gemini", or wants AI-powered literature discovery beyond arXiv/Semantic Scholar indexes.  
  `vendor/aris/skills/gemini-search/SKILL.md`
- **grant-proposal** — Draft a structured grant proposal from research ideas and literature. Supports KAKENHI (Japan), NSF (US), NSFC (China, including 面上/青年/优青/杰青/海外优青/重点), ERC (EU), DFG (Germany), SNSF (Switzerland), ARC (Australia), NWO (Netherlands), and generic formats. Use when user says \"write grant\", \"grant proposal\", \"申請書\", \"write KAKENHI\", \"科研費\", \"基金申请\", \"写基金\", \"NSF proposal\", or wants to turn   
  `vendor/aris/skills/grant-proposal/SKILL.md`
- **idea-creator** — Generate and rank research ideas given a broad direction. Use when user says "找idea", "brainstorm ideas", "generate research ideas", "what can we work on", or wants to explore a research area for publishable directions.  
  `vendor/aris/skills/idea-creator/SKILL.md`
- **idea-discovery** — Workflow 1: Full idea discovery pipeline to go from a broad research direction to validated, pilot-tested ideas. Use when user says \"找idea全流程\", \"idea discovery pipeline\", \"从零开始找方向\", or wants the complete idea exploration workflow.  
  `vendor/aris/skills/idea-discovery/SKILL.md`
- **idea-discovery-robot** — Workflow 1 adaptation for robotics and embodied AI. Orchestrates robotics-aware literature survey, idea generation, novelty check, and critical review to go from a broad robotics direction to benchmark-grounded, simulation-first ideas. Use when user says \"robotics idea discovery\", \"机器人找idea\", \"embodied AI idea\", \"机器人方向探索\", \"sim2real 选题\", or wants ideas for manipulation, locomotion, navig  
  `vendor/aris/skills/idea-discovery-robot/SKILL.md`
- **integrity-forensics** — Run the Anti-Autoresearch integrity-forensics sweep (span-anchored evidence ledger → GPT auditors propose findings → a rules-only reporter that lists every proposal with what the auditor said about it) against a paper via a SHA-pinned thin launcher — then convert the verdict into a typed policy gate (BLOCK/WARN/NO_NEW_BLOCKER) and an append-only obligations ledger. Use when user says \"integrity f  
  `vendor/aris/skills/integrity-forensics/SKILL.md`
- **interview-cheatsheet** — Generate a long-form Chinese interview-prep cheat sheet on a specific ML/LLM topic — formulas with derivations, from-scratch PyTorch code, comparison tables, and 25 高频面试题 (L1 必会 / L2 进阶 / L3 顶级 lab). Use when the user says '写面试 cheat sheet', '写一份 X 教程', '帮我准备 Y 面试题', '出一份 X 速查', or wants a 600-1000 line Chinese tutorial on a specific ML topic.  
  `vendor/aris/skills/interview-cheatsheet/SKILL.md`
- **invention-structuring** — Structure a raw invention idea into a formal invention disclosure. Use when user says \"构建发明\", \"structure invention\", \"发明构建\", \"invention disclosure\", or wants to formalize a rough idea into a patent-ready structure.  
  `vendor/aris/skills/invention-structuring/SKILL.md`
- **jurisdiction-format** — Compile patent application into jurisdiction-specific filing format. Use when user says \"格式转换\", \"jurisdiction format\", \"国家格式\", \"compile patent\", or wants formatted patent documents for CN/US/EP filing.  
  `vendor/aris/skills/jurisdiction-format/SKILL.md`
- **keenable-search** — Keyless web search and page fetch via Keenable. Use when user says "keenable search", "web search without an API key", "fetch this page as markdown", or needs broad web results beyond academic databases (arXiv, Semantic Scholar) with no search API key set up.  
  `vendor/aris/skills/keenable-search/SKILL.md`
- **kill-argument** — Two-thread adversarial review: a fresh reviewer constructs the strongest 200-word rejection memo, then a second fresh reviewer defends the paper point-by-point and surfaces still-unresolved critical issues. Use when user says \"kill argument\", \"adversarial review\", \"hostile review\", \"rebuttal preparation\", \"reviewer-2 simulation\", or before submitting a theory paper that has already passe  
  `vendor/aris/skills/kill-argument/SKILL.md`
- **lean-formalize** — Develop and verify a mathematical proof in Lean, continue an incomplete Lean project, or audit whether it proves the original statement. Connect actual inputs to intermediate lemmas, assemble the target theorem, check its transitive axioms, and provide a reproducible handoff. Use when Lean is requested or a specific proof obligation benefits from formal verification; use proof-writer for ordinary   
  `vendor/aris/skills/lean-formalize/SKILL.md`
- **mermaid-diagram** — Generate Mermaid diagrams from user requirements. Supports flowcharts, sequence diagrams, class diagrams, ER diagrams, Gantt charts, and 18 more diagram types.  
  `vendor/aris/skills/mermaid-diagram/SKILL.md`
- **meta-apply** — Privileged applier that LANDS meta-optimize / corpus-audit patches the user approved — the ONLY skill permitted to mutate the skill corpus from a self-modification proposal, with cross-model jury and human approval at landing. Use when the user says \"meta apply\", \"/meta-apply\", \"land the staged patches\", \"应用优化\", after a /meta-optimize run.  
  `vendor/aris/skills/meta-apply/SKILL.md`
- **meta-optimize** — Analyze ARIS usage logs and propose optimizations to SKILL.md files, reviewer prompts, and workflow defaults. Outer-loop harness optimization inspired by Meta-Harness (Lee et al., 2026). Use when user says \"优化技能\", \"meta optimize\", \"improve skills\", \"分析使用记录\", or wants to optimize ARIS's own harness components based on accumulated experience.  
  `vendor/aris/skills/meta-optimize/SKILL.md`
- **monitor-experiment** — Monitor running experiments, check progress, collect results. Use when user says "check results", "is it done", "monitor", or wants experiment output.  
  `vendor/aris/skills/monitor-experiment/SKILL.md`
- **novelty-check** — Verify research idea novelty against recent literature. Use when user says "查新", "novelty check", "有没有人做过", "check novelty", or wants to verify a research idea is novel before implementing.  
  `vendor/aris/skills/novelty-check/SKILL.md`
- **openalex** — Search academic papers via OpenAlex API for open citation data, institutional affiliations, and funding information. Use when user says "openalex search", "search openalex", "open citation graph", or wants comprehensive academic metadata beyond arXiv/Semantic Scholar.  
  `vendor/aris/skills/openalex/SKILL.md`
- **overleaf-sync** — Two-way sync between a local paper directory and an Overleaf project, so ARIS audit/edit workflows stay on the local copy while collaborators edit in the Overleaf web UI. Use when user says \"同步 overleaf\", \"overleaf sync\", \"推送到 overleaf\", \"connect overleaf\", \"Overleaf 桥接\", \"pull overleaf\", \"push overleaf\", or wants to bridge their ARIS paper directory with an Overleaf project.  
  `vendor/aris/skills/overleaf-sync/SKILL.md`
- **paper-claim-audit** — Zero-context verification that every number, comparison, and scope claim in the paper matches raw result files. Uses a fresh cross-model reviewer with NO prior context to prevent confirmation bias. Use when user says \"审查论文数据\", \"check paper claims\", \"verify numbers\", \"论文数字核对\", or before submission to ensure paper-to-evidence fidelity.  
  `vendor/aris/skills/paper-claim-audit/SKILL.md`
- **paper-compile** — Compile LaTeX paper to PDF, fix errors, and verify output. Use when user says \"编译论文\", \"compile paper\", \"build PDF\", \"生成PDF\", or wants to compile LaTeX into a submission-ready PDF.  
  `vendor/aris/skills/paper-compile/SKILL.md`
- **paper-figure** — Generate publication-quality figures and tables from experiment results. Use when user says \"画图\", \"作图\", \"generate figures\", \"paper figures\", or needs plots for a paper.  
  `vendor/aris/skills/paper-figure/SKILL.md`
- **paper-illustration** — Generate publication-quality AI illustrations for academic papers using Gemini image generation. Creates architecture diagrams, method illustrations with Claude-supervised iterative refinement loop. Use when user says \"生成图表\", \"画架构图\", \"AI绘图\", \"paper illustration\", \"generate diagram\", or needs visual figures for papers.  
  `vendor/aris/skills/paper-illustration/SKILL.md`
- **paper-illustration-image2** — Generate publication-quality academic illustrations through a local Codex app-server bridge that uses Codex native image generation. This is a separate experimental alternative to `paper-illustration`, intended for Claude Code users who want a GPT-image-style renderer without modifying the original skill.  
  `vendor/aris/skills/paper-illustration-image2/SKILL.md`
- **paper-plan** — Generate a structured paper outline from review conclusions and experiment results. Use when user says \"写大纲\", \"paper outline\", \"plan the paper\", \"论文规划\", or wants to create a paper plan before writing.  
  `vendor/aris/skills/paper-plan/SKILL.md`
- **paper-poster** — DEPRECATED — superseded by /paper-poster-html. Kept only as a redirect for muscle memory; do not use for new posters.  
  `vendor/aris/skills/paper-poster/SKILL.md`
- **paper-poster-html** — DEFAULT poster pipeline — build an academic conference poster (ICML/NeurIPS/ICLR/CVPR/...) as a single HTML/CSS file with measurement-driven hard gates, real paper figures, a two-hue design-token system, and print-ready PDF via headless Chromium. Use when the user says \"做海报\", \"poster\", \"conference poster\", \"paper poster\", or asks to design/redo a research poster. Supersedes the retired LaT  
  `vendor/aris/skills/paper-poster-html/SKILL.md`
- **paper-slides** — Generate conference presentation slides (beamer LaTeX → PDF + editable PPTX) from a compiled paper, with speaker notes and full talk script. Use when user says \"做PPT\", \"做幻灯片\", \"make slides\", \"conference talk\", \"presentation slides\", \"生成slides\", \"写演讲稿\", or wants beamer slides for a conference talk.  
  `vendor/aris/skills/paper-slides/SKILL.md`
- **paper-talk** — End-to-end conference talk pipeline: paper → slide outline → Beamer + PPTX → per-page polish → assurance checks (claim / citation / anonymity) → final export and report. Default-good for academic conference talks (NeurIPS / ICML / ICLR / VALSE / 投稿 talks). Trigger phrases: \"做 talk\", \"做 PPT 全流程\", \"talk pipeline\", \"end-to-end slides\", \"做演讲\", \"conference talk full workflow\". Use when the   
  `vendor/aris/skills/paper-talk/SKILL.md`
- **paper-write** — Draft LaTeX paper section by section from an outline. Use when user says \"写论文\", \"write paper\", \"draft LaTeX\", \"开始写\", or wants to generate LaTeX content from a paper plan.  
  `vendor/aris/skills/paper-write/SKILL.md`
- **paper-writing** — Workflow 3: Full paper writing pipeline that goes from a narrative report to a polished, submission-ready PDF. Use when user says \"写论文全流程\", \"write paper pipeline\", \"从报告到PDF\", \"paper writing\", or wants the complete paper generation workflow.  
  `vendor/aris/skills/paper-writing/SKILL.md`
- **patent-novelty-check** — Assess patent novelty and non-obviousness against prior art. Use when user says \"专利查新\", \"patent novelty\", \"可专利性评估\", \"patentability check\", or wants to evaluate if an invention is patentable.  
  `vendor/aris/skills/patent-novelty-check/SKILL.md`
- **patent-pipeline** — Full patent drafting pipeline from invention description to jurisdiction-formatted filing documents. Supports CN (CNIPA), US (USPTO), EP (EPO). Supports invention patents and utility models. Use when user says \"写专利\", \"patent pipeline\", \"专利申请\", \"draft patent\", \"写权利要求书\", or wants to draft a complete patent application.  
  `vendor/aris/skills/patent-pipeline/SKILL.md`
- **patent-review** — Get an external patent examiner review of a patent application. Use when user says \"专利审查\", \"patent review\", \"审查意见\", \"examiner review\", or wants critical feedback on patent claims and specification.  
  `vendor/aris/skills/patent-review/SKILL.md`
- **pixel-art** — Generate pixel art SVG illustrations for READMEs, docs, or slides. Use when user says "画像素图", "pixel art", "make an SVG illustration", "README hero image", or wants a cute visual.  
  `vendor/aris/skills/pixel-art/SKILL.md`
- **prior-art-search** — Search patent databases and academic literature for prior art relevant to an invention. Use when user says \"现有技术检索\", \"prior art search\", \"专利检索\", \"check patents\", or wants to find relevant prior art.  
  `vendor/aris/skills/prior-art-search/SKILL.md`
- **proof-checker** — Rigorous mathematical proof verification and fixing workflow. Reads a LaTeX proof, identifies gaps via cross-model review (external reviewer backend, ultra reasoning), fixes each gap with full derivations, re-reviews, and generates an audit report. Use when user says "检查证明", "verify proof", "proof check", "审证明", "check this proof", or wants rigorous mathematical verification of a theory paper.  
  `vendor/aris/skills/proof-checker/SKILL.md`
- **proof-orchestrator** — Manage a stateful, run-directory-based proof project: continuation across runs, run-local source bookkeeping, manual GPT Pro handoff packages when a local attempt stalls, and an optional DeepSeek second opinion as additional evidence only. Use when the user asks for proof-run orchestration, a GPT Pro handoff, or cross-run proof continuation — use /proof-writer for ordinary proof drafting and /proo  
  `vendor/aris/skills/proof-orchestrator/SKILL.md`
- **proof-writer** — Writes rigorous mathematical proofs for ML/AI theory. Use when asked to prove a theorem, lemma, proposition, or corollary, fill in missing proof steps, formalize a proof sketch, 补全证明, 写证明, 证明某个命题, or determine whether a claimed proof can actually be completed under the stated assumptions.  
  `vendor/aris/skills/proof-writer/SKILL.md`
- **qzcli** — Manage GPU compute jobs on the Qizhi (启智) platform using qzcli — a kubectl-style CLI tool. Use when user says "qzcli", "启智平台", "submit job", "stop job", "查计算组", "avail", "list jobs", "batch submit", or needs to manage distributed training jobs on a Qizhi instance.  
  `vendor/aris/skills/qzcli/SKILL.md`
- **rebuttal** — Workflow 4: Submission rebuttal pipeline. Parses external reviews, enforces coverage and grounding, drafts a safe text-only rebuttal under venue limits, and manages follow-up rounds. Use when user says \"rebuttal\", \"reply to reviewers\", \"ICML rebuttal\", \"OpenReview response\", or wants to answer external reviews safely.  
  `vendor/aris/skills/rebuttal/SKILL.md`
- **render-html** — Render an ARIS Markdown / JSON artifact (IDEA_REPORT, AUTO_REVIEW, KILL_ARGUMENT, PAPER_PLAN, research-wiki state, etc.) into a single-file HTML view designed for human reading. Use when the user says \"渲染 HTML\", \"出一份 HTML 报告\", \"render html\", \"make this readable\", \"export to html\", or wants a polished web-rendered view of a Markdown artifact.  
  `vendor/aris/skills/render-html/SKILL.md`
- **research-implement-feature** — Build a working artifact from a plain \"implement X for me\" request: a running end-to-end spine first, then one feature per rung, with every under-determined decision written to an assumption ledger BEFORE the code that depends on it and a cross-model sweep for the ones that slipped through undeclared. Use when user says \"给我实现\", \"implement X\", \"帮我做一个能跑的\", \"先搭个原型再加功能\", \"build this feature  
  `vendor/aris/skills/research-implement-feature/SKILL.md`
- **research-lit** — Search and analyze research papers, find related work, summarize key ideas. Use when user says "find papers", "related work", "literature review", "what does this paper say", or needs to understand academic papers.  
  `vendor/aris/skills/research-lit/SKILL.md`
- **research-pipeline** — Full end-to-end research pipeline: from a broad research direction through idea discovery, experiments, and review all the way to a polished paper PDF. Use when user says \"全流程\", \"full pipeline\", \"从找idea到投稿\", \"end-to-end research\", or wants the complete autonomous research lifecycle.  
  `vendor/aris/skills/research-pipeline/SKILL.md`
- **research-refine** — Turn a vague research direction into a problem-anchored, elegant, frontier-aware, implementation-oriented method plan via iterative GPT-6-Astra review. Use when the user says "refine my approach", "帮我细化方案", "decompose this problem", "打磨idea", "refine research plan", "细化研究方案", or wants a concrete research method that stays simple, focused, and top-venue ready instead of a vague or overbuilt idea.  
  `vendor/aris/skills/research-refine/SKILL.md`
- **research-refine-pipeline** — Run an end-to-end workflow that chains `research-refine` and `experiment-plan`. Use when the user wants a one-shot pipeline from vague research direction to focused final proposal plus detailed experiment roadmap, or asks to "串起来", build a pipeline, do it end-to-end, or generate both the method and experiment plan together.  
  `vendor/aris/skills/research-refine-pipeline/SKILL.md`
- **research-review** — Get a deep critical review of research from a selected reviewer (Codex by default, Gemini, Grok, Claude Code, or manual). Use when user says "review my research", "help me review", "get external review", or wants critical feedback on research ideas, papers, or experimental results.  
  `vendor/aris/skills/research-review/SKILL.md`
- **research-wiki** — Persistent research knowledge base that accumulates papers, ideas, experiments, claims, and their relationships across the entire research lifecycle. Inspired by Karpathy's LLM Wiki pattern. Use when user says \"知识库\", \"research wiki\", \"add paper\", \"wiki query\", \"查知识库\", or wants to build/query a persistent field map.  
  `vendor/aris/skills/research-wiki/SKILL.md`
- **resubmit-pipeline** — Workflow 5: orchestrate a text-only resubmit of a polished paper to a different venue under hard constraints (no new experiments, no bib edits, no framework changes, never overwrite prior submissions). Use when user says \"resubmit pipeline\", \"重投流程\", \"port paper to <new venue>\", \"resubmit to <venue>\", \"tighten paper for resubmission\", or has a rejected/withdrawn paper to move to a differe  
  `vendor/aris/skills/resubmit-pipeline/SKILL.md`
- **result-to-claim** — Use when experiments complete to judge what claims the results support, what they don't, and what evidence is still missing. Codex MCP evaluates results against intended claims and routes to next action (pivot, supplement, or confirm). Use after experiments finish — before writing the paper or running ablations.  
  `vendor/aris/skills/result-to-claim/SKILL.md`
- **run-experiment** — Deploy and run ML experiments on local, remote, Vast.ai, or Modal serverless GPU. Use when user says "run experiment", "deploy to server", "跑实验", or needs to launch training jobs.  
  `vendor/aris/skills/run-experiment/SKILL.md`
- **semantic-scholar** — Search published venue papers (IEEE, ACM, Springer, etc.) via Semantic Scholar API. Complements /arxiv (preprints) with citation counts, venue metadata, and TLDR. Use when user says "search semantic scholar", "find IEEE papers", "find journal papers", "venue papers", "citation search", or wants published literature beyond arXiv preprints.  
  `vendor/aris/skills/semantic-scholar/SKILL.md`
- **serverless-modal** — Run GPU workloads on Modal — training, fine-tuning, inference, batch processing. Zero-config serverless: no SSH, no Docker, auto scale-to-zero. Use when user says \"modal run\", \"modal training\", \"modal inference\", \"deploy to modal\", \"need a GPU\", \"run on modal\", \"serverless GPU\", or needs remote GPU compute.  
  `vendor/aris/skills/serverless-modal/SKILL.md`
- **slides-polish** — Per-page Codex review + targeted python-pptx / Beamer fixes for academic talk slides. Use AFTER /paper-slides (or any externally generated PPTX/Beamer) when the deck looks 'mostly OK' but the user wants a final pass that aligns visual weight with a reference, bumps PPTX fonts to projector-readable size, kills italic style leaks, fixes text-frame overflow, and catches per-slide layout drift. Trigge  
  `vendor/aris/skills/slides-polish/SKILL.md`
- **specification-writing** — Write the full patent specification from claims and invention disclosure. Use when user says \"撰写说明书\", \"write specification\", \"写说明书\", \"patent description\", or wants to draft the complete patent specification.  
  `vendor/aris/skills/specification-writing/SKILL.md`
- **system-profile** — Profile a target (script, process, GPU, memory, interconnect) for performance analysis. Use when user says \"profile\", \"benchmark\", \"bottleneck\", or wants performance analysis.  
  `vendor/aris/skills/system-profile/SKILL.md`
- **training-check** — Periodically check WandB metrics during training to catch problems early (NaN, loss divergence, idle GPUs). Avoids wasting GPU hours on broken runs. Use when training is running and you want automated health checks.  
  `vendor/aris/skills/training-check/SKILL.md`
- **vast-gpu** — Rent, manage, and destroy GPU instances on vast.ai. Use when user says \"rent gpu\", \"vast.ai\", \"rent a server\", \"cloud gpu\", or needs on-demand GPU without owning hardware.  
  `vendor/aris/skills/vast-gpu/SKILL.md`
- **web-debug-search** — Search GitHub, Stack Exchange, Chinese technical communities, official documentation, and general developer web sources for software errors, compatibility problems, API usage questions, and real-world workarounds. Use for debugging and discovery only; results are not paper-citation evidence.  
  `vendor/aris/skills/web-debug-search/SKILL.md`
- **wiki-enrich** — Fill in the per-paper TODO sections of research-wiki/papers/<slug>.md pages that literature-ingest skills leave as bare scaffolds. Use when user says 'enrich wiki', 'fill paper TODOs', 'wiki body 補完', '把 paper 摘要寫進 wiki', 'research-wiki 自動填', or after a batch ingest that left papers/ as TODO scaffolds.  
  `vendor/aris/skills/wiki-enrich/SKILL.md`
- **writing-systems-papers** — Paragraph-level structural blueprint for 10-12 page systems papers targeting OSDI, SOSP, ASPLOS, NSDI, and EuroSys. Provides page allocation, paragraph templates, and writing patterns. Use when user says \"写系统论文\", \"systems paper structure\", \"OSDI paper\", \"SOSP paper\", or wants fine-grained structural guidance for a systems conference submission.  
  `vendor/aris/skills/writing-systems-papers/SKILL.md`

## Orchestra / AI-Research-SKILLs（82）

### 

- **autoresearch** — Orchestrates end-to-end autonomous AI research projects using a two-loop architecture. The inner loop runs rapid experiment iterations with clear optimization targets. The outer loop synthesizes results, identifies patterns, and steers research direction. Routes to domain-specific skills for execution, supports continuous agent operation via Claude Code /loop and OpenClaw heartbeat, and produces r  
  `vendor/orchestra/0-autoresearch-skill/SKILL.md`

### 01-model-architecture

- **implementing-llms-litgpt** — Implements and trains LLMs using Lightning AI's LitGPT with 20+ pretrained architectures (Llama, Gemma, Phi, Qwen, Mistral). Use when need clean model implementations, educational understanding of architectures, or production fine-tuning with LoRA/QLoRA. Single-file implementations, no abstraction layers.  
  `vendor/orchestra/01-model-architecture/litgpt/SKILL.md`
- **mamba-architecture** — State-space model with O(n) complexity vs Transformers' O(n²). 5× faster inference, million-token sequences, no KV cache. Selective SSM with hardware-aware design. Mamba-1 (d_state=16) and Mamba-2 (d_state=128, multi-head). Models 130M-2.8B on HuggingFace.  
  `vendor/orchestra/01-model-architecture/mamba/SKILL.md`
- **nanogpt** — Educational GPT implementation in ~300 lines. Reproduces GPT-2 (124M) on OpenWebText. Clean, hackable code for learning transformers. By Andrej Karpathy. Perfect for understanding GPT architecture from scratch. Train on Shakespeare (CPU) or OpenWebText (multi-GPU).  
  `vendor/orchestra/01-model-architecture/nanogpt/SKILL.md`
- **rwkv-architecture** — RNN+Transformer hybrid with O(n) inference. Linear time, infinite context, no KV cache. Train like GPT (parallel), infer like RNN (sequential). Linux Foundation AI project. Production at Windows, Office, NeMo. RWKV-7 (March 2025). Models up to 14B parameters.  
  `vendor/orchestra/01-model-architecture/rwkv/SKILL.md`
- **distributed-llm-pretraining-torchtitan** — Provides PyTorch-native distributed LLM pretraining using torchtitan with 4D parallelism (FSDP2, TP, PP, CP). Use when pretraining Llama 3.1, DeepSeek V3, or custom models at scale from 8 to 512+ GPUs with Float8, torch.compile, and distributed checkpointing.  
  `vendor/orchestra/01-model-architecture/torchtitan/SKILL.md`

### 02-tokenization

- **huggingface-tokenizers** — Fast tokenizers optimized for research and production. Rust-based implementation tokenizes 1GB in <20 seconds. Supports BPE, WordPiece, and Unigram algorithms. Train custom vocabularies, track alignments, handle padding/truncation. Integrates seamlessly with transformers. Use when you need high-performance tokenization or custom tokenizer training.  
  `vendor/orchestra/02-tokenization/huggingface-tokenizers/SKILL.md`
- **sentencepiece** — Language-independent tokenizer treating text as raw Unicode. Supports BPE and Unigram algorithms. Fast (50k sentences/sec), lightweight (6MB memory), deterministic vocabulary. Used by T5, ALBERT, XLNet, mBART. Train on raw text without pre-tokenization. Use when you need multilingual support, CJK languages, or reproducible tokenization.  
  `vendor/orchestra/02-tokenization/sentencepiece/SKILL.md`

### 03-fine-tuning

- **axolotl** — Expert guidance for fine-tuning LLMs with Axolotl - YAML configs, 100+ models, LoRA/QLoRA, DPO/KTO/ORPO/GRPO, multimodal support  
  `vendor/orchestra/03-fine-tuning/axolotl/SKILL.md`
- **llama-factory** — Expert guidance for fine-tuning LLMs with LLaMA-Factory - WebUI no-code, 100+ models, 2/3/4/5/6/8-bit QLoRA, multimodal support  
  `vendor/orchestra/03-fine-tuning/llama-factory/SKILL.md`
- **peft-fine-tuning** — Parameter-efficient fine-tuning for LLMs using LoRA, QLoRA, and 25+ methods. Use when fine-tuning large models (7B-70B) with limited GPU memory, when you need to train <1% of parameters with minimal accuracy loss, or for multi-adapter serving. HuggingFace's official library integrated with transformers ecosystem.  
  `vendor/orchestra/03-fine-tuning/peft/SKILL.md`
- **unsloth** — Expert guidance for fast fine-tuning with Unsloth - 2-5x faster training, 50-80% less memory, LoRA/QLoRA optimization  
  `vendor/orchestra/03-fine-tuning/unsloth/SKILL.md`

### 04-mechanistic-interpretability

- **nnsight-remote-interpretability** — Provides guidance for interpreting and manipulating neural network internals using nnsight with optional NDIF remote execution. Use when needing to run interpretability experiments on massive models (70B+) without local GPU resources, or when working with any PyTorch architecture.  
  `vendor/orchestra/04-mechanistic-interpretability/nnsight/SKILL.md`
- **pyvene-interventions** — Provides guidance for performing causal interventions on PyTorch models using pyvene's declarative intervention framework. Use when conducting causal tracing, activation patching, interchange intervention training, or testing causal hypotheses about model behavior.  
  `vendor/orchestra/04-mechanistic-interpretability/pyvene/SKILL.md`
- **sparse-autoencoder-training** — Provides guidance for training and analyzing Sparse Autoencoders (SAEs) using SAELens to decompose neural network activations into interpretable features. Use when discovering interpretable features, analyzing superposition, or studying monosemantic representations in language models.  
  `vendor/orchestra/04-mechanistic-interpretability/saelens/SKILL.md`
- **transformer-lens-interpretability** — Provides guidance for mechanistic interpretability research using TransformerLens to inspect and manipulate transformer internals via HookPoints and activation caching. Use when reverse-engineering model algorithms, studying attention patterns, or performing activation patching experiments.  
  `vendor/orchestra/04-mechanistic-interpretability/transformer-lens/SKILL.md`

### 05-data-processing

- **nemo-curator** — GPU-accelerated data curation for LLM training. Supports text/image/video/audio. Features fuzzy deduplication (16× faster), quality filtering (30+ heuristics), semantic deduplication, PII redaction, NSFW detection. Scales across GPUs with RAPIDS. Use for preparing high-quality training datasets, cleaning web data, or deduplicating large corpora.  
  `vendor/orchestra/05-data-processing/nemo-curator/SKILL.md`
- **ray-data** — Scalable data processing for ML workloads. Streaming execution across CPU/GPU, supports Parquet/CSV/JSON/images. Integrates with Ray Train, PyTorch, TensorFlow. Scales from single machine to 100s of nodes. Use for batch inference, data preprocessing, multi-modal data loading, or distributed ETL pipelines.  
  `vendor/orchestra/05-data-processing/ray-data/SKILL.md`

### 06-post-training

- **grpo-rl-training** — Expert guidance for GRPO/RL fine-tuning with TRL for reasoning and task-specific model training  
  `vendor/orchestra/06-post-training/grpo-rl-training/SKILL.md`
- **miles-rl-training** — Provides guidance for enterprise-grade RL training using miles, a production-ready fork of slime. Use when training large MoE models with FP8/INT4, needing train-inference alignment, or requiring speculative RL for maximum throughput.  
  `vendor/orchestra/06-post-training/miles/SKILL.md`
- **openrlhf-training** — High-performance RLHF framework with Ray+vLLM acceleration. Use for PPO, GRPO, RLOO, DPO training of large models (7B-70B+). Built on Ray, vLLM, ZeRO-3. 2× faster than DeepSpeedChat with distributed architecture and GPU resource sharing.  
  `vendor/orchestra/06-post-training/openrlhf/SKILL.md`
- **simpo-training** — Simple Preference Optimization for LLM alignment. Reference-free alternative to DPO with better performance (+6.4 points on AlpacaEval 2.0). No reference model needed, more efficient than DPO. Use for preference alignment when want simpler, faster training than DPO/PPO.  
  `vendor/orchestra/06-post-training/simpo/SKILL.md`
- **slime-rl-training** — Provides guidance for LLM post-training with RL using slime, a Megatron+SGLang framework. Use when training GLM models, implementing custom data generation workflows, or needing tight Megatron-LM integration for RL scaling.  
  `vendor/orchestra/06-post-training/slime/SKILL.md`
- **torchforge-rl-training** — Provides guidance for PyTorch-native agentic RL using torchforge, Meta's library separating infra from algorithms. Use when you want clean RL abstractions, easy algorithm experimentation, or scalable training with Monarch and TorchTitan.  
  `vendor/orchestra/06-post-training/torchforge/SKILL.md`
- **fine-tuning-with-trl** — Fine-tune LLMs using reinforcement learning with TRL - SFT for instruction tuning, DPO for preference alignment, PPO/GRPO for reward optimization, and reward model training. Use when need RLHF, align model with preferences, or train from human feedback. Works with HuggingFace Transformers.  
  `vendor/orchestra/06-post-training/trl-fine-tuning/SKILL.md`
- **verl-rl-training** — Provides guidance for training LLMs with reinforcement learning using verl (Volcano Engine RL). Use when implementing RLHF, GRPO, PPO, or other RL algorithms for LLM post-training at scale with flexible infrastructure backends.  
  `vendor/orchestra/06-post-training/verl/SKILL.md`

### 07-safety-alignment

- **constitutional-ai** — Anthropic's method for training harmless AI through self-improvement. Two-phase approach - supervised learning with self-critique/revision, then RLAIF (RL from AI Feedback). Use for safety alignment, reducing harmful outputs without human labels. Powers Claude's safety system.  
  `vendor/orchestra/07-safety-alignment/constitutional-ai/SKILL.md`
- **llamaguard** — Meta's 7-8B specialized moderation model for LLM input/output filtering. 6 safety categories - violence/hate, sexual content, weapons, substances, self-harm, criminal planning. 94-95% accuracy. Deploy with vLLM, HuggingFace, Sagemaker. Integrates with NeMo Guardrails.  
  `vendor/orchestra/07-safety-alignment/llamaguard/SKILL.md`
- **nemo-guardrails** — NVIDIA's runtime safety framework for LLM applications. Features jailbreak detection, input/output validation, fact-checking, hallucination detection, PII filtering, toxicity detection. Uses Colang 2.0 DSL for programmable rails. Production-ready, runs on T4 GPU.  
  `vendor/orchestra/07-safety-alignment/nemo-guardrails/SKILL.md`
- **prompt-guard** — Meta's 86M prompt injection and jailbreak detector. Filters malicious prompts and third-party data for LLM apps. 99%+ TPR, <1% FPR. Fast (<2ms GPU). Multilingual (8 languages). Deploy with HuggingFace or batch processing for RAG security.  
  `vendor/orchestra/07-safety-alignment/prompt-guard/SKILL.md`

### 08-distributed-training

- **huggingface-accelerate** — Simplest distributed training API. 4 lines to add distributed support to any PyTorch script. Unified API for DeepSpeed/FSDP/Megatron/DDP. Automatic device placement, mixed precision (FP16/BF16/FP8). Interactive config, single launch command. HuggingFace ecosystem standard.  
  `vendor/orchestra/08-distributed-training/accelerate/SKILL.md`
- **deepspeed** — Expert guidance for distributed training with DeepSpeed - ZeRO optimization stages, pipeline parallelism, FP16/BF16/FP8, 1-bit Adam, sparse attention  
  `vendor/orchestra/08-distributed-training/deepspeed/SKILL.md`
- **training-llms-megatron** — Trains large language models (2B-462B parameters) using NVIDIA Megatron-Core with advanced parallelism strategies. Use when training models >1B parameters, need maximum GPU efficiency (47% MFU on H100), or require tensor/pipeline/sequence/context/expert parallelism. Production-ready framework used for Nemotron, LLaMA, DeepSeek.  
  `vendor/orchestra/08-distributed-training/megatron-core/SKILL.md`
- **pytorch-fsdp2** — Adds PyTorch FSDP2 (fully_shard) to training scripts with correct init, sharding, mixed precision/offload config, and distributed checkpointing. Use when models exceed single-GPU memory or when you need DTensor-based sharding with DeviceMesh.  
  `vendor/orchestra/08-distributed-training/pytorch-fsdp2/SKILL.md`
- **pytorch-lightning** — High-level PyTorch framework with Trainer class, automatic distributed training (DDP/FSDP/DeepSpeed), callbacks system, and minimal boilerplate. Scales from laptop to supercomputer with same code. Use when you want clean training loops with built-in best practices.  
  `vendor/orchestra/08-distributed-training/pytorch-lightning/SKILL.md`
- **ray-train** — Distributed training orchestration across clusters. Scales PyTorch/TensorFlow/HuggingFace from laptop to 1000s of nodes. Built-in hyperparameter tuning with Ray Tune, fault tolerance, elastic scaling. Use when training massive models across multiple machines or running distributed hyperparameter sweeps.  
  `vendor/orchestra/08-distributed-training/ray-train/SKILL.md`

### 09-infrastructure

- **lambda-labs-gpu-cloud** — Reserved and on-demand GPU cloud instances for ML training and inference. Use when you need dedicated GPU instances with simple SSH access, persistent filesystems, or high-performance multi-node clusters for large-scale training.  
  `vendor/orchestra/09-infrastructure/lambda-labs/SKILL.md`
- **modal-serverless-gpu** — Serverless GPU cloud platform for running ML workloads. Use when you need on-demand GPU access without infrastructure management, deploying ML models as APIs, or running batch jobs with automatic scaling.  
  `vendor/orchestra/09-infrastructure/modal/SKILL.md`
- **skypilot-multi-cloud-orchestration** — Multi-cloud orchestration for ML workloads with automatic cost optimization. Use when you need to run training or batch jobs across multiple clouds, leverage spot instances with auto-recovery, or optimize GPU costs across providers.  
  `vendor/orchestra/09-infrastructure/skypilot/SKILL.md`

### 10-optimization

- **awq-quantization** — Activation-aware weight quantization for 4-bit LLM compression with 3x speedup and minimal accuracy loss. Use when deploying large models (7B-70B) on limited GPU memory, when you need faster inference than GPTQ with better accuracy preservation, or for instruction-tuned and multimodal models. MLSys 2024 Best Paper Award winner.  
  `vendor/orchestra/10-optimization/awq/SKILL.md`
- **quantizing-models-bitsandbytes** — Quantizes LLMs to 8-bit or 4-bit for 50-75% memory reduction with minimal accuracy loss. Use when GPU memory is limited, need to fit larger models, or want faster inference. Supports INT8, NF4, FP4 formats, QLoRA training, and 8-bit optimizers. Works with HuggingFace Transformers.  
  `vendor/orchestra/10-optimization/bitsandbytes/SKILL.md`
- **optimizing-attention-flash** — Optimizes transformer attention with Flash Attention for 2-4x speedup and 10-20x memory reduction. Use when training/running transformers with long sequences (>512 tokens), encountering GPU memory issues with attention, or need faster inference. Supports PyTorch native SDPA, flash-attn library, H100 FP8, and sliding window attention.  
  `vendor/orchestra/10-optimization/flash-attention/SKILL.md`
- **gguf-quantization** — GGUF format and llama.cpp quantization for efficient CPU/GPU inference. Use when deploying models on consumer hardware, Apple Silicon, or when needing flexible quantization from 2-8 bit without GPU requirements.  
  `vendor/orchestra/10-optimization/gguf/SKILL.md`
- **gptq** — Post-training 4-bit quantization for LLMs with minimal accuracy loss. Use for deploying large models (70B, 405B) on consumer GPUs, when you need 4× memory reduction with <2% perplexity degradation, or for faster inference (3-4× speedup) vs FP16. Integrates with transformers and PEFT for QLoRA fine-tuning.  
  `vendor/orchestra/10-optimization/gptq/SKILL.md`
- **hqq-quantization** — Half-Quadratic Quantization for LLMs without calibration data. Use when quantizing models to 4/3/2-bit precision without needing calibration datasets, for fast quantization workflows, or when deploying with vLLM or HuggingFace Transformers.  
  `vendor/orchestra/10-optimization/hqq/SKILL.md`
- **ml-training-recipes** — Battle-tested PyTorch training recipes for all domains — LLMs, vision, diffusion, medical imaging, protein/drug discovery, spatial omics, genomics. Covers training loops, optimizer selection (AdamW, Muon), LR scheduling, mixed precision, debugging, and systematic experimentation. Use when training or fine-tuning neural networks, debugging loss spikes or OOM, choosing architectures, or optimizing G  
  `vendor/orchestra/10-optimization/ml-training-recipes/SKILL.md`

### 11-evaluation

- **evaluating-code-models** — Evaluates code generation models across HumanEval, MBPP, MultiPL-E, and 15+ benchmarks with pass@k metrics. Use when benchmarking code models, comparing coding abilities, testing multi-language support, or measuring code generation quality. Industry standard from BigCode Project used by HuggingFace leaderboards.  
  `vendor/orchestra/11-evaluation/bigcode-evaluation-harness/SKILL.md`
- **evaluating-llms-harness** — Evaluates LLMs across 60+ academic benchmarks (MMLU, HumanEval, GSM8K, TruthfulQA, HellaSwag). Use when benchmarking model quality, comparing models, reporting academic results, or tracking training progress. Industry standard used by EleutherAI, HuggingFace, and major labs. Supports HuggingFace, vLLM, APIs.  
  `vendor/orchestra/11-evaluation/lm-evaluation-harness/SKILL.md`
- **nemo-evaluator-sdk** — Evaluates LLMs across 100+ benchmarks from 18+ harnesses (MMLU, HumanEval, GSM8K, safety, VLM) with multi-backend execution. Use when needing scalable evaluation on local Docker, Slurm HPC, or cloud platforms. NVIDIA's enterprise-grade platform with container-first architecture for reproducible benchmarking.  
  `vendor/orchestra/11-evaluation/nemo-evaluator/SKILL.md`

### 12-inference-serving

- **llama-cpp** — Runs LLM inference on CPU, Apple Silicon, and consumer GPUs without NVIDIA hardware. Use for edge deployment, M1/M2/M3 Macs, AMD/Intel GPUs, or when CUDA is unavailable. Supports GGUF quantization (1.5-8 bit) for reduced memory and 4-10× speedup vs PyTorch on CPU.  
  `vendor/orchestra/12-inference-serving/llama-cpp/SKILL.md`
- **sglang** — Fast structured generation and serving for LLMs with RadixAttention prefix caching. Use for JSON/regex outputs, constrained decoding, agentic workflows with tool calls, or when you need 5× faster inference than vLLM with prefix sharing. Powers 300,000+ GPUs at xAI, AMD, NVIDIA, and LinkedIn.  
  `vendor/orchestra/12-inference-serving/sglang/SKILL.md`
- **tensorrt-llm** — Optimizes LLM inference with NVIDIA TensorRT for maximum throughput and lowest latency. Use for production deployment on NVIDIA GPUs (A100/H100), when you need 10-100x faster inference than PyTorch, or for serving models with quantization (FP8/INT4), in-flight batching, and multi-GPU scaling.  
  `vendor/orchestra/12-inference-serving/tensorrt-llm/SKILL.md`
- **serving-llms-vllm** — Serves LLMs with high throughput using vLLM's PagedAttention and continuous batching. Use when deploying production LLM APIs, optimizing inference latency/throughput, or serving models with limited GPU memory. Supports OpenAI-compatible endpoints, quantization (GPTQ/AWQ/FP8), and tensor parallelism.  
  `vendor/orchestra/12-inference-serving/vllm/SKILL.md`

### 13-mlops

- **mlflow** — Track ML experiments, manage model registry with versioning, deploy models to production, and reproduce experiments with MLflow - framework-agnostic ML lifecycle platform  
  `vendor/orchestra/13-mlops/mlflow/SKILL.md`
- **experiment-tracking-swanlab** — Provides guidance for experiment tracking with SwanLab. Use when you need open-source run tracking, local or self-hosted dashboards, and lightweight media logging for ML workflows.  
  `vendor/orchestra/13-mlops/swanlab/SKILL.md`
- **tensorboard** — Visualize training metrics, debug models with histograms, compare experiments, visualize model graphs, and profile performance with TensorBoard - Google's ML visualization toolkit  
  `vendor/orchestra/13-mlops/tensorboard/SKILL.md`
- **weights-and-biases** — Track ML experiments with automatic logging, visualize training in real-time, optimize hyperparameters with sweeps, and manage model registry with W&B - collaborative MLOps platform  
  `vendor/orchestra/13-mlops/weights-and-biases/SKILL.md`

### 18-multimodal

- **audiocraft-audio-generation** — PyTorch library for audio generation including text-to-music (MusicGen) and text-to-sound (AudioGen). Use when you need to generate music from text descriptions, create sound effects, or perform melody-conditioned music generation.  
  `vendor/orchestra/18-multimodal/audiocraft/SKILL.md`
- **blip-2-vision-language** — Vision-language pre-training framework bridging frozen image encoders and LLMs. Use when you need image captioning, visual question answering, image-text retrieval, or multimodal chat with state-of-the-art zero-shot performance.  
  `vendor/orchestra/18-multimodal/blip-2/SKILL.md`
- **clip** — OpenAI's model connecting vision and language. Enables zero-shot image classification, image-text matching, and cross-modal retrieval. Trained on 400M image-text pairs. Use for image search, content moderation, or vision-language tasks without fine-tuning. Best for general-purpose image understanding.  
  `vendor/orchestra/18-multimodal/clip/SKILL.md`
- **evaluating-cosmos-policy** — Evaluates NVIDIA Cosmos Policy on LIBERO and RoboCasa simulation environments. Use when setting up cosmos-policy for robot manipulation evaluation, running headless GPU evaluations with EGL rendering, or profiling inference latency on cluster or local GPU machines.  
  `vendor/orchestra/18-multimodal/cosmos-policy/SKILL.md`
- **llava** — Large Language and Vision Assistant. Enables visual instruction tuning and image-based conversations. Combines CLIP vision encoder with Vicuna/LLaMA language models. Supports multi-turn image chat, visual question answering, and instruction following. Use for vision-language chatbots or image understanding tasks. Best for conversational image analysis.  
  `vendor/orchestra/18-multimodal/llava/SKILL.md`
- **fine-tuning-serving-openpi** — Fine-tune and serve Physical Intelligence OpenPI models (pi0, pi0-fast, pi0.5) using JAX or PyTorch backends for robot policy inference across ALOHA, DROID, and LIBERO environments. Use when adapting pi0 models to custom datasets, converting JAX checkpoints to PyTorch, running policy inference servers, or debugging norm stats and GPU memory issues.  
  `vendor/orchestra/18-multimodal/openpi/SKILL.md`
- **fine-tuning-openvla-oft** — Fine-tunes and evaluates OpenVLA-OFT and OpenVLA-OFT+ policies for robot action generation with continuous action heads, LoRA adaptation, and FiLM conditioning on LIBERO simulation and ALOHA real-world setups. Use when reproducing OpenVLA-OFT paper results, training custom VLA action heads (L1 or diffusion), deploying server-client inference for ALOHA, or debugging normalization, LoRA merge, and c  
  `vendor/orchestra/18-multimodal/openvla-oft/SKILL.md`
- **segment-anything-model** — Foundation model for image segmentation with zero-shot transfer. Use when you need to segment any object in images using points, boxes, or masks as prompts, or automatically generate all object masks in an image.  
  `vendor/orchestra/18-multimodal/segment-anything/SKILL.md`
- **stable-diffusion-image-generation** — State-of-the-art text-to-image generation with Stable Diffusion models via HuggingFace Diffusers. Use when generating images from text prompts, performing image-to-image translation, inpainting, or building custom diffusion pipelines.  
  `vendor/orchestra/18-multimodal/stable-diffusion/SKILL.md`
- **whisper** — OpenAI's general-purpose speech recognition model. Supports 99 languages, transcription, translation to English, and language identification. Six model sizes from tiny (39M params) to large (1550M params). Use for speech-to-text, podcast transcription, or multilingual audio processing. Best for robust, multilingual ASR.  
  `vendor/orchestra/18-multimodal/whisper/SKILL.md`

### 19-emerging-techniques

- **knowledge-distillation** — Compress large language models using knowledge distillation from teacher to student models. Use when deploying smaller models with retained performance, transferring GPT-4 capabilities to open-source models, or reducing inference costs. Covers temperature scaling, soft targets, reverse KLD, logit distillation, and MiniLLM training strategies.  
  `vendor/orchestra/19-emerging-techniques/knowledge-distillation/SKILL.md`
- **long-context** — Extend context windows of transformer models using RoPE, YaRN, ALiBi, and position interpolation techniques. Use when processing long documents (32k-128k+ tokens), extending pre-trained models beyond original context limits, or implementing efficient positional encodings. Covers rotary embeddings, attention biases, interpolation methods, and extrapolation strategies for LLMs.  
  `vendor/orchestra/19-emerging-techniques/long-context/SKILL.md`
- **model-merging** — Merge multiple fine-tuned models using mergekit to combine capabilities without retraining. Use when creating specialized models by blending domain-specific expertise (math + coding + chat), improving performance beyond single models, or experimenting rapidly with model variants. Covers SLERP, TIES-Merging, DARE, Task Arithmetic, linear merging, and production deployment strategies.  
  `vendor/orchestra/19-emerging-techniques/model-merging/SKILL.md`
- **model-pruning** — Reduce LLM size and accelerate inference using pruning techniques like Wanda and SparseGPT. Use when compressing models without retraining, achieving 50% sparsity with minimal accuracy loss, or enabling faster inference on hardware accelerators. Covers unstructured pruning, structured pruning, N:M sparsity, magnitude pruning, and one-shot methods.  
  `vendor/orchestra/19-emerging-techniques/model-pruning/SKILL.md`
- **moe-training** — Train Mixture of Experts (MoE) models using DeepSpeed or HuggingFace. Use when training large-scale models with limited compute (5× cost reduction vs dense models), implementing sparse architectures like Mixtral 8x7B or DeepSeek-V3, or scaling model capacity without proportional compute increase. Covers MoE architectures, routing mechanisms, load balancing, expert parallelism, and inference optimi  
  `vendor/orchestra/19-emerging-techniques/moe-training/SKILL.md`
- **speculative-decoding** — Accelerate LLM inference using speculative decoding, Medusa multiple heads, and lookahead decoding techniques. Use when optimizing inference speed (1.5-3.6× speedup), reducing latency for real-time applications, or deploying models with limited compute. Covers draft models, tree-based attention, Jacobi iteration, parallel token generation, and production deployment strategies.  
  `vendor/orchestra/19-emerging-techniques/speculative-decoding/SKILL.md`

### 20-ml-paper-writing

- **academic-plotting** — Generates publication-quality figures for ML papers from research context. Given a paper section or description, extracts system components and relationships to generate architecture diagrams via Gemini. Given experiment results or data, auto-selects chart type and generates data-driven figures via matplotlib/seaborn. Use when creating any figure for a conference paper.  
  `vendor/orchestra/20-ml-paper-writing/academic-plotting/SKILL.md`
- **ml-paper-writing** — Write publication-ready ML/AI papers for NeurIPS, ICML, ICLR, ACL, AAAI, COLM. Use when drafting papers from research repos, structuring arguments, verifying citations, or preparing camera-ready submissions. For systems venues (OSDI, NSDI, ASPLOS, SOSP), use systems-paper-writing instead.  
  `vendor/orchestra/20-ml-paper-writing/ml-paper-writing/SKILL.md`
- **presenting-conference-talks** — Generates conference presentation slides (Beamer LaTeX PDF and editable PPTX) from a compiled paper with speaker notes and talk script. Use when preparing oral talks, spotlight presentations, or invited talks for ML and systems conferences.  
  `vendor/orchestra/20-ml-paper-writing/presenting-conference-talks/SKILL.md`
- **systems-paper-writing** — Comprehensive guide for writing systems papers targeting OSDI, SOSP, ASPLOS, NSDI, and EuroSys. Provides paragraph-level structural blueprints, writing patterns, venue-specific checklists, reviewer guidelines, LaTeX templates, and conference deadlines. Use this skill for all systems conference paper writing.  
  `vendor/orchestra/20-ml-paper-writing/systems-paper-writing/SKILL.md`

### 21-research-ideation

- **brainstorming-research-ideas** — Guides researchers through structured ideation frameworks to discover high-impact research directions. Use when exploring new problem spaces, pivoting between projects, or seeking novel angles on existing work.  
  `vendor/orchestra/21-research-ideation/brainstorming-research-ideas/SKILL.md`
- **creative-thinking-for-research** — Applies cognitive science frameworks for creative thinking to CS and AI research ideation. Use when seeking genuinely novel research directions by leveraging combinatorial creativity, analogical reasoning, constraint manipulation, and other empirically grounded creative strategies.  
  `vendor/orchestra/21-research-ideation/creative-thinking-for-research/SKILL.md`

### 22-agent-native-research-artifact

- **ara-compiler** — Compiles any research input — PDF papers, GitHub repositories, experiment logs, code directories, or raw notes — into a complete Agent-Native Research Artifact (ARA) with cognitive layer (claims, concepts, heuristics), physical layer (configs, code stubs), exploration graph, and grounded evidence. Use when ingesting a paper or codebase into a structured, machine-executable knowledge package, build  
  `vendor/orchestra/22-agent-native-research-artifact/compiler/SKILL.md`
- **ara-research-manager** — Records research provenance as a post-task epilogue, scanning conversation history at the end of a coding or research session to extract decisions, experiments, dead ends, claims, heuristics, and pivots, and writing them into the ara/ directory with user-vs-AI provenance tags. Use as a session epilogue — never during execution — to maintain a faithful, auditable trace of how a research project act  
  `vendor/orchestra/22-agent-native-research-artifact/research-manager/SKILL.md`
- **ara-rigor-reviewer** — Performs ARA Seal Level 2 semantic epistemic review on Agent-Native Research Artifacts, scoring six dimensions (evidence relevance, falsifiability, scope calibration, argument coherence, exploration integrity, methodological rigor) and producing a constructive, severity-ranked report with a Strong Accept-to-Reject recommendation. Use after Level 1 structural validation passes, when an ARA needs an  
  `vendor/orchestra/22-agent-native-research-artifact/rigor-reviewer/SKILL.md`
