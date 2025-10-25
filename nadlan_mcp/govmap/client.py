"""
Govmap API Client for Israeli real estate data.

This module provides the main GovmapClient class for interacting with the
Israeli government's Govmap API to retrieve property deals, market trends,
and real estate information.
"""

import logging
import time
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta

import requests

from nadlan_mcp.config import GovmapConfig, get_config

# Import functions from modular package
from . import validators
from . import utils
from . import filters
from . import statistics
from . import market_analysis

logger = logging.getLogger(__name__)


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

    # Validation methods (delegate to validators module)
    def _validate_address(self, address: str) -> str:
        """Validate and sanitize address input."""
        return validators.validate_address(address)

    def _validate_coordinates(self, point: Tuple[float, float]) -> Tuple[float, float]:
        """Validate coordinate input."""
        return validators.validate_coordinates(point)

    def _validate_positive_int(
        self, value: int, name: str, max_value: Optional[int] = None
    ) -> int:
        """Validate positive integer input."""
        return validators.validate_positive_int(value, name, max_value)

    # Utility methods (delegate to utils module)
    def _calculate_distance(
        self, point1: Tuple[float, float], point2: Tuple[float, float]
    ) -> float:
        """Calculate Euclidean distance between two points in ITM coordinates."""
        return utils.calculate_distance(point1, point2)

    def _is_same_building(self, search_address: str, deal_address: str) -> bool:
        """Check if a deal is from the same building as the search address."""
        return utils.is_same_building(search_address, deal_address)

    def _extract_floor_number(self, floor_str: str) -> Optional[int]:
        """Extract numeric floor number from Hebrew floor description."""
        return utils.extract_floor_number(floor_str)

    # Core API methods
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
        validators.validate_deal_type(deal_type)

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
        validators.validate_deal_type(deal_type)

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
        max_deals: int = 100,
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
            max_deals: Maximum number of deals to return (default: 100)
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
        validators.validate_deal_type(deal_type)

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
                f"[{all_deals[0]['deal_type_description'] if all_deals else 'N/A'}]"
            )
            return all_deals

        except Exception as e:
            logger.error(f"Error in find_recent_deals_for_address: {e}")
            raise

    # Filtering methods (delegate to filters module)
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

        Delegates to filters.filter_deals_by_criteria for the actual filtering logic.
        """
        return filters.filter_deals_by_criteria(
            deals=deals,
            property_type=property_type,
            min_rooms=min_rooms,
            max_rooms=max_rooms,
            min_price=min_price,
            max_price=max_price,
            min_area=min_area,
            max_area=max_area,
            min_floor=min_floor,
            max_floor=max_floor,
        )

    # Statistics methods (delegate to statistics module)
    def calculate_deal_statistics(self, deals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate statistical aggregations on deal data.

        Delegates to statistics.calculate_deal_statistics for the actual calculations.
        """
        return statistics.calculate_deal_statistics(deals)

    def _calculate_std_dev(self, values: List[float]) -> float:
        """
        Calculate standard deviation of a list of values.

        Delegates to statistics.calculate_std_dev for the actual calculation.
        """
        return statistics.calculate_std_dev(values)

    # Market analysis methods (delegate to market_analysis module)
    def _parse_deal_dates(
        self, deals: List[Dict[str, Any]], time_period_months: Optional[int] = None
    ):
        """
        Parse and filter deal dates from a list of deals.

        Delegates to market_analysis.parse_deal_dates for the actual parsing.
        """
        return market_analysis.parse_deal_dates(deals, time_period_months)

    def calculate_market_activity_score(
        self, deals: List[Dict[str, Any]], time_period_months: int = 12
    ) -> Dict[str, Any]:
        """
        Calculate market activity and liquidity metrics.

        Delegates to market_analysis.calculate_market_activity_score for the analysis.
        """
        return market_analysis.calculate_market_activity_score(
            deals, time_period_months
        )

    def analyze_investment_potential(
        self, deals: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze investment potential based on price trends and market stability.

        Delegates to market_analysis.analyze_investment_potential for the analysis.
        """
        return market_analysis.analyze_investment_potential(deals)

    def get_market_liquidity(
        self, deals: List[Dict[str, Any]], time_period_months: int = 12
    ) -> Dict[str, Any]:
        """
        Get detailed market liquidity and turnover metrics.

        Delegates to market_analysis.get_market_liquidity for the analysis.
        """
        return market_analysis.get_market_liquidity(deals, time_period_months)
