"""Smoke tests for RTOSMAP. No network, runs against the bundled demo."""
import json
import os
import subprocess
import sys

import pytest

from rtosmap import (
    TOOL_NAME,
    TOOL_VERSION,
    Severity,
    parse_map,
    analyze,
    analyze_text,
)
from rtosmap.cli import main

HERE = os.path.dirname(__file__)
DEMO = os.path.abspath(os.path.join(HERE, "..", "demos", "01-basic", "tasks.map"))


def _load_demo() -> str:
    with open(DEMO, "r", encoding="utf-8") as fh:
        return fh.read()


def test_metadata():
    assert TOOL_NAME == "rtosmap"
    assert TOOL_VERSION


def test_parse_demo():
    tasks = parse_map(_load_demo())
    names = {t.name for t in tasks}
    assert names == {"idle", "logger", "sensor", "wifi", "crypto", "audit"}
    crypto = next(t for t in tasks if t.name == "crypto")
    # 4K suffix expands to 4096
    assert crypto.stack_size == 4096
    assert crypto.peak_used == 4500
    audit = next(t for t in tasks if t.name == "audit")
    assert audit.peak_used is None


def test_kb_suffix_variants():
    tasks = parse_map("a 2KB 100\nb 1KiB 50\nc 512 10")
    sizes = {t.name: t.stack_size for t in tasks}
    assert sizes == {"a": 2048, "b": 1024, "c": 512}


def test_analyze_demo_severities():
    report = analyze_text(_load_demo())
    sev = {f.task: f.severity for f in report.findings}
    assert sev["crypto"] == Severity.CRITICAL   # overflow
    assert sev["wifi"] == Severity.CRITICAL      # 94% used
    assert sev["sensor"] == Severity.WARNING     # 82% used
    assert sev["audit"] == Severity.INFO         # no HWM
    assert sev["idle"] == Severity.OK
    assert report.worst == Severity.CRITICAL
    assert report.counts()["CRITICAL"] == 2
    assert report.counts()["WARNING"] == 1


def test_overflow_message_and_free():
    report = analyze_text("crypto 4K 4500")
    f = report.findings[0]
    assert f.severity == Severity.CRITICAL
    assert "OVERFLOW" in f.message
    assert f.free == 4096 - 4500  # negative free


def test_threshold_override():
    # sensor at 82% becomes CRITICAL if fail threshold drops to 80%.
    report = analyze_text("sensor 1024 840", warn_pct=0.70, fail_pct=0.80)
    assert report.findings[0].severity == Severity.CRITICAL


def test_findings_sorted_worst_first():
    report = analyze_text(_load_demo())
    sevs = [int(f.severity) for f in report.findings]
    assert sevs == sorted(sevs, reverse=True)


def test_invalid_stack_size_is_critical():
    report = analyze_text("bad 0 0")
    assert report.findings[0].severity == Severity.CRITICAL
    assert "invalid stack size" in report.findings[0].message


def test_parse_errors():
    with pytest.raises(ValueError):
        parse_map("only_one_field")
    with pytest.raises(ValueError):
        parse_map("dup 100 10\ndup 200 20")
    with pytest.raises(ValueError):
        parse_map("t 100 10 not_an_int")


def test_threshold_validation():
    with pytest.raises(ValueError):
        analyze([], warn_pct=0.9, fail_pct=0.8)
    with pytest.raises(ValueError):
        analyze([], warn_pct=0.0, fail_pct=0.5)


def test_to_dict_json_serializable():
    report = analyze_text(_load_demo())
    payload = report.to_dict()
    text = json.dumps(payload)  # must not raise
    back = json.loads(text)
    assert back["worst"] == "CRITICAL"
    assert back["counts"]["CRITICAL"] == 2
    assert any(fd["task"] == "crypto" for fd in back["findings"])


def test_cli_exit_code_critical(capsys):
    rc = main(["check", DEMO])
    assert rc == 1  # CRITICAL present -> CI gate fails
    out = capsys.readouterr().out
    assert "CRITICAL" in out
    assert "wifi" in out


def test_cli_json_format(capsys):
    rc = main(["check", DEMO, "--format", "json"])
    assert rc == 1
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["worst"] == "CRITICAL"


def test_cli_clean_input_exit_zero(tmp_path, capsys):
    p = tmp_path / "ok.map"
    p.write_text("idle 512 100\nlogger 2048 500\n", encoding="utf-8")
    rc = main(["check", str(p)])
    assert rc == 0
    assert "worst=OK" in capsys.readouterr().out


def test_cli_strict_warns_fail(tmp_path):
    p = tmp_path / "warn.map"
    p.write_text("sensor 1024 840\n", encoding="utf-8")
    assert main(["check", str(p)]) == 0
    assert main(["check", str(p), "--strict"]) == 1


def test_cli_bad_path_exit_two(capsys):
    rc = main(["check", "/no/such/file.map"])
    assert rc == 2


def test_module_entrypoint_version():
    out = subprocess.run(
        [sys.executable, "-m", "rtosmap", "--version"],
        capture_output=True,
        text=True,
        cwd=os.path.abspath(os.path.join(HERE, "..")),
    )
    assert out.returncode == 0
    assert TOOL_VERSION in out.stdout
