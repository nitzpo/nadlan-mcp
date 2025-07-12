#!/usr/bin/env python3
"""
Run script for FastMCP Israeli Real Estate Server

This script runs the FastMCP server for accessing Israeli government real estate data.
"""

if __name__ == "__main__":
    from nadlan_mcp.fastmcp_server import mcp
    mcp.run() 