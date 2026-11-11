"""ロボットの公開データの共有キャッシュ（rl robot が使う）。

置き場所（git の管理外。データは公開リポジトリに入れない）:

    <cache>/<robot>/<version>/raw/...                    取得したそのままのファイル
    <cache>/<robot>/<version>/raw/SHA256SUMS.txt         raw の全ファイルの sha256（_derived/ と .git/ は除く）
    <cache>/<robot>/<version>/derived/<pipeline>@<pv>/   raw から作ったもの（SHA256SUMS.txt と PIPELINE.yaml つき）

<cache> は既定で ~/research-lab/.cache/robots。環境変数 RL_ROBOT_CACHE で差し替えられる（テスト用）。
一覧は robots/catalog.yaml（RL_ROBOT_CATALOG で差し替え）。取得したファイルの一覧と sha256 の控えは
robots/sums/<robot>/<version>.txt（公開リポジトリのファイル名とハッシュだけ。中身は入れない）。

プロジェクトからは P/<link_as>（既定 data/raw/<robot>）を raw へのシンボリックリンクにし、
P/robots.lock.yaml に版と SHA256SUMS の sha256 を残す。
"""
from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from ruamel.yaml import YAML

from .common import RL, dump, load, now

SUMS = "SHA256SUMS.txt"
LOCK = "robots.lock.yaml"
LFS_HEAD = b"version https://git-lfs.github.com/spec/v1"


# ---------------------------------------------------------------- 場所と一覧
def cache_root() -> Path:
    return Path(os.environ.get("RL_ROBOT_CACHE") or (RL / ".cache" / "robots")).expanduser()


def catalog_path() -> Path:
    return Path(os.environ.get("RL_ROBOT_CATALOG") or (RL / "robots" / "catalog.yaml")).expanduser()


def sums_dir() -> Path:
    return Path(os.environ.get("RL_ROBOT_SUMS") or (catalog_path().parent / "sums")).expanduser()


def load_catalog() -> dict:
    f = catalog_path()
    if not f.exists():
        raise SystemExit(f"rl: {f} がありません")
    with f.open() as fh:
        return (YAML(typ="safe").load(fh) or {}).get("robots") or {}


def version_dir(robot: str, version: str) -> Path:
    return cache_root() / robot / str(version)


def raw_dir(robot: str, version: str) -> Path:
    return version_dir(robot, version) / "raw"


def derived_dir(robot: str, version: str, pipeline: str, pv: str) -> Path:
    return version_dir(robot, version) / "derived" / f"{pipeline}@{pv}"


def link_as(robot: str, entry: dict) -> str:
    return entry.get("link_as") or f"data/raw/{robot}"


def manifest_file(robot: str, version: str) -> Path:
    return sums_dir() / robot / f"{version}.txt"


# ---------------------------------------------------------------- sha256 の控え
def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _skip(rel: Path) -> bool:
    parts = rel.parts
    return (".git" in parts) or (parts and parts[0] == "_derived") or (len(parts) == 1 and parts[0] in (SUMS, SUMS + ".tmp"))


def scan_files(root: Path) -> list[str]:
    """raw の中の控えの対象（_derived/・.git/・先頭の SHA256SUMS.txt を除く。シンボリックリンクは対象外）。"""
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        d = Path(dirpath)
        dirnames[:] = [n for n in dirnames if n != ".git" and not (d == root and n == "_derived")
                       and not (d / n).is_symlink()]
        for n in filenames:
            p = d / n
            rel = p.relative_to(root)
            if p.is_symlink() or _skip(rel):
                continue
            out.append(rel.as_posix())
    return sorted(out)


def read_sums(path: Path) -> dict[str, str]:
    out = {}
    if not Path(path).exists():
        return out
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        sha, _, rel = line.partition("  ")
        if not rel:
            sha, _, rel = line.partition(" *")
        rel = rel.lstrip("*")
        if rel.startswith("./"):
            rel = rel[2:]
        out[rel] = sha.strip().lower()
    return out


def write_sums(root: Path, sums: dict[str, str], name: str = SUMS) -> Path:
    f = Path(root) / name
    tmp = f.with_suffix(".tmp")
    tmp.write_text("".join(f"{sums[k]}  ./{k}\n" for k in sorted(sums)), encoding="utf-8")
    tmp.replace(f)
    return f


