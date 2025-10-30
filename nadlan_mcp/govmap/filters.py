"""
Deal filtering functions.

This module provides composable functions for filtering real estate deal data.
"""

from typing import List, Optional, Union

from .models import Deal, DealFilters
from .utils import extract_floor_number


def filter_deals_by_criteria(
    deals: List[Deal],
    filters: Optional[Union[DealFilters, dict]] = None,
    property_type: Optional[str] = None,
    min_rooms: Optional[float] = None,
    max_rooms: Optional[float] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    min_area: Optional[float] = None,
    max_area: Optional[float] = None,
    min_floor: Optional[int] = None,
    max_floor: Optional[int] = None,
) -> List[Deal]:
    """
    Filter deals by various criteria.

    Can accept either a DealFilters model or individual filter parameters.
    Individual parameters take precedence over filters model.

    Args:
        deals: List of Deal model instances to filter
        filters: Optional DealFilters model or dict with filter criteria
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
        Filtered list of Deal instances

    Raises:
        ValueError: If filter criteria are invalid
    """
    if not isinstance(deals, list):
        raise ValueError("deals must be a list")

    # Convert filters dict to DealFilters model if needed
    if isinstance(filters, dict):
        filters = DealFilters(**filters)

    # If filters model provided, use its values as defaults
    if filters:
        property_type = property_type or filters.property_type
        min_rooms = min_rooms if min_rooms is not None else filters.min_rooms
        max_rooms = max_rooms if max_rooms is not None else filters.max_rooms
        min_price = min_price if min_price is not None else filters.min_price
        max_price = max_price if max_price is not None else filters.max_price
        min_area = min_area if min_area is not None else filters.min_area
        max_area = max_area if max_area is not None else filters.max_area
        min_floor = min_floor if min_floor is not None else filters.min_floor
        max_floor = max_floor if max_floor is not None else filters.max_floor

    # Validate numeric ranges (Pydantic validates these too, but check anyway)
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
            deal_type = deal.property_type_description
            # Skip deals with missing property type data when filter is active
            if not deal_type:
                continue

            # Normalize both strings for flexible matching
            property_type_normalized = property_type.lower().strip()
            deal_type_normalized = deal_type.lower().strip()

            # Handle Hebrew feminine ending variations (ה ↔ ת)
            # If the filter term ends with ה, also check for the ת variant
            # This allows "דירה" to match "דירת גג", "דירה בבניין", etc.
            if property_type_normalized.endswith("ה"):
                property_type_variant = property_type_normalized[:-1] + "ת"
                if (
                    property_type_variant not in deal_type_normalized
                    and property_type_normalized not in deal_type_normalized
                ):
                    # No match found for either variant
                    continue
            else:
                # For non-ה endings, do substring match
                if property_type_normalized not in deal_type_normalized:
                    continue

        # Room count filter
        if min_rooms is not None or max_rooms is not None:
            rooms = deal.rooms
            if rooms is None:
                continue  # Skip deals with missing room data when filter is active
            if min_rooms is not None and rooms < min_rooms:
                continue
            if max_rooms is not None and rooms > max_rooms:
                continue

        # Price filter
        if min_price is not None or max_price is not None:
            price = deal.deal_amount
            if price is None:
                continue  # Skip deals with missing price data when filter is active
            if min_price is not None and price < min_price:
                continue
            if max_price is not None and price > max_price:
                continue

        # Area filter
        if min_area is not None or max_area is not None:
            area = deal.asset_area
            if area is None:
                continue  # Skip deals with missing area data when filter is active
            if min_area is not None and area < min_area:
                continue
            if max_area is not None and area > max_area:
                continue

        # Floor filter
        if min_floor is not None or max_floor is not None:
            # Use floor_number if available, otherwise try to parse floor description
            floor_num = deal.floor_number
            if floor_num is None and deal.floor:
                # Try to extract floor number (handles Hebrew floor descriptions)
                floor_num = extract_floor_number(deal.floor)

            if floor_num is not None:
                if min_floor is not None and floor_num < min_floor:
                    continue
                if max_floor is not None and floor_num > max_floor:
                    continue

        filtered_deals.append(deal)

    return filtered_deals
