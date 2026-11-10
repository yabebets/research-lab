"""runs/<run_id>/ の記録（run.yaml・config・metrics.json・log.txt・status）を作る部品。

rl run（bin/rl-run）と rl blog が使う。書式は skills/research-lab/references/ledger.md。
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import platform
import secrets
import shlex
import shutil
import socket
import subprocess
from pathlib import Path

from . import prereg

SPLITS = ("dev", "val", "test")
STATUSES = ("queued", "running", "done", "failed", "killed")
LOG_MAX = 2 * 1024 * 1024          # log.txt は末尾 2 MB だけ残す
LOCK_FILES = ("sims.lock.yaml", "robots.lock.yaml", "container.lock.yaml", prereg.LOCK)
CONTAINER_LAUNCHERS = ("docker", "podman")
# docker run / podman run のうち、値を 1 つ取る（= で書かなければ次の語が値になる）オプション。イメージの名前を見つけるために使う
_RUN_VALUE_OPTS = {
    "-e", "--env", "--env-file", "-v", "--volume", "--mount", "-w", "--workdir", "-u", "--user", "--name", "--platform",
    "--entrypoint", "--network", "--net", "--cpus", "--cpuset-cpus", "-m", "--memory", "--memory-swap", "--shm-size", "-l",
    "--label", "--label-file", "--ulimit", "--cap-add", "--cap-drop", "--device", "--gpus", "-h", "--hostname", "--add-host",
    "--cidfile", "--tmpfs", "--security-opt", "--pull", "--restart", "--log-driver", "--log-opt", "-p", "--publish", "--expose",
    "--ipc", "--pid", "--runtime", "--stop-signal", "--stop-timeout", "--group-add", "--dns", "--mac-address", "--ip",
    "--storage-opt", "--sysctl", "--userns", "--uts", "--cgroupns", "--isolation", "--health-cmd", "-a", "--attach",
}


# ---------------------------------------------------------------- 小物
def new_run_id(when: dt.datetime | None = None) -> str:
    when = when or dt.datetime.now()
    return f"run_{when.strftime('%Y%m%d_%H%M')}_{secrets.token_hex(3)}"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with Path(p).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _run(cmd, cwd=None, timeout=10) -> str:
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, timeout=timeout)
        return r.stdout.decode(errors="replace").strip() if r.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def git_info(path: Path) -> dict | None:
    """commit・ブランチ・差分の有無・git diff の sha256。git の外なら None。"""
    top = _run(["git", "rev-parse", "--show-toplevel"], cwd=path)
    if not top:
        return None
    commit = _run(["git", "rev-parse", "HEAD"], cwd=path) or None
    diff = b""
    try:
        diff = subprocess.run(["git", "diff", "HEAD"] if commit else ["git", "diff", "--cached"],
                              cwd=path, capture_output=True, timeout=30).stdout
    except (OSError, subprocess.SubprocessError):
        pass
    porcelain = _run(["git", "status", "--porcelain", "--untracked-files=normal"], cwd=path)
    untracked = [ln[3:] for ln in porcelain.splitlines() if ln.startswith("??")]
    return {
        "repo": top,
        "commit": commit,
        "branch": _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=path) or None,
        "dirty": bool(porcelain),
        "diff_sha256": hashlib.sha256(diff).hexdigest() if diff else None,
        "untracked": len(untracked),
    }


def host_info() -> dict:
    sysname = platform.system()
    cpu = ""
    ram_gb = None
    gpu = []
    if sysname == "Darwin":
        cpu = _run(["sysctl", "-n", "machdep.cpu.brand_string"])
        mem = _run(["sysctl", "-n", "hw.memsize"])
        ram_gb = round(int(mem) / 2**30, 1) if mem.isdigit() else None
        if platform.machine() == "arm64":
            gpu.append(f"{cpu or 'Apple Silicon'} (MPS)")
    elif sysname == "Linux":
        try:
            for ln in Path("/proc/cpuinfo").read_text().splitlines():
                if ln.startswith("model name"):
                    cpu = ln.split(":", 1)[1].strip()
                    break
            if not cpu:   # arm64 の Linux は /proc/cpuinfo に model name が無い
                for ln in _run(["lscpu"]).splitlines():
                    if ln.startswith("Model name:"):
                        cpu = ln.split(":", 1)[1].strip()
                        break
            for ln in Path("/proc/meminfo").read_text().splitlines():
                if ln.startswith("MemTotal"):
                    ram_gb = round(int(ln.split()[1]) / 2**20, 1)
                    break
        except OSError:
            pass
    if shutil.which("nvidia-smi"):
        out = _run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"], timeout=15)
        gpu += [ln.strip() for ln in out.splitlines() if ln.strip()]
    return {
        "hostname": socket.gethostname(),
        "os": platform.platform(),
        "python": platform.python_version(),
        "cpu": cpu or platform.processor() or platform.machine(),
        "cpu_count": os.cpu_count(),
        "ram_gb": ram_gb,
        "gpu": gpu,
    }


def in_container() -> bool:
    """コンテナの中か（Docker の /.dockerenv、Podman の /run/.containerenv、イメージの指紋の環境変数）。"""
    return (Path("/.dockerenv").exists() or Path("/run/.containerenv").exists()
            or bool(os.environ.get("RL_IMAGE_ID") or os.environ.get("RL_IMAGE_DIGEST")))


def image_from_command(command) -> tuple[str, str] | None:
    """`docker run … IMAGE …`・`podman run …` の (起動するもの, イメージ) を返す。コンテナを起動するコマンドでなければ None。"""
    cmd = list(command or [])
    if not cmd or os.path.basename(cmd[0]) not in CONTAINER_LAUNCHERS:
        return None
    rest = cmd[1:]
    if rest[:2] == ["container", "run"]:
        rest = rest[2:]
    elif rest[:1] == ["run"]:
        rest = rest[1:]
    else:
        return None
    i = 0
    while i < len(rest):
        t = rest[i]
        if t == "--":
            i += 1
            break
        if t.startswith("-"):
            if "=" not in t and t in _RUN_VALUE_OPTS:
                i += 2
            else:
                i += 1
            continue
        return os.path.basename(cmd[0]), t
    return (os.path.basename(cmd[0]), rest[i]) if i < len(rest) else None


def inspect_image(launcher: str, ref: str) -> dict:
    """手元のイメージの ID（指紋）・RepoDigests・計算機の種類と、起動するもの（エンジン）の版。見つからなければ error を入れる。"""
    out = {"ref": ref, "id": None, "repo_digests": [], "os_arch": None, "engine": None}
    if not shutil.which(launcher):
        out["error"] = f"{launcher} が見つからない"
        return out
    raw = _run([launcher, "image", "inspect", ref], timeout=30)
    try:
        d = json.loads(raw)[0]
        out.update(id=d.get("Id"), repo_digests=d.get("RepoDigests") or [], os_arch=f"{d.get('Os')}/{d.get('Architecture')}")
    except (ValueError, IndexError, TypeError):
        out["error"] = "image inspect に失敗（イメージが手元に無い？）"
    ver = _run([launcher, "version", "--format", "{{.Server.Version}} {{.Server.Os}}/{{.Server.Arch}}"], timeout=15)
    out["engine"] = f"{launcher} {ver}" if ver else None
    return out


def container_info(command=None) -> dict | None:
    """run がどのコンテナのイメージで回ったか（plan の再現性：イメージの指紋を run ごとに残す）。

    - rl run 自身がコンテナの中で動いている：環境変数 RL_IMAGE_ID・RL_IMAGE_TAG・RL_IMAGE_DIGEST（起動する側が渡す）と、
      イメージの中の説明のファイル（環境変数 RL_IMAGE_INFO、既定 /etc/rl-image.json）の sha256・主な項目を残す
    - ホストの rl run がコンテナを起動する：コマンドが `docker run … IMAGE` か、環境変数 RL_IMAGE（包みのスクリプトを使うとき。
      包みも同じ RL_IMAGE を使う決まり）があれば、`docker image inspect` で ID を引く
    どちらでもなければ None。
    """
    if in_container():
        rec = {"inside": True, "image": os.environ.get("RL_IMAGE_TAG") or None, "id": os.environ.get("RL_IMAGE_ID") or None,
               "repo_digest": os.environ.get("RL_IMAGE_DIGEST") or None, "info": None}
        p = Path(os.environ.get("RL_IMAGE_INFO") or "/etc/rl-image.json")
        if p.is_file():
            try:
                txt = p.read_bytes()
                info = json.loads(txt)
                rec["info"] = {"path": str(p), "sha256": hashlib.sha256(txt).hexdigest(),
                               **{k: info.get(k) for k in ("tag", "platform", "os", "source_commit") if k in info}}
                rec["image"] = rec["image"] or info.get("tag")
            except (OSError, ValueError):
                rec["info"] = {"path": str(p), "error": "読めない"}
        return rec
    found = image_from_command(command)
    env_ref = os.environ.get("RL_IMAGE")
    if not found and not env_ref:
        return None
    launcher, ref = found if found else (os.environ.get("RL_IMAGE_LAUNCHER") or "docker", env_ref)
    rec = {"inside": False, "launcher": launcher, "via": "command" if found else "RL_IMAGE"}
    rec.update(inspect_image(launcher, ref))
    rec["image"] = rec.pop("ref")
    return rec


def lock_hashes(proj: Path) -> dict:
    return {name: sha256_file(proj / name) for name in LOCK_FILES if (proj / name).is_file()}


def read_metrics(run_dir: Path):
    f = Path(run_dir) / "metrics.json"
    if not f.exists():
        return None
    try:
        return json.loads(f.read_text())
    except (json.JSONDecodeError, OSError):
        return "invalid"


def read_status(run_dir: Path) -> str:
    f = Path(run_dir) / "status"
    return f.read_text().strip() if f.exists() else "?"


def run_dirs(proj: Path) -> list[Path]:
    """run のフォルダを、run_id の日時 → run.yaml の開始時刻の順に。"""
    ds = [p for p in (proj / "runs").glob("run_*") if p.is_dir()]

    def key(p):
        st = ""
        f = p / "run.yaml"
        if f.exists():
            for ln in f.read_text(errors="replace").splitlines():
                if ln.startswith("started_at:"):
                    st = ln.split(":", 1)[1].strip().strip("'\"")
                    break
        return (p.name[:17], st, p.name)
    return sorted(ds, key=key)


def load_run_yaml(run_dir: Path) -> dict:
    from ruamel.yaml import YAML
    f = Path(run_dir) / "run.yaml"
    if not f.exists():
        return {}
    try:
        return YAML(typ="safe", pure=True).load(f.read_text()) or {}
    except Exception:  # noqa: BLE001
        return {}


def find_run(proj: Path, ref: str) -> Path | None:
    """run_id そのもの、または一意に決まる部分文字列。"""
    exact = proj / "runs" / ref
    if exact.is_dir():
        return exact
    cands = [p for p in run_dirs(proj) if ref in p.name]
    return cands[0] if len(cands) == 1 else None


# ---------------------------------------------------------------- test の回数と確認
def test_runs(proj: Path, exclude: str | None = None) -> list[str]:
    """test の評価として数える run。

    metrics.json の split が test のもの（宣言が val でも数える）と、--split test で始めた run
    （失敗・中断・実行中も数える。落ちたら回数が戻る、という抜け道を作らない）。
    """
    out = []
    for r in run_dirs(proj):
        if r.name == exclude:
            continue
        m = read_metrics(r)
        if (isinstance(m, dict) and m.get("split") == "test") or load_run_yaml(r).get("split") == "test":
            out.append(r.name)
    return out


def split_guard(proj: Path, led, split: str) -> tuple[list[str], list[str]]:
    """(拒否の理由, 警告)。理由が空なら実行してよい。"""
    errs, warns = [], []
    if split not in SPLITS:
        return [f"--split は {'|'.join(SPLITS)} のどれか（{split!r} は使えません）"], []
    if split != "test":
        return [], []
    gates = led.get("gates") or {}
    if not (gates.get("G2") or {}).get("approved"):
        errs.append("G2（計画と評価プロトコルの承認）の前は test で評価できません。dev か val で回してください")
    proto = led.get("protocol") or {}
    mx = proto.get("max_test_evals")
    used = test_runs(proj)
    if mx is None:
        errs.append("research.yaml の protocol.max_test_evals がありません。test の評価回数は G2 で人が決めます")
    elif len(used) >= int(mx):
        errs.append(f"test での評価は G2 で決めた {mx} 回をすでに使い切っています（{len(used)} 回: {', '.join(used)}）。"
                    "増やすなら blockers に書いて人に確認する")
    d = prereg.drift(proj, led)
    if d["locked"] and d["drift"]:
        errs.append("事前登録が凍結時から変わっています（rl prereg check で確認）。変更を戻すか、人の承認を取って再凍結するまで test は回せません")
        errs += ["  " + m for m in d["messages"]]
    elif not d["locked"] and (gates.get("G2") or {}).get("approved"):
        warns.append("事前登録が凍結されていません（rl prereg freeze を推奨）")
    return errs, warns


# ---------------------------------------------------------------- run.yaml
def _dump_yaml(data, path: Path) -> None:
    from ruamel.yaml import YAML
    y = YAML()
    y.default_flow_style = False
    y.width = 4096
    y.indent(mapping=2, sequence=4, offset=2)
    tmp = Path(path).with_suffix(".yaml.tmp")
    with tmp.open("w") as f:
        f.write("# rl run が書く実行の記録（書式: skills/research-lab/references/ledger.md）\n")
        y.dump(data, f)
    tmp.replace(path)


def write_status(run_dir: Path, status: str) -> None:
    assert status in STATUSES
    (Path(run_dir) / "status").write_text(status + "\n")


def start(proj: Path, led, *, task: str, purpose: str, split: str = "dev", seed=None,
          config: str | None = None, tags=(), command=None, cwd: str | None = None,
          data_version: str | None = None, cluster: str | None = None) -> Path:
    """run のフォルダを作り、run.yaml（status: running）を書く。確認（split_guard）は呼ぶ側で済ませる。"""
    run_id = new_run_id()
    run_dir = proj / "runs" / run_id
    while run_dir.exists():
        run_id = new_run_id()
        run_dir = proj / "runs" / run_id
    run_dir.mkdir(parents=True)
    cwd = cwd or os.getcwd()
    cfg_rec = None
    if config:
        src = Path(config).expanduser().resolve()
        if not src.is_file():
            shutil.rmtree(run_dir)
            raise FileNotFoundError(f"--config のファイルがありません: {config}")
        dst_name = "config.yaml" if src.suffix in (".yaml", ".yml") else f"config{src.suffix}"
        shutil.copy2(src, run_dir / dst_name)
        cfg_rec = {"source": str(src), "copy": dst_name, "sha256": sha256_file(src)}
    gp = git_info(proj)
    gc = git_info(Path(cwd)) if Path(cwd).exists() else None
    d = prereg.drift(proj, led)
    rec = {
        "run_id": run_id,
        "project": str(led.get("project") or proj.name),
        "task": task,
        "purpose": purpose,
        "tags": list(tags or []),
        "split": split,
        "seed": seed,
        "data_version": data_version,
        "command": list(command) if command else None,
        "command_str": shlex.join(command) if command else None,
        "cwd": cwd,
        "config": cfg_rec,
        "git": gp,
        "git_cwd": gc if gc and gp and gc.get("repo") != gp.get("repo") else None,
        "locks": lock_hashes(proj),
        "prereg": {"locked": d["locked"], "drift": d["drift"]},
        "host": host_info(),
        "container": container_info(command),
        "compute": {"where": cluster or "local", "gpu_usd": None},
        "started_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "ended_at": None,
        "elapsed_sec": None,
        "exit_code": None,
        "status": "running",
        "status_reason": None,
        "llm": None,
        "metrics_keys": None,
        "log": None,
    }
    _dump_yaml(rec, run_dir / "run.yaml")
    write_status(run_dir, "running")
    return run_dir


def child_env(proj: Path, run_dir: Path, rec: dict) -> dict:
    env = dict(os.environ)
    env.update({
        "RL_RUN_DIR": str(run_dir.resolve()),
        "RL_RUN_ID": run_dir.name,
        "RL_PROJECT": str(proj.resolve()),
        "RL_PROJECT_NAME": str(rec.get("project") or proj.name),
        "RL_SPLIT": str(rec.get("split") or ""),
        "RL_TASK": str(rec.get("task") or ""),
        "PYTHONUNBUFFERED": "1",
    })
    if rec.get("seed") is not None:
        env["RL_SEED"] = str(rec["seed"])
    else:
        env.pop("RL_SEED", None)
    return env


def llm_spend(run_dir: Path) -> dict | None:
    f = Path(run_dir) / "llm_calls.jsonl"
    if not f.exists():
        return None
    calls, cost, by_model = 0, 0.0, {}
    for ln in f.read_text(errors="replace").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            o = json.loads(ln)
        except json.JSONDecodeError:
            continue
        calls += 1
        c = o.get("cost_usd") or 0
        try:
            c = float(c)
        except (TypeError, ValueError):
            c = 0.0
        cost += c
        m = o.get("model")
        if m:
            by_model[m] = round(by_model.get(m, 0.0) + c, 6)
    return {"calls": calls, "cost_usd": round(cost, 6), "by_model": by_model or None}


def truncate_log(path: Path, limit: int = LOG_MAX) -> dict:
    path = Path(path)
    if not path.exists():
        return {"bytes_total": 0, "truncated": False}
    size = path.stat().st_size
    if size <= limit:
        return {"bytes_total": size, "truncated": False}
    with path.open("rb") as f:
        f.seek(size - limit)
        tail = f.read()
    nl = tail.find(b"\n")
    if 0 <= nl < 4096:
        tail = tail[nl + 1:]
    head = f"[rl] ログが大きいので末尾 {limit // (1024 * 1024)} MB だけ残しました（元は {size} バイト）\n".encode()
    path.write_bytes(head + tail)
    return {"bytes_total": size, "truncated": True}


def finish(proj: Path, run_dir: Path, *, exit_code: int | None, killed: bool = False,
           no_metrics: bool = False, status: str | None = None, reason: str | None = None) -> dict:
    """status を決め、run.yaml を仕上げる。戻り値は仕上げた run.yaml の中身。"""
    rec = load_run_yaml(run_dir)
    run_dir = Path(run_dir)
    started = rec.get("started_at")
    end = dt.datetime.now().astimezone()
    elapsed = None
    if started:
        try:
            elapsed = round((end - dt.datetime.fromisoformat(str(started))).total_seconds(), 1)
        except ValueError:
            pass
    reasons = [reason] if reason else []
    m = read_metrics(run_dir)
    if m == "invalid" or (m is not None and not isinstance(m, dict)):
        reasons.append("metrics.json が JSON のオブジェクトとして読めません")
        m_ok = False
    elif m is None:
        m_ok = no_metrics
        if not no_metrics and not killed and status in (None, "done"):
            reasons.append("metrics.json が書かれていません（$RL_RUN_DIR/metrics.json に書く。書かない実行は --no-metrics）")
    else:
        m_ok = True
        decl = rec.get("split")
        if "split" not in m:
            m["split"] = decl
            (run_dir / "metrics.json").write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n")
            rec["split_added_by_rl"] = True
        elif m.get("split") != decl:
            m_ok = False
            reasons.append(f"metrics.json の split（{m.get('split')}）が宣言（--split {decl}）と違います")
        rec["metrics_keys"] = [k for k in m if k != "split"]
    if status is None:
        if killed:
            status = "killed"
        elif exit_code not in (0, None):
            status = "failed"
            reasons.insert(0, f"終了コード {exit_code}")
        elif not m_ok:
            status = "failed"
        else:
            status = "done"
    if status not in STATUSES:
        raise ValueError(f"status は {STATUSES} のどれか")
    rec.update({
        "ended_at": end.isoformat(timespec="seconds"),
        "elapsed_sec": elapsed,
        "exit_code": exit_code,
        "status": status,
        "status_reason": "; ".join(reasons) or None,
        "llm": llm_spend(run_dir),
        "log": truncate_log(run_dir / "log.txt"),
    })
    _dump_yaml(rec, run_dir / "run.yaml")
    write_status(run_dir, status)
    return rec


def fmt_elapsed(sec) -> str:
    if sec is None:
        return "-"
    sec = int(sec)
    if sec < 60:
        return f"{sec}s"
    if sec < 3600:
        return f"{sec // 60}m{sec % 60:02d}s"
    return f"{sec // 3600}h{(sec % 3600) // 60:02d}m"
