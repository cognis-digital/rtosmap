# Demo 08 — JSON output for scripted / agent triage

## Where the data came from

An industrial protocol gateway (Cortex-M7, FreeRTOS) bridging Modbus,
OPC-UA, and MQTT. This map mixes size units on purpose — `8K`, `4KiB`,
`4KB`, and raw byte counts all appear — to show that rtosmap normalises
them (every K-form expands to 1024 bytes).

## What to expect

- `ota_agent`   — 7400B of an `8K` (8192B) stack = 90.3% → **CRITICAL**.
- `tcpip`       — 6900B of `8K` = 84.2% → **WARNING**.
- `opcua_server`— 9800B of `16K` = 59.8% → **OK** (big but well-provisioned).
- Total mapped stack: **54,784 bytes** (`total_stack_bytes` in JSON) — handy
  for RAM-budget reporting.

`worst = CRITICAL`, exit code **1**.

## Run it

```bash
python -m rtosmap check demos/08-json-triage-jq/tasks.map --format json
```

Triage with `jq` — list only the tasks that must be fixed:

```bash
python -m rtosmap check demos/08-json-triage-jq/tasks.map --format json \
  | jq -r '.findings[] | select(.severity=="CRITICAL") | "\(.task): \(.message)"'
```

Pull the RAM budget for a report:

```bash
python -m rtosmap check demos/08-json-triage-jq/tasks.map --format json \
  | jq '{worst, counts, total_stack_bytes}'
```

## How to act

The JSON contract (`worst`, `counts`, `total_stack_bytes`, `findings[]`) is
stable, so an LLM agent or a CI script can branch on `worst` and open one
issue per CRITICAL finding. Here that means a single ticket: grow
`ota_agent`'s stack before the next OTA campaign.
