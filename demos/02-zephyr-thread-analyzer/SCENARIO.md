# Demo 02 — Zephyr thread analyzer on an nRF5340 (BLE)

## Where the data came from

A Nordic nRF5340 dev kit running a Zephyr + Bluetooth LE peripheral build
with `CONFIG_THREAD_ANALYZER=y`. The thread analyzer prints, per thread,
the stack size and the number of *unused* bytes seen so far. We converted
each line to `peak_used = stack_size - unused` and recorded it as
`<name> <stack_size> <peak_used> [priority]` in `threads.map`.

This is exactly the kind of snapshot you would capture from a soak test or
a connected-stress run and then diff in CI on every firmware PR.

## What to expect

The BLE controller path is the danger zone:

- `bt_rx`     — 96.7% used → **CRITICAL**. The receive thread spikes when
  multiple ATT/L2CAP packets arrive back-to-back; 68B of headroom is not
  enough margin for an ISR tail-call.
- `mpsl_work` — 98.6% used → **CRITICAL**. The Multiprotocol Service Layer
  work thread is at 14B free — effectively one push away from corruption.
- Everything else (main, sysworkq, logging, shell, idle, bt_tx) is healthy.

## Run it

```bash
python -m rtosmap check demos/02-zephyr-thread-analyzer/threads.map
```

## How to act

Bump `CONFIG_BT_RX_STACK_SIZE` and the MPSL work-queue stack by at least
512B each, re-run the soak test, and re-capture the map. Gate the PR with:

```bash
python -m rtosmap check demos/02-zephyr-thread-analyzer/threads.map --fail 90
```

Exit code is **1** until the two controller threads drop below 90% used.
