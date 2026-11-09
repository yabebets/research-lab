#!/usr/bin/env python3
"""vendor/ と skills/ の SKILL.md を集めて索引を作る（標準ライブラリだけ）。

出力:
  vendor/INDEX.md   人とエージェントが読む一覧（出典・カテゴリ別）
  vendor/index.json 機械が読む一覧（name, description, path, source）

使い方: python3 scripts/build-index.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 索引に載せないディレクトリ（他ホスト向けのミラーや共有の参照文書）
SKIP_PARTS = {
    "skills-codex",
    "skills-codex-claude-review",
    "skills-codex-gemini-review",
    "shared-references",
    "templates",
    "examples",
    "references",
}

SOURCES = [
    ("own", ROOT / "skills", "research-lab（自前）"),
    ("paper-writing", ROOT / "vendor" / "research-paper-writing", "Master-cai / Research-Paper-Writing-Skills"),
    ("aris", ROOT / "vendor" / "aris" / "skills", "ARIS / Auto-claude-code-research-in-sleep"),
    ("orchestra", ROOT / "vendor" / "orchestra", "Orchestra / AI-Research-SKILLs"),
]


def parse_frontmatter(text: str) -> dict[str, str]:
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    if not m:
        return {}
    meta: dict[str, str] = {}
    key = None
    for line in m.group(1).splitlines():
        km = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if km:
            key = km.group(1)
            val = km.group(2).strip()
            if val in (">", "|", ">-", "|-"):
                val = ""
            meta[key] = val.strip("\"'")
        elif key and line.startswith((" ", "\t")):
            meta[key] = (meta[key] + " " + line.strip()).strip()
    return meta


def first_heading(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return ""


def collect() -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for source, base, _label in SOURCES:
        if not base.exists():
            continue
        for skill_md in sorted(base.rglob("SKILL.md")):
            rel_parts = skill_md.relative_to(base).parts[:-1]
            if any(p in SKIP_PARTS for p in rel_parts):
                continue
            if source == "own" and skill_md.parent.is_symlink():
                continue  # vendor へのリンクは二重に載せない
            text = skill_md.read_text(encoding="utf-8", errors="replace")
            meta = parse_frontmatter(text)
            name = meta.get("name") or skill_md.parent.name
            desc = meta.get("description") or first_heading(text)
            category = rel_parts[0] if (source == "orchestra" and len(rel_parts) > 1) else ""
            items.append(
                {
                    "name": name,
                    "description": re.sub(r"\s+", " ", desc)[:400],
                    "path": str(skill_md.relative_to(ROOT)),
                    "source": source,
                    "category": category,
                }
            )
    return items


def render(items: list[dict[str, str]]) -> str:
    out = [
        "# スキル索引（自動生成）",
        "",
        "`python3 scripts/build-index.py` が作る。手で直さない。",
        "ここにあるスキルは、`research-lab` スキルの指示で **SKILL.md を Read して従う** ライブラリ。",
        "グローバルに登録しているのは `skills/` の自前スキルと research-paper-writing だけ。",
        "研究プロジェクトの中では、`rl new` が ARIS の主要スキルをプロジェクト用に登録する。",
        "",
    ]
    for source, _base, label in SOURCES:
        rows = [i for i in items if i["source"] == source]
        if not rows:
            continue
        out += [f"## {label}（{len(rows)}）", ""]
        if source == "orchestra":
            cats = sorted({r["category"] for r in rows})
            for cat in cats:
                out += [f"### {cat}", ""]
                for r in [r for r in rows if r["category"] == cat]:
                    out.append(f"- **{r['name']}** — {r['description']}  \n  `{r['path']}`")
                out.append("")
        else:
            for r in rows:
                out.append(f"- **{r['name']}** — {r['description']}  \n  `{r['path']}`")
            out.append("")
    return "\n".join(out)


def main() -> None:
    items = collect()
    (ROOT / "vendor" / "INDEX.md").write_text(render(items), encoding="utf-8")
    (ROOT / "vendor" / "index.json").write_text(
        json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    by = {}
    for i in items:
        by[i["source"]] = by.get(i["source"], 0) + 1
    print(f"{len(items)} skills indexed: {by}")


if __name__ == "__main__":
    main()
