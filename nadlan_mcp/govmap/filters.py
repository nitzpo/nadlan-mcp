"""
Deal filtering functions.

This module provides composable functions for filtering real estate deal data.
"""

from typing import Any, Dict, List, Optional

from .utils import extract_floor_number


def filter_deals_by_criteria(
    deals: List[Dict[str, Any]],
    property_type: Optional[str] = None,
    min_rooms: Optional[float] = None,
    max_rooms: Optional[float] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    min_area: Optional[float] = None,
    max_area: Optional[float] = None,
    min_floor: Optional[int] = None,
    max_floor: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Filter deals by various criteria.

    Args:
        deals: List of deal dictionaries to filter
        property_type: Property type to filter by (Hebrew description)
        min_rooms: Minimum number of rooms
        max_rooms: Maximum number of rooms
        min_price: Minimum deal amount
        max_price: Maximum deal amount
        min_area: Minimum asset area (square meters)
        max_area: Maximum asset area (square meters)
        min_floor: Minimum floor number
        max_floor: Maximum floor number

    Returns:
        Filtered list of deals

    Raises:
        ValueError: If filter criteria are invalid
    """
    if not isinstance(deals, list):
        raise ValueError("deals must be a list")

    # Validate numeric ranges
    if min_rooms is not None and max_rooms is not None and min_rooms > max_rooms:
        raise ValueError("min_rooms cannot be greater than max_rooms")
    if min_price is not None and max_price is not None and min_price > max_price:
        raise ValueError("min_price cannot be greater than max_price")
    if min_area is not None and max_area is not None and min_area > max_area:
        raise ValueError("min_area cannot be greater than max_area")
    if min_floor is not None and max_floor is not None and min_floor > max_floor:
        raise ValueError("min_floor cannot be greater than max_floor")

    filtered_deals = []

    for deal in deals:
        # Property type filter
        if property_type is not None:
            deal_type = deal.get(
                "propertyTypeDescription", deal.get("assetTypeHeb", "")
            )
            # Skip deals with missing property type data when filter is active
            if not deal_type:
                continue

            # Normalize both strings for flexible matching
            property_type_normalized = property_type.lower().strip()
            deal_type_normalized = deal_type.lower().strip()

            # Check if the filter term appears in the deal type
            # This allows "דירה" to match "דירת גג", "דירה בבניין", etc.
            if property_type_normalized not in deal_type_normalized:
                continue

        # Room count filter
        if min_rooms is not None or max_rooms is not None:
            rooms = deal.get("assetRoomNum")
            if rooms is None:
                continue  # Skip deals with missing room data when filter is active
            try:
                rooms = float(rooms)
                if min_rooms is not None and rooms < min_rooms:
                    continue
                if max_rooms is not None and rooms > max_rooms:
                    continue
            except (TypeError, ValueError):
                continue  # Skip deals with invalid room data when filter is active

        # Price filter
        if min_price is not None or max_price is not None:
            price = deal.get("dealAmount")
            if price is None:
                continue  # Skip deals with missing price data when filter is active
            try:
                price = float(price)
                if min_price is not None and price < min_price:
                    continue
                if max_price is not None and price > max_price:
                    continue
            except (TypeError, ValueError):
                continue  # Skip deals with invalid price data when filter is active

        # Area filter
        if min_area is not None or max_area is not None:
            area = deal.get("assetArea")
            if area is None:
                continue  # Skip deals with missing area data when filter is active
            try:
                area = float(area)
                if min_area is not None and area < min_area:
                    continue
                if max_area is not None and area > max_area:
                    continue
            except (TypeError, ValueError):
                continue  # Skip deals with invalid area data when filter is active

        # Floor filter
        if min_floor is not None or max_floor is not None:
            floor_str = deal.get("floorNo", "")
            if floor_str and isinstance(floor_str, str):
                # Try to extract floor number (handles Hebrew floor descriptions)
                floor_num = extract_floor_number(floor_str)
                if floor_num is not None:
                    if min_floor is not None and floor_num < min_floor:
                        continue
                    if max_floor is not None and floor_num > max_floor:
                        continue

        filtered_deals.append(deal)

    return filtered_deals