def make_sums(root: Path, log=None) -> dict[str, str]:
    files = scan_files(root)
    out = {}
    for i, rel in enumerate(files):
        out[rel] = sha256_file(root / rel)
        if log and i and i % 500 == 0:
            log(f"  … {i}/{len(files)}")
    return out


def verify_sums(root: Path, sums: dict[str, str], extra_ok: bool = True) -> list[str]:
    """問題の一覧（空なら一致）。extra_ok=False なら、控えに無いファイルも問題にする。"""
    probs = []
    for rel, sha in sorted(sums.items()):
        p = Path(root) / rel
        if not p.exists():
            probs.append(f"無い: {rel}")
        elif sha256_file(p) != sha:
            probs.append(f"sha256 が違う: {rel}")
    if not extra_ok:
        for rel in scan_files(Path(root)):
            if rel not in sums:
                probs.append(f"控えに無い: {rel}")
    return probs


def sums_digest(path: Path) -> str:
    return sha256_file(path) if Path(path).exists() else ""


def dir_size(root: Path) -> int:
    total = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [n for n in dirnames if not (Path(dirpath) / n).is_symlink()]
        for n in filenames:
            p = Path(dirpath) / n
            if not p.is_symlink():
                total += p.stat().st_size
    return total


def human(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return str(n)


# ---------------------------------------------------------------- 取得（fetch）
def _download(url: str, dest: Path, log=print) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": "research-lab-rl-robot"})
    with urllib.request.urlopen(req, timeout=120) as r, open(tmp, "wb") as f:
        shutil.copyfileobj(r, f, 1 << 20)
    tmp.replace(dest)


def _run(cmd, cwd=None, env=None, input=None):
    r = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, input=input)
    if r.returncode != 0:
        raise RuntimeError(f"{' '.join(map(str, cmd))}\n{r.stderr.strip()[-800:]}")
    return r.stdout


def _gh_owner_repo(repo: str) -> tuple[str, str]:
    s = repo.rstrip("/").removesuffix(".git")
    parts = s.split("github.com/")[-1].split("/")
    return parts[0], parts[1]


def _fetch_git(src: dict, stage: Path, keep: set[str] | None, log=print) -> list[str]:
    """commit を固定した sparse checkout。include は gitignore の書式（no-cone）。"""
    repo, commit = src["repo"], src["commit"]
    dest = src.get("dest", "")
    work = Path(tempfile.mkdtemp(prefix="rl-robot-git-", dir=stage.parent))
    try:
        env = dict(os.environ, GIT_LFS_SKIP_SMUDGE="1", GIT_TERMINAL_PROMPT="0")
        _run(["git", "init", "-q"], cwd=work)
        _run(["git", "remote", "add", "origin", repo], cwd=work)
        _run(["git", "config", "core.quotepath", "off"], cwd=work)
        _run(["git", "config", "core.precomposeunicode", "true"], cwd=work)
        _run(["git", "fetch", "-q", "--depth", "1", "--filter=blob:none", "origin", commit], cwd=work, env=env)
        inc = list(src.get("include") or [])
        if src.get("include_from_manifest") and keep is not None:
            # 控え（robots/sums/）にある分だけを取る。gitignore の書式なので特殊な文字は逃がす
            pre = (dest.rstrip("/") + "/") if dest else ""
            strip = src.get("strip") or ""
            inc = ["/" + _gitpat(strip + k[len(pre):]) for k in sorted(keep) if k.startswith(pre)]
        if inc:
            _run(["git", "sparse-checkout", "set", "--no-cone", "--stdin"], cwd=work, env=env, input="\n".join(inc) + "\n")
        _run(["git", "checkout", "-q", "FETCH_HEAD"], cwd=work, env=env)
        got = _run(["git", "rev-parse", "HEAD"], cwd=work).strip()
        if not got.startswith(commit[:7]):
            raise RuntimeError(f"commit が違う: {got} != {commit}")
        owner, name = _gh_owner_repo(repo)
        excl = src.get("exclude") or []
        strip = src.get("strip") or ""
        mapping = src.get("map") or {}
        written = []
        for rel in scan_files(work):
            if any(fnmatch.fnmatch(rel, pat) or fnmatch.fnmatch(Path(rel).name, pat) for pat in excl):
                continue
            if mapping:
                tgt = None
                for a, b in mapping.items():
                    if rel == a:
                        tgt = b
                    elif a.endswith("/") and rel.startswith(a):
                        tgt = b + rel[len(a):]
                if tgt is None:
                    continue
            elif src.get("flatten"):
                tgt = Path(rel).name
            else:
                tgt = rel[len(strip):] if strip and rel.startswith(strip) else rel
            out_rel = f"{dest.rstrip('/')}/{tgt}" if dest else tgt
            if keep is not None and out_rel not in keep:
                continue
            out = stage / out_rel
            out.parent.mkdir(parents=True, exist_ok=True)
            p = work / rel
            head = p.open("rb").read(len(LFS_HEAD))
            if head == LFS_HEAD and p.stat().st_size < 1024:
                meta = dict(l.split(" ", 1) for l in p.read_text().splitlines() if " " in l)
                oid = meta.get("oid", "").removeprefix("sha256:")
                url = f"https://media.githubusercontent.com/media/{owner}/{name}/{commit}/{rel}"
                log(f"  LFS: {rel}（{human(int(meta.get('size', 0)))}）")
                _download(urllib.request.quote(url, safe=":/"), out, log)
                if sha256_file(out) != oid:
                    raise RuntimeError(f"LFS の sha256 が oid と違う: {rel}")
            else:
                shutil.move(str(p), str(out))
            written.append(out_rel)
        return written
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _gitpat(path: str) -> str:
    out = []
    for ch in path:
        out.append("\\" + ch if ch in "\\[]*?!#" else ch)
    return "".join(out)


