"""rl sim の追加分（別の Python の venv・worker の記録・Colab のノートブック）のテスト。bin/rl をモジュールとして読む。

    uv run --with pytest --with ruamel.yaml pytest tests/robots -q
"""
from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import stat
from pathlib import Path

import pytest

RL = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def rl():
    loader = importlib.machinery.SourceFileLoader("rl_cli", str(RL / "bin" / "rl"))
    spec = importlib.util.spec_from_loader("rl_cli", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def fake_python(venv: Path, version: str) -> None:
    py = venv / "bin" / "python"
    py.parent.mkdir(parents=True)
    py.write_text(f"#!/bin/sh\necho {version}\n")
    py.chmod(py.stat().st_mode | stat.S_IEXEC)


def test_tool_venv_uses_separate_venv_when_python_differs(rl, tmp_path):
    fake_python(tmp_path / ".venv", "3.11.15")
    assert rl.tool_venv(tmp_path, "mujoco", {}) == tmp_path / ".venv"
    assert rl.tool_venv(tmp_path, "x", {"python": "3.11"}) == tmp_path / ".venv"
    assert rl.tool_venv(tmp_path, "drake", {"python": "3.12"}) == tmp_path / ".cache" / "venvs" / "drake"


def test_save_sim_lock_keeps_worker_section(rl, tmp_path):
    rl.save_sim_lock(tmp_path, {"mujoco": {"kind": "py", "packages": {"mujoco": "4.0.0"}}},
                     {"host": "dev-worker", "tools": {"mujoco": {"kind": "py", "packages": {"mujoco": "4.0.0"}}}})
    rl.save_sim_lock(tmp_path, {"mujoco": {"kind": "py", "packages": {"mujoco": "4.0.1"}}})   # 手元だけ書き直す
    data = rl.load_sim_lock_all(tmp_path)
    assert data["tools"]["mujoco"]["packages"]["mujoco"] == "4.0.1"
    assert data["worker"]["tools"]["mujoco"]["packages"]["mujoco"] == "4.0.0"


def test_colab_notebook_pins_locked_versions(rl, tmp_path):
    proj = tmp_path / "p"
    proj.mkdir()
    lock = {"mujoco": {"kind": "py", "packages": {"mujoco": "4.0.0"}, "python": "3.11.15"},
            "menagerie": {"kind": "git", "repo": "https://github.com/google-deepmind/mujoco_menagerie", "commit": "a" * 40},
            "isaacgym": {"kind": "remote", "template": "configs/sky/isaacgym.yaml"}}
    cat = rl.load_catalog()
    nb = rl.colab_notebook(proj, ["mujoco", "menagerie", "isaacgym"], cat, lock)
    text = json.dumps(nb, ensure_ascii=False)
    assert rl.COLAB_NOTE in "".join(nb["cells"][0]["source"])
    assert "mujoco==4.0.0" in text and "a" * 40 in text and "isaacgym（remote）" in text
    assert len({c["id"] for c in nb["cells"]}) == len(nb["cells"])
    for c in nb["cells"]:
        if c["cell_type"] == "code":
            compile("".join(l for l in c["source"] if not l.lstrip().startswith(("!", "%"))), "cell", "exec")
    with pytest.raises(SystemExit):
        rl.colab_notebook(proj, ["drake"], cat, lock)   # lock に無い道具は書かない


def test_worker_script_pins_uv_and_never_uses_brew(rl):
    s = rl.worker_script("echo hi")
    assert "uv==" in s and "brew" not in s and s.rstrip().endswith("echo hi")


def test_sim_catalog_new_entries(rl):
    cat = rl.load_catalog()
    for name in ("drake", "mjx", "mujoco-warp", "lerobot", "openpi", "openvla-oft", "cosmos-policy"):
        t = cat[name]
        assert t.get("license"), name
        if t["kind"] == "remote":
            assert (RL / t["template"]).exists(), name
        if t.get("repo") and t.get("ref"):
            assert len(t["ref"]) == 40, name
    assert cat["drake"]["smoke"] in rl.SMOKE and cat["lerobot"]["smoke"] in rl.SMOKE
