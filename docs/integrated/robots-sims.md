# ロボットのデータの共有キャッシュ（rl robot）と rl sim の追加 — 取り込みの提案

プロジェクトごとに置いていたロボットの公開データ（CAD・手順書・部品表）を共有のキャッシュに集め、版と sha256 で管理する `rl robot` を足した。`rl sim` には Drake・MJX・MuJoCo Warp・方策（LeRobot・openpi・OpenVLA-OFT・Cosmos Policy）、dev-worker への導入、Colab のノートブックを足した。README・SKILL.md・ledger.md・テンプレートは触っていない。取り込むときの差分を最後に書く。

## 作ったもの

| ファイル | 中身 |
|---|---|
| `robots/catalog.yaml` | 10 機種の取得元（commit・タグ・取得の方法）・ライセンス（ハード・文書・ソフト・他社の部品）・中身・登録が要るもの・派生物と作ったスクリプト。データは書かない |
| `robots/sums/<robot>/<version>.txt` | 取得したファイルの一覧と sha256 の控え（公開リポジトリのファイル名とハッシュだけ、計 150 KB）。次の取得はこの分だけを取り、照合する。**指示の範囲（catalog.yaml だけ）を少し超えた**。不要なら消してよい（fetch は include の指定で動く。照合が主なファイルだけになる） |
| `lib/rlkit/robots.py` | キャッシュ・控え・取得（git の sparse checkout・Git LFS・リリースの添付・zip・Web の保存）・リンク・ロック・確認・移行 |
| `bin/rl-robot` | `rl robot list / show / fetch / link / check / migrate` |
| `bin/rl` の sim の節 | 別の Python の道具（`python:`）、`--worker`、`rl sim run`、`rl sim colab`、Drake・LeRobot の動作確認 |
| `sims/catalog.yaml` | drake・mjx・mujoco-warp・lerobot・openpi・openvla-oft・cosmos-policy を追加 |
| `templates/sky/` | mjx・mujoco-warp・openpi・openvla-oft・cosmos-policy（SkyPilot 0.14.2 の `Task.from_yaml` で読めることを確認） |
| `tests/robots/` | pytest 15 件（一時フォルダのキャッシュ・file:// の git と URL でネットに出ずに確かめる。rl sim の追加分 5 件） |

テスト：`uv run --with pytest --with ruamel.yaml pytest tests/robots -q`

`templates/colab/` は作っていない。ノートブックは `sims.lock.yaml` から毎回組み立てる（`bin/rl` の `colab_notebook`）ので、固定のひな形が要らなかった。

## rl robot

```
~/research-lab/.cache/robots/<robot>/<version>/raw/...                 取得したそのまま（git の管理外）
                                              raw/SHA256SUMS.txt       raw の全ファイル（_derived/ と .git/ は除く）
                                              derived/<pipeline>@<pv>/ 派生物（SHA256SUMS.txt と PIPELINE.yaml＝入力・道具・スクリプトの sha256）
<project>/data/raw/<robot> → 上の raw（シンボリックリンク。開発用は data/raw/dev/<robot>）
<project>/robots.lock.yaml   版・SHA256SUMS.txt の sha256・使った派生物
```

| コマンド | すること |
|---|---|
| `rl robot list` / `show <robot>` | 一覧とキャッシュにあるもの / 1 機種の詳細 |
| `rl robot fetch <robot..> [--force]` | 一覧のとおりに取得し、sha256 を確かめる。あれば何もしない。ログイン・登録・メールが要るものは取らない（`gated:` に書くだけ） |
| `rl robot link <robot..> --project P` | リンクを張り、`robots.lock.yaml` に書く。実体のフォルダがあれば拒否 |
| `rl robot check [--project P] [--quick]` | リンクの行き先・ロックとの一致・全ファイルの sha256・派生物 |
| `rl robot migrate --project P [--apply]` | 既定は下見。既存の SHA256SUMS.txt を確かめ → 全ファイルの控えを作り → キャッシュへ移し → 移した先で確かめ → リンク。合わなければ移さない。キャッシュに同じ中身があれば、確かめてから手元の写しを消す |

