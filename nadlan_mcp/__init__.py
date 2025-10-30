"""
Israel Real Estate MCP

A Python-based Mission Control Program to interact with the Israeli government's
public real estate data API (Govmap).
"""

from .govmap import GovmapClient
from .govmap.models import (
    Address,
    AutocompleteResponse,
    AutocompleteResult,
    CoordinatePoint,
    Deal,
    DealFilters,
    DealStatistics,
    InvestmentAnalysis,
    LiquidityMetrics,
    MarketActivityScore,
)

__version__ = "2.0.0"  # Breaking change: Pydantic models integration (Phase 4.1)
__all__ = [
    "GovmapClient",
    # Pydantic models
    "CoordinatePoint",
    "Address",
    "AutocompleteResult",
    "AutocompleteResponse",
    "Deal",
    "DealStatistics",
    "MarketActivityScore",
    "InvestmentAnalysis",
    "LiquidityMetrics",
    "DealFilters",
]
