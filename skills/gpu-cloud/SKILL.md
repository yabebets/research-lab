---
name: gpu-cloud
description: RunPod・Lambda の GPU を SkyPilot で立て、研究プロジェクトの予算の範囲で実験を回し、使い終わったら必ず消すためのスキル。費用の見積もり、G2 で承認した予算の確認、上限時間とアイドル時の自動削除、消し忘れの掃除（rl gpu reap）、ARIS の run-experiment（gpu: remote）との接続を扱う。トリガー例：「GPU で学習を回して」「RunPod で」「Lambda で」「費用を見積もって」「GPU が残っていないか確認して」「クラウドの GPU を片付けて」。
---

# gpu-cloud — RunPod / Lambda の GPU を安全に使う

GPU の確保は **SkyPilot**（RunPod と Lambda の両方に対応）、実験の実行は ARIS の `run-experiment` / `experiment-queue`（`gpu: remote` で SSH 先を使う）、予算と後片付けは `rl gpu` が受け持つ。

## 最初に 1 回だけ（人がやる）

```bash
uv tool install "skypilot[runpod,lambda]"
# RunPod: https://www.runpod.io/console/user/settings で API キーを作り
runpod config                      # キーを貼る（~/.runpod/config.toml）
# Lambda: https://cloud.lambda.ai/api-keys でキーを作り
mkdir -p ~/.lambda_cloud && echo "api_key = <KEY>" > ~/.lambda_cloud/lambda_keys
sky check runpod lambda            # 両方 enabled になれば OK
```

キーはエージェントに貼らない。`rl doctor --clouds` で状態を確認できる。

## 使い方

```bash
# 1. 費用を見積もる（plan.md の表に書く。G2 で人が承認する）
sky launch --dryrun templates/sky/train.yaml     # 候補の GPU と時間単価が出る
sky show-gpus A100-80GB --infra runpod             # GPU ごとの単価

# 2. 立てる（G2 の承認・1 回の上限時間・残り予算を確認してから sky launch する）
rl gpu up <project> configs/sky/train.yaml --hours 4 --usd-per-hour 1.89

# 3. 実行する（ARIS）: CLAUDE.md の「Remote Server」に rl gpu up が表示したクラスタ名を書き、
#    /run-experiment か /experiment-queue。ログは sky logs <cluster>

# 4. 結果を取る → runs/<run_id>/ に保存（ckpt は大きいので必要なものだけ）
rsync -avz <cluster>:~/sky_workdir/outputs/<run>/ runs/<run_id>/

# 5. 消す（費用を台帳に足す）
rl gpu down <project> <cluster>
```

## 消し忘れを防ぐ 3 重の仕組み

1. **実行コマンドを `timeout ${MAX_HOURS}h` で包む**（`templates/sky/train.yaml`）。上限時間で学習が止まる
2. **アイドルになったら自動削除**：`rl gpu up` は `sky launch --down -i <分>` で立てる。学習が終わって指定の分数アイドルが続くと消える
3. **`rl gpu reap`**：記録した上限時間を過ぎたクラスタを消す。夜間ループが毎回呼ぶ。手で `rl gpu status` も確認できる

さらに、作業の最後には必ず `rl gpu status` を見て、残っているものを消す。

## 予算の決まり

- `research.yaml` の `budget.gpu_usd`（G2 で人が決める上限）から、使った分（`gpu_usd_spent`）と稼働中の見積もりを引いた残りを超える `rl gpu up` は拒否される
- 予算の 80% を超えそうなときは、夜間ループは止まって人に確認する
- 費用は「単価 × 稼働時間」の概算。正確な請求は RunPod・Lambda の管理画面で確かめる（月に 1 回、`notes/cost.md` に照合結果を書く）
- スポット（中断ありの安い GPU）を使うときは、チェックポイントを 30 分ごとにクラウドのストレージかローカルに保存する設計にしてから

## GPU の選び方の目安

| 用途 | 目安 |
|---|---|
| 小さなモデルの学習・デバッグ | RTX 4090 / A6000（24〜48GB） |
| 7B 前後の LoRA・VLA の微調整（openpi・OpenVLA） | A100-80GB 1 枚 |
| 7B 前後のフル微調整・大きめの学習 | H100 / A100 を 4〜8 枚（Orchestra `08-distributed-training`） |
| 推論・評価だけ | 安い GPU で vLLM（Orchestra `12-inference-serving/vllm`） |
| Isaac Sim / Isaac Lab | RTX 系（レイトレーシング用の RT コアが要る。A100 / H100 では描画が動かない） |
| π0・π0.5 の LoRA（openpi） | RTX 4090（22.5 GB 以上）。全体の微調整は A100-80GB / H100 |
| Cosmos Policy の学習 | 80 GB ×8 以上（論文は H100 ×8〜64 で 48 時間）。推論は 10 GB 以上の 1 枚 |

最初は必ず小さく（短い時間・少ないデータ）で動作確認してから本番を立てる。

## 道具の導入（rl sim）

- SkyPilot は `rl sim setup skypilot --project <name>` で入れる（版がプロジェクトの `sims.lock.yaml` に残る）。RunPod・Lambda のアカウントと支払いの設定は人の作業
- タスク定義のひな形は `templates/sky/`：Isaac Lab・Isaac Gym・ManiSkill・Genesis・MJX・MuJoCo Warp、方策の openpi（Ubuntu 22.04 の Docker イメージ）・OpenVLA-OFT・Cosmos Policy。`rl sim setup <tool>` でプロジェクトの `configs/sky/` に写し、`rl gpu up <project> configs/sky/<tool>.yaml --hours H --usd-per-hour X` で立てる。リポジトリは catalog の commit で固定してある
- 重みの取得に HF の同意が要るもの（Cosmos-Predict2 など）は、人が HF で同意してから、トークンを `sky launch --secret HF_TOKEN` で渡す（ファイルに書かない）
- GPU の要らない重い処理（テスト・前処理）は、先に dev-worker（`rl sim run --worker`）で回せないか考える。費用がかからない
