# Demo 04 — Clean baseline (CI passes, exit 0)

## Where the data came from

An STM32 / FreeRTOS motor-control board after a stack-sizing pass: every
task was given roughly 40% margin over its observed high-water mark. This
is the "known-good" map you commit as a regression guard so that a future
PR which quietly grows a stack gets caught.

## What to expect

Every task is **OK**. Worst severity is `OK`, all counters are zero, and
the process exits **0** — even under `--strict`, which would also fail on
WARNINGs. This is the green light a release branch wants to see.

## Run it

```bash
python -m rtosmap check demos/04-clean-baseline-ci/tasks.map --strict
echo "exit code: $?"   # 0
```

## How to act

Nothing to fix. Wire this exact invocation into CI as a guard:

```yaml
# .github/workflows/firmware.yml
- name: Stack headroom gate
  run: python -m rtosmap check fw/stack.map --strict
```

If a later change pushes any task past 80% used, `--strict` turns the build
red before the firmware ever ships.
