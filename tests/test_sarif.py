"""Tests for the SARIF 2.1.0 exporter and version wiring."""
import json
import os

from rtosmap import TOOL_NAME, TOOL_VERSION
from rtosmap.core import analyze_text, to_sarif
from rtosmap.cli import main

HERE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(HERE, ".."))
DEMO = os.path.join(ROOT, "demos", "01-basic", "tasks.map")


def _demo_text() -> str:
    with open(DEMO, "r", encoding="utf-8") as fh:
        return fh.read()


def test_version_matches_version_file():
    """The reported version must track the repo VERSION file, not a fallback."""
    with open(os.path.join(ROOT, "VERSION"), "r", encoding="utf-8") as fh:
        expected = fh.read().strip()
    assert TOOL_VERSION == expected
    assert TOOL_VERSION != "0.1.0"  # the old silent fallback


def test_sarif_envelope_shape():
    report = analyze_text(_demo_text())
    doc = to_sarif(report, artifact_uri="tasks.map")
    assert doc["version"] == "2.1.0"
    assert doc["$schema"].endswith("sarif-2.1.0.json")
    assert len(doc["runs"]) == 1
    driver = doc["runs"][0]["tool"]["driver"]
    assert driver["name"] == TOOL_NAME
    assert driver["version"] == TOOL_VERSION
    # one result per finding
    assert len(doc["runs"][0]["results"]) == len(report.findings)


def test_sarif_overflow_maps_to_error_rule():
    report = analyze_text("crypto 4K 4500")
    doc = to_sarif(report)
    res = doc["runs"][0]["results"][0]
    assert res["ruleId"] == "RTOS-OVERFLOW"
    assert res["level"] == "error"
    assert "crypto" in res["message"]["text"]


def test_sarif_rules_are_defined_for_every_result():
    """Every ruleId used by a result must have a matching rule descriptor."""
    report = analyze_text(_demo_text())
    doc = to_sarif(report)
    rule_ids = {r["id"] for r in doc["runs"][0]["tool"]["driver"]["rules"]}
    used = {res["ruleId"] for res in doc["runs"][0]["results"]}
    assert used.issubset(rule_ids)


def test_sarif_levels_track_severity():
    # invalid size -> error, low headroom warning -> warning, healthy -> none
    text = "bad 0 0\nsensor 1024 840\nidle 512 100\naudit 2048 -\n"
    report = analyze_text(text)
    doc = to_sarif(report)
    by_task = {r["properties"]["task"]: r for r in doc["runs"][0]["results"]}
    assert by_task["bad"]["level"] == "error"
    assert by_task["bad"]["ruleId"] == "RTOS-INVALID-SIZE"
    assert by_task["sensor"]["level"] == "warning"
    assert by_task["idle"]["level"] == "none"
    assert by_task["audit"]["ruleId"] == "RTOS-UNVERIFIED"
    assert by_task["audit"]["level"] == "note"


def test_sarif_region_start_line_at_least_one():
    """SARIF startLine must be >= 1 even for synthetic single-line input."""
    report = analyze_text("idle 512 100")
    doc = to_sarif(report)
    region = doc["runs"][0]["results"][0]["locations"][0]["physicalLocation"]["region"]
    assert region["startLine"] >= 1


def test_cli_sarif_format(capsys):
    rc = main(["check", DEMO, "--format", "sarif"])
    assert rc == 1  # CRITICAL present
    payload = json.loads(capsys.readouterr().out)
    assert payload["version"] == "2.1.0"
    assert payload["runs"][0]["tool"]["driver"]["name"] == "rtosmap"
    # the demo path is used as the artifact uri
    uri = payload["runs"][0]["results"][0]["locations"][0]["physicalLocation"][
        "artifactLocation"
    ]["uri"]
    assert uri.endswith("tasks.map")


def test_cli_sarif_is_valid_json_clean_input(tmp_path, capsys):
    p = tmp_path / "ok.map"
    p.write_text("idle 512 100\nlogger 2048 500\n", encoding="utf-8")
    rc = main(["check", str(p), "--format", "sarif"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert all(r["level"] == "none" for r in payload["runs"][0]["results"])
