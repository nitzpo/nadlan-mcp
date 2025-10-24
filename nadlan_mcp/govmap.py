from datetime import datetime, timedelta
import logging
import re
import time
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

import requests

from nadlan_mcp.config import GovmapConfig, get_config

logger = logging.getLogger(__name__)

# Market activity score thresholds (deals per month)
ACTIVITY_VERY_HIGH_THRESHOLD = 10
ACTIVITY_HIGH_THRESHOLD = 5
ACTIVITY_MODERATE_THRESHOLD = 3
ACTIVITY_LOW_THRESHOLD = 1

# Price volatility thresholds (coefficient of variation %)
VOLATILITY_VERY_VOLATILE_THRESHOLD = 50
VOLATILITY_VOLATILE_THRESHOLD = 30
VOLATILITY_MODERATE_THRESHOLD = 20
VOLATILITY_STABLE_THRESHOLD = 10

# Market liquidity thresholds (deals per month)
LIQUIDITY_VERY_HIGH_THRESHOLD = 8
LIQUIDITY_HIGH_THRESHOLD = 5
LIQUIDITY_MODERATE_THRESHOLD = 2
LIQUIDITY_LOW_THRESHOLD = 0.5


class GovmapClient:
    """
    A client for interacting with the Israeli government's Govmap API.

    This class provides methods to search for properties, find block/parcel information,
    and retrieve real estate deal data with automatic retries and rate limiting.

    Attributes:
        config: Configuration object with API settings
        session: Requests session for connection pooling
        last_request_time: Timestamp of last API request for rate limiting
    """

    def __init__(self, config: Optional[GovmapConfig] = None):
        """
        Initialize the GovmapClient.

        Args:
            config: Optional configuration object. If None, uses global config.
        """
        self.config = config or get_config()
        self.base_url = self.config.base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update(
            {"Content-Type": "application/json", "User-Agent": self.config.user_agent}
        )
        self.last_request_time = 0.0

    def _rate_limit(self):
        """
        Enforce rate limiting by sleeping if necessary.

        Ensures requests don't exceed the configured requests_per_second.
        """
        min_interval = 1.0 / self.config.requests_per_second
        elapsed = time.time() - self.last_request_time
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        self.last_request_time = time.time()

    def _validate_address(self, address: str) -> str:
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

    def _validate_coordinates(self, point: Tuple[float, float]) -> Tuple[float, float]:
        """
        Validate coordinate input.

        Args:
            point: Tuple of (longitude, latitude)

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
        if not (0 < lon < 400000):  # Rough bounds for Israeli ITM longitude
            logger.warning(f"Longitude {lon} may be outside Israeli bounds")
        if not (0 < lat < 1400000):  # Rough bounds for Israeli ITM latitude
            logger.warning(f"Latitude {lat} may be outside Israeli bounds")

        return (lon, lat)

    def _validate_positive_int(
        self, value: int, name: str, max_value: Optional[int] = None
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

    def autocomplete_address(self, search_text: str) -> Dict[str, Any]:
        """
        Find the most likely match for a given address using autocomplete.

        Args:
            search_text: The address to search for (e.g., "סוקולוב 38 חולון")

        Returns:
            Dict containing the JSON response from the API with coordinates

        Raises:
            requests.RequestException: If the API request fails after retries
            ValueError: If the response is invalid or input is invalid
        """
        search_text = self._validate_address(search_text)
        url = f"{self.base_url}/search-service/autocomplete"

        payload = {
            "searchText": search_text,
            "language": "he",
            "isAccurate": False,
            "maxResults": 10,
        }

        # Retry logic with exponential backoff
        for attempt in range(self.config.max_retries + 1):
            try:
                self._rate_limit()

                logger.info(
                    f"Searching for address: {search_text} (attempt {attempt + 1}/{self.config.max_retries + 1})"
                )
                timeout = (self.config.connect_timeout, self.config.read_timeout)
                response = self.session.post(url, json=payload, timeout=timeout)
                response.raise_for_status()

                data = response.json()
                if not data or "results" not in data:
                    raise ValueError("Invalid response format from autocomplete API")

                return data

            except (requests.RequestException, requests.Timeout) as e:
                if attempt < self.config.max_retries:
                    wait_time = min(
                        self.config.retry_min_wait * (2**attempt),
                        self.config.retry_max_wait,
                    )
                    logger.warning(
                        f"Request failed (attempt {attempt + 1}), retrying in {wait_time}s: {e}"
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(
                        f"Request failed after {self.config.max_retries + 1} attempts: {e}"
                    )
                    raise
        # This line should never be reached but satisfies type checker
        raise RuntimeError(
            "Unexpected error: retry loop exited without return or raise"
        )

    def get_gush_helka(self, point: Tuple[float, float]) -> Dict[str, Any]:
        """
        Get Gush (Block) and Helka (Parcel) information for a coordinate point.

        Args:
            point: A tuple of (longitude, latitude)

        Returns:
            Dict containing the JSON response with block and parcel data

        Raises:
            requests.RequestException: If the API request fails after retries
            ValueError: If the response or input is invalid
        """
        point = self._validate_coordinates(point)
        url = f"{self.base_url}/layers-catalog/entitiesByPoint"

        payload = {"point": list(point), "layers": [{"layerId": "16"}], "tolerance": 0}

        # Retry logic with exponential backoff
        for attempt in range(self.config.max_retries + 1):
            try:
                self._rate_limit()

                logger.info(
                    f"Getting Gush/Helka for point: {point} (attempt {attempt + 1}/{self.config.max_retries + 1})"
                )
                timeout = (self.config.connect_timeout, self.config.read_timeout)
                response = self.session.post(url, json=payload, timeout=timeout)
                response.raise_for_status()

                data = response.json()
                return data

            except (requests.RequestException, requests.Timeout) as e:
                if attempt < self.config.max_retries:
                    wait_time = min(
                        self.config.retry_min_wait * (2**attempt),
                        self.config.retry_max_wait,
                    )
                    logger.warning(
                        f"Request failed (attempt {attempt + 1}), retrying in {wait_time}s: {e}"
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(
                        f"Request failed after {self.config.max_retries + 1} attempts: {e}"
                    )
                    raise
        # This line should never be reached but satisfies type checker
        raise RuntimeError(
            "Unexpected error: retry loop exited without return or raise"
        )

    def get_deals_by_radius(
        self, point: Tuple[float, float], radius: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Find real estate deals within a specified radius of a point.

        Args:
            point: A tuple of (longitude, latitude)
            radius: The search radius in meters (default: 50)

        Returns:
            List of deals found within the radius

        Raises:
            requests.RequestException: If the API request fails after retries
            ValueError: If the response or input is invalid
        """
        point = self._validate_coordinates(point)
        radius = self._validate_positive_int(radius, "radius", max_value=5000)
        url = f"{self.base_url}/real-estate/deals/{point[0]},{point[1]}/{radius}"

        # Retry logic with exponential backoff
        for attempt in range(self.config.max_retries + 1):
            try:
                self._rate_limit()

                logger.info(
                    f"Getting deals by radius for point: {point}, radius: {radius}m (attempt {attempt + 1}/{self.config.max_retries + 1})"
                )
                timeout = (self.config.connect_timeout, self.config.read_timeout)
                response = self.session.get(url, timeout=timeout)
                response.raise_for_status()

                data = response.json()
                if not isinstance(data, list):
                    raise ValueError(
                        f"Expected list response, got {type(data).__name__}"
                    )
                return data

            except (requests.RequestException, requests.Timeout) as e:
                if attempt < self.config.max_retries:
                    wait_time = min(
                        self.config.retry_min_wait * (2**attempt),
                        self.config.retry_max_wait,
                    )
                    logger.warning(
                        f"Request failed (attempt {attempt + 1}), retrying in {wait_time}s: {e}"
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(
                        f"Request failed after {self.config.max_retries + 1} attempts: {e}"
                    )
                    raise
        # This line should never be reached but satisfies type checker
        raise RuntimeError(
            "Unexpected error: retry loop exited without return or raise"
        )

    def get_street_deals(
        self,
        polygon_id: str,
        limit: int = 10,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        deal_type: int = 2,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve detailed information about deals on a specific street.

        Args:
            polygon_id: The ID of the lot's polygon
            limit: Maximum number of deals to return (default: 10)
            start_date: Start date for search in 'YYYY-MM' format
            end_date: End date for search in 'YYYY-MM' format
            deal_type: Deal type filter (1=first hand/new, 2=second hand/used, default: 2)

        Returns:
            List of detailed deal information for the street

        Raises:
            requests.RequestException: If the API request fails after retries
            ValueError: If the response or input is invalid
        """
        if not polygon_id or not isinstance(polygon_id, str):
            raise ValueError("polygon_id must be a non-empty string")
        polygon_id = polygon_id.strip()
        if not polygon_id:
            raise ValueError("polygon_id cannot be empty or whitespace only")

        limit = self._validate_positive_int(limit, "limit", max_value=1000)
        if deal_type not in (1, 2):
            raise ValueError(
                "deal_type must be 1 (first hand/new) or 2 (second hand/used)"
            )

        url = f"{self.base_url}/real-estate/street-deals/{polygon_id}"

        params: Dict[str, Any] = {"limit": limit, "dealType": deal_type}
        if start_date:
            params["startDate"] = start_date
        if end_date:
            params["endDate"] = end_date

        # Retry logic with exponential backoff
        for attempt in range(self.config.max_retries + 1):
            try:
                self._rate_limit()

                logger.info(
                    f"Getting street deals for polygon: {polygon_id}, dealType: {deal_type} (attempt {attempt + 1}/{self.config.max_retries + 1})"
                )
                timeout = (self.config.connect_timeout, self.config.read_timeout)
                response = self.session.get(url, params=params, timeout=timeout)
                response.raise_for_status()

                data = response.json()
                # API returns {data: [...], totalCount: ..., limit: ..., offset: ...}
                if isinstance(data, dict) and "data" in data:
                    if not isinstance(data["data"], list):
                        raise ValueError(
                            f"Expected list in 'data' field, got {type(data['data']).__name__}"
                        )
                    return data["data"]
                elif isinstance(data, list):
                    return data
                else:
                    raise ValueError(
                        f"Unexpected response format: {type(data).__name__}"
                    )

            except (requests.RequestException, requests.Timeout) as e:
                if attempt < self.config.max_retries:
                    wait_time = min(
                        self.config.retry_min_wait * (2**attempt),
                        self.config.retry_max_wait,
                    )
                    logger.warning(
                        f"Request failed (attempt {attempt + 1}), retrying in {wait_time}s: {e}"
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(
                        f"Request failed after {self.config.max_retries + 1} attempts: {e}"
                    )
                    raise
        # This line should never be reached but satisfies type checker
        raise RuntimeError(
            "Unexpected error: retry loop exited without return or raise"
        )

    def get_neighborhood_deals(
        self,
        polygon_id: str,
        limit: int = 10,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        deal_type: int = 2,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve deals within the same neighborhood as the given polygon_id.

        Args:
            polygon_id: The ID of the lot's polygon
            limit: Maximum number of deals to return (default: 10)
            start_date: Start date for search in 'YYYY-MM' format
            end_date: End date for search in 'YYYY-MM' format
            deal_type: Deal type filter (1=first hand/new, 2=second hand/used, default: 2)

        Returns:
            List of deals in the neighborhood

        Raises:
            requests.RequestException: If the API request fails after retries
            ValueError: If the response or input is invalid
        """
        if not polygon_id or not isinstance(polygon_id, str):
            raise ValueError("polygon_id must be a non-empty string")
        polygon_id = polygon_id.strip()
        if not polygon_id:
            raise ValueError("polygon_id cannot be empty or whitespace only")

        limit = self._validate_positive_int(limit, "limit", max_value=1000)
        if deal_type not in (1, 2):
            raise ValueError(
                "deal_type must be 1 (first hand/new) or 2 (second hand/used)"
            )

        url = f"{self.base_url}/real-estate/neighborhood-deals/{polygon_id}"

        params: Dict[str, Any] = {"limit": limit, "dealType": deal_type}
        if start_date:
            params["startDate"] = start_date
        if end_date:
            params["endDate"] = end_date

        # Retry logic with exponential backoff
        for attempt in range(self.config.max_retries + 1):
            try:
                self._rate_limit()

                logger.info(
                    f"Getting neighborhood deals for polygon: {polygon_id}, dealType: {deal_type} (attempt {attempt + 1}/{self.config.max_retries + 1})"
                )
                timeout = (self.config.connect_timeout, self.config.read_timeout)
                response = self.session.get(url, params=params, timeout=timeout)
                response.raise_for_status()

                data = response.json()
                # API returns {data: [...], totalCount: ..., limit: ..., offset: ...}
                if isinstance(data, dict) and "data" in data:
                    if not isinstance(data["data"], list):
                        raise ValueError(
                            f"Expected list in 'data' field, got {type(data['data']).__name__}"
                        )
                    return data["data"]
                elif isinstance(data, list):
                    return data
                else:
                    raise ValueError(
                        f"Unexpected response format: {type(data).__name__}"
                    )

            except (requests.RequestException, requests.Timeout) as e:
                if attempt < self.config.max_retries:
                    wait_time = min(
                        self.config.retry_min_wait * (2**attempt),
                        self.config.retry_max_wait,
                    )
                    logger.warning(
                        f"Request failed (attempt {attempt + 1}), retrying in {wait_time}s: {e}"
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(
                        f"Request failed after {self.config.max_retries + 1} attempts: {e}"
                    )
                    raise
        # This line should never be reached but satisfies type checker
        raise RuntimeError(
            "Unexpected error: retry loop exited without return or raise"
        )

    def find_recent_deals_for_address(
        self,
        address: str,
        years_back: int = 2,
        radius: int = 30,
        max_deals: int = 50,
        deal_type: int = 2,
    ) -> List[Dict[str, Any]]:
        """
        Find all relevant real estate deals for a given address from the last few years.

        This is the main use case function that ties everything together.
        Street deals include deals from the same building which get highest priority.

        Args:
            address: The address to search for
            years_back: How many years back to search (default: 2)
            radius: Search radius in meters for initial coordinate search (default: 30)
                   Small radius since street deals cover the entire street anyway
            max_deals: Maximum number of deals to return (default: 50)
            deal_type: Deal type filter (1=first hand/new, 2=second hand/used, default: 2)

        Returns:
            List of deals found for the address area, with same building deals prioritized first,
            then street deals, then neighborhood deals

        Raises:
            ValueError: If address cannot be found or processed, or input is invalid
            requests.RequestException: If API requests fail after retries
        """
        # Validate inputs
        address = self._validate_address(address)
        years_back = self._validate_positive_int(years_back, "years_back", max_value=50)
        radius = self._validate_positive_int(radius, "radius", max_value=5000)
        max_deals = self._validate_positive_int(max_deals, "max_deals", max_value=10000)
        if deal_type not in (1, 2):
            raise ValueError(
                "deal_type must be 1 (first hand/new) or 2 (second hand/used)"
            )

        try:
            # Step 1: Get coordinates for the address
            logger.info(
                f"Starting search for address: {address}, dealType: {deal_type}"
            )
            autocomplete_result = self.autocomplete_address(address)

            if not autocomplete_result.get("results"):
                raise ValueError(f"No results found for address: {address}")

            # Get the best match (first result)
            best_match = autocomplete_result["results"][0]
            if "shape" not in best_match:
                raise ValueError("No coordinates found in autocomplete result")

            # Parse coordinates from WKT POINT string
            # Format: "POINT(longitude latitude)"
            shape_str = best_match["shape"]
            if not shape_str.startswith("POINT("):
                raise ValueError("Invalid coordinate format in autocomplete result")

            # Extract coordinates from "POINT(x y)"
            coords_str = shape_str[6:-1]  # Remove "POINT(" and ")"
            coords = coords_str.split()
            if len(coords) != 2:
                raise ValueError("Invalid coordinate format in autocomplete result")

            point = (float(coords[0]), float(coords[1]))
            search_address_normalized = address.lower().strip()
            logger.info(f"Found coordinates: {point}")

            # Step 2: Get deals by radius to find polygon IDs
            nearby_deals = self.get_deals_by_radius(point, radius=radius)

            # Extract unique polygon IDs
            polygon_ids = set()
            for deal in nearby_deals:
                if "polygon_id" in deal:
                    polygon_ids.add(str(deal["polygon_id"]))

            logger.info(f"Found {len(polygon_ids)} unique polygon IDs")

            # Step 3: Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=years_back * 365)
            start_date_str = start_date.strftime("%Y-%m")
            end_date_str = end_date.strftime("%Y-%m")

            # Step 4: Get street and neighborhood deals for each polygon
            # Prioritize: same building (0) > street deals (1) > neighborhood deals (2)
            building_deals = []
            street_deals = []
            neighborhood_deals = []
            seen_deals = set()  # For deduplication

            for polygon_id in polygon_ids:
                try:
                    # Get street deals first (higher priority)
                    current_street_deals = self.get_street_deals(
                        polygon_id,
                        limit=max_deals // 2,  # Allocate more to street deals
                        start_date=start_date_str,
                        end_date=end_date_str,
                        deal_type=deal_type,
                    )

                    # Get neighborhood deals (lower priority)
                    current_neighborhood_deals = self.get_neighborhood_deals(
                        polygon_id,
                        limit=max_deals // 4,  # Allocate less to neighborhood deals
                        start_date=start_date_str,
                        end_date=end_date_str,
                        deal_type=deal_type,
                    )

                    # Process street deals and separate building deals
                    for deal in current_street_deals:
                        # Create unique deal ID for deduplication
                        deal_id = f"{deal.get('dealId', '')}{deal.get('dealDate', '')}"
                        if deal_id not in seen_deals:
                            seen_deals.add(deal_id)
                            deal["source_polygon_id"] = polygon_id
                            deal["deal_source"] = "street"

                            # Check if this is from the same building
                            # Construct address from API fields (API doesn't have single "address" field)
                            street = deal.get("streetNameHeb", "")
                            house_num = str(deal.get("houseNum", ""))
                            deal_address = f"{street} {house_num}".lower().strip()
                            if self._is_same_building(
                                search_address_normalized, deal_address
                            ):
                                deal["deal_source"] = "same_building"
                                deal["priority"] = 0  # Highest priority
                                building_deals.append(deal)
                            else:
                                deal["priority"] = 1  # Street deals priority
                                street_deals.append(deal)

                    # Add neighborhood deals with lowest priority
                    for deal in current_neighborhood_deals:
                        # Create unique deal ID for deduplication
                        deal_id = f"{deal.get('dealId', '')}{deal.get('dealDate', '')}"
                        if deal_id not in seen_deals:
                            seen_deals.add(deal_id)
                            deal["source_polygon_id"] = polygon_id
                            deal["deal_source"] = "neighborhood"
                            deal["priority"] = 2  # Lowest priority
                            neighborhood_deals.append(deal)

                except Exception as e:
                    logger.warning(f"Error processing polygon {polygon_id}: {e}")
                    continue

            # Step 5: Combine and prioritize: building deals first, then street, then neighborhood
            all_deals = building_deals + street_deals + neighborhood_deals

            # Use stable sort: first by date (newest first), then by priority
            # Since Python's sort is stable, the second sort maintains date order within each priority
            all_deals.sort(
                key=lambda x: x.get("dealDate", "1900-01-01"), reverse=True
            )  # Newest first
            all_deals.sort(
                key=lambda x: x.get("priority", 3)
            )  # Priority first (0=building, 1=street, 2=neighborhood)

            # Limit to max_deals
            if len(all_deals) > max_deals:
                all_deals = all_deals[:max_deals]

            # Add price per square meter calculation and deal type info
            for deal in all_deals:
                price = deal.get("dealAmount", 0)
                area = deal.get("assetArea", 0)
                if (
                    isinstance(price, (int, float))
                    and isinstance(area, (int, float))
                    and area > 0
                ):
                    deal["price_per_sqm"] = round(price / area, 2)
                else:
                    deal["price_per_sqm"] = None

                # Add deal type description for clarity
                deal["deal_type"] = deal_type
                deal["deal_type_description"] = (
                    "first_hand_new" if deal_type == 1 else "second_hand_used"
                )

            logger.info(
                f"Found {len(all_deals)} total deals for address: {address} "
                f"(Building: {len(building_deals)}, Street: {len(street_deals)}, Neighborhood: {len(neighborhood_deals)}) "
                f"[{deal['deal_type_description'] if all_deals else 'N/A'}]"
            )
            return all_deals

        except Exception as e:
            logger.error(f"Error in find_recent_deals_for_address: {e}")
            raise

    def _calculate_distance(self, point1: Tuple[float, float], point2: Tuple[float, float]) -> float:
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

    def _is_same_building(self, search_address: str, deal_address: str) -> bool:
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
                addr.replace("רח'", "")
                .replace("רחוב", "")
                .replace("שד'", "")
                .replace("שדרות", "")
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
        if len(search_address) > 5 and len(deal_address) > 5:
            if search_address in deal_address or deal_address in search_address:
                return True

        return False

    def filter_deals_by_criteria(
        self,
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
                # Normalize both strings for flexible matching
                property_type_normalized = property_type.lower().strip()
                deal_type_normalized = deal_type.lower().strip()

                # Check if the filter term appears in the deal type
                # This allows "דירה" to match "דירת גג", "דירה בבניין", etc.
                if property_type_normalized not in deal_type_normalized:
                    continue

            # Room count filter
            rooms = deal.get("assetRoomNum")
            if rooms is not None:
                try:
                    rooms = float(rooms)
                    if min_rooms is not None and rooms < min_rooms:
                        continue
                    if max_rooms is not None and rooms > max_rooms:
                        continue
                except (TypeError, ValueError):
                    pass  # Skip deals with invalid room data

            # Price filter
            price = deal.get("dealAmount")
            if price is not None:
                try:
                    price = float(price)
                    if min_price is not None and price < min_price:
                        continue
                    if max_price is not None and price > max_price:
                        continue
                except (TypeError, ValueError):
                    pass  # Skip deals with invalid price data

            # Area filter
            area = deal.get("assetArea")
            if area is not None:
                try:
                    area = float(area)
                    if min_area is not None and area < min_area:
                        continue
                    if max_area is not None and area > max_area:
                        continue
                except (TypeError, ValueError):
                    pass  # Skip deals with invalid area data

            # Floor filter
            floor_str = deal.get("floorNo", "")
            if floor_str and isinstance(floor_str, str):
                # Try to extract floor number (handles Hebrew floor descriptions)
                floor_num = self._extract_floor_number(floor_str)
                if floor_num is not None:
                    if min_floor is not None and floor_num < min_floor:
                        continue
                    if max_floor is not None and floor_num > max_floor:
                        continue

            filtered_deals.append(deal)

        return filtered_deals

    def _extract_floor_number(self, floor_str: str) -> Optional[int]:
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

    def calculate_deal_statistics(self, deals: List[Dict[str, Any]]) -> Dict[str, Any]:
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
                "std_dev": round(self._calculate_std_dev(prices), 2)
                if len(prices) > 1
                else 0,
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

    def _calculate_std_dev(self, values: List[float]) -> float:
        """Calculate standard deviation of a list of values."""
        if len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        return variance**0.5

    def _parse_deal_dates(
        self, deals: List[Dict[str, Any]], time_period_months: Optional[int] = None
    ) -> Tuple[List[str], Dict[str, int], Dict[str, int]]:
        """
        Parse and filter deal dates from a list of deals.

        This helper method centralizes the date parsing logic used across
        multiple market analysis functions. It validates dates, filters by
        time period if specified, and groups deals by month and quarter.

        Args:
            deals: List of deal dictionaries with 'dealDate' field
            time_period_months: Optional time period to filter (from today backwards)

        Returns:
            Tuple containing:
                - List of valid deal date strings
                - Dictionary mapping year-month to deal counts
                - Dictionary mapping year-quarter to deal counts

        Raises:
            ValueError: If no valid deal dates are found
        """
        from collections import defaultdict

        # Calculate cutoff date if time period is specified
        cutoff_date = None
        if time_period_months is not None:
            cutoff_date = datetime.now() - timedelta(days=time_period_months * 30)
            cutoff_date_str = cutoff_date.strftime("%Y-%m-%d")

        monthly_deals = defaultdict(int)
        quarterly_deals = defaultdict(int)
        deal_dates = []

        for deal in deals:
            date_str = deal.get("dealDate", "")
            if not date_str:
                continue

            try:
                # Filter by time period if specified
                if cutoff_date is not None and date_str < cutoff_date_str:
                    continue

                # Parse date components
                year = int(date_str[:4])
                month = int(date_str[5:7])
                quarter = (month - 1) // 3 + 1  # 1-4

                # Track by month and quarter
                year_month = f"{year}-{month:02d}"
                year_quarter = f"{year}-Q{quarter}"

                monthly_deals[year_month] += 1
                quarterly_deals[year_quarter] += 1
                deal_dates.append(date_str)
            except (ValueError, IndexError):
                logger.warning(f"Invalid date format: {date_str}")
                continue

        if not deal_dates:
            raise ValueError("No valid deal dates found in deals list")

        return deal_dates, dict(monthly_deals), dict(quarterly_deals)

    def calculate_market_activity_score(
        self, deals: List[Dict[str, Any]], time_period_months: int = 12
    ) -> Dict[str, Any]:
        """
        Calculate market activity and liquidity metrics.

        This function analyzes deal frequency, velocity, and market activity levels
        to provide a comprehensive view of market liquidity.

        Args:
            deals: List of deal dictionaries
            time_period_months: Time period to analyze in months (default: 12)

        Returns:
            Dictionary containing:
                - total_deals: Total number of deals
                - deals_per_month: Average deals per month
                - activity_score: Market activity score (0-100)
                - trend: Activity trend ('increasing', 'stable', 'decreasing')
                - monthly_distribution: Deals per month breakdown
                - activity_level: Description ('very_high', 'high', 'moderate', 'low', 'very_low')

        Raises:
            ValueError: If deals list is empty or invalid
        """
        if not deals:
            raise ValueError("Cannot calculate market activity from empty deals list")

        # Parse deal dates and group by month (with time period filtering)
        deal_dates, monthly_deals, _ = self._parse_deal_dates(deals, time_period_months)

        # Calculate metrics
        total_deals = len(deal_dates)
        unique_months = len(monthly_deals)
        deals_per_month = total_deals / unique_months if unique_months > 0 else 0

        # Calculate activity score (0-100)
        # Based on deals per month using defined thresholds
        if deals_per_month >= ACTIVITY_VERY_HIGH_THRESHOLD:
            activity_score = 100
            activity_level = "very_high"
        elif deals_per_month >= ACTIVITY_HIGH_THRESHOLD:
            activity_score = 75 + ((deals_per_month - ACTIVITY_HIGH_THRESHOLD) / ACTIVITY_HIGH_THRESHOLD) * 25
            activity_level = "high"
        elif deals_per_month >= ACTIVITY_MODERATE_THRESHOLD:
            activity_score = 50 + ((deals_per_month - ACTIVITY_MODERATE_THRESHOLD) / (ACTIVITY_HIGH_THRESHOLD - ACTIVITY_MODERATE_THRESHOLD)) * 25
            activity_level = "moderate"
        elif deals_per_month >= ACTIVITY_LOW_THRESHOLD:
            activity_score = 25 + ((deals_per_month - ACTIVITY_LOW_THRESHOLD) / (ACTIVITY_MODERATE_THRESHOLD - ACTIVITY_LOW_THRESHOLD)) * 25
            activity_level = "low"
        else:
            activity_score = deals_per_month * 25
            activity_level = "very_low"

        # Calculate trend (compare first half vs second half)
        sorted_months = sorted(monthly_deals.keys())
        if len(sorted_months) >= 4:
            mid_point = len(sorted_months) // 2
            first_half_avg = sum(monthly_deals[m] for m in sorted_months[:mid_point]) / mid_point
            second_half_avg = sum(monthly_deals[m] for m in sorted_months[mid_point:]) / (
                len(sorted_months) - mid_point
            )

            change_ratio = (second_half_avg - first_half_avg) / first_half_avg if first_half_avg > 0 else 0

            if change_ratio > 0.15:
                trend = "increasing"
            elif change_ratio < -0.15:
                trend = "decreasing"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"

        return {
            "total_deals": total_deals,
            "unique_months": unique_months,
            "deals_per_month": round(deals_per_month, 2),
            "activity_score": round(activity_score, 1),
            "activity_level": activity_level,
            "trend": trend,
            "monthly_distribution": dict(sorted(monthly_deals.items())),
        }

    def analyze_investment_potential(self, deals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze investment potential based on price trends and market stability.

        This function calculates price appreciation rates, market volatility,
        and provides investment metrics for decision-making. The MCP provides
        data metrics; the LLM interprets them for investment advice.

        Args:
            deals: List of deal dictionaries with price and date information

        Returns:
            Dictionary containing:
                - price_appreciation_rate: Annual price growth rate (%)
                - price_volatility: Price volatility score (0-100, lower is more stable)
                - market_stability: Stability rating ('very_stable', 'stable', 'moderate', 'volatile', 'very_volatile')
                - price_trend: Price direction ('increasing', 'stable', 'decreasing')
                - avg_price_per_sqm: Average price per square meter
                - price_change_pct: Total price change percentage
                - investment_score: Overall investment score (0-100)
                - data_quality: Quality of data ('excellent', 'good', 'fair', 'limited')

        Raises:
            ValueError: If deals list is empty or lacks required data
        """
        if not deals:
            raise ValueError("Cannot analyze investment potential from empty deals list")

        # Extract price per sqm and dates
        price_data = []
        for deal in deals:
            price_per_sqm = deal.get("price_per_sqm")
            date_str = deal.get("dealDate", "")

            if isinstance(price_per_sqm, (int, float)) and price_per_sqm > 0 and date_str:
                try:
                    # Parse date for sorting
                    year = int(date_str[:4])
                    month = int(date_str[5:7])
                    price_data.append((year + month / 12.0, price_per_sqm))
                except (ValueError, IndexError):
                    continue

        if len(price_data) < 3:
            raise ValueError(
                "Insufficient data for investment analysis (need at least 3 valid deals with price and date)"
            )

        # Sort by time
        price_data.sort(key=lambda x: x[0])
        times = [p[0] for p in price_data]
        prices = [p[1] for p in price_data]

        # Calculate average price
        avg_price_per_sqm = sum(prices) / len(prices)

        # Calculate price appreciation rate (using linear regression approximation)
        n = len(price_data)
        sum_t = sum(times)
        sum_p = sum(prices)
        sum_tp = sum(t * p for t, p in price_data)
        sum_t2 = sum(t * t for t in times)

        # Linear regression slope
        if n * sum_t2 - sum_t * sum_t != 0:
            slope = (n * sum_tp - sum_t * sum_p) / (n * sum_t2 - sum_t * sum_t)
            # Convert to annual percentage change
            price_appreciation_rate = (slope / avg_price_per_sqm) * 100 if avg_price_per_sqm > 0 else 0
        else:
            price_appreciation_rate = 0

        # Calculate price change from first to last deal
        if prices[0] > 0:
            price_change_pct = ((prices[-1] - prices[0]) / prices[0]) * 100
        else:
            price_change_pct = 0

        # Determine price trend
        if price_appreciation_rate > 2:
            price_trend = "increasing"
        elif price_appreciation_rate < -2:
            price_trend = "decreasing"
        else:
            price_trend = "stable"

        # Calculate price volatility (coefficient of variation)
        std_dev = self._calculate_std_dev(prices)
        if avg_price_per_sqm > 0:
            coefficient_of_variation = (std_dev / avg_price_per_sqm) * 100
        else:
            coefficient_of_variation = 0

        # Convert CV to volatility score (0-100, lower is better)
        # Using defined volatility thresholds
        if coefficient_of_variation > VOLATILITY_VERY_VOLATILE_THRESHOLD:
            volatility_score = 100
            market_stability = "very_volatile"
        elif coefficient_of_variation > VOLATILITY_VOLATILE_THRESHOLD:
            volatility_score = 75 + ((coefficient_of_variation - VOLATILITY_VOLATILE_THRESHOLD) / (VOLATILITY_VERY_VOLATILE_THRESHOLD - VOLATILITY_VOLATILE_THRESHOLD)) * 25
            market_stability = "volatile"
        elif coefficient_of_variation > VOLATILITY_MODERATE_THRESHOLD:
            volatility_score = 50 + ((coefficient_of_variation - VOLATILITY_MODERATE_THRESHOLD) / (VOLATILITY_VOLATILE_THRESHOLD - VOLATILITY_MODERATE_THRESHOLD)) * 25
            market_stability = "moderate"
        elif coefficient_of_variation > VOLATILITY_STABLE_THRESHOLD:
            volatility_score = 25 + ((coefficient_of_variation - VOLATILITY_STABLE_THRESHOLD) / (VOLATILITY_MODERATE_THRESHOLD - VOLATILITY_STABLE_THRESHOLD)) * 25
            market_stability = "stable"
        else:
            volatility_score = (coefficient_of_variation / VOLATILITY_STABLE_THRESHOLD) * 25
            market_stability = "very_stable"

        # Calculate investment score (0-100)
        # Positive: price appreciation, market stability (low volatility)
        # Negative: price decline, high volatility
        appreciation_component = min(max(price_appreciation_rate * 5, -25), 50)  # -25 to +50
        stability_component = (100 - volatility_score) * 0.5  # 0 to 50

        investment_score = max(0, min(100, appreciation_component + stability_component))

        # Data quality assessment
        if n >= 20:
            data_quality = "excellent"
        elif n >= 10:
            data_quality = "good"
        elif n >= 5:
            data_quality = "fair"
        else:
            data_quality = "limited"

        return {
            "price_appreciation_rate": round(price_appreciation_rate, 2),
            "price_volatility": round(volatility_score, 1),
            "market_stability": market_stability,
            "price_trend": price_trend,
            "avg_price_per_sqm": round(avg_price_per_sqm, 0),
            "price_change_pct": round(price_change_pct, 2),
            "investment_score": round(investment_score, 1),
            "data_quality": data_quality,
            "sample_size": n,
        }

    def get_market_liquidity(
        self, deals: List[Dict[str, Any]], time_period_months: int = 12
    ) -> Dict[str, Any]:
        """
        Get detailed market liquidity and turnover metrics.

        This function provides granular liquidity metrics including deal velocity,
        quarterly trends, and market turnover indicators.

        Args:
            deals: List of deal dictionaries
            time_period_months: Time period to analyze in months (default: 12)

        Returns:
            Dictionary containing:
                - total_deals: Total number of deals in period
                - deals_per_month: Average deals per month
                - deals_per_quarter: Average deals per quarter
                - quarterly_breakdown: Deals grouped by quarter
                - velocity_score: Market velocity score (0-100)
                - liquidity_rating: Liquidity rating ('very_high', 'high', 'moderate', 'low', 'very_low')
                - trend_direction: Trend in liquidity ('improving', 'stable', 'declining')
                - most_active_period: Quarter/month with most activity

        Raises:
            ValueError: If deals list is empty or invalid
        """
        if not deals:
            raise ValueError("Cannot calculate market liquidity from empty deals list")

        # Parse deal dates and group by month and quarter (with time period filtering)
        deal_dates, monthly_deals, quarterly_deals = self._parse_deal_dates(deals, time_period_months)

        # Calculate metrics
        total_deals = len(deal_dates)
        unique_months = len(monthly_deals)
        unique_quarters = len(quarterly_deals)

        deals_per_month = total_deals / unique_months if unique_months > 0 else 0
        deals_per_quarter = total_deals / unique_quarters if unique_quarters > 0 else 0

        # Calculate velocity score (similar to activity score but focused on turnover)
        # Based on monthly deal velocity using defined thresholds
        if deals_per_month >= LIQUIDITY_VERY_HIGH_THRESHOLD:
            velocity_score = 100
            liquidity_rating = "very_high"
        elif deals_per_month >= LIQUIDITY_HIGH_THRESHOLD:
            velocity_score = 75 + ((deals_per_month - LIQUIDITY_HIGH_THRESHOLD) / (LIQUIDITY_VERY_HIGH_THRESHOLD - LIQUIDITY_HIGH_THRESHOLD)) * 25
            liquidity_rating = "high"
        elif deals_per_month >= LIQUIDITY_MODERATE_THRESHOLD:
            velocity_score = 50 + ((deals_per_month - LIQUIDITY_MODERATE_THRESHOLD) / (LIQUIDITY_HIGH_THRESHOLD - LIQUIDITY_MODERATE_THRESHOLD)) * 25
            liquidity_rating = "moderate"
        elif deals_per_month >= LIQUIDITY_LOW_THRESHOLD:
            velocity_score = 25 + ((deals_per_month - LIQUIDITY_LOW_THRESHOLD) / (LIQUIDITY_MODERATE_THRESHOLD - LIQUIDITY_LOW_THRESHOLD)) * 25
            liquidity_rating = "low"
        else:
            velocity_score = deals_per_month * 50
            liquidity_rating = "very_low"

        # Determine trend direction (compare recent quarter to earlier quarters)
        sorted_quarters = sorted(quarterly_deals.keys())
        if len(sorted_quarters) >= 3:
            recent_quarter_avg = quarterly_deals[sorted_quarters[-1]]
            earlier_quarters_avg = sum(quarterly_deals[q] for q in sorted_quarters[:-1]) / (
                len(sorted_quarters) - 1
            )

            if recent_quarter_avg > earlier_quarters_avg * 1.2:
                trend_direction = "improving"
            elif recent_quarter_avg < earlier_quarters_avg * 0.8:
                trend_direction = "declining"
            else:
                trend_direction = "stable"
        else:
            trend_direction = "insufficient_data"

        # Find most active period
        if quarterly_deals:
            most_active_quarter = max(quarterly_deals.items(), key=lambda x: x[1])
            most_active_period = f"{most_active_quarter[0]} ({most_active_quarter[1]} deals)"
        else:
            most_active_period = "N/A"

        return {
            "total_deals": total_deals,
            "unique_months": unique_months,
            "unique_quarters": unique_quarters,
            "deals_per_month": round(deals_per_month, 2),
            "deals_per_quarter": round(deals_per_quarter, 2),
            "quarterly_breakdown": dict(sorted(quarterly_deals.items())),
            "monthly_breakdown": dict(sorted(monthly_deals.items())),
            "velocity_score": round(velocity_score, 1),
            "liquidity_rating": liquidity_rating,
            "trend_direction": trend_direction,
            "most_active_period": most_active_period,
        }
