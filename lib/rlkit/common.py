"""台帳の場所の解決と、rl 本体と同じ書式の YAML の読み書き。

追加コマンド（bin/rl-<name>）は、先頭で次のように読み込む:

    import sys, pathlib
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "lib"))
    from rlkit.common import RL, resolve_project, load, dump, add_log, now, die

依存は ruamel.yaml だけ（bin/rl と同じく uv run --script の inline metadata で入れる）。
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

from ruamel.yaml import YAML

RL = Path(__file__).resolve().parent.parent.parent
PROJECTS = RL / "projects"
PROGRAMS = RL / "programs"
CACHE = RL / ".cache"

yaml = YAML()
yaml.preserve_quotes = True
yaml.width = 4096
yaml.indent(mapping=2, sequence=4, offset=2)   # テンプレートと同じ「  - 」の書式


def now() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def die(msg: str) -> None:
    print(f"rl: {msg}", file=sys.stderr)
    sys.exit(1)


def resolve_project(ref: str | None) -> Path:
    if ref is None:
        p = Path.cwd()
        while p != p.parent:
            if (p / "research.yaml").exists():
                return p
            p = p.parent
        die("研究プロジェクトの中で実行するか、名前かパスを指定してください")
    cand = Path(ref).expanduser()
    if (cand / "research.yaml").exists():
        return cand.resolve()
    if (PROJECTS / ref / "research.yaml").exists():
        return PROJECTS / ref
    die(f"プロジェクトが見つかりません: {ref}")


def load(path: Path):
    with Path(path).open() as f:
        return yaml.load(f)


def dump(data, path: Path) -> None:
    path = Path(path)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w") as f:
        yaml.dump(data, f)
    tmp.replace(path)


def add_log(led, by: str, what: str) -> None:
    if led.get("log") is None:
        led["log"] = []
    led["log"].append({"at": now(), "by": by, "what": what})
