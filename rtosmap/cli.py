"""Command-line interface for RTOSMAP.

Examples
--------
  # Human-readable table (default)
  rtosmap check demos/01-basic/tasks.map

  # JSON for CI / piping
  rtosmap check demos/01-basic/tasks.map --format json | jq .worst

  # Custom thresholds (warn at 70%, fail at 85%)
  rtosmap check tasks.map --warn 70 --fail 85

  # Read from stdin
  cat tasks.map | rtosmap check -

Exit codes: 0 = no CRITICAL findings, 1 = at least one CRITICAL finding,
2 = usage/parse error. WARNINGs alone exit 0 unless --strict is given.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Optional

from . import TOOL_NAME, TOOL_VERSION
from .core import Severity, analyze_text, to_sarif


def _read_input(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def _render_table(report) -> str:
    rows = []
    header = ["SEV", "TASK", "USED%", "PEAK", "STACK", "FREE", "MESSAGE"]
    rows.append(header)
    for f in report.findings:
        used = "-" if f.used_pct is None else f"{f.used_pct*100:.1f}"
        peak = "-" if f.peak_used is None else str(f.peak_used)
        free = "-" if f.free is None else str(f.free)
        rows.append(
            [
                f.severity.name,
                f.task,
                used,
                peak,
                str(f.stack_size),
                free,
                f.message,
            ]
        )
    widths = [max(len(r[c]) for r in rows) for c in range(len(header))]
    lines = []
    for ri, row in enumerate(rows):
        cells = [row[c].ljust(widths[c]) for c in range(len(row))]
        lines.append("  ".join(cells).rstrip())
        if ri == 0:
            lines.append("  ".join("-" * widths[c] for c in range(len(row))))
    counts = report.counts()
    summary = (
        f"\nworst={report.worst.name}  "
        f"critical={counts['CRITICAL']} warning={counts['WARNING']} "
        f"info={counts['INFO']} ok={counts['OK']}"
    )
    return "\n".join(lines) + summary


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=TOOL_NAME,
        description=(
            "Map RTOS task stacks and flag stack-overflow risks from a "
            "stack map file."
        ),
        epilog=(
            "map format per line: <name> <stack_size> <peak_used> [priority]\n"
            "sizes accept K/KB suffix (e.g. 4K). '#' starts a comment.\n\n"
            "example: rtosmap check tasks.map --format json --warn 70 --fail 85"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version", action="version", version=f"{TOOL_NAME} {TOOL_VERSION}"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser(
        "check",
        help="analyze a stack map file and report risky tasks",
        description="Analyze a stack map file and report stack-overflow risks.",
    )
    check.add_argument(
        "mapfile",
        help="path to the RTOS stack map file, or '-' for stdin",
    )
    check.add_argument(
        "--format",
        choices=["table", "json", "sarif"],
        default="table",
        help="output format: table, json, or sarif (default: table)",
    )
    check.add_argument(
        "--warn",
        type=float,
        default=80.0,
        metavar="PCT",
        help="used%% at/above which a task is a WARNING (default: 80)",
    )
    check.add_argument(
        "--fail",
        type=float,
        default=90.0,
        metavar="PCT",
        help="used%% at/above which a task is CRITICAL (default: 90)",
    )
    check.add_argument(
        "--strict",
        action="store_true",
        help="exit non-zero on WARNING findings too (not just CRITICAL)",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "check":
        try:
            text = _read_input(args.mapfile)
        except OSError as e:
            print(f"{TOOL_NAME}: cannot read {args.mapfile!r}: {e}", file=sys.stderr)
            return 2
        try:
            report = analyze_text(
                text,
                warn_pct=args.warn / 100.0,
                fail_pct=args.fail / 100.0,
            )
        except ValueError as e:
            print(f"{TOOL_NAME}: {e}", file=sys.stderr)
            return 2

        if args.format == "json":
            print(json.dumps(report.to_dict(), indent=2))
        elif args.format == "sarif":
            uri = "stdin" if args.mapfile == "-" else args.mapfile
            print(json.dumps(to_sarif(report, artifact_uri=uri), indent=2))
        else:
            print(_render_table(report))

        worst = report.worst
        if worst >= Severity.CRITICAL:
            return 1
        if args.strict and worst >= Severity.WARNING:
            return 1
        return 0

    parser.error("unknown command")  # pragma: no cover
    return 2
