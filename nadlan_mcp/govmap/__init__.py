"""
Govmap package - Israeli government real estate data API client.

This package provides a modular interface to the Govmap API for querying
Israeli real estate deals, market trends, and property information.

Public API:
    - GovmapClient: Main API client class
    - Pydantic models for type-safe data structures
    - filter_deals_by_criteria: Filter deals by various criteria
    - calculate_deal_statistics: Calculate statistical aggregations
    - calculate_market_activity_score: Market activity and trend metrics
    - analyze_investment_potential: Investment analysis and price trends
    - get_market_liquidity: Market liquidity and velocity metrics
"""

# Pydantic models
# Main API client
from .client import GovmapClient

# Filter functions
from .filters import filter_deals_by_criteria

# Market analysis functions
from .market_analysis import (
    analyze_investment_potential,
    calculate_market_activity_score,
    get_market_liquidity,
    parse_deal_dates,
)
from .models import (
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

# Statistics functions
from .statistics import calculate_deal_statistics, calculate_std_dev

# Utility functions
from .utils import calculate_distance, extract_floor_number, is_same_building

# Validation functions
from .validators import (
    validate_address,
    validate_coordinates,
    validate_deal_type,
    validate_positive_int,
)

__all__ = [
    # Main client class
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
    # Filtering
    "filter_deals_by_criteria",
    # Statistics
    "calculate_deal_statistics",
    "calculate_std_dev",
    # Market analysis
    "calculate_market_activity_score",
    "analyze_investment_potential",
    "get_market_liquidity",
    "parse_deal_dates",
    # Utilities
    "calculate_distance",
    "is_same_building",
    "extract_floor_number",
    # Validation
    "validate_address",
    "validate_coordinates",
    "validate_positive_int",
    "validate_deal_type",
]