- 派生物：`raw/_derived/<名前>` は `derived/<名前>@<版>/` に移し、元の場所に相対リンクを残した（ノートやスクリプトに書いたパスがそのまま使える）
- T20 の前処理の出力（`data/derived/dev/*`）は**プロジェクトに残した**。設定が「本番の前に凍結する」段階で、まだ他のプロジェクトで使い回す形ではないため。一覧には `location: project` の派生物として載せ、`robots.lock.yaml` に各 `manifest.json` の sha256 を残した。凍結したら `derived/l0_preprocess@<版>/` へ移すのがよい
- 取得のときに手元で作ったファイル（ToddlerBot の `v1.0.0/SHA256SUMS.txt` と `_local.urdf`、Poppy の `tree.json`、ORCA の `base_left_tree.json`）は `local_files` として一覧に書いた。取り直せないが、控えには入っている

## 移行の報告（robot-assembly-bench、2026-11-10）

`rl robot migrate --project robot-assembly-bench --apply`。同じディスクなので rename（4 秒）。8 機種とも、既存の控えが一致してから移した。

| 機種 | 版 | 大きさ（_derived 込み） | raw のファイル | 控えに足した | 派生物（キャッシュへ） |
|---|---|---|---|---|---|
| roboto_origin | e60f6745 | 682 MB | 288 | 98（SolidWorks 74、URDF の STL 24） | sw_asm・urdf_zero・part_stl・register・text |
| asimov_v1 | 43aa368a | 513 MB | 101 | 0 | text |
| openarm | 1.0.1 | 228 MB | 313 | 0 | — |
| xlerobot | b017b5e6 | 304 MB | 87 | 0 | text |
| toddlerbot | e337f3b1 | 198 MB | 85 | 30（v1.0.0 の描写 29、ほか 1） | urdf_zero・v1_assemblies_zero |
| poppy_humanoid | 1.0.2 | 178 MB | 2 | 0 | — |
| orca_v2 | 0ce26465 | 122 MB | 4 | 1（zip の __MACOSX） | — |
| amazing_hand | 3e824107 | 3.3 MB | 1 | 0 | — |
| 計 | | 2.2 GB | | | |

- リンク 8 本（`data/raw/{asimov_v1,openarm,roboto_origin,xlerobot}`、`data/raw/dev/{toddlerbot,poppy_humanoid,orca_v2,amazing_hand}`）。既存の控えが一部だったもの（roboto・toddlerbot・orca）は元の控えを `SHA256SUMS.orig.txt` として残した
- ほかに so101（a758567c、18 ファイル 27 MB）を `rl robot fetch so101` で取得した。lekiwi は一覧だけ（未取得）
- 移したあとの確認：`rl robot check --project robot-assembly-bench` 全部 ✓、`rl robot check`（キャッシュ全体）全部 ✓、プロジェクトの `uv run pytest -q` **25 passed**、`rl sim check` 全部 ✓（drake を足したあとも ✓）。`data/derived/dev/orca_v2/full_cut/manifest.json` に書かれた STEP の絶対パスもリンク経由で開ける
- **取得の手順の検証**：一時キャッシュに取り直して控えと突き合わせた。openarm 313/313、xlerobot 87/87、roboto_origin 288/288、toddlerbot・orca_v2・amazing_hand・poppy_humanoid は local_files を除いて一致、asimov_v1 は全体の STEP（Git LFS、520 MB、oid と一致）だけ一致。Asimov の手順書の HTML 100 枚は Web の保存なので取り直せない（`snapshot`）

## rl sim の追加

### 一覧に足した道具

