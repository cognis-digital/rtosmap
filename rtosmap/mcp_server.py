"""RTOSMAP MCP server — exposes scan() as an MCP tool for Cognis.Studio."""
from __future__ import annotations
from rtosmap.core import scan, to_json

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
    def rtosmap_scan(target: str) -> str:
        """Statically map task structures, stack usage, and ISR call graphs in FreeRTOS/Zephyr firmware to flag stack overflows and priority-inversion risks.. Returns JSON findings."""
        return to_json(scan(target))

    app.run()
    return 0
