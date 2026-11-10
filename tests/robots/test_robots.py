"""rl robot（lib/rlkit/robots.py）のテスト。キャッシュ・一覧・控えは一時フォルダに差し替える。

    uv run --with pytest --with ruamel.yaml pytest tests/robots -q
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path

import pytest

RL = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RL / "lib"))
from rlkit import robots as R  # noqa: E402


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


@pytest.fixture
def env(tmp_path, monkeypatch):
    cache = tmp_path / "cache"
    cat = tmp_path / "robots" / "catalog.yaml"
    cat.parent.mkdir()
    monkeypatch.setenv("RL_ROBOT_CACHE", str(cache))
    monkeypatch.setenv("RL_ROBOT_CATALOG", str(cat))
    monkeypatch.delenv("RL_ROBOT_SUMS", raising=False)
    proj = tmp_path / "proj"
    (proj / "data" / "raw").mkdir(parents=True)
    (proj / "research.yaml").write_text("project: {name: proj}\n")
    return dict(tmp=tmp_path, cache=cache, cat=cat, proj=proj)


def write_catalog(path: Path, text: str) -> dict:
    path.write_text(text)
    return R.load_catalog()


def make_robot_dir(root: Path) -> dict[str, str]:
    files = {"a.step": b"STEP-A", "docs/manual.pdf": b"%PDF", "sub/dir/b.txt": b"hello"}
    for rel, data in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    (root / "_derived" / "tree").mkdir(parents=True)
    (root / "_derived" / "tree" / "t.json").write_text("{}")
    (root / "_derived" / "notes.txt").write_text("x")
    (root / ".git").mkdir()
    (root / ".git" / "HEAD").write_text("ref")
    sums = {k: sha(v) for k, v in files.items()}
    # 取得のときの控え（一部だけ。migrate はこれを確かめてから全ファイルの控えを作る）
    R.write_sums(root, {"a.step": sums["a.step"]})
    return sums


CAT = """
robots:
  toy:
    role: test
    version: "abc12345"
    sources: []
    derived:
      - {name: tree, version: "2026-01-01", from: tree, scripts: []}
      - {name: text, version: "2026-01-01", from: [notes.txt], scripts: []}
  toydev:
    role: dev
    version: "1.0"
    link_as: data/raw/dev/toydev
    sources: []