def _fetch_url(src: dict, stage: Path, log=print) -> list[str]:
    out = stage / src["dest"]
    log(f"  取得: {src['url']}")
    _download(src["url"], out, log)
    if src.get("sha256") and sha256_file(out) != src["sha256"]:
        raise RuntimeError(f"sha256 が違う: {src['dest']}（公開値 {src['sha256'][:12]}…）")
    return [src["dest"]]


def _fetch_unzip(src: dict, stage: Path, log=print) -> list[str]:
    zf = stage / src["from"]
    written = []
    with zipfile.ZipFile(zf) as z:
        for m in z.namelist():
            if m.endswith("/"):
                continue
            if src.get("members") and not any(fnmatch.fnmatch(m, pat) for pat in src["members"]):
                continue
            out_rel = f"{src.get('dest', '').rstrip('/')}/{m}".lstrip("/")
            out = stage / out_rel
            out.parent.mkdir(parents=True, exist_ok=True)
            with z.open(m) as fi, open(out, "wb") as fo:
                shutil.copyfileobj(fi, fo, 1 << 20)
            written.append(out_rel)
    return written


def fetch(robot: str, entry: dict, force: bool = False, log=print) -> Path:
    """一覧のとおりに取得して <cache>/<robot>/<version>/raw/ に置く。既にあれば何もしない（--force で取り直す）。"""
    if entry.get("pending"):
        # 公開待ち：データがまだ公開されていない機種は取りに行かない（一覧に載せて見張るだけ）
        log(f"= {robot}: 公開待ち（{entry['pending']}）。取りません")
        return None
    version = str(entry["version"])
    raw = raw_dir(robot, version)
    if (raw / SUMS).exists() and not force:
        log(f"= {robot} {version}: 取得済み（{raw}）")
        return raw
    man = read_sums(manifest_file(robot, version))
    keep = set(man) if man else None
    stage = version_dir(robot, version) / ".staging"
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)
    skipped = []
    for src in entry.get("sources") or []:
        m = src.get("method")
        log(f"- {robot}: {m} {src.get('repo') or src.get('url') or src.get('from') or ''}")
        if m == "git":
            _fetch_git(src, stage, keep, log)
        elif m == "url":
            _fetch_url(src, stage, log)
        elif m == "unzip":
            _fetch_unzip(src, stage, log)
        elif m in ("snapshot", "manual"):
            skipped.append(src)
            log(f"  自動では取れません（{src.get('note', '手の作業')}）")
        else:
            raise RuntimeError(f"method が不明: {m}")
    sums = make_sums(stage, log)
    if man:
        miss = sorted(k for k in set(man) - set(sums) if not any(fnmatch.fnmatch(k, pat) for pat in entry.get("local_files") or []))
        bad = [k for k in man if k in sums and sums[k] != man[k]]
        extra = sorted(set(sums) - set(man))
        for k in extra:
            (stage / k).unlink()
            sums.pop(k)
        if bad:
            raise RuntimeError(f"{robot}: 控え（{manifest_file(robot, version)}）と sha256 が違う {len(bad)} 件: {bad[:5]}")
        if miss:
            log(f"  ⚠ 控えにあって取れなかったもの {len(miss)} 件（例 {miss[:3]}）" + ("。スナップショット・手の作業の分" if skipped else ""))
    local = [k for k in (man or {}) if any(fnmatch.fnmatch(k, pat) for pat in entry.get("local_files") or [])]
    if local:
        log(f"  取得のときに手元で作ったファイル {len(local)} 件は取り直せません（local_files）: {local[:3]}")
    for rel, sha in (entry.get("verify") or {}).items():
        if rel in sums and sums[rel] != sha:
            raise RuntimeError(f"{robot}: {rel} の sha256 が一覧の値と違う")
    write_sums(stage, sums)
    mf = manifest_file(robot, version)
    if not man and not skipped:
        # 初めて取った版は、ファイルの一覧と sha256 を robots/sums/ に控える（次からはこの分だけを取り、照合する）
        mf.parent.mkdir(parents=True, exist_ok=True)
        write_sums(mf.parent, sums, name=mf.name)
        log(f"  控えを書きました: {mf}")
    if raw.exists():
        shutil.rmtree(raw)
    stage.replace(raw)
    log(f"✓ {robot} {version}: {len(sums)} ファイル、{human(dir_size(raw))} → {raw}")
    return raw


