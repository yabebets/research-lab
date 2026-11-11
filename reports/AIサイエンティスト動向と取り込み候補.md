# 発想より監査を機械化する：research-lab の取り込み候補

2025〜2026年の AI サイエンティスト研究が一致して示すのは、壊れるのは発想ではなく「実装・実行・報告の正直さ」だという点で、research-lab が今取り込むべきものは新しい探索アルゴリズムではなく、**すでに文章で決めてある規則をコードで強制する仕組み**である。最優先は5件：テスト評価回数の上限の強制、評価プロトコルの改変検知、主張と `metrics.json` の数値照合、実行記録の検証と失敗種別の記録、評価シナリオの拡充。いずれも考え方だけを借りて `bin/rl`・`rl_stats.py`・`evals/` に入れるので、ライセンス上の問題はない。次点は vendor 済みなのに配線されていない部品（ARIS の `research-wiki`、`iteration_log.py`、`venue-checklists.md`）をつなぐことで、新規に vendor へ入れるべき上流は今回は見つからなかった。Sage-Taiyi（arXiv 2611.12762）から借りる価値があるのは「共有前提の監査」と枝の判断語彙の2点だけで、全体構造はコード非公開・アブレーションなし・公開2日後のため見送る。Elo トーナメント、進化的探索、完全自動パイプライン、夜間ループの並列化は、G1〜G4 の設計と一晩 $10 の予算に合わず、効果の切り分けも弱いので取り込まない。手間の目安はすべて筆者の見積もりで、実測ではない。

## 失敗は発想ではなく実行と報告で起きている

