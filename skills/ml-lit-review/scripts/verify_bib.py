#!/usr/bin/env python3
"""BibTeX の各エントリが実在し、タイトル・著者・年が合っているかを確かめる（標準ライブラリだけ）。

調べる順番
  1. arXiv ID（eprint / arxiv / url / journal に arXiv:XXXX.XXXXX）→ arXiv API
  2. DOI → Crossref
  3. タイトル → OpenAlex の検索（なければ Semantic Scholar）
判定
  OK          タイトルの類似度 ≥ 0.90 かつ（年・筆頭著者の姓が合う、または比べる情報がない）
  CHECK       見つかったが、類似度 0.70〜0.90、または年・筆頭著者が合わない
  NOT_FOUND   見つからない（捏造・誤記の疑い。必ず人か別の方法で確かめる）
  ERROR       通信の失敗など（判定できていない。OK と扱わない）

使い方
  verify_bib.py paper/refs.bib                 # 表を出す
  verify_bib.py paper/refs.bib --json out.json # 機械が読む結果も保存
  verify_bib.py paper/refs.bib --only key1,key2
終了コード: NOT_FOUND か ERROR が 1 件でもあれば 1
"""
from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

UA = "research-lab-verify-bib/1.0 (citation checker)"
SLEEP = 1.1


def http_get(url: str, timeout: int = 20) -> bytes:
    headers = {"User-Agent": UA, "Accept": "application/json, application/xml"}
    if "semanticscholar.org" in url and os.environ.get("S2_API_KEY"):
        headers["x-api-key"] = os.environ["S2_API_KEY"]
    req = urllib.request.Request(url, headers=headers)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and attempt < 2:
                time.sleep(3 * (attempt + 1))
                continue
            if e.code == 404:
                return b""
            raise
    return b""


