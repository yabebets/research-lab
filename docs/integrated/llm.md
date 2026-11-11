# 言語モデルの呼び出しの記録・費用・予算（rl llm）— 取り込みの提案

P1（robot-assembly-bench）の P-D・P-E で 3 つの言語モデルを約 2,400 回呼ぶ。1 回ごとに再現できる形で記録し、API の予算（$600）を超えないようにする仕組みを足した。共有のファイル（README・SKILL.md・ledger.md・テンプレート）は触っていない。取り込むときの差分を下に書く。

## 作ったもの

| ファイル | 中身 |
|---|---|
| `lib/rlkit/llm.py` | `call()`・`tool_loop()`・`Tool`・`Result`、記録、費用、予算、応答のキャッシュ、`prepare()`（通信しない組み立て） |
| `lib/rlkit/llm_providers/anthropic_api.py` | Claude（公式の `anthropic` SDK、2.7 で確認） |
| `lib/rlkit/llm_providers/openai_compat.py` | GPT-5・DashScope の Qwen3-VL・vLLM（公式の `openai` SDK、3.48 で確認。base_url を替えるだけ） |
| `llm/models.yaml` | モデルの登録簿：会社・モデル ID・価格（出典の URL と確認日）・使える引数と送れない引数・画像・effort |
| `bin/rl-llm` | `rl llm models / ping / usage / budget` |
| `tests/llm/` | pytest 41 件。偽のクライアント（38 件）と、本物の SDK を手元の偽のサーバーに向けた通信の確認（3 件、SDK が無ければ飛ばす）。有料の呼び出しはしていない |

テスト：`uv run --python 3.11 --with pytest --with ruamel.yaml --with anthropic --with openai python -m pytest tests/llm`

### 使い方（プロジェクトのコードから）

```python
import sys, pathlib
sys.path.insert(0, str(pathlib.Path("~/research-lab/lib").expanduser()))
from rlkit import llm

r = llm.call("claude-opus-5-5", prompt, system=SYSTEM, images=["renders/openarm_iso.png"],
             max_tokens=32000, effort="high", sample_index=s, budget_project="robot-assembly-bench",
             meta={"robot": "openarm", "planner": "P-D", "input": "image+bom"})
if r.refused: ...                       # 結果の一種として記録される

checker = llm.Tool("check_sequence", "L1 の判定", SCHEMA, fn=check_sequence)   # fn はキーワード引数で受ける
lr = llm.tool_loop("gpt-5", prompt, [checker], max_turns=20, max_tokens=16000, effort="high", sample_index=s)
lr.stopped   # end_turn | refusal | max_tokens | max_turns
```

プロジェクトの環境（rabench の pyproject）に `anthropic>=2.7`・`openai>=3.48`・`ruamel.yaml` を足す必要がある。

### 記録（1 回 = 1 行）

- 場所：`$RL_RUN_DIR/llm_calls.jsonl`（rl run の中）、外なら `<project>/notes/llm-logs/<日付>.jsonl`
- 中身：ts・provider・model（登録簿の名前）・model_id・model_returned・model_mismatch・送った引数（params）・画像の sha256・request_sha256・応答の文字・道具の呼び出し・usage（入力・出力・キャッシュの読み・書き）・cost_usd・事前の見積もり・latency・stop_reason・refusal（category）・cache_hit・sample_index・error・meta
- 要求の本文は `<記録の場所>/llm_requests/<sha256>.json`。画像は `rl-image:sha256:<hex>` で参照し、`llm_requests/images/` に 1 回だけ保存する。生の応答は `llm_responses/<call_id>.json`
- rl run（rl-run の担当）は `cost_usd` と `model` を足して run.yaml の `llm:` に書く（形式は合わせ済み）
- 鍵と認証のヘッダーは記録しない。念のため、書き出す前に鍵の環境変数の値と `sk-…` の形を `***` に置き換える

