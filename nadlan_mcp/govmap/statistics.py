"""
Statistical calculation functions for deal data.

This module provides pure mathematical functions for analyzing real estate deal data.
"""

from collections import Counter
from typing import Any, Dict, List


def calculate_deal_statistics(deals: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate statistical aggregations on deal data.

    Args:
        deals: List of deal dictionaries

    Returns:
        Dictionary with statistical metrics

    Raises:
        ValueError: If deals is not a valid list
    """
    if not isinstance(deals, list):
        raise ValueError("deals must be a list")

    if not deals:
        return {
            "count": 0,
            "price_stats": {},
            "area_stats": {},
            "price_per_sqm_stats": {},
            "room_distribution": {},
        }

    # Extract numeric values
    prices = []
    areas = []
    price_per_sqm_values = []
    rooms = []

    for deal in deals:
        price = deal.get("dealAmount")
        if isinstance(price, (int, float)) and price > 0:
            prices.append(price)

        area = deal.get("assetArea")
        if isinstance(area, (int, float)) and area > 0:
            areas.append(area)

        pps = deal.get("price_per_sqm")
        if pps is None and price and area and area > 0:
            pps = price / area
        if isinstance(pps, (int, float)) and pps > 0:
            price_per_sqm_values.append(pps)

        room_count = deal.get("assetRoomNum")
        if isinstance(room_count, (int, float)):
            rooms.append(room_count)

    # Calculate statistics
    stats: Dict[str, Any] = {"count": len(deals)}

    # Price statistics
    if prices:
        sorted_prices = sorted(prices)
        stats["price_stats"] = {
            "mean": round(sum(prices) / len(prices), 2),
            "median": sorted_prices[len(sorted_prices) // 2],
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
        stats["area_stats"] = {
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
        stats["price_per_sqm_stats"] = {
            "mean": round(sum(price_per_sqm_values) / len(price_per_sqm_values), 2),
            "median": round(sorted_pps[len(sorted_pps) // 2], 2),
            "min": round(min(price_per_sqm_values), 2),
            "max": round(max(price_per_sqm_values), 2),
            "p25": round(sorted_pps[len(sorted_pps) // 4], 2),
            "p75": round(sorted_pps[(3 * len(sorted_pps)) // 4], 2),
        }

    # Room distribution
    if rooms:
        room_counts = Counter(rooms)
        stats["room_distribution"] = dict(sorted(room_counts.items()))

    return stats


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
