# Demo 01 - Basic stack-risk check

This demo runs RTOSMAP against a small FreeRTOS-style stack map
(`tasks.map`) describing six tasks. Each line is:

```
<task_name> <stack_size_bytes> <peak_used_bytes> [priority]
```

Sizes may use a `K`/`KB` suffix (so `4K` == 4096). Lines starting with
`#` are comments. This is the single line-per-task summary you would emit
from `uxTaskGetStackHighWaterMark` (FreeRTOS), the Zephyr thread analyzer,
or a ThreadX stack dump.

## Input (`tasks.map`)

- `idle`     — tiny, healthy.
- `logger`   — comfortable headroom.
- `sensor`   — 82% used → **WARNING** (low headroom).
- `wifi`     — 94% used → **CRITICAL** (critically low headroom).
- `crypto`   — peak 4500B on a 4096B (`4K`) stack → **CRITICAL** (overflow).
- `audit`    — no high-water-mark recorded → **INFO** (unverified).

## Run it

```bash
python -m rtosmap check demos/01-basic/tasks.map
# or JSON for CI:
python -m rtosmap check demos/01-basic/tasks.map --format json
```

## Expected result

- Two **CRITICAL** findings (`crypto` overflow, `wifi` low headroom).
- One **WARNING** (`sensor`).
- One **INFO** (`audit`, no high-water-mark).
- `worst` = `CRITICAL`.
- Process exit code **1** (CI gate fails), because a CRITICAL exists.

With default thresholds (warn 80%, fail 90%) the `crypto` and `wifi`
tasks are the stack-overflow risks a reviewer must address before merge.