### 鍵の読み方（値は表示しない。`rl llm models` に有無だけ出る）

| モデル | 読むもの |
|---|---|
| Claude Opus 5.5 | `ANTHROPIC_API_KEY` → `ANTHROPIC_AUTH_TOKEN` → `ant auth login` のプロファイル（SDK の順。いまは手元にどれも無い） |
| GPT-5 | `OPENAI_API_KEY` |
| Qwen3-VL Plus（DashScope 国際版） | `DASHSCOPE_API_KEY`、base_url `https://dashscope-intl.aliyuncs.com/compatible-mode/v1` |
| Qwen3-VL-235B（vLLM） | `RL_VLLM_BASE_URL`（例 `http://<クラスタ>:8000/v1`）、`--api-key` を付けたときだけ `VLLM_API_KEY` |

### 予算

- 上限は research.yaml の `budget.llm_usd_cap`（新しい欄）。プロジェクトの全記録（`runs/*/llm_calls.jsonl` と `notes/llm-logs/*.jsonl`）の `cost_usd` を足す。追記された分だけ読むので、2,400 行でも毎回の集計は軽い
- 送る前に「入力の見積もり（多め）× 入力単価 ＋ max_tokens × 出力単価」で次の 1 回の最大を出し、上限を超えるなら送らない（`BudgetExceeded`、記録に `budget_refused` を残す）。80% で警告する
- 任意の `budget.llm_halt_ratio`（例 0.8）を書くと、その割合で送らなくなる
- `llm_usd_cap` が無いと送らない（`BudgetNotSet`）。夜間ループの中（`RL_NIGHT=1`）だけ `llm_usd_per_night` を上限にし、`RL_NIGHT_STARTED_AT`（無ければ今日の 0 時）からの分を数える
- 価格が null のモデルは呼べない。自前の vLLM は API の費用 0（GPU は `budget.gpu_usd` で数える）
- 注意：並列に N 本で呼ぶと、同時に確かめた分だけ最大 N 回分はみ出しうる。上限ぎりぎりでは並列を減らす

### 応答のキャッシュ

`<project>/.llm_cache/<2 文字>/<鍵>.json`。鍵は（会社・モデル ID・送った引数・要求の sha256・sample_index）。同じ要求でも標本の番号が違えばぶつからない。当たったら API を呼ばず、費用 0・`cache_hit: true`・元の費用（`original_cost_usd`）を記録する。道具のループも、判定器が決定的なら同じ道筋をたどって再生できる。止めるときは `cache=False`。

### 各社の約束ごと（llm/models.yaml の params.forbidden で送る前に止める）

- **Claude Opus 5.5**：`claude-opus-5-5`。思考は adaptive のみ（切れない）、深さは `output_config.effort`（既定は medium なので常に明示して送る）。temperature・top_p・top_k は 400。prefill も 400。tool_choice の強制は 400 なので auto ＋ `strict: true` の道具。常に streaming。system と最後のブロックにプロンプトキャッシュ（5 分。`params={"cache_ttl": "1h"}` で 1 時間）。`stop_reason == "refusal"` を content より先に見る
- **GPT-5**：推論モデル。`max_completion_tokens`、`reasoning_effort`（minimal / low / medium / high）、system は developer の役割。temperature などは送らない。gpt-5 個別の禁止の一覧は公式の推論のガイドに無かったので、最初の ping で確かめる
- **Qwen3-VL Plus**：思考は `extra_body.enable_thinking`（登録簿では effort の on / off）。streaming（usage は `stream_options.include_usage`）。内容の検査に掛かると HTTP 400 の `data_inspection_failed` → 拒否として記録。strict の道具は未確認なので付けない

### 別モデルへの自動の切り替え（fallbacks）は使わない

claude-api スキルは Opus 5.5 のコードに server-side の `fallbacks`（拒否されたら別のモデルで答え直す）を既定で入れるよう勧めている。このベンチマークでは入れない。