# ---------------------------------------------------------------- 派生物
def derived_entries(entry: dict) -> list[dict]:
    return [d for d in (entry.get("derived") or []) if d.get("location", "cache") == "cache"]


def write_pipeline_meta(dd: Path, robot: str, version: str, d: dict, project: Path | None) -> None:
    meta = {"robot": robot, "robot_version": version, "pipeline": d["name"], "version": str(d["version"]),
            "desc": d.get("desc", ""), "inputs": d.get("inputs", []), "tools": d.get("tools", []),
            "scripts": [], "written": now()}
    for s in d.get("scripts") or []:
        p = RL / s   # 一覧の scripts は research-lab からの相対パス（projects/<名前>/... を含む）
        meta["scripts"].append({"path": s, "sha256": sha256_file(p) if p.exists() else None})
    y = YAML()
    y.width = 4096
    with (dd / "PIPELINE.yaml").open("w") as f:
        y.dump(meta, f)


def check_derived(robot: str, version: str, d: dict) -> list[str]:
    dd = derived_dir(robot, version, d["name"], str(d["version"]))
    if not (dd / SUMS).exists():
        return [f"{dd} がありません"]
    sums = read_sums(dd / SUMS)
    return verify_sums(dd, sums)


# ---------------------------------------------------------------- プロジェクトのロック
def load_lock(proj: Path) -> dict:
    f = proj / LOCK
    if not f.exists():
        return {}
    return (load(f) or {}).get("robots") or {}


def save_lock(proj: Path, robots: dict) -> None:
    dump({"note": "rl robot link が書く。使ったロボットのデータの版と SHA256SUMS.txt の sha256（データ本体は ~/research-lab/.cache/robots/ にあり、公開しない）",
          "robots": robots}, proj / LOCK)


def link(robot: str, entry: dict, proj: Path, log=print) -> dict:
    version = str(entry["version"])
    raw = raw_dir(robot, version)
    if not (raw / SUMS).exists():
        raise SystemExit(f"rl: {robot} {version} がキャッシュにありません（rl robot fetch {robot}）")
    dst = proj / link_as(robot, entry)
    if dst.is_symlink():
        if Path(os.readlink(dst)) != raw:
            dst.unlink()
    elif dst.exists():
        raise SystemExit(f"rl: {dst} が実体のフォルダです。先に rl robot migrate --project {proj.name} で移してください")
    if not dst.is_symlink():
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.symlink_to(raw, target_is_directory=True)
    lock = load_lock(proj)
    derived = {}
    for d in derived_entries(entry):
        dd = derived_dir(robot, version, d["name"], str(d["version"]))
        if (dd / SUMS).exists():
            derived[f"{d['name']}@{d['version']}"] = {"sums_sha256": sums_digest(dd / SUMS)}
    for d in entry.get("derived") or []:
        if d.get("location") == "project":
            outs = {}
            for o in d.get("outputs") or []:
                mf = proj / o / "manifest.json"
                if mf.exists():
                    outs[o] = sha256_file(mf)
            if outs:
                derived[f"{d['name']}@{d['version']}"] = {"location": "project", "manifest_sha256": outs}
    lock[robot] = {"version": version, "role": entry.get("role"), "link": link_as(robot, entry), "cache": str(raw),
                   "sums_sha256": sums_digest(raw / SUMS), "derived": derived, "linked": now()}
    save_lock(proj, lock)
    log(f"✓ {robot} {version}: {link_as(robot, entry)} → {raw}")
    return lock[robot]


