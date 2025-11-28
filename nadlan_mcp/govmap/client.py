"""
Govmap API Client for Israeli real estate data.

This module provides the main GovmapClient class for interacting with the
Israeli government's Govmap API to retrieve property deals, market trends,
and real estate information.
"""

from datetime import datetime, timedelta
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

import requests

from nadlan_mcp.config import GovmapConfig, get_config

# Import functions from modular package
from . import filters, market_analysis, statistics, utils, validators

# Import models
from .models import (
    AutocompleteResponse,
    AutocompleteResult,
    CoordinatePoint,
    Deal,
    DealStatistics,
    InvestmentAnalysis,
    LiquidityMetrics,
    MarketActivityScore,
)

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

    def _validate_positive_int(self, value: int, name: str, max_value: Optional[int] = None) -> int:
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
    def autocomplete_address(self, search_text: str) -> AutocompleteResponse:
        """
        Find the most likely match for a given address using autocomplete.

        Args:
            search_text: The address to search for (e.g., "סוקולוב 38 חולון")

        Returns:
            AutocompleteResponse model with results and coordinates

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

                # Parse results into AutocompleteResult models
                results = []
                for result in data.get("results", []):
                    # Parse coordinates from WKT POINT format if available
                    coordinates = None
                    shape_str = result.get("shape", "")
                    if shape_str and shape_str.startswith("POINT("):
                        try:
                            coords_str = shape_str[6:-1]  # Remove "POINT(" and ")"
                            coords = coords_str.split()
                            if len(coords) == 2:
                                coordinates = CoordinatePoint(
                                    longitude=float(coords[0]), latitude=float(coords[1])
                                )
                        except (ValueError, IndexError) as e:
                            logger.warning(
                                f"Failed to parse coordinates from shape: {shape_str}, error: {e}"
                            )

                    results.append(
                        AutocompleteResult(
                            text=result.get("text", ""),
                            id=result.get("id", ""),
                            type=result.get("type", ""),
                            score=result.get("score", 0),
                            coordinates=coordinates,
                            shape=shape_str if shape_str else None,
                        )
                    )

                return AutocompleteResponse(
                    resultsCount=data.get("resultsCount", len(results)), results=results
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
        raise RuntimeError("Unexpected error: retry loop exited without return or raise")

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
        raise RuntimeError("Unexpected error: retry loop exited without return or raise")

    def get_deals_by_radius(
        self, point: Tuple[float, float], radius: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Find polygon metadata within a specified radius of a point.

        **NOTE**: This endpoint returns polygon metadata, NOT actual deal transactions!
        The response contains polygon_id, dealscount, settlementNameHeb, etc.
        To get actual deals, extract polygon_ids and call get_street_deals() or get_neighborhood_deals().

        Use find_recent_deals_for_address() for the complete workflow.

        Args:
            point: A tuple of (longitude, latitude)
            radius: The search radius in meters (default: 50)

        Returns:
            List of polygon metadata dicts (not Deal objects)

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
                    raise ValueError(f"Expected list response, got {type(data).__name__}")

                # NOTE: This endpoint returns polygon metadata, not actual deals!
                # The response contains: dealscount, polygon_id, settlementNameHeb, streetNameHeb, houseNum, objectid
                # We return these as-is (raw dicts) since they're used only for extracting polygon_ids
                # in find_recent_deals_for_address()
                logger.info(f"Found {len(data)} polygon metadata records")

                # For backward compatibility, return empty list of Deals since these aren't actual deals
                # The raw data is available in the response but we don't try to validate as Deal objects
                # TODO: Consider creating a PolygonMetadata model for type safety
                return data  # Return raw dicts temporarily

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
        raise RuntimeError("Unexpected error: retry loop exited without return or raise")

    def get_street_deals(
        self,
        polygon_id: str,
        limit: int = 10,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        deal_type: int = 2,
    ) -> List[Deal]:
        """
        Retrieve detailed information about deals on a specific street.

        Args:
            polygon_id: The ID of the lot's polygon
            limit: Maximum number of deals to return (default: 10)
            start_date: Start date for search in 'YYYY-MM' format
            end_date: End date for search in 'YYYY-MM' format
            deal_type: Deal type filter (1=first hand/new, 2=second hand/used, default: 2)

        Returns:
            List of Deal models for the street

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

        params = {"limit": limit, "dealType": deal_type}
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
                deal_dicts = []
                if isinstance(data, dict) and "data" in data:
                    if not isinstance(data["data"], list):
                        raise ValueError(
                            f"Expected list in 'data' field, got {type(data['data']).__name__}"
                        )
                    deal_dicts = data["data"]
                elif isinstance(data, list):
                    deal_dicts = data
                else:
                    raise ValueError(f"Unexpected response format: {type(data).__name__}")

                # Parse each deal dict into Deal model
                deals = []
                for deal_dict in deal_dicts:
                    try:
                        deal = Deal.model_validate(deal_dict)
                        deals.append(deal)
                    except Exception as e:
                        logger.warning(f"Failed to parse deal: {e}. Skipping deal.")
                        continue

                return deals

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
        raise RuntimeError("Unexpected error: retry loop exited without return or raise")

    def get_neighborhood_deals(
        self,
        polygon_id: str,
        limit: int = 10,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        deal_type: int = 2,
    ) -> List[Deal]:
        """
        Retrieve deals within the same neighborhood as the given polygon_id.

        Args:
            polygon_id: The ID of the lot's polygon
            limit: Maximum number of deals to return (default: 10)
            start_date: Start date for search in 'YYYY-MM' format
            end_date: End date for search in 'YYYY-MM' format
            deal_type: Deal type filter (1=first hand/new, 2=second hand/used, default: 2)

        Returns:
            List of Deal models in the neighborhood

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

        params = {"limit": limit, "dealType": deal_type}
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
                deal_dicts = []
                if isinstance(data, dict) and "data" in data:
                    if not isinstance(data["data"], list):
                        raise ValueError(
                            f"Expected list in 'data' field, got {type(data['data']).__name__}"
                        )
                    deal_dicts = data["data"]
                elif isinstance(data, list):
                    deal_dicts = data
                else:
                    raise ValueError(f"Unexpected response format: {type(data).__name__}")

                # Parse each deal dict into Deal model
                deals = []
                for deal_dict in deal_dicts:
                    try:
                        deal = Deal.model_validate(deal_dict)
                        deals.append(deal)
                    except Exception as e:
                        logger.warning(f"Failed to parse deal: {e}. Skipping deal.")
                        continue

                return deals

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
        raise RuntimeError("Unexpected error: retry loop exited without return or raise")

    def find_recent_deals_for_address(
        self,
        address: str,
        years_back: int = 2,
        radius: int = 30,
        max_deals: int = 100,
        deal_type: int = 2,
    ) -> List[Deal]:
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
            List of Deal models found for the address area, with same building deals prioritized first,
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
            logger.info(f"Starting search for address: {address}, dealType: {deal_type}")
            autocomplete_result = self.autocomplete_address(address)

            if not autocomplete_result.results:
                raise ValueError(f"No results found for address: {address}")

            # Try multiple autocomplete results to find one with nearby polygons
            # (autocomplete can return different coordinates for vague queries)
            nearby_polygons = []
            point = None

            for result in autocomplete_result.results[:3]:  # Try top 3 results
                if not result.coordinates:
                    continue

                test_point = (result.coordinates.longitude, result.coordinates.latitude)
                test_polygons = self.get_deals_by_radius(test_point, radius=radius)

                if test_polygons:
                    point = test_point
                    nearby_polygons = test_polygons
                    logger.info(
                        f"Using autocomplete result: '{result.text}' with {len(test_polygons)} polygons"
                    )
                    break

            # Fallback: if no results had polygons at specified radius, try expanding radius
            if not nearby_polygons and radius < 200:
                logger.warning(f"No polygons found at {radius}m radius, expanding to 200m")
                # Use first result with coordinates for expanded search
                for result in autocomplete_result.results[:3]:
                    if result.coordinates:
                        test_point = (result.coordinates.longitude, result.coordinates.latitude)
                        nearby_polygons = self.get_deals_by_radius(test_point, radius=200)
                        if nearby_polygons:
                            point = test_point
                            logger.info(
                                f"Found {len(nearby_polygons)} polygons at expanded 200m radius"
                            )
                            break

            # Final fallback: use first result even if no polygons (will return empty results)
            if not point:
                best_match = autocomplete_result.results[0]
                if not best_match.coordinates:
                    raise ValueError("No coordinates found in any autocomplete result")
                point = (best_match.coordinates.longitude, best_match.coordinates.latitude)
                logger.warning(
                    f"No polygons found for '{best_match.text}', will return empty results"
                )

            search_address_normalized = address.lower().strip()
            logger.info(f"Using coordinates: {point}")

            # Extract polygon metadata with coordinates for distance calculation
            # Use dict to deduplicate by polygon_id (keep closest occurrence)
            polygon_dict = {}
            for metadata in nearby_polygons:
                polygon_id = metadata.get("polygon_id")
                if not polygon_id:
                    continue

                polygon_id_str = str(polygon_id)

                # Extract polygon center coordinates (use shape if available, fallback to search point)
                # Most polygon metadata includes shape which can be parsed for center
                # For now, use metadata coordinates if available, otherwise estimate
                poly_coords = None
                if "longitude" in metadata and "latitude" in metadata:
                    poly_coords = (float(metadata["longitude"]), float(metadata["latitude"]))
                # If no coordinates in metadata, we'll use the search point as approximation
                # (this is suboptimal but ensures we don't skip polygons)

                # Calculate distance from search point
                distance = 0.0
                if poly_coords:
                    distance = utils.calculate_distance(point, poly_coords)

                # Deduplicate: keep the polygon with shortest distance if duplicate IDs exist
                if (
                    polygon_id_str not in polygon_dict
                    or distance < polygon_dict[polygon_id_str]["distance"]
                ):
                    polygon_dict[polygon_id_str] = {
                        "polygon_id": polygon_id_str,
                        "distance": distance,
                        "metadata": metadata,
                    }

            # Convert dict to list
            polygon_metadata_list = list(polygon_dict.values())

            # Sort polygons by distance (closest first)
            polygon_metadata_list.sort(key=lambda x: x["distance"])
            logger.info(
                f"Found {len(polygon_metadata_list)} unique polygon IDs, sorted by distance"
            )

            # Limit polygons to query (performance optimization)
            max_polygons = self.config.max_polygons_to_query
            if len(polygon_metadata_list) > max_polygons:
                polygon_metadata_list = polygon_metadata_list[:max_polygons]
                logger.info(f"Limited to {max_polygons} closest polygons for performance")

            # Step 3: Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=years_back * 365)
            start_date_str = start_date.strftime("%Y-%m")
            end_date_str = end_date.strftime("%Y-%m")

            # Step 4: Get street and neighborhood deals for each polygon (sorted by distance)
            # Prioritize: same building (0) > street deals (1) > neighborhood deals (2)
            # With progressive querying: query closest polygon first, expand if needed
            building_deals = []
            street_deals = []
            neighborhood_deals = []
            seen_deals = set()  # For deduplication

            for polygon_meta in polygon_metadata_list:
                polygon_id = polygon_meta["polygon_id"]
                polygon_distance = polygon_meta["distance"]

                # Smart early termination: stop if we have good coverage of high-priority deals
                # Prefer same-building and street deals over neighborhood deals
                high_priority_count = len(building_deals) + len(street_deals)
                total_collected = high_priority_count + len(neighborhood_deals)

                # Stop if we have enough deals AND we're getting too far from the search point
                if total_collected >= max_deals:
                    logger.info(f"Collected {total_collected} deals, stopping polygon queries")
                    break

                # Log polygon being queried
                logger.info(
                    f"Querying polygon {polygon_id} (distance: {polygon_distance:.0f}m from search point)"
                )

                try:
                    # Get street deals first (higher priority)
                    current_street_deals = self.get_street_deals(
                        polygon_id,
                        limit=max(1, max_deals // 2),  # Allocate more to street deals (min 1)
                        start_date=start_date_str,
                        end_date=end_date_str,
                        deal_type=deal_type,
                    )

                    # Get neighborhood deals (lower priority) - optional for performance
                    current_neighborhood_deals = []
                    # Skip neighborhood deals if we have enough street deals
                    if len(street_deals) < max_deals // 2:
                        current_neighborhood_deals = self.get_neighborhood_deals(
                            polygon_id,
                            limit=max(
                                1, max_deals // 4
                            ),  # Allocate less to neighborhood deals (min 1)
                            start_date=start_date_str,
                            end_date=end_date_str,
                            deal_type=deal_type,
                        )

                    # Process street deals and separate building deals
                    for deal in current_street_deals:
                        # Create unique deal ID for deduplication
                        deal_id = f"{deal.objectid}{deal.deal_date}"
                        if deal_id not in seen_deals:
                            seen_deals.add(deal_id)

                            # Calculate distance from search point to deal
                            # Most deals don't have individual coordinates, so use polygon distance
                            deal_distance = polygon_distance

                            # Store metadata using dynamic attributes (allowed by extra='allow')
                            deal.source_polygon_id = polygon_id
                            deal.deal_source = "street"
                            deal.distance_meters = round(deal_distance, 1)

                            # Check if this is from the same building
                            # Construct address from model fields (try multiple field names)
                            # API returns streetNameHeb/streetNameEng and houseNum
                            street = (
                                getattr(deal, "streetNameHeb", None)
                                or getattr(deal, "streetNameEng", None)
                                or deal.street_name
                                or ""
                            )
                            house_num = str(
                                getattr(deal, "houseNum", None) or deal.house_number or ""
                            )
                            deal_address = f"{street} {house_num}".lower().strip()
                            if self._is_same_building(search_address_normalized, deal_address):
                                deal.deal_source = "same_building"
                                deal.priority = 0  # Highest priority
                                building_deals.append(deal)
                            else:
                                # Apply distance filter for street deals (not same building)
                                if deal_distance <= self.config.max_street_deal_distance_meters:
                                    deal.priority = 1  # Street deals priority
                                    street_deals.append(deal)
                                else:
                                    logger.debug(
                                        f"Filtered street deal at {deal_distance:.0f}m "
                                        f"(max: {self.config.max_street_deal_distance_meters}m)"
                                    )

                    # Add neighborhood deals with lowest priority
                    for deal in current_neighborhood_deals:
                        # Create unique deal ID for deduplication
                        deal_id = f"{deal.objectid}{deal.deal_date}"
                        if deal_id not in seen_deals:
                            seen_deals.add(deal_id)

                            # Calculate distance from search point (use polygon distance)
                            deal_distance = polygon_distance

                            # Apply distance filter for neighborhood deals
                            if deal_distance <= self.config.max_neighborhood_deal_distance_meters:
                                # Store metadata using dynamic attributes
                                deal.source_polygon_id = polygon_id
                                deal.deal_source = "neighborhood"
                                deal.priority = 2  # Lowest priority
                                deal.distance_meters = round(deal_distance, 1)
                                neighborhood_deals.append(deal)
                            else:
                                logger.debug(
                                    f"Filtered neighborhood deal at {deal_distance:.0f}m "
                                    f"(max: {self.config.max_neighborhood_deal_distance_meters}m)"
                                )

                except Exception as e:
                    logger.warning(f"Error processing polygon {polygon_id}: {e}")
                    continue

            # Step 5: Combine and prioritize: building deals first, then street, then neighborhood
            all_deals = building_deals + street_deals + neighborhood_deals

            # Multi-level sort with stable sorting:
            # 1. Date (newest first) - applied first to maintain recency within same priority/distance
            # 2. Distance (closest first) - applied second to prefer closer deals within same priority
            # 3. Priority (same building > street > neighborhood) - applied last as primary sort
            # Since Python's sort is stable, each sort maintains the order of previous sorts
            all_deals.sort(key=lambda x: x.deal_date or "1900-01-01", reverse=True)  # Newest first
            all_deals.sort(
                key=lambda x: getattr(x, "distance_meters", 999999)
            )  # Distance second (closer first)
            all_deals.sort(
                key=lambda x: getattr(x, "priority", 3)
            )  # Priority first (0=building, 1=street, 2=neighborhood)

            # Limit to max_deals
            if len(all_deals) > max_deals:
                all_deals = all_deals[:max_deals]

            # Add deal type metadata for clarity
            # Note: price_per_sqm is now a computed field on the Deal model
            for deal in all_deals:
                deal.deal_type = deal_type
                deal.deal_type_description = (
                    "first_hand_new" if deal_type == 1 else "second_hand_used"
                )

            logger.info(
                f"Found {len(all_deals)} total deals for address: {address} "
                f"(Building: {len(building_deals)}, Street: {len(street_deals)}, Neighborhood: {len(neighborhood_deals)}) "
                f"[{all_deals[0].deal_type_description if all_deals else 'N/A'}]"
            )
            return all_deals

        except Exception as e:
            logger.error(f"Error in find_recent_deals_for_address: {e}")
            raise

    # Filtering methods (delegate to filters module)
    def filter_deals_by_criteria(
        self,
        deals: List[Deal],
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

        Delegates to filters.filter_deals_by_criteria for the actual filtering logic.

        Args:
            deals: List of Deal model instances to filter
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
    def calculate_deal_statistics(
        self, deals: List[Deal], iqr_multiplier: Optional[float] = None
    ) -> DealStatistics:
        """
        Calculate statistical aggregations on deal data.

        Delegates to statistics.calculate_deal_statistics for the actual calculations.

        Args:
            deals: List of Deal model instances
            iqr_multiplier: Override IQR multiplier for outlier detection (optional)

        Returns:
            DealStatistics model with comprehensive metrics
        """
        return statistics.calculate_deal_statistics(deals, iqr_multiplier=iqr_multiplier)

    def _calculate_std_dev(self, values: List[float]) -> float:
        """
        Calculate standard deviation of a list of values.

        Delegates to statistics.calculate_std_dev for the actual calculation.
        """
        return statistics.calculate_std_dev(values)

    # Market analysis methods (delegate to market_analysis module)
    def _parse_deal_dates(self, deals: List[Deal], time_period_months: Optional[int] = None):
        """
        Parse and filter deal dates from a list of deals.

        Delegates to market_analysis.parse_deal_dates for the actual parsing.

        Args:
            deals: List of Deal model instances
            time_period_months: Optional time period to filter (from today backwards)

        Returns:
            Tuple containing deal dates, monthly distribution, and quarterly distribution
        """
        return market_analysis.parse_deal_dates(deals, time_period_months)

    def calculate_market_activity_score(
        self, deals: List[Deal], time_period_months: int = 12
    ) -> MarketActivityScore:
        """
        Calculate market activity and liquidity metrics.

        Delegates to market_analysis.calculate_market_activity_score for the analysis.

        Args:
            deals: List of Deal model instances
            time_period_months: Time period to analyze in months (default: 12)

        Returns:
            MarketActivityScore model with activity metrics
        """
        return market_analysis.calculate_market_activity_score(deals, time_period_months)

    def analyze_investment_potential(self, deals: List[Deal]) -> InvestmentAnalysis:
        """
        Analyze investment potential based on price trends and market stability.

        Delegates to market_analysis.analyze_investment_potential for the analysis.

        Args:
            deals: List of Deal model instances with price and date information

        Returns:
            InvestmentAnalysis model with investment metrics
        """
        return market_analysis.analyze_investment_potential(deals)

    def get_market_liquidity(
        self, deals: List[Deal], time_period_months: int = 12
    ) -> LiquidityMetrics:
        """
        Get detailed market liquidity and turnover metrics.

        Delegates to market_analysis.get_market_liquidity for the analysis.

        Args:
            deals: List of Deal model instances
            time_period_months: Time period to analyze in months (default: 12)

        Returns:
            LiquidityMetrics model with liquidity and velocity metrics
        """
        return market_analysis.get_market_liquidity(deals, time_period_months)
