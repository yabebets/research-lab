---
name: physical-ai-research
description: フィジカル AI・ロボティクス研究（模倣学習・VLA・強化学習・sim2real・操作・移動）を進めるスキル。LeRobot と SO-ARM101、MuJoCo / ManiSkill / Isaac Lab / LIBERO などのシミュレータとベンチマーク、方策（ACT・Diffusion Policy・SmolVLA・π0/openpi・OpenVLA-OFT・GR00T）の選び方、データ収録、実機評価のプロトコル（試行数・判定基準・順番）、実機の安全ルール、CoRL・RSS・ICRA・IROS 向けの書き方を扱う。トリガー例：「ロボットの研究テーマを考えて」「SO-101 で実験したい」「VLA を微調整したい」「sim2real」「実機評価の設計」「成功率を何回測ればいい？」。
---

# physical-ai-research — フィジカル AI・ロボティクス

`research-lab` の段階（S1〜S7）の中で、ロボティクスに特有の部分を受け持つ。統計は `ml-rigor`、GPU は `gpu-cloud`、アイデア出しは ARIS `idea-discovery-robot`、VLA の学習は Orchestra `18-multimodal/openpi` `openvla-oft` `cosmos-policy` も読む。

## 実機の安全ルール（最優先）

- **実機を動かすコマンドは、人がそばにいて、その場で「動かしてよい」と言ったときだけ実行する。** 夜間ループでは実機を動かさない（`rl night` は `lerobot-record` などを禁止している）。
- 初めて動かす方策・設定は、まずシミュレーションで、次に実機で速度・トルクを落として 1 回、人が非常停止できる状態で。
- 作業範囲に人の手や壊れ物がないこと、ケーブルが巻き込まれないことを毎回確認する。
- SO-ARM101 の既知の注意：グリッパーの過負荷で、モーター ID 6 が応答しなくなることがある。実験の前に、設定の `robot.health_check` でサーボを確認する（下の「手元の資産」）。

## 手元の資産

手元のロボットは `rl config robot` で確認する（設定の書式は `config.example.yaml`）。

| 設定 | 中身 |
|---|---|
| `robot.repo` | ドライバ・校正・道具を置いたリポジトリ。空ならロボットなし（シミュレーションだけで進める） |
| `robot.description` | 機種とソフトの版（例：SO-ARM101 のリーダー・フォロワー、LeRobot 0.5.x） |
| `robot.status_doc` | 最新の状況を書いたメモ（`robot.repo` からの相対パス）。データ・学習済み方策・評価の進み具合はここを読む |
| `robot.health_check` | 実験の前に `robot.repo` で実行するサーボの確認コマンド |
| `robot.sim_dir` | シミュレーション（環境・台本の専門家・データ収集・評価のスクリプト） |

研究プロジェクトのコードは `rl new` で作ったプロジェクトに置く。ロボットのドライバ・校正・道具は `robot.repo` を参照し、コピーしない。

## 研究の型と使う道具

| 型 | よくある問い | 道具 |
|---|---|---|
| 模倣学習（少数のデモ） | デモの数・質・多様性と成功率の関係、データの増やし方、観測（カメラ位置・解像度・触覚） | LeRobot の ACT・Diffusion Policy・SmolVLA、LeRobotDataset |
| VLA の微調整 | 汎用モデルを少ないデータで自分のロボットに合わせる、言語指示への汎化 | π0 / π0.5（openpi、LeRobot にも実装）、OpenVLA-OFT、GR00T N1、SmolVLA。Orchestra `18-multimodal/*` |
| 強化学習・sim2real | シミュレーションで学習して実機に移す、報酬設計、ドメインランダム化 | MuJoCo / MJX、ManiSkill3、Isaac Lab（RTX GPU 必須）、Genesis。RL の統計は `rl_stats.py iqm` |
| ベンチマーク研究 | 手法をシミュレーションの標準課題で比べる | LIBERO、RoboCasa、SimplerEnv、ManiSkill の課題、CALVIN |
| 世界モデル・データ生成 | 生成した映像・シミュレーションでデータを増やす | Cosmos（Orchestra `cosmos-policy`）、MimicGen 系 |

詳しい選び方と注意点は [references/stack.md](references/stack.md)。

## 実機評価のプロトコル（G2 で固定する）

詳しくは [references/real-robot-eval.md](references/real-robot-eval.md)。要点だけ：

1. **試行数は計算で決める**：`rl_stats.py trials <p1> <p2>`。成功率 60% と 80% の差を見分けるには、1 条件あたり約 80 回が要る。10 回の測定では Wilson の区間が ±25pt 前後になり（5/10 なら 24〜76%）、条件の比較には使えない（「動作確認」として報告する）。
2. **成功の判定基準を事前に文で書く**（例：「ブロックの底面の 50% 以上がトレイの内側にあり、腕が休止姿勢に戻った」）。
3. **初期配置を事前に決める**：物体の位置・向きの格子やランダムな表を作り、条件間で同じ配置を使う（ペアの比較になる）。
4. **条件の順番を交互かランダムにする**（A を全部やってから B、にしない。照明・電池・摩耗の影響が条件に混ざる）。
5. **全試行を録画し、失敗の内訳を分類する**（把持の失敗、落下、衝突、タイムアウト、認識の失敗）。
6. 可能なら、評価する人が条件を知らない状態で判定する。
7. 結果は `rl_stats.py wilson`（各条件）と `twoprop`（比較）で計算する。

## シミュレーションと実機の主張の分け方

- `claims.yaml` の `eval_type` を `sim_only` / `real_gt` で分ける。sim の結果だけで「実機で有効」と書かない。
- sim2real を主張するなら、sim での成績・実機での成績・その差（転移による落ち幅）を同じ表に並べる。
- シミュレーションの物理・見た目のパラメータ（摩擦、質量、カメラの内部・外部パラメータ、照明）を付録に書く。

## 論文の書き方（CoRL・RSS・ICRA・IROS・RA-L）

章ごとの書き方は Master-cai の `research-paper-writing`。ロボティクスで追加で必要なもの：

- ハードウェアの説明（ロボット・グリッパー・センサー・カメラの位置、写真つき）
- 課題の定義の図（初期配置の範囲、成功条件）
- 実機の試行数・成功率と信頼区間、失敗の内訳の表
- 動画（補足資料。成功と失敗の両方）
- 計算資源（学習の GPU 時間）と推論の速度（Hz）、遅延
- 限界（物体の種類・環境の範囲・安全面）

学会別の査読の観点は `venue-review`。