def check_project(proj: Path, cat: dict, deep: bool = True, log=print) -> bool:
    lock = load_lock(proj)
    if not lock:
        log("このプロジェクトはロボットのデータを使っていません（rl robot link）")
        return True
    ok = True
    for robot, e in lock.items():
        dst = proj / e.get("link", f"data/raw/{robot}")
        raw = Path(e.get("cache", ""))
        probs = []
        if not dst.is_symlink():
            probs.append(f"{e.get('link')} がシンボリックリンクではない")
        elif not dst.resolve() == raw.resolve():
            probs.append(f"{e.get('link')} の行き先が記録と違う（{os.readlink(dst)}）")
        if not (raw / SUMS).exists():
            probs.append(f"キャッシュに無い: {raw}（rl robot fetch {robot}）")
        else:
            if sums_digest(raw / SUMS) != e.get("sums_sha256"):
                probs.append("SHA256SUMS.txt が記録と違う（取り直したか、版が変わった）")
            if deep:
                probs += verify_sums(raw, read_sums(raw / SUMS))[:10]
        cat_e = cat.get(robot) or {}
        if cat_e and str(cat_e.get("version")) != str(e.get("version")):
            probs.append(f"一覧の版 {cat_e.get('version')} と違う版 {e.get('version')} を使っている")
        for key, de in (e.get("derived") or {}).items():
            if de.get("location") == "project":
                for o, sha in (de.get("manifest_sha256") or {}).items():
                    mf = proj / o / "manifest.json"
                    if not mf.exists() or sha256_file(mf) != sha:
                        probs.append(f"派生物 {key} の {o}/manifest.json が記録と違う")
                continue
            name, _, pv = key.partition("@")
            dd = derived_dir(robot, str(e.get("version")), name, pv)
            if sums_digest(dd / SUMS) != de.get("sums_sha256"):
                probs.append(f"派生物 {key} の SHA256SUMS.txt が記録と違う")
            elif deep:
                probs += verify_sums(dd, read_sums(dd / SUMS))[:5]
        ok &= not probs
        log(("✓ " if not probs else "✗ ") + f"{robot} {e.get('version')}" + ("" if not probs else "\n    " + "\n    ".join(probs)))
    return ok


def check_cache(cat: dict, deep: bool = True, log=print) -> bool:
    ok = True
    for robot, entry in cat.items():
        version = str(entry["version"])
        raw = raw_dir(robot, version)
        if not (raw / SUMS).exists():
            continue
        probs = verify_sums(raw, read_sums(raw / SUMS)) if deep else []
        man = read_sums(manifest_file(robot, version))
        if man and man != read_sums(raw / SUMS):
            probs.append(f"控え {manifest_file(robot, version).name} と SHA256SUMS.txt が違う")
        for d in derived_entries(entry):
            probs += [f"{d['name']}: {p}" for p in check_derived(robot, version, d)[:5]]
        ok &= not probs
        log(("✓ " if not probs else "✗ ") + f"{robot} {version}" + ("" if not probs else "\n    " + "\n    ".join(probs[:10])))
    return ok


# ---------------------------------------------------------------- 移行（migrate）
def _move_tree(src: Path, dst: Path, log=print) -> None:
    """同じディスクなら rename。違えばコピーして sha256 を確かめてから元を消す。"""
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.rename(src, dst)
    except OSError:
        shutil.copytree(src, dst, symlinks=True)
        a, b = make_sums(src), make_sums(dst)
        if a != b:
            shutil.rmtree(dst)
            raise RuntimeError(f"コピーが元と一致しません: {src}")
        shutil.rmtree(src)


def plan_migrate(proj: Path, cat: dict) -> list[dict]:
    plans = []
    for robot, entry in cat.items():
        src = proj / link_as(robot, entry)
        if src.is_symlink() or not src.is_dir():
            continue
        plans.append({"robot": robot, "entry": entry, "src": src, "version": str(entry["version"])})
    raw_root = proj / "data" / "raw"
    known = {(proj / link_as(r, e)).resolve() for r, e in cat.items()}
    unknown = []
    if raw_root.is_dir():
        for p in sorted(raw_root.iterdir()):
            if p.is_dir() and not p.is_symlink() and p.resolve() not in known and not any(k.is_relative_to(p.resolve()) for k in known):
                unknown.append(p)
    return plans + [{"robot": None, "src": p} for p in unknown]