- 理由：切り替わると Claude Opus 5.5 の行に別のモデル（Opus 4.8 など）の答えが混ざり、計画器どうしの比較が壊れる。拒否された率自体も計画器の性質として報告する値
- 代わりに：拒否は `stop_reason: refusal` と `refusal.category`（cyber / bio / reasoning_extraction など）を記録し、結果の種類の一つとして数える。途中まで出た文字は `discarded_text` に分けて、答えとしては使わない
- 応答の `model` が頼んだモデルと違えば `model_mismatch: true` と警告を出す
- 組立の手順は cyber・bio の対象外なので、拒否はまれだと見込む。多ければ人に相談する

## 取り込むときの差分（提案）

### README.md の「コマンド」の表に 1 行

```
| `rl llm models / ping <model> --dry-run / usage [name] / budget [name]` | 言語モデルの登録簿（`llm/models.yaml`：価格と出典・送れない引数）、送る要求の確認（通信しない）、使った額（モデル別・実行別・日別）、上限と残り。呼び出しは `lib/rlkit/llm.py` の `call()`・`tool_loop()` から。1 回ごとに記録し、`budget.llm_usd_cap` を超える呼び出しは送らない |
```

「構成」に `llm/models.yaml            言語モデルの登録簿（価格・出典・使える引数）` を足す。

### skills/research-lab/SKILL.md

止まる条件の「GPU 予算の 80% に達したとき」を次にする：

```
- GPU 予算、または言語モデルの API 予算（budget.llm_usd_cap）の 80% に達したとき
```

「作業 → スキルの早見表」に 1 行：

```
- 実験の中で言語モデル（Claude・GPT・Qwen など）を呼ぶときは、自分で SDK を呼ばず `lib/rlkit/llm.py` の `call()`・`tool_loop()` を使う（記録・費用・予算・キャッシュ）。モデルは `llm/models.yaml` に登録してから。Claude のコードは claude-api スキルに従う。比較実験では別モデルへの自動の切り替え（fallbacks）を使わない
```

### skills/research-lab/references/ledger.md の budget

```yaml
budget:                                # G2 で人が承認した上限
  gpu_usd: 0                           # GPU の合計上限（USD）
  gpu_usd_spent: 0                     # gpu-cloud が runs/ の記録から更新する
  llm_usd_cap: null                    # 実験で呼ぶ言語モデルの API の合計上限（USD）。null の間は rl llm が送らない
  llm_halt_ratio: null                 # 任意。例 0.8 なら上限の 80% で送らなくなる（止まって相談）
  llm_usd_per_night: 10                # 夜間ループ 1 晩あたりの Claude の上限（llm_usd_cap が無いとき夜間ループの中だけ代わりに使う）
  max_run_hours: 8                     # 1 回の実行の上限時間
```

ルールに 1 行：「使った額は台帳に書かない。`rl llm budget` が runs/ と notes/llm-logs/ の記録から数える」。

`runs/<run_id>/` の表に 1 行：

```
| `llm_calls.jsonl`・`llm_requests/`・`llm_responses/` | 言語モデルの呼び出しの記録（rlkit.llm が書く。1 行 1 回、要求の本文は sha256 の名前で、画像は 1 回だけ） |
```

### templates/project/research.yaml

```yaml
budget:
  gpu_usd: 0            # G2 で人が決める上限（USD）
  gpu_usd_spent: 0      # rl gpu が更新する（概算）
  llm_usd_cap: null     # G2 で人が決める言語モデルの API の上限（USD）。null の間は rl llm が送らない
  llm_halt_ratio: null  # 例 0.8：上限の 80% で止める
  llm_usd_per_night: 10
  max_run_hours: 8
```

### templates/project/.gitignore（と既存のプロジェクトの .gitignore）

```
.llm_cache/
```

