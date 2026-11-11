"""実験の記録（runs/）から、ブログ仕立ての下書き（notes/blog/*.md）を作り、点検する。

数字の出どころは runs/<id>/metrics.json だけ。rl blog が作る「結果」の表がその写しで、
本文の数字はその表（か、引用・出典つきの箇所）にあるものだけを使う。
公開（Zenn・HF・SNS）は人が決める。ここは下書きまで。
"""
from __future__ import annotations

import datetime as dt
import json
import math
import os
import re
import secrets
import statistics
from pathlib import Path

from ruamel.yaml import YAML

from . import runs as R

RL = Path(__file__).resolve().parent.parent.parent
TEMPLATE = RL / "templates" / "blog" / "post.md"
IMG_EXT = {".png", ".gif", ".jpg", ".jpeg", ".webp", ".svg"}
BLOCKS = ("setup", "results", "repro")
DOMAIN_TOPICS = {"robotics": "robotics", "ml": "machinelearning", "cv": "computervision",
                 "nlp": "nlp", "systems": "systems"}
META_RE = re.compile(r"<!--\s*rl:blog\s+(\{.*?\})\s*-->", re.S)


def start_marker(name):
    return f"<!-- rl:blog:auto:{name}:start（rl blog が runs/ から作る。手で直さない） -->"


def end_marker(name):
    return f"<!-- rl:blog:auto:{name}:end -->"


BLOCK_RE = {n: re.compile(r"<!-- rl:blog:auto:" + n + r":start.*?-->\n?(.*?)<!-- rl:blog:auto:" + n + r":end -->", re.S)
            for n in BLOCKS}


# ---------------------------------------------------------------- 小物
def fmt(v) -> str:
    if isinstance(v, bool):
        return str(v).lower()
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        if math.isnan(v) or math.isinf(v):
            return str(v)
        return f"{v:.4g}"
    if v is None:
        return "-"
    s = json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else str(v)
    return s if len(s) <= 40 else s[:37] + "…"


def flat_metrics(m: dict) -> dict:
    out = {}
    for k, v in m.items():
        if k == "split":
            continue
        if isinstance(v, dict):
            for k2, v2 in v.items():
                if not isinstance(v2, (dict, list)):
                    out[f"{k}.{k2}"] = v2
        else:
            out[k] = v
    return out


