"""RTOSMAP MCP server — exposes analyze_text() as an MCP tool for Cognis.Studio."""
from __future__ import annotations

import json

from rtosmap.core import analyze_text


def serve() -> int:
    """Start an MCP stdio server. Requires the optional 'mcp' extra:
        pip install "cognis-rtosmap[mcp]"
    """
    try:
        from mcp.server.fastmcp import FastMCP
    except Exception:
        print("Install the MCP extra: pip install 'cognis-rtosmap[mcp]'")
        return 1
    app = FastMCP("rtosmap")

    @app.tool()
    def rtosmap_scan(map_text: str) -> str:
        """Analyze RTOS stack map text and return JSON findings.

        map_text: stack map content (one task per line:
        <name> <stack_size> <peak_used> [priority]).
        Returns JSON findings with severity, overflow, and headroom data.
        """
        try:
            report = analyze_text(map_text)
            return json.dumps(report.to_dict())
        except ValueError as exc:
            return json.dumps({"error": str(exc)})

    app.run()
    return 0
