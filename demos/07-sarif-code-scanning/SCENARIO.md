# Demo 07 — SARIF export into GitHub code-scanning

## Where the data came from

Smart-meter firmware on a Cortex-M4 (FreeRTOS), with DLMS/COSEM metering,
AES crypto, and a PPP modem link. The map is tuned so that **every SARIF
rule id** rtosmap can emit shows up, so you can see exactly how findings
render in the GitHub "Security → Code scanning" tab.

## What to expect

Running with `--format sarif` produces a valid **SARIF 2.1.0** log. Each
finding maps to a stable rule id so code-scanning can track and suppress it
across runs:

| Rule id                  | SARIF level | Triggered by              |
|--------------------------|-------------|---------------------------|
| `RTOS-OVERFLOW`          | error       | `crypto_aes` (peak > size)|
| `RTOS-HEADROOM-CRITICAL` | error       | `dlms_cosem`, `modem_ppp` |
| `RTOS-UNVERIFIED`        | note        | `audit_log` (no HWM)      |
| `RTOS-OK`                | none        | the healthy tasks         |

Three `error`-level results, one `note`, four `none`.

## Run it

```bash
python -m rtosmap check demos/07-sarif-code-scanning/tasks.map \
    --format sarif > rtosmap.sarif
```

Validate it is well-formed SARIF:

```bash
python -c "import json,sys; d=json.load(open('rtosmap.sarif')); \
assert d['version']=='2.1.0'; print(len(d['runs'][0]['results']),'results OK')"
```

## How to act — wire it into CI

```yaml
# .github/workflows/firmware.yml
- name: rtosmap stack scan
  run: python -m rtosmap check fw/stack.map --format sarif > rtosmap.sarif
  continue-on-error: true            # let upload run even when the gate fails
- uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: rtosmap.sarif
```

Stack-overflow and low-headroom findings then appear as annotations right on
the PR's changed files — no extra dashboard required.