"""


def test_sums_roundtrip_and_scan(tmp_path):
    root = tmp_path / "r"
    sums = make_robot_dir(root)
    assert R.scan_files(root) == sorted(sums)          # _derived・.git・先頭の SHA256SUMS.txt は対象外
    made = R.make_sums(root)
    assert made == sums
    R.write_sums(root, made)
    assert R.read_sums(root / R.SUMS) == sums
    assert R.verify_sums(root, sums) == []
    (root / "a.step").write_bytes(b"changed")
    assert any("a.step" in p for p in R.verify_sums(root, sums))


def test_migrate_dry_run_changes_nothing(env):
    cat = write_catalog(env["cat"], CAT)
    src = env["proj"] / "data" / "raw" / "toy"
    make_robot_dir(src)
    before = sorted(p.as_posix() for p in src.rglob("*"))
    plans = R.plan_migrate(env["proj"], cat)
    assert [p["robot"] for p in plans] == ["toy"]
    R.migrate_one(env["proj"], plans[0], apply=False, log=lambda *a: None)
    assert src.is_dir() and not src.is_symlink()
    assert sorted(p.as_posix() for p in src.rglob("*")) == before
    assert not env["cache"].exists()


def test_migrate_apply_moves_links_and_locks(env):
    cat = write_catalog(env["cat"], CAT)
    proj = env["proj"]
    src = proj / "data" / "raw" / "toy"
    sums = make_robot_dir(src)
    (proj / "data" / "raw" / "stray").mkdir()           # 一覧に無いものは触らない
    plans = R.plan_migrate(proj, cat)
    assert any(p["robot"] is None and p["src"].name == "stray" for p in plans)
    rep = R.migrate_one(proj, [p for p in plans if p["robot"] == "toy"][0], apply=True, log=lambda *a: None)
    raw = env["cache"] / "toy" / "abc12345" / "raw"
    assert src.is_symlink() and src.resolve() == raw.resolve()
    assert R.read_sums(raw / R.SUMS) == sums             # 全ファイルの控え（既存の控えの上位集合）
    assert rep["added_entries"] == 2
    # 派生物は derived/ へ。古いパスはリンクで残る
    dd = env["cache"] / "toy" / "abc12345" / "derived" / "tree@2026-01-01"
    assert (dd / "t.json").exists() and (dd / R.SUMS).exists() and (dd / "PIPELINE.yaml").exists()
    assert (src / "_derived" / "tree" / "t.json").read_text() == "{}"
    assert (src / "_derived" / "notes.txt").read_text() == "x"
    assert (src / "_derived" / "tree").is_symlink()
    # 控え（robots/sums/）とロック
    assert R.read_sums(env["tmp"] / "robots" / "sums" / "toy" / "abc12345.txt") == sums
    lock = R.load_lock(proj)
    assert lock["toy"]["version"] == "abc12345"
    assert lock["toy"]["sums_sha256"] == R.sha256_file(raw / R.SUMS)
    assert set(lock["toy"]["derived"]) == {"tree@2026-01-01", "text@2026-01-01"}
    assert (proj / "data" / "raw" / "stray").is_dir()
    assert R.check_project(proj, cat, log=lambda *a: None)
    assert R.check_cache(cat, log=lambda *a: None)
    # 2 回目は何もしない
    assert [p for p in R.plan_migrate(proj, cat) if p["robot"]] == []


def test_migrate_refuses_when_existing_sums_do_not_match(env):
    cat = write_catalog(env["cat"], CAT)
    src = env["proj"] / "data" / "raw" / "toy"
    make_robot_dir(src)
    (src / "a.step").write_bytes(b"corrupted")
    plan = R.plan_migrate(env["proj"], cat)[0]
    with pytest.raises(RuntimeError):
        R.migrate_one(env["proj"], plan, apply=True, log=lambda *a: None)
    assert src.is_dir() and not src.is_symlink() and (src / "a.step").read_bytes() == b"corrupted"
    assert not (env["cache"] / "toy" / "abc12345" / "raw").exists()


def test_migrate_second_project_reuses_cache(env, tmp_path):
    cat = write_catalog(env["cat"], CAT)
    a = env["proj"]
    make_robot_dir(a / "data" / "raw" / "toydev")       # link_as は data/raw/dev/toydev。ここは一覧に無い場所
    (a / "data" / "raw" / "dev").mkdir()
    os.rename(a / "data" / "raw" / "toydev", a / "data" / "raw" / "dev" / "toydev")
    R.migrate_one(a, [p for p in R.plan_migrate(a, cat) if p["robot"] == "toydev"][0], apply=True, log=lambda *x: None)
    b = tmp_path / "projb"
    (b / "data" / "raw" / "dev").mkdir(parents=True)
    (b / "research.yaml").write_text("x: 1\n")
    make_robot_dir(b / "data" / "raw" / "dev" / "toydev")
    rep = R.migrate_one(b, [p for p in R.plan_migrate(b, cat) if p["robot"] == "toydev"][0], apply=True, log=lambda *x: None)
    assert "手元の写しを消した" in rep["action"]
    assert (b / "data" / "raw" / "dev" / "toydev").is_symlink()
    assert R.check_project(b, cat, log=lambda *x: None)


def test_check_detects_tampering_and_broken_link(env):
    cat = write_catalog(env["cat"], CAT)
    proj = env["proj"]
    make_robot_dir(proj / "data" / "raw" / "toy")
    R.migrate_one(proj, R.plan_migrate(proj, cat)[0], apply=True, log=lambda *a: None)
    raw = env["cache"] / "toy" / "abc12345" / "raw"
    (raw / "docs" / "manual.pdf").write_bytes(b"tampered")
    assert not R.check_project(proj, cat, log=lambda *a: None)
    assert R.check_project(proj, cat, deep=False, log=lambda *a: None)   # --quick は中身を見ない
    (raw / "docs" / "manual.pdf").write_bytes(b"%PDF")
    link = proj / "data" / "raw" / "toy"
    link.unlink()
    link.symlink_to(env["tmp"])
    assert not R.check_project(proj, cat, log=lambda *a: None)


def test_link_refuses_real_directory(env):
    cat = write_catalog(env["cat"], CAT)
    make_robot_dir(R.raw_dir("toy", "abc12345"))
    R.write_sums(R.raw_dir("toy", "abc12345"), R.make_sums(R.raw_dir("toy", "abc12345")))
    (env["proj"] / "data" / "raw" / "toy").mkdir()
    with pytest.raises(SystemExit):
        R.link("toy", cat["toy"], env["proj"], log=lambda *a: None)


def _git(*args, cwd):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def test_fetch_git_sparse_map_and_url(env, tmp_path):
    # 手元の git リポジトリと file:// の URL で、ネットに出ずに fetch を確かめる
    repo = tmp_path / "upstream"
    (repo / "descriptions" / "bot" / "assets").mkdir(parents=True)
    (repo / "descriptions" / "bot" / "bot.urdf").write_text("<robot/>")
    (repo / "descriptions" / "bot" / "assets" / "m.stl").write_bytes(b"solid m")
    (repo / "docs").mkdir()
    (repo / "docs" / "manual.pdf").write_bytes(b"%PDF-1")
    (repo / "big.bin").write_bytes(b"x" * 100)
    (repo / "[weird] name.txt").write_text("w")
    _git("init", "-q", cwd=repo)
    _git("config", "uploadpack.allowFilter", "true", cwd=repo)
    _git("config", "uploadpack.allowAnySHA1InWant", "true", cwd=repo)
    _git("-c", "user.email=t@t", "-c", "user.name=t", "add", "-A", cwd=repo)
    _git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init", cwd=repo)
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True).stdout.strip()
    asset = tmp_path / "release.tar.gz"
    asset.write_bytes(b"tarball")
    cat = write_catalog(env["cat"], f"""