def migrate_one(proj: Path, plan: dict, apply: bool, log=print) -> dict:
    robot, entry, src, version = plan["robot"], plan["entry"], plan["src"], plan["version"]
    rep = {"robot": robot, "version": version, "src": str(src.relative_to(proj)), "size": dir_size(src)}
    old = read_sums(src / SUMS)
    files = scan_files(src)
    rep.update(files=len(files), old_entries=len(old))
    dsrc = src / "_derived"
    ders = []
    for d in derived_entries(entry):
        frm = d.get("from")
        if not frm:
            continue
        frms = frm if isinstance(frm, list) else [frm]
        present = [f for f in frms if (dsrc / f).exists() and not (dsrc / f).is_symlink()]
        if present:
            ders.append((d, present))
    rep["derived"] = [f"{d['name']}@{d['version']}（{', '.join(p)}）" for d, p in ders]
    vd = version_dir(robot, version)
    raw = vd / "raw"
    log(f"- {robot}: {rep['src']}（{human(rep['size'])}、ファイル {len(files)}、既存の控え {len(old)} 件）→ {raw}")
    for d, p in ders:
        log(f"    派生物: _derived/{', _derived/'.join(p)} → derived/{d['name']}@{d['version']}/")
    if not apply:
        return rep
    # 1 既存の控えを確かめる
    probs = verify_sums(src, old)
    if probs:
        raise RuntimeError(f"{robot}: 既存の SHA256SUMS.txt と合いません（移しません）: {probs[:5]}")
    # 2 全ファイルの控えを作る（既存の控えの上位集合）
    sums = make_sums(src, log)
    added = sorted(set(sums) - set(old))
    rep["added_entries"] = len(added)
    if raw.exists():
        # 既にキャッシュにある（別のプロジェクトから移した・fetch した）→ 同じなら手元の写しを消してリンクだけ
        have = read_sums(raw / SUMS)
        if have != sums:
            raise RuntimeError(f"{robot}: キャッシュに違う中身の {raw} があります。手で確かめてください")
        if verify_sums(raw, have):
            raise RuntimeError(f"{robot}: キャッシュの {raw} が壊れています")
        if ders:
            raise RuntimeError(f"{robot}: _derived が残っています。手で derived/ へ移してください")
        shutil.rmtree(src)
        rep["action"] = "キャッシュに同じものがあり、手元の写しを消した"
    else:
        write_sums(src, sums)
        if old and old != sums:
            write_sums(src, old, name="SHA256SUMS.orig.txt")
        _move_tree(src, raw, log)
        # 3 移した先で確かめる
        probs = verify_sums(raw, sums)
        if probs:
            raise RuntimeError(f"{robot}: 移した先で一致しません: {probs[:5]}")
        rep["action"] = "キャッシュへ移した"
        # 4 派生物を derived/ へ。raw/_derived/<名前> には相対のリンクを残す（古いパスがそのまま使える）
        for d, present in ders:
            dd = derived_dir(robot, version, d["name"], str(d["version"]))
            dd.mkdir(parents=True, exist_ok=True)
            for f in present:
                s = raw / "_derived" / f
                t = dd / f if isinstance(d.get("from"), list) else dd
                if t == dd:
                    for child in s.iterdir():
                        os.rename(child, dd / child.name)
                    s.rmdir()
                else:
                    os.rename(s, t)
                rel = os.path.relpath(t, s.parent)
                s.symlink_to(rel, target_is_directory=t.is_dir())
            dsums = make_sums(dd)
            dsums.pop("PIPELINE.yaml", None)
            write_sums(dd, dsums)
            write_pipeline_meta(dd, robot, version, d, proj)
    # 5 一覧の控え（robots/sums/）とプロジェクトのリンク
    mf = manifest_file(robot, version)
    if not mf.exists():
        mf.parent.mkdir(parents=True, exist_ok=True)
        write_sums(mf.parent, sums, name=mf.name)
    elif read_sums(mf) != sums:
        log(f"  ⚠ 控え {mf} と中身が違います（控えは書き換えません）")
    link(robot, entry, proj, log)
    return rep
