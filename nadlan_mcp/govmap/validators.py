"""
Input validation functions for Govmap API client.

This module provides pure validation functions with no dependencies on other modules.
All functions are stateless and raise ValueError on validation failure.
"""

import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def validate_address(address: str) -> str:
    """
    Validate and sanitize address input.

    Args:
        address: Address string to validate

    Returns:
        Sanitized address string

    Raises:
        ValueError: If address is invalid
    """
    if not address or not isinstance(address, str):
        raise ValueError("Address must be a non-empty string")
    address = address.strip()
    if not address:
        raise ValueError("Address cannot be empty or whitespace only")
    if len(address) > 500:
        raise ValueError("Address is too long (max 500 characters)")
    return address


def validate_coordinates(point: Tuple[float, float]) -> Tuple[float, float]:
    """
    Validate coordinate input.

    Args:
        point: Tuple of (longitude, latitude) in ITM projection

    Returns:
        Validated coordinate tuple

    Raises:
        ValueError: If coordinates are invalid
    """
    if not isinstance(point, (tuple, list)) or len(point) != 2:
        raise ValueError("Point must be a tuple of (longitude, latitude)")
    try:
        lon, lat = float(point[0]), float(point[1])
    except (TypeError, ValueError):
        raise ValueError("Coordinates must be numeric values")

    # Basic validation for Israeli coordinates (ITM projection)
    # ITM bounds for Israel: X (longitude) ~150,000-300,000, Y (latitude) ~3,500,000-4,000,000
    if not (150000 <= lon <= 300000):  # ITM longitude bounds for Israel
        logger.warning(f"Longitude {lon} appears to be outside Israeli ITM bounds (150,000-300,000)")
    if not (3500000 <= lat <= 4000000):  # ITM latitude bounds for Israel
        logger.warning(f"Latitude {lat} appears to be outside Israeli ITM bounds (3,500,000-4,000,000)")

    return (lon, lat)


def validate_positive_int(
    value: int, name: str, max_value: Optional[int] = None
) -> int:
    """
    Validate positive integer input.

    Args:
        value: Value to validate
        name: Name of the parameter (for error messages)
        max_value: Optional maximum allowed value

    Returns:
        Validated integer

    Raises:
        ValueError: If value is invalid
    """
    if not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    if value <= 0:
        raise ValueError(f"{name} must be positive")
    if max_value and value > max_value:
        raise ValueError(f"{name} must be <= {max_value}")
    return value


def validate_deal_type(deal_type: int) -> int:
    """
    Validate deal type parameter.

    Args:
        deal_type: Deal type (1=first hand/new, 2=second hand/used)

    Returns:
        Validated deal type

    Raises:
        ValueError: If deal type is invalid
    """
    if deal_type not in (1, 2):
        raise ValueError("deal_type must be 1 (first hand) or 2 (second hand)")
    return deal_type