robots:
  bot:
    role: dev
    version: "{commit[:8]}"
    sources:
      - method: git
        repo: file://{repo}
        commit: {commit}
        include: ["/descriptions/bot/", "/docs/manual.pdf"]
        map:
          descriptions/bot/: repo_x/
          docs/manual.pdf: manual_v1.pdf
      - method: url
        url: file://{asset}
        dest: release.tar.gz
        sha256: {sha(b"tarball")}
""")
    raw = R.fetch("bot", cat["bot"], log=lambda *a: None)
    assert sorted(R.read_sums(raw / R.SUMS)) == ["manual_v1.pdf", "release.tar.gz", "repo_x/assets/m.stl", "repo_x/bot.urdf"]
    assert not (raw / "big.bin").exists()
    assert R.verify_sums(raw, R.read_sums(raw / R.SUMS)) == []
    # 2 回目は取らない
    (raw / "marker").write_text("1")
    R.fetch("bot", cat["bot"], log=lambda *a: None)
    assert (raw / "marker").exists()
    # 控え（robots/sums/）があれば、その分だけを取る（include_from_manifest、特殊な文字のパス）
    man = {"x/[weird] name.txt": sha(b"w"), "x/docs/manual.pdf": sha(b"%PDF-1")}
    mf = R.manifest_file("bot2", "v1")
    mf.parent.mkdir(parents=True, exist_ok=True)
    R.write_sums(mf.parent, man, name=mf.name)
    cat2 = write_catalog(env["cat"], f"""
robots:
  bot2:
    version: "v1"
    sources:
      - {{method: git, repo: "file://{repo}", commit: {commit}, dest: x, include_from_manifest: true}}
""")
    raw2 = R.fetch("bot2", cat2["bot2"], log=lambda *a: None)
    assert R.read_sums(raw2 / R.SUMS) == man


def test_fetch_rejects_wrong_sha(env, tmp_path):
    asset = tmp_path / "a.bin"
    asset.write_bytes(b"real")
    cat = write_catalog(env["cat"], f"""
robots:
  bad:
    version: "1"
    sources:
      - {{method: url, url: "file://{asset}", dest: a.bin, sha256: "{'0' * 64}"}}
""")
    with pytest.raises(RuntimeError):
        R.fetch("bad", cat["bad"], log=lambda *a: None)
    assert not (R.raw_dir("bad", "1") / R.SUMS).exists()


def test_real_catalog_is_well_formed(monkeypatch):
    monkeypatch.delenv("RL_ROBOT_CATALOG", raising=False)
    cat = R.load_catalog()
    for robot, e in cat.items():
        assert isinstance(e["version"], str), robot          # 3e824107 のような版が数値にならない
        assert e.get("role") in ("test", "dev", "other"), robot
        assert e.get("licenses", {}).get("hardware"), robot
        for s in e.get("sources") or []:
            assert s["method"] in ("git", "url", "unzip", "snapshot", "manual"), robot
            if s["method"] == "git":
                assert len(s["commit"]) == 40, robot          # commit は 40 桁で固定
            if s["method"] == "url" and "releases/download" in s["url"]:
                assert len(s.get("sha256", "")) == 64, robot
        for d in e.get("derived") or []:
            assert d.get("location", "cache") in ("cache", "project")
            for sc in d.get("scripts") or []:
                assert not sc.startswith("/"), sc


def test_fetch_skips_pending(env):
    """公開待ちの機種は取りに行かず、キャッシュも作らない。"""
    from rlkit import robots as R
    logs = []
    entry = {"role": "other", "version": "pending", "pending": "まだ公開されていない", "sources": []}
    assert R.fetch("future_bot", entry, log=logs.append) is None
    assert any("公開待ち" in m for m in logs)
    assert not (env["cache"] / "future_bot").exists()