def parse_bib(text: str) -> list[dict]:
    entries = []
    i = 0
    while True:
        m = re.compile(r"@(\w+)\s*\{\s*([^,\s]+)\s*,", re.S).search(text, i)
        if not m:
            break
        typ, key = m.group(1).lower(), m.group(2)
        j, depth = m.end(), 1
        while j < len(text) and depth:
            depth += {"{": 1, "}": -1}.get(text[j], 0)
            j += 1
        body = text[m.end(): j - 1]
        i = j
        if typ in ("comment", "string", "preamble"):
            continue
        fields = {}
        for fm in re.finditer(r"(\w+)\s*=\s*", body):
            name = fm.group(1).lower()
            k = fm.end()
            if k < len(body) and body[k] == "{":
                d, s = 0, k
                while k < len(body):
                    d += {"{": 1, "}": -1}.get(body[k], 0)
                    k += 1
                    if d == 0:
                        break
                val = body[s + 1: k - 1]
            elif k < len(body) and body[k] == '"':
                e = body.find('"', k + 1)
                val = body[k + 1: e]
            else:
                e = re.search(r"[,\n]", body[k:])
                val = body[k: k + (e.start() if e else len(body))]
            fields.setdefault(name, re.sub(r"\s+", " ", val).strip())
        entries.append({"key": key, "type": typ, **fields})
    return entries


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = re.sub(r"\\[a-zA-Z]+\s*|[{}$\\]", "", s)
    s = re.sub(r"[^a-z0-9 ]", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()


def sim(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, norm(a), norm(b)).ratio()


def first_author_last(authors: str) -> str:
    if not authors:
        return ""
    first = re.split(r"\s+and\s+", authors)[0]
    last = first.split(",")[0] if "," in first else first.split()[-1] if first.split() else ""
    return norm(last)


def find_arxiv_id(e: dict) -> str | None:
    for f in ("eprint", "arxiv", "url", "journal", "note", "howpublished"):
        v = e.get(f, "")
        m = re.search(r"(\d{4}\.\d{4,5})(v\d+)?", v)
        if m and (f == "eprint" or "arxiv" in v.lower()):
            return m.group(1)
    return None


def look_arxiv(aid: str):
    data = http_get(f"https://export.arxiv.org/api/query?id_list={aid}")
    if not data:
        return None
    ns = {"a": "http://www.w3.org/2005/Atom"}
    root = ET.fromstring(data)
    ent = root.find("a:entry", ns)
    if ent is None or ent.find("a:title", ns) is None:
        return None
    title = ent.find("a:title", ns).text or ""
    if title.strip().lower() == "error":
        return None
    authors = [a.find("a:name", ns).text for a in ent.findall("a:author", ns)]
    year = (ent.find("a:published", ns).text or "")[:4]
    return {"title": title, "first_author": authors[0] if authors else "", "year": year, "via": f"arXiv:{aid}"}


def look_crossref(doi: str):
    data = http_get("https://api.crossref.org/works/" + urllib.parse.quote(doi))
    if not data:
        return None
    msg = json.loads(data).get("message", {})
    title = (msg.get("title") or [""])[0]
    au = msg.get("author") or [{}]
    parts = ((msg.get("issued") or {}).get("date-parts") or [[None]])[0] or [None]
    year = str(parts[0]) if parts[0] is not None else ""   # Crossref に年が無いと [[None]] が返る
    return {"title": title, "first_author": au[0].get("family", ""), "year": year, "via": f"doi:{doi}"}


def look_openalex(title: str):
    q = urllib.parse.urlencode({"search": title, "per-page": 3})
    data = http_get(f"https://api.openalex.org/works?{q}")
    if not data:
        return None
    best = None
    for w in json.loads(data).get("results", []):
        t = w.get("title") or ""
        au = (w.get("authorships") or [{}])[0].get("author", {}).get("display_name", "")
        cand = {"title": t, "first_author": au, "year": str(w.get("publication_year") or ""), "via": "openalex"}
        if best is None or sim(title, t) > sim(title, best["title"]):
            best = cand
    return best


def look_s2(title: str):
    q = urllib.parse.urlencode({"query": title, "limit": 3, "fields": "title,year,authors"})
    data = http_get(f"https://api.semanticscholar.org/graph/v1/paper/search?{q}")
    if not data:
        return None
    best = None
    for p in json.loads(data).get("data", []):
        cand = {"title": p.get("title") or "", "year": str(p.get("year") or ""),
                "first_author": (p.get("authors") or [{}])[0].get("name", ""), "via": "semantic-scholar"}
        if best is None or sim(title, cand["title"]) > sim(title, best["title"]):
            best = cand
    return best


def check(e: dict) -> dict:
    title = e.get("title", "")
    res = {"key": e["key"], "bib_title": title, "bib_year": e.get("year", ""), "verdict": "NOT_FOUND"}
    found = None
    try:
        aid = find_arxiv_id(e)
        if aid:
            found = look_arxiv(aid)
            time.sleep(SLEEP)
        if not found and e.get("doi"):
            found = look_crossref(e["doi"])
            time.sleep(SLEEP)
        if (not found or sim(title, found["title"]) < 0.9) and title:
            alt = look_openalex(title)
            time.sleep(SLEEP)
            if not alt or sim(title, alt["title"]) < 0.9:
                try:
                    alt2 = look_s2(title)
                except Exception as ex:  # S2 は鍵なしだと回数制限が厳しい。OpenAlex の結果で判定を続ける
                    alt2 = None
                    res["note"] = f"Semantic Scholar 失敗（{str(ex)[:40]}）、OpenAlex だけで判定"
                time.sleep(SLEEP)
                if alt2 and (not alt or sim(title, alt2["title"]) > sim(title, alt["title"])):
                    alt = alt2
            if alt and (not found or sim(title, alt["title"]) > sim(title, found["title"])):
                if found:
                    res["note"] = f"ID が指す論文のタイトルが違う（{found['via']}: {found['title'][:80]}）"
                found = alt
    except Exception as ex:  # 通信の失敗は判定不能として残す
        res.update(verdict="ERROR", note=str(ex)[:160])
        return res
    if not found:
        return res
    s = sim(title, found["title"])
    res.update(found_title=found["title"], found_year=found["year"], found_first_author=found["first_author"],
               via=found["via"], title_similarity=round(s, 3))
    year_ok = not e.get("year") or not found["year"] or abs(int(re.sub(r"\D", "", e["year"]) or 0) - int(re.sub(r"\D", "", found["year"]) or 0)) <= 1
    fa_bib = first_author_last(e.get("author", ""))
    fa_ok = not fa_bib or not found["first_author"] or fa_bib in norm(found["first_author"])
    if s >= 0.9 and year_ok and fa_ok:
        res["verdict"] = "OK"
    elif s >= 0.7:
        res["verdict"] = "CHECK"
        why = [w for w, ok in (("年", year_ok), ("筆頭著者", fa_ok), ("タイトル", s >= 0.9)) if not ok]
        res["note"] = (res.get("note", "") + " 不一致: " + "・".join(why)).strip()
    else:
        res["verdict"] = "NOT_FOUND"
        res["note"] = (res.get("note", "") + f" いちばん近い候補: {found['title'][:80]}").strip()
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("bib")
    ap.add_argument("--json")
    ap.add_argument("--only")
    a = ap.parse_args()
    entries = parse_bib(open(a.bib, encoding="utf-8").read())
    if a.only:
        keep = set(a.only.split(","))
        entries = [e for e in entries if e["key"] in keep]
    results = []
    for e in entries:
        r = check(e)
        results.append(r)
        print(f"{r['verdict']:<9} {r['key']:<28} {r.get('title_similarity', '-')!s:<6} {r.get('via', '')}  {r.get('note', '')}")
    counts = {}
    for r in results:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    print(f"\n{len(results)} 件: {counts}")
    if a.json:
        json.dump(results, open(a.json, "w"), ensure_ascii=False, indent=1)
    sys.exit(1 if counts.get("NOT_FOUND") or counts.get("ERROR") else 0)


if __name__ == "__main__":
    main()
