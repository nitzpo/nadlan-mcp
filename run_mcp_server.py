#!/usr/bin/env python3
"""
Run the Israel Real Estate MCP Server

Usage:
    python run_mcp_server.py
"""

import asyncio
import sys
import os

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nadlan_mcp.mcp_server import main

if __name__ == "__main__":
    print("🏠 Starting Israel Real Estate MCP Server...")
    print("🔗 Connect your AI agent to this server to access Israeli real estate data")
    print("📊 Available tools: address search, market analysis, neighborhood comparison")
    print("=" * 70)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"❌ Server error: {e}")
        sys.exit(1) 