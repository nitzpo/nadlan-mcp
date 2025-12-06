"""
Statistical calculation functions for deal data.

This module provides pure mathematical functions for analyzing real estate deal data.
"""

from collections import Counter
import logging
from typing import Dict, List, Optional

from nadlan_mcp.config import GovmapConfig, get_config

from .models import Deal, DealStatistics, OutlierReport
from .outlier_detection import filter_deals_for_analysis

logger = logging.getLogger(__name__)


def _calculate_basic_stats(deals: List[Deal]) -> Dict:
    """
    Internal helper to calculate basic statistics from a deal list.

    Args:
        deals: List of Deal model instances

    Returns:
        Dictionary with price_stats, area_stats, price_per_sqm_stats,
        property_type_dist, and date_range
    """
    # Extract numeric values
    prices = []
    areas = []
    price_per_sqm_values = []
    property_types = []
    deal_dates = []

    for deal in deals:
        # Prices
        if deal.deal_amount and deal.deal_amount > 0:
            prices.append(deal.deal_amount)

        # Areas
        if deal.asset_area and deal.asset_area > 0:
            areas.append(deal.asset_area)

        # Price per sqm (use computed field)
        if deal.price_per_sqm:
            price_per_sqm_values.append(deal.price_per_sqm)

        # Property types
        if deal.property_type_description:
            property_types.append(deal.property_type_description)

        # Deal dates
        if deal.deal_date:
            deal_dates.append(deal.deal_date)

    # Calculate statistics
    price_stats = {}
    area_stats = {}
    price_per_sqm_stats = {}

    # Price statistics
    if prices:
        sorted_prices = sorted(prices)
        price_stats = {
            "mean": round(sum(prices) / len(prices), 2),
            "median": (
                sorted_prices[len(sorted_prices) // 2]
                + sorted_prices[(len(sorted_prices) - 1) // 2]
            )
            / 2,
            "min": min(prices),
            "max": max(prices),
            "p25": sorted_prices[len(sorted_prices) // 4],
            "p75": sorted_prices[(3 * len(sorted_prices)) // 4],
            "std_dev": round(calculate_std_dev(prices), 2) if len(prices) > 1 else 0,
            "total": sum(prices),
        }

    # Area statistics
    if areas:
        sorted_areas = sorted(areas)
        area_stats = {
            "mean": round(sum(areas) / len(areas), 2),
            "median": sorted_areas[len(sorted_areas) // 2],
            "min": min(areas),
            "max": max(areas),
            "p25": sorted_areas[len(sorted_areas) // 4],
            "p75": sorted_areas[(3 * len(sorted_areas)) // 4],
        }

    # Price per sqm statistics
    if price_per_sqm_values:
        sorted_pps = sorted(price_per_sqm_values)
        price_per_sqm_stats = {
            "mean": round(sum(price_per_sqm_values) / len(price_per_sqm_values), 2),
            "median": round(sorted_pps[len(sorted_pps) // 2], 2),
            "min": round(min(price_per_sqm_values), 2),
            "max": round(max(price_per_sqm_values), 2),
            "p25": round(sorted_pps[len(sorted_pps) // 4], 2),
            "p75": round(sorted_pps[(3 * len(sorted_pps)) // 4], 2),
        }

    # Property type distribution
    property_type_dist = {}
    if property_types:
        type_counts = Counter(property_types)
        property_type_dist = dict(sorted(type_counts.items()))

    # Date range
    date_range_dict = None
    if deal_dates:
        try:
            # Convert dates to ISO strings for consistent formatting
            from datetime import date as date_type

            parsed_dates = []
            for d in deal_dates:
                try:
                    # Handle date objects (from Pydantic models)
                    if isinstance(d, date_type):
                        parsed_dates.append(d.isoformat())
                    else:
                        # Handle string dates
                        date_str = str(d)
                        # Handle ISO format with timezone (e.g., "2025-01-01T00:00:00.000Z")
                        if "T" in date_str:
                            date_str = date_str.split("T")[0]
                        parsed_dates.append(date_str)
                except (ValueError, TypeError):
                    logger.warning(f"Invalid date format: {d}")
                    continue

            if parsed_dates:
                sorted_dates = sorted(parsed_dates)
                date_range_dict = {
                    "earliest": sorted_dates[0],
                    "latest": sorted_dates[-1],
                }
        except (ValueError, TypeError):
            logger.warning("Invalid date format in date range calculation")
            pass

    return {
        "price_statistics": price_stats,
        "area_statistics": area_stats,
        "price_per_sqm_statistics": price_per_sqm_stats,
        "property_type_distribution": property_type_dist,
        "date_range": date_range_dict,
    }


def calculate_deal_statistics(
    deals: List[Deal],
    config: Optional[GovmapConfig] = None,
    iqr_multiplier: Optional[float] = None,
    include_outlier_deals: bool = True,
) -> DealStatistics:
    """
    Calculate statistical aggregations on deal data with optional outlier filtering.

    This function calculates comprehensive statistics on real estate deals, optionally
    filtering outliers based on configuration. When outlier filtering is enabled, it
    returns both original (unfiltered) and filtered statistics for transparency.

    Args:
        deals: List of Deal model instances
        config: Configuration object (optional, uses global config if not provided)
        iqr_multiplier: Override IQR multiplier (optional, uses config value if not provided)
        include_outlier_deals: If True (default), include the removed outlier deals in the outlier report
                              This allows LLMs to see what was filtered out

    Returns:
        DealStatistics model with comprehensive metrics, including:
        - Original statistics (calculated on all deals)
        - Filtered statistics (calculated after outlier removal, if enabled)
        - Outlier report (details on what was filtered out, including outlier_deals if requested)

    Raises:
        ValueError: If deals is not a valid list
    """
    if not isinstance(deals, list):
        raise ValueError("deals must be a list")

    if config is None:
        config = get_config()

    if not deals:
        return DealStatistics(
            total_deals=0,
            price_statistics={},
            area_statistics={},
            price_per_sqm_statistics={},
            property_type_distribution={},
            date_range=None,
        )

    # Step 1: Calculate statistics on original data
    original_stats = _calculate_basic_stats(deals)

    # Step 2: Apply outlier filtering if enabled
    outlier_report_data = None
    filtered_stats = None

    if (
        config.analysis_outlier_method != "none"
        and len(deals) >= config.analysis_min_deals_for_outlier_detection
    ):
        # Filter deals for analysis (primarily targeting price_per_sqm outliers)
        filtered_deals, report_dict = filter_deals_for_analysis(
            deals,
            config,
            metric="price_per_sqm",
            iqr_multiplier=iqr_multiplier,
            include_outlier_deals=include_outlier_deals,
        )

        # Create OutlierReport model
        outlier_report_data = OutlierReport(**report_dict)

        # Calculate statistics on filtered data
        if filtered_deals and len(filtered_deals) > 0:
            filtered_basic_stats = _calculate_basic_stats(filtered_deals)
            filtered_stats = {
                "filtered_deal_count": len(filtered_deals),
                "filtered_price_statistics": filtered_basic_stats["price_statistics"],
                "filtered_area_statistics": filtered_basic_stats["area_statistics"],
                "filtered_price_per_sqm_statistics": filtered_basic_stats[
                    "price_per_sqm_statistics"
                ],
            }

    # Step 3: Return comprehensive DealStatistics with both original and filtered data
    return DealStatistics(
        total_deals=len(deals),
        **original_stats,
        outlier_report=outlier_report_data,
        **(filtered_stats if filtered_stats else {}),
    )


def calculate_std_dev(values: List[float]) -> float:
    """
    Calculate standard deviation of a list of values.

    Args:
        values: List of numeric values

    Returns:
        Standard deviation
    """
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
    return variance**0.5
