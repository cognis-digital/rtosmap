"""Guard: every bundled demo must parse and analyze cleanly.

Keeps the demos/ scenarios honest — if a demo map file ever becomes
malformed, this fails instead of shipping a broken example.
"""
import glob
import os

import pytest

from rtosmap.core import analyze_text, parse_map, to_sarif

HERE = os.path.dirname(__file__)
DEMOS = os.path.abspath(os.path.join(HERE, "..", "demos"))

MAP_FILES = sorted(
    glob.glob(os.path.join(DEMOS, "*", "*.map"))
)


def test_demos_present():
    # 01-basic plus the added scenarios
    assert len(MAP_FILES) >= 7


@pytest.mark.parametrize("path", MAP_FILES, ids=lambda p: os.path.basename(os.path.dirname(p)))
def test_demo_parses_and_analyzes(path):
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    tasks = parse_map(text)
    assert tasks, f"{path} parsed to zero tasks"
    report = analyze_text(text)
    assert len(report.findings) == len(tasks)
    # SARIF render must not raise and must cover every finding
    doc = to_sarif(report, artifact_uri=os.path.basename(path))
    assert len(doc["runs"][0]["results"]) == len(report.findings)


@pytest.mark.parametrize("path", MAP_FILES, ids=lambda p: os.path.basename(os.path.dirname(p)))
def test_demo_has_scenario(path):
    scenario = os.path.join(os.path.dirname(path), "SCENARIO.md")
    assert os.path.isfile(scenario), f"missing SCENARIO.md beside {path}"
