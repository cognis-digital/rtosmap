# Demo 05 — Safety-critical build with a tight headroom policy

## Where the data came from

An infusion-pump motor controller, software classified **IEC 62304 Class C**
(a failure could harm a patient). The project's coding standard mandates at
least **50% stack headroom** on every task, so the map is analysed with
`--warn 40 --fail 50` instead of the defaults.

This map deliberately contains the full range of defects a Class C design
review must surface in one shot.

## What to expect

- `occlusion_isr` — peak 1100B on a 1024B stack → **CRITICAL / STACK OVERFLOW**.
  The occlusion-detection ISR already overran. This is a stop-ship defect.
- `battery_mon`   — declared stack size `0` → **CRITICAL / invalid stack size**.
  A misconfigured `xTaskCreate` call; the task has no stack at all.
- `alarm_mgr`     — 63.5% used → **CRITICAL** under the 50% policy.
- `dose_engine`, `pump_motor`, `ui_render` → **WARNING** (above 40% used).
- `selftest`      — no high-water-mark recorded → **INFO**. Class C cannot
  ship an *unmeasured* task; instrument it and re-capture.

`worst = CRITICAL`, exit code **1**.

## Run it

```bash
python -m rtosmap check demos/05-safety-critical-tight/tasks.map --warn 40 --fail 50
```

For the audit trail, emit SARIF and attach it to the design-history file:

```bash
python -m rtosmap check demos/05-safety-critical-tight/tasks.map \
    --warn 40 --fail 50 --format sarif > stack-review.sarif
```

## How to act

Fix the overflow and the zero-size task first, instrument `selftest`, then
re-size the WARNING tasks until all are at or below 40% used.
