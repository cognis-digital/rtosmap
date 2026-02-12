# RTOSMAP — Architecture

> Statically map task structures, stack usage, and ISR call graphs in FreeRTOS/Zephyr firmware to flag stack overflows and priority-inversion risks.

```
input ──▶ collect ──▶ rules/analyzers ──▶ score ──▶ findings ──▶ table · json
                              │                          │
                         (this repo)                 MCP tool (agents)
```

- **collect** normalizes the target (file/dir/API) into records.
- **rules/analyzers** apply the heuristics shipped in `rtosmap/core.py`.
- **score** ranks by severity.
- **MCP server** (`rtosmap mcp`) exposes `scan` for Cognis.Studio agents.

Extend by adding a rule + a test + a `demos/NN-*/SCENARIO.md`. See [CONTRIBUTING.md](../CONTRIBUTING.md).