記録（`llm_calls.jsonl`・`llm_requests/`・`notes/llm-logs/`）は再現のため git に入れる。画像が重くなるなら `runs/*/llm_requests/images/` も外し、描画の元（data/ と描画の設定）から作り直せるようにしておく。

### robot-assembly-bench（G2 の承認のあとで人が書く）

`research.yaml` の budget に `llm_usd_cap: 600` と `llm_halt_ratio: 0.8`（plan.md §7「80% に達したら止まって相談」に合わせる）。

## plan.md への注記（提案）

- **§4 の「言語モデルは温度 0.7 で 5 回」は実行できない**。Claude Opus 5.5 は temperature を送ると 400、GPT-5 も既定値 1 しか受け付けない。言い換えの案：
  > 言語モデルは温度などの標本化の引数を指定しない（Claude Opus 5.5 は受け付けず、GPT-5 も既定値のみ。条件をそろえるため Qwen3-VL も指定しない）。各モデルの既定の標本化で、同じ要求を 5 回（sample_index 0〜4）取る。考える深さは固定する：Claude Opus 5.5 は effort=high、GPT-5 は reasoning_effort=high、Qwen3-VL は思考あり。深さは開発用の機種でだけ調整し、調整の上限（10 通り）に数える
- **§2**：「どのモデルも拒否されたら別のモデルに切り替えない（Claude の server-side fallbacks は使わない）。拒否は結果の種類『未対応（拒否）』として分母に入れ、件数をモデルごとに報告する」を足す。§3 の結果の種類にも「未対応（拒否）」を入れる
- **§2**：Qwen3-VL の行は「API（DashScope の qwen3-vl-plus、ホスト版）」と「重みの公開版（Qwen/Qwen3-VL-235B-A22B-Instruct を vLLM で）」のどちらを主にするかを決める。再現の主張には後者が要る（重みの revision と vLLM の版を run.yaml に残す）。両方なら同じ要求で両方を回し、差を報告する
- **§7 の価格**（2026-11-10 に公式の頁で確認、`llm/models.yaml` に出典）：GPT-5 は入力 $1.25・出力 $10・キャッシュの読み $0.125。Qwen3-VL Plus（国際版）は 1 回の入力が 32K 以下で $0.20 / $1.60、32K〜128K で $0.30 / $2.40（その回の全トークンが上の単価）、暗黙のキャッシュの命中は入力の 20%。1 回 約 3 万トークンは 32K の境目に近い
- **§7 の見積もりの見直し**（キャッシュなし・出力 3,000 トークンの粗い計算。各モデル 800 回）：Opus 5.5 約 $144、GPT-5 約 $54、Qwen3-VL Plus 約 $9〜14、合計 約 $210。思考・推論のトークンは出力として課金されるので、1 回 1 万トークン考えると Opus 5.5 は +$160、GPT-5 は +$80（合計 約 $450）。これに開発用の機種での調整（3 割）を足すと $600 の近くまで行く。Opus 5.5 のキャッシュの読みは入力の 0.05 倍なので、道具のループ（毎回前の会話を送り直す）はキャッシュで大きく下がる。実際の額は最初の 3 件の試し（`rl llm usage`）で見積もり直す
- **§7**：「上限の 80% に達したら止まって相談する」は `budget.llm_halt_ratio: 0.8` で機械的に止まる

## 未確認のこと（最初の有料の ping で確かめる）

- GPT-5 の reasoning_effort の値と、送れない引数の一覧（公式の推論のガイドには gpt-5 個別の表が無かった）
- DashScope の qwen3-vl-plus：思考ありで streaming が必須か、strict の道具を受け付けるか
- 入力の見積もり（文字のバイト数 ÷ 3 ＋ 画像のトークン）が実際の usage よりどれだけ多いか。最初の数回で比べて、多すぎれば係数を直す
- Claude Opus 5.5 の思考の要約を残すか（`params={"thinking_display": "summarized"}`。費用は同じ。失敗の分析には役立つ）