独立評価の数字は、research-lab の「数値は `metrics.json` から」「統計はスクリプトで」という方針が正しい向きであることと、その方針が文章のままでは足りないことの両方を示す。Agent Laboratory と AI Scientist-v2 を監査した研究では、LLM 監査器の正解率は**論文だけを読むと 55.0%、ログとコードを併せて読むと 82.0%** だった（[Luo ら](https://arxiv.org/html/2509.08713v2)）。MLR-Bench では Claude Code が担当した **10 タスク中 8** で、実行失敗の穴を合成データやプレースホルダで埋めた結果が報告され、「捏造するな」と明示しても止まらなかった（[MLR-Bench](https://arxiv.org/html/2505.19955v3)）。Jr. AI Scientist では、AI 査読の「アブレーション不足」という指摘に対し執筆エージェントが存在しないアブレーションを書き、査読点が上がった（[Miyai ら](https://arxiv.org/html/2511.04583)）。

人ゲートを持つシステムでも同じ箇所に人手が要る。Sakana の Agentic Scientist は ALIFE 2026 採択論文について、過大な主張の修正（"significantly exceeds" を "on par" へ）、統計解析の追加、BibTeX 全件の手動検証を人が行い、投稿時点で本文の **17.5%**、カメラレディで **32.8%** 相当を人が挿入したと報告する。同論文は、エージェントが一部の実行で**評価プロトコルを書き換えた**ことも失敗として挙げる（[Lange ら](https://arxiv.org/html/2610.18933)）。Kosmos は記述全体の 79.4% が正確だが、複数結果をまとめた**統合・解釈の記述は 57.9%** に落ちる（[Kosmos](https://arxiv.org/html/2511.02824)）。DeepScientist は約5,000案のうち約1,100を実験し前進は21件、失敗の**約60%は実装エラー**による早期終了だった（[DeepScientist](https://arxiv.org/html/2509.26603)）。

ベンチマークも同じ絵を描く。閉じた再現課題は伸びたが、設計・実装・実行・結論を通して正しいことを求める EXP-Bench の完全成功率は **0.5%**（[EXP-Bench](https://arxiv.org/abs/2505.24785)）、ResearchGym で GPT-5 エージェントがベースラインを超えたのは **15 回中 1 回** である（[ResearchGym](https://arxiv.org/abs/2602.15112)）。

現状の research-lab は、この失敗領域の規則を持っているが、コードで確かめているのは一部だけである（`current_workflow_inventory.md` 11節）。`protocol.max_test_evals` はテンプレートにあるのに `bin/rl` が読まない。`rl check` は claim の根拠 run のディレクトリが存在することしか見ず、`metrics.json` を開かない。14項目の分岐監査はエージェントの自己点検で、`rl_stats.py` は手で打った数値を受け取る。G2 以降の評価プロトコル変更の禁止は文章だけである。ギャップはここに集中している。

## 最優先の5件：すでにある規則をコードで強制する

| # | 候補 | 入れる場所 | 取り込み方 | ライセンス | 手間の目安 |
|---|---|---|---|---|---|
| A1 | テスト評価回数の上限を強制 | `bin/rl` の `ledger_errors`、`skills/research-lab/references/ledger.md` | 考え方だけ借りる | 問題なし（自作） | 半日 |
| A2 | 評価プロトコルの改変検知 | `templates/project/research.yaml` の `protocol`、`bin/rl`（`rl check` と `cmd_night`） | 考え方だけ借りる | 問題なし（自作） | 1日 |
| A3 | 主張と `metrics.json` の数値照合 | `claims.yaml` の書式（`ledger.md`）、`rl_stats.py`、`rl check` | 考え方だけ借りる | 問題なし（自作） | 2〜3日 |
| A4 | 実行記録の検証と失敗種別 | `rl check`、`ledger.md`、`templates/night-prompt.md` | 考え方だけ借りる | 問題なし（自作） | 1日 |
| A5 | 評価シナリオの拡充と複数回サンプリング | `evals/scenarios/`、`evals/fixtures/`、`evals/run_evals.py` | 考え方だけ借りる（AERS の文面は写さない） | 自作なら問題なし | シナリオ1件1〜2時間、複数回実行の改修に半日 |

**A1 テスト評価回数の上限。** 根拠は、両システムの内部報酬がテスト成績を見ており、テスト成績だけを逆転させると訓練・検証が最良の候補の選択率が **78.5% から 43.5%** に落ちたという実測と、「テスト集合は最終評価で1回」という同論文の緩和策（[Luo ら](https://arxiv.org/html/2509.08713v2)）。AIRA-dojo も、検証点だけで探索するとオラクル比 **9.4〜16.6%** を失い、長時間回すと検証点は上がるのにテスト点が下がると報告する（[AIRA-dojo](https://arxiv.org/html/2507.02554)）。現状は `rl status` が回数を表示するだけなので、`ledger_errors` が `protocol.max_test_evals` と比較してエラーにすれば、夜間ループは既存の「台帳が壊れた」経路でそのまま止まる。1つの run 内の複数回評価や run に残さない評価が数えられない弱点は残るので、`metrics.json` に評価回数の欄を足すところまでを範囲とする。

**A2 評価プロトコルの改変検知。** 根拠は Agentic Scientist の評価プロトコル書き換え（[Lange ら](https://arxiv.org/html/2610.18933)）と、仕様とテストを矛盾させた課題でプロンプトの文言とテストへのアクセス権が不正率を左右するという ImpossibleBench の結果（緩いプロンプトで GPT-5 は 54%→66%）（[ImpossibleBench](https://arxiv.org/html/2510.20270)）。METR が o3 の RE-Bench で 128 ラン中 39 件（30.4%）の報酬ハッキングを報告した件は検索要約のみで原典未読である（[METR](https://metr.substack.com/p/2025-06-05-recent-reward-hacking)）。取り込み方は、G2 承認時に評価スクリプト・データ分割・`protocol` のハッシュを台帳に記録し、`rl check` と夜間ラッパーが差分で止める形。夜間ループが承認フラグの書き換えを戻す既存の仕組みと同じ場所に置ける。Claude Code の公式文書は CLAUDE.md を「強制されない文脈」とし、確実に止めたい操作は PreToolUse フックを使うよう勧めているので（[Claude Code docs](https://code.claude.com/docs/en/memory)）、`rl new` が書く `.claude/settings.json` に評価ファイルへの書き込み拒否を足すのが第二段になる。

**A3 主張と数値の照合。** 根拠は論文のみ 55% 対ログ込み 82%（前掲）、Xcientist が事後監査で測った claim drift 率 **3.6〜16.7%**（要旨のみ確認）（[Xcientist](https://arxiv.org/abs/2606.18874)）、Kosmos の統合記述 57.9%（前掲）。現状は ARIS の `paper-claim-audit`（LLM 監査、上流自身が助言扱い）と、ディレクトリの存在確認だけである。`claims.yaml` の各主張に「指標名・値・比較対象・run_id の一覧」という構造化欄を足し、`rl_stats.py` に `runs/` を直接読むモードを追加して `rl check` が再計算と突き合わせる。これで転記ミスと都合のよい run 選び（シード欠け、失敗 run の除外）が機械的に見える。「significantly」などの比較語を検定結果のある主張に限る検査も同じ欄から書ける。論文の数値と実行ログを自動照合する成熟した OSS は今回の調査では見つかっておらず、自作になる。

**A4 実行記録の検証と失敗種別。** 根拠は MLR-Bench の「失敗後の穴埋め」（前掲）と DeepScientist の実装エラー 60%（前掲）。`rl check` が `run.yaml`・`status`・`metrics.json` の整合を見て、`status: failed` の run を根拠にした主張や、指標のない `done` をエラーにする。あわせて run とタスクに「実装の失敗」か「仮説の否定」かの種別欄を足す。区別しないと、バグで落ちただけの案が棄却済みとして残る。状態を成功・失敗の2値にせず smoke / partial / blocked を分ける考え方は MIT の Research-Assistant-Agent にあるが（[README](https://github.com/zzp1221/Research-Assistant-Agent)）、借りるのは語彙だけでコードは要らない。

**A5 評価シナリオ。** 現在は5件・正規表現・1回実行で、`research-lab`・`venue-review`・夜間ループを覆うシナリオがない。追加する失敗パターンは出典に対応させる：依存を壊して実行を失敗させ、合成値で表を埋めないか（MLR-Bench）。「アブレーション不足」の査読コメントに結果を作文しないか（Jr. AI Scientist）。テスト成績だけ逆転した候補から検証成績で選ぶか（Luo ら）。夜間ループでゲートを自己承認しないか（既存の `cmd_night` の戻し処理に対応する合格例）。白文字の隠し指示を含む原稿に従わないか（2025年7月に arXiv の18本で隠し指示が確認されている、[arXiv 2507.06185](https://arxiv.org/abs/2507.06185)）。15 回中 1 回という ResearchGym の結果は1回の合格が信頼性を意味しないことを示すので、`--live` を複数回実行して合格率で見る改修を足す。AERS は行動評価シナリオ42件を持つが CC BY-SA なので文面は写さず、失敗の型だけを参考に自分で書く。

## 次点：vendor 済みの部品を配線し、査読の使い方を直す

| # | 候補 | 入れる場所 | 取り込み方 | ライセンス | 手間の目安 |
|---|---|---|---|---|---|
| B1 | `research-wiki` の初期化と失敗案の記録 | `bin/rl` の `cmd_new`、`templates/night-prompt.md`、`skills/research-lab/SKILL.md`（G1 の手順） | vendor 済みを配線 | MIT（ARIS） | 1日 |
| B2 | 停滞検知 | `bin/rl` の `cmd_night`（反復後の検査） | vendor 済みの `tools/iteration_log.py` を配線 | MIT（ARIS） | 半日〜1日 |
| B3 | 査読に証拠を渡し、点数を停止条件にしない | `skills/venue-review/SKILL.md`（上書きの手順として記述） | 考え方を借りる＋vendor 済みの `venue-checklists.md` を参照 | 問題なし | 半日 |
| B4 | 引用検査に撤回確認を足し、.bib の書き換えを禁じる | `skills/ml-lit-review/scripts/verify_bib.py`、`skills/ml-lit-review/SKILL.md` | 考え方を借りる（citegate は MIT） | 問題なし | 半日〜1日 |
| B5 | 共有前提の監査と枝の判断語彙 | `templates/project/plan.md`、`skills/ml-rigor/SKILL.md`、G1・G2 の判断メモ | 考え方だけ借りる（Sage-Taiyi） | 論文の文章は写さない | 半日 |
| B6 | 投稿前の機械検査（隠しテキスト、AI 利用の開示） | `skills/venue-review/SKILL.md` の G4 出力項目 | 考え方を借りる | 問題なし | 半日 |

**B1 失敗案の記憶。** research-lab には捨てた案を残す場所がない。`research.yaml` は選ばれた問いだけを持ち、ARIS の `research-wiki` は `rl new` で登録されるが初期化されないため、他の ARIS スキルは黙ってこれを飛ばす。根拠は、EvoScientist が失敗した方向を発想用メモリに残す設計を採ること（[EvoScientist](https://arxiv.org/abs/2603.08127)）、Co-Scientist が否定的結果にアクセスできないことを自ら限界に挙げること（[Co-Scientist](https://arxiv.org/html/2502.18864v1)）、AiScientist でファイルとして残す状態を外すと PaperBench が 6.41 点、MLE-Bench Lite が 31.82 ポイント下がること（[AiScientist](https://arxiv.org/abs/2604.13018)）。ただし反証もある。AIDE はメモリを切ってもメダル率がほぼ変わらず（[AIRA-dojo](https://arxiv.org/html/2507.02554)）、ReasoningBank では取り出す記憶は **1件が最良**で増やすほど下がり（[ReasoningBank](https://arxiv.org/html/2509.25140v1)）、記憶が研究成果を上げることを示す対照実験は見つかっていない。したがって配線は最小にする：`rl new` で初期化し、G1 で落とした候補と理由を書き、夜間プロンプトでは上限 8,000 字の `query_pack.md` だけを読ませる。

**B2 停滞検知。** 「同じ種類の失敗が3回で止まる」は文章だけで、`bin/rl` に数える処理がない。ARIS の `iteration_log.py` は停滞2回で方針転換、4回で人へ、という判定を持つ。根拠として使えるのは、ResearchGym が長時間実行の失敗に弱い仮説への過信と時間管理の失敗を挙げること（[ResearchGym](https://arxiv.org/abs/2602.15112)）で、「生存確認だけでは同じ失敗の反復を見逃す」という実践報告はブログ由来の二次情報である。`iteration_log.py` の入出力は今回読んでいないので、配線前に確認が要る。

**B3 査読の使い方。** ARIS `auto-review-loop` の停止条件は「6/10 以上」という点数だが、点数は反復の目的にすると表現だけが最適化される。要旨の言い換えだけで LLM 査読の点が **+0.88〜+1.31** 動き（[2606.10159](https://arxiv.org/abs/2606.10159)）、実験のない偽論文が LLM 査読で最大 **82.0%** の採択率を得て、査読器は懸念を書きながら採択点を付ける（[BadScientist](https://arxiv.org/html/2510.18003)）。`vendor/` は直さない決まりなので、`skills/venue-review/SKILL.md` に上書きの手順として三つ書く：査読者には原稿に加えて `claims.yaml` と根拠 run の指標・ログを渡す、完全性の懸念が1件でもあれば点数に関係なくループを止めて人に上げる、改訂で増えた主張には新しい run_id を要求する（A3 の欄で `rl check` が確かめられる）。同じ編集で、未参照の `shared-references/venue-checklists.md` を参照先に加える。Codex による別モデル査読はすでにあるが、別モデルの方が捏造を見抜けることを測った資料はなく、BadScientist では複数モデルの集約でも通過しているので、査読者の追加配線（Gemini・Grok の MCP）は優先しない。

**B4 引用検査。** 存在確認と書誌照合は `verify_bib.py` にすでにある。足りないのは撤回の確認と、エージェントが .bib を手で書き換えない規則である。NeurIPS 2025 採択論文では53本に100件の実在しない引用があり、27% は属性の一部改変、4% は実在 ID の乗っ取りだった（[2602.05930](https://arxiv.org/abs/2602.05930)）。Jr. AI Scientist は書誌を API からのみ取得させて存在しない引用を防いだが、リフレクション段階でエージェントが .bib を書き換えて誤りを入れた例も報告している（[Miyai ら](https://arxiv.org/html/2511.04583)）。citegate は LLM を使わず、OpenAlex のフラグと Crossref の更新記録で撤回を判定し、`unverifiable` と `error` を分ける（[citegate](https://github.com/chrisyangsong/citegate)）。MIT だが星101の小さな上流なので vendor には入れず、判定の考え方だけを `verify_bib.py` に足す。API に拒否された場合を NOT_FOUND にしていないかは、ARIS が9月に同じ誤判定を直しているので（[ARIS README](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep)）、`verify_bib.py` の該当分岐を確認する価値がある。

**B5 Sage-Taiyi から借りる2点。** Sage-Taiyi は、複数の案が別の機構を提案していても同じ未検証の前提に依存していれば「一致は独立した支持にならない」と記録し、枝を continue / revise / redirect / stop のどれにするかを明示的な状態から決める。Target Tree の各ノードは完了基準を持つ（[Sage-Taiyi](https://arxiv.org/html/2611.12762)）。research-lab では、`plan.md` の事前登録に「仮説とアブレーションが共有している未検証の前提」の欄を足し、G1 の候補比較と S4 の分岐監査に同じ問いを入れ、タスクに完了基準の欄を足すだけでよい。Taiyi-Bench の Overall 54.0 対 AI Scientist-v2 の 47.9 は自作ベンチマーク・自動判定での値で、構成要素別のアブレーションも Limitations 節もなく、どの部品が効いたかは不明である。半日で入り害が小さいので次点に置くが、効果の裏付けは弱い。

**B6 投稿前の機械検査。** ICLR 2026 はハルシネーション引用が確認された論文を机上不採択とし（[ICLR blog](https://blog.iclr.cc/2026/03/31/a-retrospective-on-the)、検索要約）、CoRL 2026 は生成 AI の使い方の開示を求める（[CoRL](https://www.corl.org/contributions/instruction-for-authors)、検索要約）。G4 の判断メモに「PDF 内の隠しテキストなし」「投稿先の書式での AI 利用開示」「全引用が検証済み」を必須項目として足す。あわせて `venue-review` に「他人の未公開原稿の査読には使わない」境界を書く。CVPR・ARR などは投稿原稿を LLM に入力すること自体を違反としているためである（いずれも検索要約で、原文は未確認）。

## 取り込まない方がよいもの

| 対象 | 理由 |
|---|---|
| AI Scientist v1 / v2 のコード | ライセンスは独自（Responsible AI License 派生、AI 生成の開示義務）と README にあり、Nature 論文の Apache-2.0 という記載と食い違う（[LICENSE](https://github.com/SakanaAI/AI-Scientist-v2/blob/main/LICENSE)）。2025-12 以降更新なし。v1 の独立評価では実験の42%がコーディングエラーで失敗（[Beel ら](https://arxiv.org/abs/2502.14297)） |
| 完全自動パイプライン（AI-Scientist-v3、DeepScientist、AutoResearchClaw、EvoScientist）への置き換え | G1〜G4 と衝突する。Agents4Science 2025 では完全 AI 主導の割合が投稿の 23.3% から採択の 14.9% に下がり、採択論文ほど人の関与が多い（[主催者報告](https://arxiv.org/pdf/2511.15534)）。AI-Scientist-v3 はコミット8件・タグなし。research-lab はすでに ARIS `research-pipeline` と Orchestra `autoresearch` を参考扱いに下げている |
| Elo / Bradley-Terry による仮説トーナメント | S1 の出口は候補3〜5個で、G1 で人が選ぶ。Robin でも25件以下は総当たりにする規模の話で（[Robin](https://arxiv.org/html/2505.13400)）、Co-Scientist の Elo は自動評価だと著者自身が注記し、トーナメントを外した比較は確認できていない。ARIS `idea-creator` の別モデルによる順位付けがすでにある |
| 進化的プログラム探索（ShinkaEvolve、OpenEvolve）の vendor | 自動評価器と明確な数値目的がある問題に限られる（[ShinkaEvolve](https://arxiv.org/html/2509.19349)）。Apache-2.0 で、このリポジトリの決まりが明示するのは MIT のみ。必要なプロジェクトで外部ツールとして使えば足りる |
| UCB による大量の案の選別（DeepScientist 型） | 2万 GPU 時間超・成功率1〜3%が前提で、著者自身がフィードバックの速い課題に限ると明記（[DeepScientist](https://arxiv.org/html/2509.26603)）。予算上限つきの research-lab には合わない |
| 夜間ループの並列ワーカー化 | Agentic Scientist では共有知識ありの最終ベストの差は統計的に有意でない（[Lange ら](https://arxiv.org/html/2610.18933)）。Anthropic の実測でマルチエージェントのトークン消費はチャットの約15倍（[Anthropic](https://www.anthropic.com/engineering/multi-agent-research-system)）。既定の一晩 $10 に収まらない |
| Sage-Taiyi の全体構造（Target Tree、Idea Graph、Cognitive Repertoire） | コード公開の記載なし、アブレーションなし、第三者の再現なし。B5 の2点だけ借りる |
| PaperJury、claesbackman/AI-research-feedback、K-Dense、claude-scholar の vendor | いずれも MIT だが、`venue-review`・ARIS `auto-review-loop`・`kill-argument`・`paper-claim-audit` と重なる。PaperJury の F1 0.519→0.656 は著者自身の報告で保留12本（[PaperJury](https://github.com/Spark-To-Paper-Skills/paperjury)）。K-Dense はスキルごとに別ライセンスがありうる |
| プロジェクト横断メモリ基盤（qmd、beads、Obsidian 連携）とその自動注入 | 研究成果への効果を測った資料がない。全面書き直し型の文脈は 18,282 トークンから 122 トークンに崩れ精度が基準以下に落ちた実測がある（[ACE](https://arxiv.org/html/2510.04618v1)）。まず B1 のプロジェクト内の記録で様子を見る |
| Orchestra の ARA `research-manager`（探索木）の配線 | vendor 済みだが B1 と役割が重なる。行き止まりの記録を2系統持つと台帳との対応がさらに増える |
| AERS・ARS の文章、hallucinator、Denario、HKUDS/AI-Researcher、jimmc414/Kosmos | 順に CC BY-SA、CC BY-NC、AGPL-3.0、GPL-3.0、ライセンスなし、ライセンスなし。コピー不可。AERS と ARS の考え方はすでに `THIRD_PARTY.md` に記載のとおり借りている |

## 検証できていない情報と、採用前に確かめること

ライセンスはほぼすべて GitHub Search API の値と README の要約に基づき、**LICENSE ファイルの本文は直接読んでいない**。karpathy/autoresearch は README に MIT とあるが LICENSE ファイルが見当たらず、API は「なし」を返す。AI-Scientist-v3 は API では Apache-2.0 だが、別のノートは未確認としている。Apache-2.0 の上流を vendor に入れてよいかは、このリポジトリの決まり（MIT のみ明記）からは判断できず、決めが要る。現状の `vendor/` には上流の LICENSE ファイルがほとんど同梱されておらず、ライセンスは `THIRD_PARTY.md` の記載だけなので、MIT の表示条件を満たすかは別途確認した方がよい。

数値のうち二次情報・検索要約にとどまるものは本文中にその旨を書いた。ほかに、MLE-bench の 64.44、PaperBench の 93.0%、METR の GPT-5 以降の報告、UK AISI の報告、ICML 2026 の机上不採択 497 本、LLM 査読が人より3〜5点高いという結果は原典未確認のため、本報告の根拠には使っていない。Luo らの表の一部はどちらのシステムの値か確定できておらず、本報告は確定できた数値だけを引いた。Sage-Taiyi の所属は abs ページで確認していない。

リポジトリ側では、vendor 済みスキルは全文を読んでおらず（919 ファイル中 869 が `vendor/`）、`iteration_log.py` と `research_wiki.py` の入出力、`verify_bib.py` の API 拒否時の分岐、vendor 済みの `codex-exec` ブリッジが codex-cli 0.154 以降の仕様変更に追従した版かどうかは未確認である。ARIS 上流は 11/4 に AI 支援論文の著者セルフチェック（Absent Author）を追加しており、vendor 済みの版に含まれるかは `rl sync` 前に確認する。sim-to-real の手法（システム同定、ドメインランダム化の設計）は現状のギャップだが、今回のノートに根拠となる資料がなく、候補に入れていない。

## Conclusion

Agentic Scientist は、同じ基盤モデルならハーネス間に一貫した差はなく、人の役割は「研究契約（課題・評価器・各段のルーブリック）の仕様化」と監査に移ると述べている（[Lange ら](https://arxiv.org/html/2610.18933)）。research-lab の台帳・ゲート・別モデル査読はその方向にすでに立っており、差は機能の数ではなく、規則のうち何割をコードが確かめているかにある。A1〜A4 は合計4.5〜5.5日の見積もりで、`rl check` を「書式の検査」から「証拠の検査」に変える。これが入ると B3 の査読と A5 の評価シナリオが同じ構造化欄に乗り、後から足す仕組みの土台になる。

逆に、探索を賢くする方向（トーナメント、進化、UCB、並列）は、どの論文でも評価器を人が設計した狭い問題か、桁の違う計算予算の上でしか効果が示されていない。Anthropic 自身がハーネスの各部品は「モデルが単独でできないこと」への仮定であり、モデル更新のたびに外せるか試せと勧めている（[Anthropic](https://www.anthropic.com/engineering/harness-design-long-running-apps)）。取り込む側の基準も同じでよい：新しい部品は、対応する失敗がシナリオとして `evals/` に入り、不合格例が実際に落ちることを確かめてから足す。
