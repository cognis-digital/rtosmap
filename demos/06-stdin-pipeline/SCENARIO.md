# Demo 06 — Pipe a live ThreadX capture in over stdin

## Where the data came from

An automotive body-control module (NXP S32K, Azure RTOS / ThreadX). ThreadX
pre-fills every thread stack with `0xEFEFEFEF`; the lowest stack word that is
no longer the fill value marks the high-water mark. A small on-target shell
command walks each thread control block and prints
`<name> <stack_size> <peak_used> <priority>` — which is exactly rtosmap's
input format, so you can pipe it straight in with `-` (read from stdin) and
never touch a file.

## What to expect

- `diag_uds`   — 96.4% used → **CRITICAL** (112B free). The UDS diagnostic
  service blows up during a multi-frame ISO-TP transfer.
- `canopen_rx` — 91.8% used → **CRITICAL** (168B free).
- Everything else is healthy.

`worst = CRITICAL`, exit code **1**.

## Run it

Pipe the bundled capture (stand-in for the live device output):

```bash
cat demos/06-stdin-pipeline/threadx.map | python -m rtosmap check -
```

Or straight off the target over a serial bridge:

```bash
ssh ecu 'tx_stack_dump' | python -m rtosmap check - --format json | jq '.counts'
```

## How to act

Grow `diag_uds` and `canopen_rx` by 512B each. Because this reads stdin,
the same one-liner drops into a flashing/soak script with zero temp files.