| 道具 | 種類 | 版 | ライセンス（コード） | 重み・注意 |
|---|---|---|---|---|
| drake | py（手元） | drake 1.58.0 | BSD-3-Clause（PyPI の分類は BSD と Other/Proprietary） | macOS arm64 の 1.58 の wheel は cp312・macOS 26 以降だけ。プロジェクトの .venv（3.11）とは別の venv `.cache/venvs/drake`（Python 3.12.13）に入れた。箱を落とす MultibodyPlant の確認つき |
| mjx | remote（CUDA） | mujoco-mjx 4.0.0 | Apache-2.0 | `jax[cuda12]`。CPU の JAX なら Mac でも動く（遅い） |
| mujoco-warp | remote（CUDA） | mujoco-warp 4.0.0、commit 4d1c64bc | Apache-2.0（warp-lang も Apache-2.0） | |
| lerobot | py（手元） | lerobot 0.7.x（Python 3.12 以上） | Apache-2.0 | macOS arm64 に入ることを確認（0.7.0、torch 2.15.0、MPS が使える、ACT の設定を読める）。重み：SmolVLA は Apache-2.0、π0・π0.5（lerobot/pi0_base・pi05_base）は Gemma の利用条件。プロジェクトには入れていない |
| openpi | remote（CUDA） | commit 215abfb2（2026-08-24） | Apache-2.0 | 重み（gs://openpi-assets、ログイン不要）は PaliGemma 由来で Gemma Terms of Use（LICENSE_GEMMA.txt）。Ubuntu 22.04 だけ。推論・LoRA は RTX 4090、全体の微調整は A100-80GB / H100 |
| openvla-oft | remote（CUDA） | commit e4287e94（2025-09-09） | MIT | 重み（openvla/openvla-7b・moojink/openvla-7b-oft-*）は HF のタグが MIT。土台の Llama 2 7B の条件は未確認。手順は SETUP.md（Python 3.10・flash-attn 2.5.5） |
| cosmos-policy | remote（CUDA） | commit 18a2acca（2026-01-23） | Apache-2.0 | **公開のリポジトリがある**（NVlabs/cosmos-policy）。重み（nvidia/Cosmos-Policy-*）は NVIDIA One-Way Noncommercial License（非商用）。土台の Cosmos-Predict2-2B は HF で同意が要る（gated）→ 人の作業。学習は 80 GB ×8 以上 |

`rl sim setup drake --project robot-assembly-bench` を実行し、`sims.lock.yaml` に `venv: .cache/venvs/drake`・`python: 3.12.13` 付きで記録した。`.cache/venvs/` は uv が作る `.gitignore` で git の対象外、offload の同期の対象外（`.cache`）。

### dev-worker（`--worker`）

- `rl sim setup <tool..> --project P --worker`：手元の `sims.lock.yaml` の版を `==` で固定して、Worker のプロジェクトのミラー（`~/offload/robot-assembly-bench--42bd1c96`）に入れる。Python も手元と同じ版（3.11.15）を uv で入れる。git の道具はミラーの `.cache/sims/<名前>/<commit>`。cli と remote は入れない。結果は `sims.lock.yaml` の `worker:` に書く
- `rl sim check --worker`：Worker の版が記録と手元の両方に合うか、動作の確認（手元と同じ SMOKE）
- `rl sim run --project P [--worker] [--tool T] -- <cmd>`：プロジェクトの .venv（`--tool` ならその道具の venv）で実行。`--worker` は `offload run` で。スクリプトは base64 で渡す（offload の引数の読み替えと引用符を避ける）
- 試した：`rl sim setup mujoco menagerie --worker`（34 秒）、`rl sim check --worker`（mujoco 4.0.0、箱の高さ 0.0499、menagerie 98a70c56）、`rl sim run --worker -- python -c …`（Worker で UR5e を読み込み 1000 ステップ）
- Worker に uv が無かったので、`~/.local/share/rl/uv` に手元と同じ uv 0.11.7 を入れる手順を組み込んだ（Homebrew は触らない）

### Colab（`rl sim colab --project P [tools..]`）

`P/notebooks/colab_setup.ipynb` を書く。先頭の markdown に「試し用。ここで得た結果は論文に使わない（記録は rl run で）」。`pip install` は lock の版を `==` で、モデル集は lock の commit で `git fetch --depth 1`、版の照合のセル、動作の確認のセル。remote・cli の道具は「入れないもの」として書くだけ。保存のたびに `uv run --with nbformat` で検証する。robot-assembly-bench で作成済み（8 セル、検証済み）。

## 気づいたこと・人に確かめたいこと

