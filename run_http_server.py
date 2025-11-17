#!/usr/bin/env python3
"""
HTTP Server Entry Point for Nadlan-MCP

This module provides an HTTP/SSE transport server for the Nadlan-MCP service,
enabling deployment to cloud platforms like Render, Railway, or Docker containers.

For local Claude Desktop integration, use run_fastmcp_server.py (stdio transport) instead.
"""

import os
import sys
import logging
import uvicorn
from nadlan_mcp.fastmcp_server import mcp

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Run the FastMCP server with HTTP transport using uvicorn."""
    # Get port from environment variable (Render sets PORT automatically)
    port = int(os.environ.get("PORT", 8000))
    host = "0.0.0.0"

    logger.info("=" * 60)
    logger.info("Starting Nadlan-MCP HTTP Server")
    logger.info("=" * 60)
    logger.info(f"Transport: HTTP (via uvicorn)")
    logger.info(f"Host: {host}")
    logger.info(f"Port: {port}")
    logger.info(f"MCP Endpoint: http://{host}:{port}/mcp")
    logger.info(f"Health Check: http://{host}:{port}/health")
    logger.info("=" * 60)

    try:
        # Get the HTTP ASGI app from FastMCP
        # Try different possible method names based on FastMCP version
        if hasattr(mcp, 'streamable_http_app'):
            app = mcp.streamable_http_app()
        elif hasattr(mcp, 'http_app'):
            app = mcp.http_app()
        elif hasattr(mcp, 'get_app'):
            app = mcp.get_app()
        else:
            # Fallback: try to access the app directly
            app = getattr(mcp, 'app', None)
            if app is None:
                raise AttributeError(
                    "FastMCP instance has no HTTP app method. "
                    "Available methods: " + ", ".join(dir(mcp))
                )

        logger.info(f"Using app: {type(app).__name__}")

        # Run with uvicorn
        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level="info"
        )
    except Exception as e:
        logger.error(f"Failed to start HTTP server: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
