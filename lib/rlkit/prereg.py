"""事前登録の凍結（prereg.lock.yaml）と、凍結後の変更（ずれ）の検出。

G2 で承認した事前登録を、2 か所のハッシュで固定する:
  - plan.md の「## 事前登録 …」の節（次の `## ` まで）
  - research.yaml の protocol（キーを並べ替えた正規の YAML）

rl prereg freeze / check と、rl run の test 実行の前の確認が使う。
"""
from __future__ import annotations

import datetime as dt
import difflib
import hashlib
import io
import re
import subprocess
from pathlib import Path

from ruamel.yaml import YAML

LOCK = "prereg.lock.yaml"
# 「## 4. 事前登録」「## 事前登録（ml-rigor のテンプレート）」のどちらでも拾う
HEADING = re.compile(r"^##[ \t]+(?:[0-9０-９]+[.．、]?[ \t]*)?事前登録.*$", re.M)
NEXT_H2 = re.compile(r"^##[ \t]", re.M)


def sha256(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode()
    return hashlib.sha256(data).hexdigest()


def to_plain(x):
    """ruamel の CommentedMap / CommentedSeq を素の dict / list に。"""
    if isinstance(x, dict):
        return {str(k): to_plain(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [to_plain(v) for v in x]
    if isinstance(x, (dt.date, dt.datetime)):
        return x.isoformat()
    if isinstance(x, bool):
        return bool(x)
    if isinstance(x, int):          # ruamel の ScalarInt など
        return int(x)
    if isinstance(x, float):
        return float(x)
    if isinstance(x, str):
        return str(x)
    return x


def _sorted(x):
    if isinstance(x, dict):
        return {k: _sorted(x[k]) for k in sorted(x)}
    if isinstance(x, list):
        return [_sorted(v) for v in x]
    return x


def canonical_yaml(obj) -> str:
    y = YAML(typ="safe", pure=True)
    y.default_flow_style = False
    y.width = 4096
    buf = io.StringIO()
    y.dump(_sorted(to_plain(obj)), buf)
    return buf.getvalue()


def plan_section(plan_text: str) -> tuple[str, str] | None:
    """(見出し, 節の本文（見出しを含む・正規化済み）) を返す。見つからなければ None。"""
    m = HEADING.search(plan_text)
    if not m:
        return None
    rest = plan_text[m.end():]
    n = NEXT_H2.search(rest)
    body = plan_text[m.start(): m.end() + (n.start() if n else len(rest))]
    lines = [ln.rstrip() for ln in body.replace("\r\n", "\n").split("\n")]
    while lines and not lines[-1]:
        lines.pop()
    return m.group(0).strip(), "\n".join(lines) + "\n"


def _git(proj: Path, *args) -> str:
    try:
        r = subprocess.run(["git", *args], cwd=proj, capture_output=True, text=True, timeout=20)
        return r.stdout.strip() if r.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def current(proj: Path, led) -> dict:
    """今の plan.md の節と protocol のハッシュ。"""
    plan = proj / "plan.md"
    out = {"plan": None, "protocol": None, "errors": []}
    if not plan.exists():
        out["errors"].append("plan.md がありません")
    else:
        sec = plan_section(plan.read_text())
        if sec is None:
            out["errors"].append("plan.md に「## 事前登録」の節がありません（見出しは `## 事前登録…` か `## 4. 事前登録…`）")
        else:
            out["plan"] = {"heading": sec[0], "text": sec[1], "sha256": sha256(sec[1])}
    proto = (led or {}).get("protocol")
    if proto is None:
        out["errors"].append("research.yaml に protocol がありません")
    else:
        text = canonical_yaml(proto)
        out["protocol"] = {"text": text, "sha256": sha256(text), "frozen": _sorted(to_plain(proto))}
    return out


def load_lock(proj: Path) -> dict | None:
    f = proj / LOCK
    if not f.exists():
        return None
    y = YAML(typ="safe", pure=True)
    return y.load(f.read_text()) or {}


def build_lock(proj: Path, led, cur: dict, by: str = "rl prereg freeze") -> tuple[dict, str]:
    """(lock の中身, 節のコピーの相対パス)。"""
    today = dt.date.today().isoformat()
    copy_rel = f"prereg/plan-section-{today}.md"
    g2 = ((led.get("gates") or {}).get("G2") or {})
    lock = {
        "frozen_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "frozen_by": by,
        "gate": {"G2_approved": bool(g2.get("approved")), "G2_decided_at": to_plain(g2.get("decided_at"))},
        "plan": {
            "path": "plan.md",
            "heading": cur["plan"]["heading"],
            "sha256": cur["plan"]["sha256"],
            "git_commit": _git(proj, "log", "-1", "--format=%H", "--", "plan.md") or None,
            "git_dirty": bool(_git(proj, "status", "--porcelain", "--", "plan.md")),
            "copy": copy_rel,
        },
        "protocol": {"sha256": cur["protocol"]["sha256"], "frozen": cur["protocol"]["frozen"]},
        "history": [],
    }
    return lock, copy_rel


def write_lock(proj: Path, lock: dict) -> None:
    y = YAML()
    y.default_flow_style = False
    y.width = 4096
    y.indent(mapping=2, sequence=4, offset=2)
    buf = io.StringIO()
    buf.write("# 事前登録の凍結（rl prereg freeze が書く。手で直さない。変えるなら人の承認を取って --refreeze）\n")
    y.dump(lock, buf)
    tmp = proj / (LOCK + ".tmp")
    tmp.write_text(buf.getvalue())
    tmp.replace(proj / LOCK)


def _dict_diff(a, b, prefix="") -> list[str]:
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            p = f"{prefix}.{k}" if prefix else str(k)
            if k not in a:
                out.append(f"protocol.{p}: 追加 → {b[k]!r}")
            elif k not in b:
                out.append(f"protocol.{p}: 削除（凍結時 {a[k]!r}）")
            else:
                out += _dict_diff(a[k], b[k], p)
    elif a != b:
        out.append(f"protocol.{prefix}: {a!r} → {b!r}")
    return out


def drift(proj: Path, led) -> dict:
    """{"locked": bool, "drift": bool, "messages": [...], "diff": str}"""
    lock = load_lock(proj)
    res = {"locked": lock is not None, "drift": False, "messages": [], "diff": ""}
    if lock is None:
        return res
    cur = current(proj, led)
    for e in cur["errors"]:
        res["drift"] = True
        res["messages"].append(e)
    if cur["plan"] and cur["plan"]["sha256"] != (lock.get("plan") or {}).get("sha256"):
        res["drift"] = True
        res["messages"].append("plan.md の事前登録の節が凍結時から変わっています")
        copy = proj / ((lock.get("plan") or {}).get("copy") or "")
        if copy.is_file():
            res["diff"] = "".join(difflib.unified_diff(
                copy.read_text().splitlines(True), cur["plan"]["text"].splitlines(True),
                fromfile=f"凍結時 ({copy.name})", tofile="今の plan.md"))
    if cur["protocol"] and cur["protocol"]["sha256"] != (lock.get("protocol") or {}).get("sha256"):
        res["drift"] = True
        res["messages"].append("research.yaml の protocol が凍結時から変わっています")
        res["messages"] += ["  " + d for d in _dict_diff((lock.get("protocol") or {}).get("frozen") or {},
                                                        cur["protocol"]["frozen"])]
    return res
