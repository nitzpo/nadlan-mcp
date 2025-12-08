"""
Utility functions for Govmap client.

This module provides shared helper functions with no external dependencies
(except standard library).
"""

import re
from typing import Optional, Tuple


def calculate_distance(point1: Tuple[float, float], point2: Tuple[float, float]) -> float:
    """
    Calculate Euclidean distance between two points in ITM coordinates.

    ITM (Israeli Transverse Mercator) uses meters as units, so Euclidean
    distance provides accurate results for distances within Israel.

    Args:
        point1: (longitude, latitude) in ITM
        point2: (longitude, latitude) in ITM

    Returns:
        Distance in meters
    """
    dx = point2[0] - point1[0]
    dy = point2[1] - point1[1]
    return (dx * dx + dy * dy) ** 0.5


def extract_shape_centroid(shape_wkt: Optional[str]) -> Optional[Tuple[float, float]]:
    """
    Extract centroid coordinates from WKT geometry (MULTIPOLYGON/POLYGON).

    Parses WKT string and calculates centroid as average of all coordinate points.

    Args:
        shape_wkt: WKT geometry string (e.g., "MULTIPOLYGON(...)")

    Returns:
        (longitude, latitude) tuple in ITM coordinates, or None if parsing fails
    """
    if not shape_wkt or not isinstance(shape_wkt, str):
        return None

    try:
        # Extract all coordinate pairs using regex
        # Matches: "number.number number.number" or "number number"
        coord_pattern = r"([\d.]+)\s+([\d.]+)"
        matches = re.findall(coord_pattern, shape_wkt)

        if not matches:
            return None

        # Calculate average (centroid)
        lons = [float(m[0]) for m in matches]
        lats = [float(m[1]) for m in matches]

        centroid_lon = sum(lons) / len(lons)
        centroid_lat = sum(lats) / len(lats)

        return (centroid_lon, centroid_lat)

    except (ValueError, ZeroDivisionError):
        return None


def is_same_building(search_address: str, deal_address: str) -> bool:
    """
    Check if a deal is from the same building as the search address.

    Args:
        search_address: The normalized search address (lowercase, stripped)
        deal_address: The normalized deal address (lowercase, stripped)

    Returns:
        True if likely the same building, False otherwise
    """
    if not search_address or not deal_address:
        return False

    # Exact match
    if search_address == deal_address:
        return True

    # Extract key components for comparison
    def extract_address_parts(addr: str) -> tuple:
        """Extract street name and number from address"""
        # Remove common prefixes/suffixes and normalize
        addr_clean = (
            addr.replace("רח'", "").replace("רחוב", "").replace("שד'", "").replace("שדרות", "")
        )
        addr_clean = addr_clean.replace("  ", " ").strip()

        # Try to extract number and street name
        parts = addr_clean.split()
        if len(parts) >= 2:
            # Look for number (could be at start or end)
            for i, part in enumerate(parts):
                if part.isdigit() or any(c.isdigit() for c in part):
                    number = part
                    street_parts = parts[:i] + parts[i + 1 :]
                    street_name = " ".join(street_parts).strip()
                    return (street_name, number)

        return (addr_clean, "")

    search_street, search_number = extract_address_parts(search_address)
    deal_street, deal_number = extract_address_parts(deal_address)

    # Same street and same number = same building
    if (
        search_street
        and deal_street
        and search_number
        and deal_number
        and search_street == deal_street
        and search_number == deal_number
    ):
        return True

    # Check if one address is contained in the other (for different formats of same address)
    return (
        len(search_address) > 5
        and len(deal_address) > 5
        and (search_address in deal_address or deal_address in search_address)
    )


def extract_floor_number(floor_str: str) -> int | None:
    """
    Extract numeric floor number from Hebrew floor description.

    Args:
        floor_str: Floor description string (e.g., "שלישית", "קומה 3", "3")

    Returns:
        Floor number or None if cannot be extracted
    """
    if not floor_str:
        return None

    # Hebrew ordinal floor names to numbers
    hebrew_floors = {
        "קרקע": 0,
        "מרתף": -1,
        "ראשונה": 1,
        "שניה": 2,
        "שלישית": 3,
        "רביעית": 4,
        "חמישית": 5,
        "שישית": 6,
        "שביעית": 7,
        "שמינית": 8,
        "תשיעית": 9,
        "עשירית": 10,
    }

    floor_lower = floor_str.lower().strip()

    # Check for direct match with Hebrew names
    for heb, num in hebrew_floors.items():
        if heb in floor_lower:
            return num

    # Try to extract number from string
    numbers = re.findall(r"\d+", floor_str)
    if numbers:
        try:
            return int(numbers[0])
        except ValueError:
            pass

    return None
