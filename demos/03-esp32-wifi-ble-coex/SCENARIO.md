# Demo 03 — ESP32-S3 WiFi + BLE coexistence under OTA load

## Where the data came from

An ESP32-S3 (ESP-IDF / FreeRTOS) running WiFi + BLE coexistence. Stack
high-water marks were captured with `uxTaskGetStackHighWaterMark()`
(converted from words to bytes) during the worst case: an **OTA firmware
pull over HTTPS while a BLE GATT client stayed connected**. Coexistence
is when stacks peak, because both radios' callbacks run deep.

## What to expect — and why we tune the thresholds

Coexistence builds run hot by design, so the default 80/90 thresholds flag
too much noise. This demo uses `--warn 75 --fail 90` to match a board
where ~88% steady-state is normal but anything sustained above 90% is a
real overflow risk.

- `wifi`         — 93.8% used → **CRITICAL** (224B free). The WiFi task is
  the one that actually needs more stack.
- `tcpip`, `btHostTask`, `btController` → **WARNING** — expected coexistence
  pressure; watch them, but they are not yet failing.
- `ota_task` is comfortable (56%) even though it has the largest stack —
  HTTPS buffers live on the heap, not the stack.

## Run it

```bash
python -m rtosmap check demos/03-esp32-wifi-ble-coex/tasks.map --warn 75 --fail 90
```

## How to act

Raise `CONFIG_ESP_WIFI_TASK_STACK_SIZE` by 512–1024B and re-test. To gate a
PR strictly (fail on the WARNINGs too, e.g. before a production release):

```bash
python -m rtosmap check demos/03-esp32-wifi-ble-coex/tasks.map --warn 75 --fail 90 --strict
```

Exit code is **1** here (a CRITICAL is present).