1. **offload の不具合**：`~/.offload/projects/<名前>.conf` が無いプロジェクトでは、`resolve_project` の最後の `[ -f conf ] && . conf` が 1 を返し、`set -e` で `offload run` が何も言わずに終了 1 になる。回避に `~/.offload/projects/robot-assembly-bench.conf`（説明のコメントと `EXTRA_EXCLUDES=''` だけ）を作った。offload 本体は直していない（直すなら `[ -f … ] && . … || true`）
2. **Worker ではデータのリンクが切れる**：`data/raw/*` は手元の絶対パスへのリンクなので、Worker のミラーでは行き先が無い（以前は 2 GB 余りが毎回同期の対象だった）。データを読む処理を Worker で走らせるなら、Worker で `rl robot fetch`（キャッシュの場所を合わせる）か、`rl sim run --worker` でデータを使わないものに限る
3. **robots/sums/ を足した**（上の表）。公開してよい情報（公開リポジトリのパスとハッシュ）だけだが、指示の範囲外なので確認してほしい
4. Asimov の BOM（メール登録）、Onshape、MakerWorld、tnkr.ai、Cosmos-Predict2（HF の同意）は自動では取らない。取るかは人が決める
5. `robots.lock.yaml` はプロジェクトの git では未追跡。追跡するかはプロジェクトの判断（中身は版とハッシュと手元のパス）

## 取り込むときの差分

### README.md

コマンドの表の `rl sim` の行を置き換え、`rl robot` の行を足す：

```markdown
| `rl sim list / setup <tool..> / check / launch <tool> [--model M] [--dry-run]` | シミュレーターと道具（`sims/catalog.yaml`：MuJoCo・モデル集・Drake・干渉の判定・STEP の読み込み・ASAP・Fabrica・LeRobot・SkyPilot、借りた GPU で動かす Isaac Lab・Isaac Gym・ManiSkill・Genesis・MJX・MuJoCo Warp・openpi・OpenVLA-OFT・Cosmos Policy）をプロジェクトに入れ、版を `sims.lock.yaml` に残し、動作を確かめ、起動する。Python の版が合わない道具（Drake 1.58 は 3.12）は別の venv に入れる |
| `rl sim setup/check --worker`・`rl sim run [--worker] [--tool T] -- <cmd>`・`rl sim colab [tool..]` | 同じ版を dev-worker（offload）に入れて確かめる・プロジェクトの venv で手元か Worker で実行する・同じ版を入れる Colab のノートブック（試し用。結果は論文に使わない）を書く |
| `rl robot list / fetch <robot> / link <robot> --project P / check / migrate --project P [--apply]` | ロボットの公開データ（CAD・手順書・部品表。`robots/catalog.yaml`）を共有のキャッシュ（`.cache/robots/`）に版と sha256 つきで取り、プロジェクトからリンクで使う。版は `robots.lock.yaml` に残る。ログイン・登録が要るものは取らない |
```

構成の図に足す：

```
robots/catalog.yaml        ロボットの公開データの一覧（取得元・版・ライセンス・派生物。rl robot が読む。データは入れない）
robots/sums/               取得したファイルの一覧と sha256 の控え
lib/rlkit/                 追加コマンドと研究コードが共有する部品（robots.py など）
.cache/robots/             ロボットのデータの共有キャッシュ（<robot>/<version>/{raw,derived}。git の管理外・公開しない）
```

`bin/rl` の先頭の使い方の文（docstring）の `rl sim` の行の下に、次の 1 行を足す（sim の節の外なので触っていない）：

```
  rl sim setup/check --worker / run [--worker] [--tool T] -- <cmd> / colab [tool..]   dev-worker に同じ版を入れる・そこで実行する・Colab のノートブックを書く
```

### skills/research-lab/SKILL.md

「プロジェクトの作り方と構成」のコマンドの `rl sim check` の行の下に足す：

```bash
rl robot fetch openarm && rl robot link openarm --project <name>   # ロボットの公開データを共有キャッシュから使う（版は robots.lock.yaml）
rl robot check --project <name>     # リンクと sha256 を確かめる
```

構成の図の `runs/<run_id>/` の下に足す：

```
  data/raw/<robot>  # ~/research-lab/.cache/robots/<robot>/<version>/raw へのリンク（rl robot link）。実体をプロジェクトに置かない
  robots.lock.yaml  # 使ったロボットのデータの版と sha256
  sims.lock.yaml    # 入れた道具の版（手元と worker:）
```

### skills/physical-ai-research/SKILL.md

「手元の資産」の表のあとに節を足す：

