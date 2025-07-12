"""
Israel Real Estate MCP

A Python-based Mission Control Program to interact with the Israeli government's
public real estate data API (Govmap).
"""

from .main import GovmapClient

__version__ = "1.0.0"
__all__ = ["GovmapClient"] 