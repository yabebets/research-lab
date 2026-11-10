"""tests/annotate の共通の準備。lib/ を import の道に足す。

実行: uv run --with pytest --with ruamel.yaml --with jsonschema pytest tests/annotate -q
"""
import sys
from pathlib import Path

import pytest

RL = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RL / "lib"))
FIX = Path(__file__).resolve().parent / "fixtures"
RL_STATS = RL / "skills" / "ml-rigor" / "scripts" / "rl_stats.py"
TRIAL = RL / "projects" / "robot-assembly-bench" / "notes" / "ir-trial"


@pytest.fixture
def minimal(tmp_path):
    """最小の v0.2 を一時フォルダに写したパス。"""
    p = tmp_path / "toy.yaml"
    p.write_text((FIX / "minimal_v02.yaml").read_text())
    return p