```markdown
## ロボットの公開データ（rl robot）

他のロボットの CAD・手順書・部品表は `~/research-lab/robots/catalog.yaml` に一覧がある（取得元の commit・ライセンス・登録が要るもの・派生物）。プロジェクトに直接ダウンロードせず、`rl robot fetch <robot>` で共有のキャッシュに取り、`rl robot link <robot> --project <name>` でリンクして使う。版と sha256 は `robots.lock.yaml` に残る。

- 一覧に無い機種を足すときは catalog.yaml に 1 項目（取得元の commit かタグ・取得の方法・ハード／文書／ソフトのライセンス・他社の部品の除外・登録が要るもの）。ログイン・メール登録・同意のクリックが要るものは `gated:` に書くだけで、自動で取らない
- 既にプロジェクトに置いてしまったデータは `rl robot migrate --project <name>`（下見）→ `--apply`
- 派生物（STEP からのメッシュなど）は、作ったスクリプトと版を catalog の `derived:` に書く。他社の部品モデル（モータ・ねじ・電池）は再配布しない
- データは公開しない（research-lab は公開リポジトリ。キャッシュは git の管理外）
```

「シミュレーターと道具を入れる（rl sim）」の箇条を次に置き換える：

```markdown
- 手元（Mac）で動く：`mujoco`、`menagerie`（モデル集）、`drake`（MultibodyPlant。Python 3.12 の別の venv）、`lerobot`（ACT・SmolVLA。Python 3.12 の別の venv、MPS で小さく学習）、`geom`（trimesh・fcl）、`cad`（OCP）、`asap`、`fabrica`（計画部）
- 借りた GPU で動かす：`isaaclab`・`isaacgym`（RTX 系）、`maniskill`・`genesis`・`mjx`・`mujoco-warp`（CUDA）、方策の `openpi`（π0・π0.5）・`openvla-oft`・`cosmos-policy`。`rl sim setup` は `configs/sky/<tool>.yaml` を置くだけで、立てるのは G2 の承認のあとの `rl gpu up`
- **重みのライセンスはコードと別**：π0・π0.5 は Gemma の利用条件、Cosmos Policy は NVIDIA の非商用、OpenVLA は MIT（土台の Llama 2 の条件は別に確認）、SmolVLA は Apache-2.0。論文・公開物に使う前に確かめる
- dev-worker（2 台目の Mac。GPU なし）で回すとき：`rl sim setup <tool> --project <name> --worker` で同じ版を入れ、`rl sim run --project <name> --worker -- <cmd>`。確かめるのは `rl sim check --worker`
- Colab で試すとき：`rl sim colab --project <name>` で同じ版を入れるノートブックを作る。**Colab の結果は試し用で、論文に使わない**（記録は `rl run` で）
- 確かめる：`rl sim check`（版の食い違いと、簡単な動作の確認）
- 起動する：`rl sim launch mujoco --model universal_robots_ur5e`（`--dry-run` で読み込めるかだけ確かめる）
- 一覧に無い道具を足すときは `sims/catalog.yaml` に 1 項目足す（版の範囲・ライセンス・動く計算機・確認の手順。Python の版の制約は `python:`）
```

### skills/gpu-cloud/SKILL.md

「道具の導入（rl sim）」の 2 つ目の箇条を置き換える：

```markdown
- タスク定義のひな形は `templates/sky/`：Isaac Lab・Isaac Gym・ManiSkill・Genesis・MJX・MuJoCo Warp、方策の openpi（Ubuntu 22.04 の Docker イメージ）・OpenVLA-OFT・Cosmos Policy。`rl sim setup <tool>` でプロジェクトの `configs/sky/` に写し、`rl gpu up <project> configs/sky/<tool>.yaml --hours H --usd-per-hour X` で立てる。リポジトリは catalog の commit で固定してある
- 重みの取得に HF の同意が要るもの（Cosmos-Predict2 など）は、人が HF で同意してから、トークンを `sky launch --secret HF_TOKEN` で渡す（ファイルに書かない）
- GPU の要らない重い処理（テスト・前処理）は、先に dev-worker（`rl sim run --worker`）で回せないか考える。費用がかからない
```

「GPU の選び方の目安」の表に行を足す：

```markdown
| π0・π0.5 の LoRA（openpi） | RTX 4090（22.5 GB 以上）。全体の微調整は A100-80GB / H100 |
| Cosmos Policy の学習 | 80 GB ×8 以上（論文は H100 ×8〜64 で 48 時間）。推論は 10 GB 以上の 1 枚 |
```
