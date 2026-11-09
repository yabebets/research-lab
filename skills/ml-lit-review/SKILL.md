---
name: ml-lit-review
description: ML・CV・NLP・ロボティクスの文献調査と引用の検証。arXiv・Semantic Scholar・OpenAlex で集め、関連研究の比較表（手法・課題・データ・指標・結果・コード）と空白の地図を作り、BibTeX の全エントリを scripts/verify_bib.py で実在確認する（捏造・誤記の検出）。トリガー例：「関連研究を調べて」「この分野のサーベイ」「新規性があるか確かめて」「related work を書く材料」「参考文献をチェックして」「bib が正しいか確認して」。
---

# ml-lit-review — 文献調査と引用の検証

## 流れ

1. **問いを 1 文にする**（何について、どの範囲で、何年以降）。`research.yaml` の `question` があればそれを使う。
2. **集める**：ARIS の `research-lit`（プロジェクト内なら `/research-lit`）で arXiv・Semantic Scholar・OpenAlex を横断する。道具は `$ARIS_REPO/tools/arxiv_fetch.py` `semantic_scholar_fetch.py` `openalex_fetch.py`。重要な論文は、引用している論文・引用されている論文を 1 段たどる。
3. **ふるいにかける**：採否の基準を先に書く（課題・設定・年・査読の有無）。除外した理由も残す。
4. **比較表を作る**：`notes/literature/matrix.md` に、1 行 1 論文で

   | 論文 | 年・会議 | 課題 | 手法の要点 | データ・環境 | 指標と主な結果 | コード | 私たちとの違い |
   |---|---|---|---|---|---|---|---|

   **論文を開いて読んだ行だけ**を埋める。要旨だけで埋めた行は「要旨のみ」と書く（要旨だけで自信を持って書かない）。
5. **空白の地図**：表から「誰もやっていない組み合わせ」「主張が割れている点」「評価が弱い点」を 3〜5 個。ARIS `novelty-check` で新規性を、`kill-argument` で弱点を確かめる。
6. **BibTeX を作る**：`paper/refs.bib`。arXiv の論文は `eprint` に ID を入れる。会議版があれば会議版を優先（DBLP の BibTeX が正確）。
7. **検証する（必須）**：

   ```bash
   python3 ~/research-lab/skills/ml-lit-review/scripts/verify_bib.py paper/refs.bib --json notes/literature/bib-check.json
   ```

   - `OK` 以外は全部直すか、人に確認する。`NOT_FOUND` は捏造・誤記の疑い。**論文に残さない**。
   - `ERROR` は判定できていないだけ（通信・回数制限）。時間をおいて再実行する。`S2_API_KEY` を環境変数に入れると Semantic Scholar の制限がゆるむ。
   - 本文での引用のしかた（その論文が本当にそう言っているか）は ARIS の `citation-audit` で確かめる。

## 書き方の決まり

- 引用する主張は、その論文の本文（節・表・図）を確認したものだけ。要旨や他の論文の孫引きで書かない。
- 「初めて」「唯一」と書く前に `novelty-check` を通し、検索した範囲（データベース・キーワード・日付）を `notes/literature/search-log.md` に残す。
- 出版の前に、新しく出た論文がないか最後にもう一度だけ検索する（arXiv は毎日増える）。

## Vault との関係

調査の要約（だから何か、どの空白を狙うか）は Vault に、比較表と BibTeX はプロジェクトに。ロボティクスは `Exp Robotics/2_Research/`、それ以外は `Research/`。
