"""Dual transport: stdio (Claude Desktop) or SSE (HTTP)."""

import os
import sys

from lidar_mcp.server import mcp


def main() -> None:
    port = os.environ.get("MCP_PORT") or os.environ.get("PORT")
    if port:
        host = os.environ.get("MCP_HOST", "127.0.0.1")
        mcp.run(transport="sse", host=host, port=int(port))
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    main()
