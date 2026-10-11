"""The static site runs templates/planner.js; it must agree with src/financial.py."""
import json
import shutil
import subprocess

import pytest

from src.data import ROOT
from src.financial import PlannerError, plan

CASES = [
    (15_000_000, 10_000_000, 6_000_000, 100_000_000, 3.46),
    (15_000_000, 10_000_000, 6_000_000, 100_000_000, 0),
    (200, 10, 10, 100, 5),
    (0, 5, 5, 100, 3),
    (-1, 10, 5, 100, 3),
    (0, 10, 5, 0, 3),
    (0, 101, 100, 1_000_000, 50),
    (0, 10, 5, 100, -60),
]


@pytest.mark.skipif(not shutil.which("node"), reason="node not installed")
def test_js_planner_matches_python():
    script = f"""
      const {{ plan }} = require({json.dumps(str(ROOT / "templates" / "planner.js"))});
      const out = {json.dumps(CASES)}.map((c) => {{ try {{ return plan(...c); }} catch (e) {{ return {{code: e.code}}; }} }});
      console.log(JSON.stringify(out));"""
    js = json.loads(subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True).stdout)
    for case, got in zip(CASES, js):
        try:
            want = plan(*case)
        except PlannerError as e:
            assert got == {"code": e.code}, case
            continue
        assert got["months_to_goal"] == want["months_to_goal"], case
        assert abs(got["inflation_adjusted_goal"] - want["inflation_adjusted_goal"]) <= 1, case
