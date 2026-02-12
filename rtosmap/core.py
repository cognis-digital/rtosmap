"""Core engine for RTOSMAP.

Pure-stdlib parsing + analysis. A library user imports `parse_map` /
`analyze` / `analyze_text` and gets structured results back.

The analysis computes, per task, the stack headroom (free bytes) and the
used fraction, then classifies a severity using two configurable thresholds:

  * warn_pct  - used fraction at/above which a task is a WARNING
  * fail_pct  - used fraction at/above which a task is CRITICAL

We also detect structural problems independent of usage:

  * OVERFLOW   - peak usage already exceeds allocated stack
  * INVALID    - non-positive / nonsensical stack size
  * MISSING    - peak usage unknown (recorded as a separate finding so CI
                 can decide whether unmeasured tasks are acceptable)
"""
from __future__ import annotations

import enum
import re
from dataclasses import dataclass, field, asdict
from typing import Iterable, Optional


class Severity(enum.IntEnum):
    """Ordered so max()/sorting works and JSON shows the name."""
    OK = 0
    INFO = 1
    WARNING = 2
    CRITICAL = 3

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.name


_SIZE_RE = re.compile(r"^(\d+)\s*(k|kb|kib)?$", re.IGNORECASE)


def _parse_size(token: str) -> Optional[int]:
    """Parse a byte size that may carry a K/KB/KiB suffix. None if unknown."""
    token = token.strip()
    if token in ("", "-", "?", "n/a", "na", "unknown"):
        return None
    m = _SIZE_RE.match(token)
    if not m:
        raise ValueError(f"invalid size token: {token!r}")
    value = int(m.group(1))
    if m.group(2):
        value *= 1024
    return value


@dataclass
class Task:
    """One RTOS task / thread and its stack accounting."""
    name: str
    stack_size: int
    peak_used: Optional[int] = None
    priority: Optional[int] = None
    line_no: int = 0

    @property
    def free(self) -> Optional[int]:
        if self.peak_used is None:
            return None
        return self.stack_size - self.peak_used

    @property
    def used_pct(self) -> Optional[float]:
        if self.peak_used is None or self.stack_size <= 0:
            return None
        return self.peak_used / self.stack_size


@dataclass
class Finding:
    """A single analysis result for a task."""
    task: str
    severity: Severity
    used_pct: Optional[float]
    free: Optional[int]
    stack_size: int
    peak_used: Optional[int]
    message: str
    line_no: int = 0

    def to_dict(self) -> dict:
        d = asdict(self)
        d["severity"] = self.severity.name
        if self.used_pct is not None:
            d["used_pct"] = round(self.used_pct, 4)
        return d


@dataclass
class Report:
    findings: list[Finding] = field(default_factory=list)
    tasks: list[Task] = field(default_factory=list)

    @property
    def worst(self) -> Severity:
        if not self.findings:
            return Severity.OK
        return max(f.severity for f in self.findings)

    def counts(self) -> dict:
        out = {s.name: 0 for s in Severity}
        for f in self.findings:
            out[f.severity.name] += 1
        return out

    def to_dict(self) -> dict:
        return {
            "worst": self.worst.name,
            "counts": self.counts(),
            "total_stack_bytes": sum(t.stack_size for t in self.tasks if t.stack_size > 0),
            "findings": [f.to_dict() for f in self.findings],
        }


def parse_map(text: str) -> list[Task]:
    """Parse the RTOS stack map text into Task records.

    Format per line: name stack_size peak_used [priority]
    '#' comments and blank lines ignored. Raises ValueError with a line
    number on malformed input.
    """
    tasks: list[Task] = []
    seen: set[str] = set()
    for i, raw in enumerate(text.splitlines(), start=1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 2:
            raise ValueError(
                f"line {i}: expected at least '<name> <stack_size>', got {raw!r}"
            )
        name = parts[0]
        if name in seen:
            raise ValueError(f"line {i}: duplicate task name {name!r}")
        seen.add(name)
        try:
            stack_size = _parse_size(parts[1])
        except ValueError as e:
            raise ValueError(f"line {i}: {e}") from None
        if stack_size is None:
            raise ValueError(f"line {i}: stack size is required for task {name!r}")
        peak_used = None
        if len(parts) >= 3:
            try:
                peak_used = _parse_size(parts[2])
            except ValueError as e:
                raise ValueError(f"line {i}: {e}") from None
        priority = None
        if len(parts) >= 4:
            try:
                priority = int(parts[3])
            except ValueError:
                raise ValueError(
                    f"line {i}: priority must be an integer, got {parts[3]!r}"
                ) from None
        tasks.append(
            Task(
                name=name,
                stack_size=stack_size,
                peak_used=peak_used,
                priority=priority,
                line_no=i,
            )
        )
    return tasks


def _classify(task: Task, warn_pct: float, fail_pct: float) -> Finding:
    """Produce a single Finding for a task."""
    common = dict(
        task=task.name,
        used_pct=task.used_pct,
        free=task.free,
        stack_size=task.stack_size,
        peak_used=task.peak_used,
        line_no=task.line_no,
    )

    if task.stack_size <= 0:
        return Finding(
            severity=Severity.CRITICAL,
            message=f"invalid stack size ({task.stack_size} bytes)",
            **common,
        )

    if task.peak_used is None:
        return Finding(
            severity=Severity.INFO,
            message="no high-water-mark recorded; stack usage unverified",
            **common,
        )

    if task.peak_used > task.stack_size:
        over = task.peak_used - task.stack_size
        return Finding(
            severity=Severity.CRITICAL,
            message=(
                f"STACK OVERFLOW: peak {task.peak_used}B exceeds allocated "
                f"{task.stack_size}B by {over}B"
            ),
            **common,
        )

    pct = task.used_pct or 0.0
    if pct >= fail_pct:
        return Finding(
            severity=Severity.CRITICAL,
            message=(
                f"critically low headroom: {pct*100:.1f}% used, "
                f"only {task.free}B free"
            ),
            **common,
        )
    if pct >= warn_pct:
        return Finding(
            severity=Severity.WARNING,
            message=(
                f"low headroom: {pct*100:.1f}% used, {task.free}B free"
            ),
            **common,
        )
    return Finding(
        severity=Severity.OK,
        message=f"healthy: {pct*100:.1f}% used, {task.free}B free",
        **common,
    )


def analyze(
    tasks: Iterable[Task],
    warn_pct: float = 0.80,
    fail_pct: float = 0.90,
) -> Report:
    """Analyze parsed tasks and return a Report.

    warn_pct/fail_pct are used-fraction thresholds in [0, 1].
    """
    if not (0.0 < warn_pct <= 1.0) or not (0.0 < fail_pct <= 1.0):
        raise ValueError("thresholds must be in (0, 1]")
    if fail_pct < warn_pct:
        raise ValueError("fail_pct must be >= warn_pct")
    task_list = list(tasks)
    findings = [_classify(t, warn_pct, fail_pct) for t in task_list]
    # Sort worst-first, then by used fraction descending for stable triage.
    findings.sort(
        key=lambda f: (-int(f.severity), -(f.used_pct or 0.0), f.task)
    )
    return Report(findings=findings, tasks=task_list)


def analyze_text(
    text: str,
    warn_pct: float = 0.80,
    fail_pct: float = 0.90,
) -> Report:
    """Convenience: parse + analyze in one call."""
    return analyze(parse_map(text), warn_pct=warn_pct, fail_pct=fail_pct)