def slugify(title: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    s = re.sub(r"-+", "-", s)[:50].strip("-")
    return s if len(s) >= 3 else f"post-{secrets.token_hex(3)}"


def rel(target: Path, start: Path) -> str:
    return Path(os.path.relpath(target, start)).as_posix()


def sanitize(s: str, proj: Path) -> str:
    """絶対パス（ユーザー名が出る）をプロジェクト相対・~ に置き換える。"""
    if not s:
        return s
    s = s.replace(str(proj.resolve()), ".").replace(str(proj), ".")
    return s.replace(str(Path.home()), "~")


def run_date(run_id: str) -> dt.date | None:
    m = re.match(r"run_(\d{8})_", run_id)
    if not m:
        return None
    try:
        return dt.datetime.strptime(m.group(1), "%Y%m%d").date()
    except ValueError:
        return None


def select_runs(proj: Path, runs_csv: str | None, since: str | None) -> list[str]:
    if runs_csv:
        out = []
        for ref in [x.strip() for x in runs_csv.split(",") if x.strip()]:
            d = R.find_run(proj, ref)
            if d is None:
                raise ValueError(f"run が見つかりません（または候補が複数）: {ref}")
            out.append(d.name)
        return out
    if since:
        day = dt.date.fromisoformat(since)
        return [d.name for d in R.run_dirs(proj)
                if (run_date(d.name) or dt.date.min) >= day and R.read_status(d) in ("done", "failed", "killed")]
    return []


def _run_info(proj: Path, rid: str) -> tuple[dict, dict | None]:
    d = proj / "runs" / rid
    m = R.read_metrics(d)
    return R.load_run_yaml(d), (m if isinstance(m, dict) else None)


# ---------------------------------------------------------------- 自動の節
def results_block(proj: Path, post_dir: Path, run_ids: list[str]) -> str:
    if not run_ids:
        return "TODO: 対象の run がありません。`rl blog refresh` の前に、本文の先頭の rl:blog のコメントに runs を足す\n"
    infos = [(rid, *_run_info(proj, rid)) for rid in run_ids]
    keys: list[str] = []
    for _, _, m in infos:
        for k in flat_metrics(m or {}):
            if k not in keys:
                keys.append(k)
    head = ["run", "状態", "split", "タスク", "seed", "印"] + keys
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for rid, rec, m in infos:
        fm = flat_metrics(m or {})
        link = f"[{rid}]({rel(proj / 'runs' / rid, post_dir)}/)"
        row = [link, R.read_status(proj / "runs" / rid), str((m or {}).get("split") or rec.get("split") or "-"),
               str(rec.get("task") or "-"), fmt(rec.get("seed")), ",".join(rec.get("tags") or []) or "-"]
        row += [fmt(fm[k]) if k in fm else "-" for k in keys]
        lines.append("| " + " | ".join(row) + " |")
    out = "\n".join(lines) + "\n"
    # 同じタスク・split・印の run が 2 つ以上あれば、平均 ± 標準偏差
    groups: dict[tuple, list[dict]] = {}
    for rid, rec, m in infos:
        if m is None or R.read_status(proj / "runs" / rid) != "done":
            continue
        g = (str(rec.get("task") or "-"), str(m.get("split") or rec.get("split") or "-"), ",".join(rec.get("tags") or []) or "-")
        groups.setdefault(g, []).append(flat_metrics(m))
    agg = [(g, ms) for g, ms in groups.items() if len(ms) >= 2]
    if agg:
        num_keys = [k for k in keys if any(isinstance(ms_k.get(k), (int, float)) and not isinstance(ms_k.get(k), bool)
                                           for _, ms in agg for ms_k in ms)]
        h2 = ["タスク", "split", "印", "n"] + num_keys
        out += "\n同じタスク・split・印の done の run の平均 ± 標準偏差（seed 間。信頼区間は `rl_stats.py ci` で）\n\n"
        out += "| " + " | ".join(h2) + " |\n|" + "---|" * len(h2) + "\n"
        for (task, split, tags), ms in agg:
            row = [task, split, tags, str(len(ms))]
            for k in num_keys:
                vals = [x[k] for x in ms if isinstance(x.get(k), (int, float)) and not isinstance(x.get(k), bool)]
                if len(vals) >= 2:
                    row.append(f"{fmt(float(statistics.mean(vals)))} ± {fmt(float(statistics.stdev(vals)))}")
                elif vals:
                    row.append(fmt(vals[0]))
                else:
                    row.append("-")
            out += "| " + " | ".join(row) + " |\n"
    failed = [rid for rid, _, _ in infos if R.read_status(proj / "runs" / rid) != "done"]
    if failed:
        out += f"\n失敗・中断した run も表に残している（{len(failed)} 件）。平均には入れていない。\n"
    return out


def _groups(proj: Path, run_ids: list[str], only_done: bool = False) -> list[tuple[dict, list[str]]]:
    """同じ設定（タスク・コマンド・commit・設定ファイル・split・印）の run をまとめる。seed だけ違う run は 1 つに。"""
    out: dict[tuple, tuple[dict, list[str]]] = {}
    for rid in run_ids:
        if only_done and R.read_status(proj / "runs" / rid) != "done":
            continue
        rec, _ = _run_info(proj, rid)
        g = rec.get("git") or {}
        key = (rec.get("task"), rec.get("command_str"), g.get("commit"), g.get("diff_sha256"), g.get("dirty"),
               (rec.get("config") or {}).get("sha256"), rec.get("split"), tuple(rec.get("tags") or []), rec.get("data_version"))
        out.setdefault(key, (rec, []))[1].append(rid)
    return list(out.values())


def _seeds(proj: Path, rids: list[str]) -> list:
    return [R.load_run_yaml(proj / "runs" / r).get("seed") for r in rids]


def setup_block(proj: Path, post_dir: Path, run_ids: list[str]) -> str:
    if not run_ids:
        return ""
    parts = []
    for rec, rids in _groups(proj, run_ids):
        g = rec.get("git") or {}
        host = rec.get("host") or {}
        seeds = [x for x in _seeds(proj, rids) if x is not None]
        commit = f"`{g['commit'][:10]}`" if g.get("commit") else "（commit なし）"
        bits = [f"- run: {', '.join(rids)}" + (f"（seed {', '.join(map(str, seeds))}）" if seeds else ""),
                f"- 目的: {rec.get('purpose') or '-'}（{rec.get('task') or '-'}、split {rec.get('split') or '-'}）",
                f"- commit: {commit}" + ("（commit していない変更あり）" if g.get("dirty") and g.get("commit") else ""),
                f"- 計算環境: {host.get('cpu') or '-'}" + (f" / GPU: {', '.join(host.get('gpu') or [])}" if host.get("gpu") else "")
                + f" / {(rec.get('compute') or {}).get('where') or 'local'}",
                "- 所要時間: " + ", ".join(R.fmt_elapsed(R.load_run_yaml(proj / "runs" / r).get("elapsed_sec")) for r in rids)]
        if rec.get("data_version"):
            bits.append(f"- データ: {rec['data_version']}")
        if (rec.get("locks") or {}).get("sims.lock.yaml"):
            bits.append(f"- シミュレーターの版: sims.lock.yaml（sha256 `{rec['locks']['sims.lock.yaml'][:12]}`）")
        cfg = rec.get("config") or {}
        if cfg.get("copy"):
            bits.append(f"- 設定: [{cfg['copy']}]({rel(proj / 'runs' / rids[0] / cfg['copy'], post_dir)})")
        cmd = sanitize(rec.get("command_str") or "", proj)
        block = "\n".join(bits) + "\n"
        if cmd:
            block += f"\n```bash\n{cmd}\n```\n"
        parts.append(block)
    return "\n".join(parts)


def find_figures(proj: Path, run_ids: list[str], extra: list[str] | None = None) -> list[tuple[str, Path]]:
    out = []
    for rid in run_ids:
        d = proj / "runs" / rid
        n = 0
        for p in sorted(d.rglob("*")):
            if p.suffix.lower() in IMG_EXT and p.is_file() and not ({"ckpt", "llm_requests", "llm_responses"} & set(p.relative_to(d).parts)) \
                    and len(p.relative_to(d).parts) <= 3:
                out.append((rid, p))
                n += 1
                if n >= 12:
                    break
    for f in extra or []:
        p = Path(f)
        p = p if p.is_absolute() else (proj / p if (proj / p).exists() else Path.cwd() / p)
        if p.is_file():
            out.append(("", p.resolve()))
    return out


def figures_section(proj: Path, post_dir: Path, run_ids: list[str], extra: list[str] | None = None) -> str:
    """図の節（新規作成のときだけ作る。説明文は書き手が直すので自動の枠にしない）。"""
    figs = find_figures(proj, run_ids, extra)
    if not figs:
        return "TODO: 図がまだない。run のフォルダに PNG・GIF を保存するか、`--figs` で指定して作り直す\n"
    out = []
    for rid, p in figs:
        label = f"{rid}/{p.name}" if rid else p.name
        out.append(f"![{label}]({rel(p, post_dir)})\n*図: TODO: 何を示す図か 1 行で（{label}）*\n")
    return "\n".join(out)


def repro_block(proj: Path, post_dir: Path, run_ids: list[str], project: str) -> str:
    if not run_ids:
        return ""
    lines, notes = ["```bash"], []
    for rec, rids in _groups(proj, run_ids, only_done=True):
        g = rec.get("git") or {}
        if g.get("commit"):
            lines.append(f"git checkout {g['commit'][:10]}")
        seeds = [x for x in _seeds(proj, rids) if x is not None]
        opts = [f"--task {rec.get('task')}", f"--purpose \"再現: {rids[0]}\"", f"--split {rec.get('split') or 'dev'}"]
        for t in rec.get("tags") or []:
            opts.append(f"--tag {t}")
        cfg = rec.get("config") or {}
        if cfg.get("copy"):
            opts.append(f"--config runs/{rids[0]}/{cfg['copy']}")
        cmd = sanitize(rec.get("command_str") or "<command>", proj)
        if len(seeds) > 1:
            lines.append(f"for s in {' '.join(map(str, seeds))}; do")
            lines.append(f"  rl run exec {project} {' '.join(opts)} --seed $s -- {cmd}")
            lines.append("done")
        else:
            if seeds:
                opts.append(f"--seed {seeds[0]}")
            lines.append(f"rl run exec {project} {' '.join(opts)} -- {cmd}")
        if not g.get("commit"):
            notes.append(f"- {', '.join(rids)} は git の commit がない状態で回した。同じ結果になるかはコードの版しだい")
        elif g.get("dirty"):
            notes.append(f"- {', '.join(rids)} は commit していない変更がある状態で回した（git diff の sha256 "
                         f"`{(g.get('diff_sha256') or '-')[:12]}`）。同じ結果にはその差分が要る")
    lines.append("```")
    out = "\n".join(lines) + "\n"
    if notes:
        out += "\n" + "\n".join(notes) + "\n"
    out += "\n記録（設定・ログ・指標）は各 run のフォルダ（`runs/<run_id>/`）にある。\n"
    return out


def wrap(name: str, body: str) -> str:
    return f"{start_marker(name)}\n{body.rstrip()}\n{end_marker(name)}"


def render_blocks(proj: Path, post_dir: Path, meta: dict) -> dict:
    rids = meta.get("runs") or []
    return {
        "setup": wrap("setup", setup_block(proj, post_dir, rids)),
        "results": wrap("results", results_block(proj, post_dir, rids)),
        "repro": wrap("repro", repro_block(proj, post_dir, rids, meta.get("project") or proj.name)),
    }


# ---------------------------------------------------------------- 新規・更新
def front_matter(title: str, date: str, project: str, run_ids, zenn: bool, emoji: str, topics: list[str]) -> str:
    t = json.dumps(title, ensure_ascii=False)
    if zenn:
        tp = ", ".join(json.dumps(x) for x in topics[:5])
        return f'---\ntitle: {t}\nemoji: "{emoji}"\ntype: "tech"\ntopics: [{tp}]\npublished: false\n---\n'
    return f"---\ntitle: {t}\ndate: {date}\nproject: {project}\nruns: [{', '.join(run_ids)}]\npublished: false\n---\n"


def new_post(proj: Path, led, *, title: str, run_ids: list[str], zenn: bool = False, slug: str | None = None,
             emoji: str = "🧪", topics: list[str] | None = None, figs: list[str] | None = None,
             date: str | None = None, force: bool = False) -> Path:
    date = date or dt.date.today().isoformat()
    slug = slug or slugify(title)
    if zenn and not re.fullmatch(r"[a-z0-9_-]{12,50}", slug):
        raise ValueError(f"Zenn の slug は a-z0-9・-・_ の 12〜50 文字（{slug!r}）。--slug で指定")
    post_dir = proj / "notes" / "blog"
    post_dir.mkdir(parents=True, exist_ok=True)
    path = post_dir / f"{date}-{slug}.md"
    if path.exists() and not force:
        raise FileExistsError(f"すでにあります: {path}（上書きは --force、表の更新は rl blog refresh）")
    project = str(led.get("project") or proj.name)
    if not topics:
        topics = [DOMAIN_TOPICS.get(str(led.get("domain")), "research")]
        tags = {t for rid in run_ids for t in (R.load_run_yaml(proj / "runs" / rid).get("tags") or [])}
        if "sim" in tags:
            topics.append("simulation")
    meta = {"project": project, "runs": run_ids, "figs": list(figs or []), "slug": slug}
    blocks = render_blocks(proj, post_dir, meta)
    text = TEMPLATE.read_text()
    text = (text.replace("{{FRONT_MATTER}}", front_matter(title, date, project, run_ids, zenn, emoji, topics).rstrip())
                .replace("{{META}}", json.dumps(meta, ensure_ascii=False))
                .replace("{{SETUP}}", blocks["setup"]).replace("{{RESULTS}}", blocks["results"])
                .replace("{{FIGURES}}", figures_section(proj, post_dir, run_ids, figs)).replace("{{REPRO}}", blocks["repro"])
                .replace("{{TITLE}}", title).replace("{{DATE}}", date).replace("{{PROJECT}}", project))
    path.write_text(text)
    return path


def read_meta(text: str) -> dict | None:
    m = META_RE.search(text)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return None


def project_of(post: Path) -> Path | None:
    p = post.resolve().parent
    while p != p.parent:
        if (p / "research.yaml").exists():
            return p
        p = p.parent
    return None


def refresh(post: Path) -> list[str]:
    """自動の節を runs/ から作り直す。変わった節の名前を返す。"""
    text = post.read_text()
    meta = read_meta(text)
    proj = project_of(post)
    if meta is None or proj is None:
        raise ValueError("rl blog の下書きではありません（rl:blog のコメントか、プロジェクトが見つからない）")
    blocks = render_blocks(proj, post.resolve().parent, meta)
    changed = []
    for name, new in blocks.items():
        m = BLOCK_RE[name].search(text)
        if m is None:
            continue
        old = text[m.start():m.end()]
        if old != new:
            text = text[:m.start()] + new + text[m.end():]
            changed.append(name)
    post.write_text(text)
    return changed


# ---------------------------------------------------------------- 点検
_A = r"(?![A-Za-z])"   # ASCII の単位の後ろに英字が続かない（日本語は続いてよい）
UNITS = (r"%|％|ポイント|倍|回|秒|分|時間|エピソード|ステップ|エポック|試行|件|°|×|ドル|円|"
         r"(?:pt|ms|sec|min|Hz|fps|FPS|mm|cm|kg|Nm|deg|rad|GB|MB|USD|steps?|epochs?|s|h|m|g|N|x)" + _A)
NUM_UNIT = re.compile(r"(?<![A-Za-z0-9_.\-/])([-+]?\d[\d,]*(?:\.\d+)?)\s?(" + UNITS + r")")
DOLLAR = re.compile(r"(?<![A-Za-z0-9_.])\$\s?(\d[\d,]*(?:\.\d+)?)")
ANY_NUM = re.compile(r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?")
SIM_TERMS = re.compile(r"(?i)\b(sim|simulation|simulator|mujoco|isaac\s*(?:lab|gym|sim)?|maniskill|genesis|pybullet|gazebo)\b|シミュ|仮想環境")
PRIVATE = re.compile(r"(?i)\bNDA\b|秘密|非公開|社外秘|機密|confidential|[\w.+-]+@[\w-]+\.[a-z]{2,}(?:\.[a-z]{2,})?|/Users/[^/\s)]+|/home/[^/\s)]+")


def split_front_matter(text: str) -> tuple[dict, str, int]:
    if text.startswith("---\n"):
        end = text.find("\n---", 4)
        if end != -1:
            try:
                fm = YAML(typ="safe", pure=True).load(text[4:end]) or {}
            except Exception:  # noqa: BLE001
                fm = {"_invalid": True}
            body_start = text.find("\n", end + 4) + 1
            return fm, text[body_start:], text[:body_start].count("\n")
    return {}, text, 0


def _blank(m: re.Match) -> str:
    return "\n" * m.group(0).count("\n")


def _allowed_numbers(proj: Path | None, meta: dict | None, body: str) -> list[float]:
    vals = []
    for name in ("results", "setup"):
        m = BLOCK_RE[name].search(body)
        if m:
            txt = re.sub(r"\]\([^)]*\)", "]", m.group(1))       # リンク先の run_id の数字は除く
            txt = re.sub(r"\brun_\d{8}_\d{4}_[0-9a-f]+\b", "", txt)
            vals += [float(x) for x in ANY_NUM.findall(txt)]
    if proj and meta:
        for rid in meta.get("runs") or []:
            m = R.read_metrics(proj / "runs" / rid)
            if isinstance(m, dict):
                vals += [float(v) for v in flat_metrics(m).values() if isinstance(v, (int, float)) and not isinstance(v, bool)]
    return vals


def _traced(token: str, allowed: list[float]) -> bool:
    s = token.replace(",", "").lstrip("+")
    try:
        v = float(s)
    except ValueError:
        return True
    dec = len(s.split(".")[1]) if "." in s else 0
    loose = dec >= 1 or abs(v) >= 10      # 有効数字 2 桁以上なら丸めを認める
    for a in allowed:
        for c in (a, a * 100, a / 100):
            if c == v or (loose and round(c, dec) == v):
                return True
    return False


def check(post: Path) -> tuple[list[str], list[str]]:
    """(エラー, 警告)。"""
    errs, warns = [], []
    text = post.read_text()
    fm, body, offset = split_front_matter(text)
    if fm.get("_invalid"):
        errs.append("front matter が YAML として読めません")
    if fm.get("published") is True:
        errs.append("published: true になっています。公開は人が決める（下書きは published: false のまま）")
    meta = read_meta(text)
    proj = project_of(post)
    if meta is None:
        warns.append("rl:blog のコメントがありません（rl blog new で作った下書きではない）。結果の表との照合ができません")
    elif proj is not None:
        cur = render_blocks(proj, post.resolve().parent, meta)
        m = BLOCK_RE["results"].search(body)
        if m is None:
            errs.append("結果の表（rl:blog:auto:results）がありません。数字の出どころが runs/ だと示せません")
        elif body[m.start():m.end()] != cur["results"]:
            errs.append("結果の表が runs/ の metrics.json と一致しません（手で直した？ `rl blog refresh` で作り直す）")
        for name in ("setup", "repro"):
            mm = BLOCK_RE[name].search(body)
            if mm and body[mm.start():mm.end()] != cur[name]:
                warns.append(f"自動の節 {name} が runs/ と合っていません（`rl blog refresh`）")
        for rid in meta.get("runs") or []:
            if not (proj / "runs" / rid).is_dir():
                errs.append(f"対象の run がありません: {rid}")

    allowed = _allowed_numbers(proj, meta, body)
    # 点検しない部分を空行に置き換える（行番号は保つ）
    prose = body
    for name in BLOCKS:
        prose = BLOCK_RE[name].sub(_blank, prose)
    prose = re.sub(r"```.*?```", _blank, prose, flags=re.S)
    prose = re.sub(r"<!--.*?-->", _blank, prose, flags=re.S)

    todo = 0
    for i, line in enumerate(prose.split("\n"), start=offset + 1):
        raw = line
        if "TODO" in raw:
            todo += 1
        s = raw.strip()
        if s.startswith(">") or re.match(r"\[\^[^\]]+\]:", s):
            continue                                   # 引用・脚注の定義
        s = re.sub(r"`[^`]*`", "", s)                   # インラインコード
        s = re.sub(r"\]\([^)]*\)", "]", s)               # リンク・画像の行き先
        s = re.sub(r"https?://\S+", "", s)
        for sent in re.split(r"(?<=[。．！？])", s):
            if "[^" in sent or "出典" in sent:
                continue                               # 出典つきの文
            for mt in NUM_UNIT.finditer(sent):
                if not _traced(mt.group(1), allowed):
                    warns.append(f"{i} 行目: 「{mt.group(0)}」が結果の表にありません（表の数字を使うか、出典・引用にする）")
            for mt in DOLLAR.finditer(sent):
                if not _traced(mt.group(1), allowed):
                    warns.append(f"{i} 行目: 「{mt.group(0)}」が結果の表にありません")

    # シミュレーションの結果を、そうと書かずに出していないか
    tags = set()
    if proj and meta:
        for rid in meta.get("runs") or []:
            tags |= set(R.load_run_yaml(proj / "runs" / rid).get("tags") or [])
    # 自動の節・コード・コメント・TODO の行（雛形の例文）を除いた本文
    plain = "\n".join(ln for ln in prose.split("\n") if "TODO" not in ln) + "\n" + str(fm.get("title") or "")
    if ("sim" in tags or SIM_TERMS.search(plain)) and "シミュレーション" not in plain:
        warns.append("シミュレーションの結果を扱っているのに「シミュレーション」と書いていません（実機の結果と読まれないように）")
    if "sim" in tags and "real" not in tags and re.search(r"実機で", plain):
        warns.append("対象の run は sim の印だけなのに「実機で」と書いています")

    for i, line in enumerate(text.split("\n"), start=1):
        for mt in PRIVATE.finditer(line):
            warns.append(f"{i} 行目: 「{mt.group(0)}」— 非公開の情報・連絡先・手元のパスではないか確かめる")

    for mt in re.finditer(r"!\[[^\]]*\]\(([^)\s]+)\)", body):
        target = mt.group(1)
        if not re.match(r"https?://|/", target) and not (post.resolve().parent / target).exists():
            warns.append(f"画像が見つかりません: {target}")
    if proj:
        for rid in set(re.findall(r"\brun_\d{8}_\d{4}_[0-9a-f]{6}\b", plain)):
            if not (proj / "runs" / rid).is_dir():
                warns.append(f"本文の {rid} が runs/ にありません")
    if todo:
        warns.append(f"TODO が {todo} 箇所残っています")
    return errs, warns


def list_posts(proj: Path) -> list[dict]:
    out = []
    for p in sorted((proj / "notes" / "blog").glob("*.md")):
        text = p.read_text()
        fm, _, _ = split_front_matter(text)
        meta = read_meta(text) or {}
        out.append({"path": p, "title": fm.get("title") or p.stem, "published": fm.get("published"),
                    "zenn": "emoji" in fm, "runs": len(meta.get("runs") or []), "todo": text.count("TODO")})
    return out
