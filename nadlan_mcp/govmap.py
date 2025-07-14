import requests
import logging

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple, Optional

logger = logging.getLogger(__name__)


class GovmapClient:
    """
    A client for interacting with the Israeli government's Govmap API.

    This class provides methods to search for properties, find block/parcel information,
    and retrieve real estate deal data.
    """

    def __init__(self, base_url: str = "https://www.govmap.gov.il/api/"):
        """
        Initialize the GovmapClient.

        Args:
            base_url: The base URL for the Govmap API
        """
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'NadlanMCP/1.0.0'
        })

    def autocomplete_address(self, search_text: str) -> Dict[str, Any]:
        """
        Find the most likely match for a given address using autocomplete.

        Args:
            search_text: The address to search for (e.g., "סוקולוב 38 חולון")

        Returns:
            Dict containing the JSON response from the API with coordinates

        Raises:
            requests.RequestException: If the API request fails
            ValueError: If the response is invalid
        """
        url = f"{self.base_url}/search-service/autocomplete"

        payload = {
            "searchText": search_text,
            "language": "he",
            "isAccurate": False,
            "maxResults": 10
        }

        try:
            logger.info(f"Searching for address: {search_text}")
            response = self.session.post(url, json=payload)
            response.raise_for_status()

            data = response.json()
            if not data or 'results' not in data:
                raise ValueError("Invalid response format from autocomplete API")

            return data

        except requests.RequestException as e:
            logger.error(f"Error calling autocomplete API: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON response: {e}")
            raise ValueError("Invalid JSON response from API")

    def get_gush_helka(self, point: Tuple[float, float]) -> Dict[str, Any]:
        """
        Get Gush (Block) and Helka (Parcel) information for a coordinate point.

        Args:
            point: A tuple of (longitude, latitude)

        Returns:
            Dict containing the JSON response with block and parcel data

        Raises:
            requests.RequestException: If the API request fails
            ValueError: If the response is invalid
        """
        url = f"{self.base_url}/layers-catalog/entitiesByPoint"

        payload = {
            "point": list(point),
            "layers": [{"layerId": "16"}],
            "tolerance": 0
        }

        try:
            logger.info(f"Getting Gush/Helka for point: {point}")
            response = self.session.post(url, json=payload)
            response.raise_for_status()

            data = response.json()
            return data

        except requests.RequestException as e:
            logger.error(f"Error calling entitiesByPoint API: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON response: {e}")
            raise ValueError("Invalid JSON response from API")

    def get_deals_by_radius(self, point: Tuple[float, float], radius: int = 50) -> List[Dict[str, Any]]:
        """
        Find real estate deals within a specified radius of a point.

        Args:
            point: A tuple of (longitude, latitude)
            radius: The search radius in meters (default: 50)

        Returns:
            List of deals found within the radius

        Raises:
            requests.RequestException: If the API request fails
        """
        url = f"{self.base_url}/real-estate/deals/{point[0]},{point[1]}/{radius}"

        try:
            logger.info(f"Getting deals by radius for point: {point}, radius: {radius}m")
            response = self.session.get(url)
            response.raise_for_status()

            data = response.json()
            return data if isinstance(data, list) else []

        except requests.RequestException as e:
            logger.error(f"Error calling deals by radius API: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON response: {e}")
            return []

    def get_street_deals(self, polygon_id: str, limit: int = 10,
                        start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retrieve detailed information about deals on a specific street.

        Args:
            polygon_id: The ID of the lot's polygon
            limit: Maximum number of deals to return (default: 10)
            start_date: Start date for search in 'YYYY-MM' format
            end_date: End date for search in 'YYYY-MM' format

        Returns:
            List of detailed deal information for the street

        Raises:
            requests.RequestException: If the API request fails
        """
        url = f"{self.base_url}/real-estate/street-deals/{polygon_id}"

        params: Dict[str, Any] = {"limit": limit}
        if start_date:
            params["startDate"] = start_date
        if end_date:
            params["endDate"] = end_date

        try:
            logger.info(f"Getting street deals for polygon: {polygon_id}")
            response = self.session.get(url, params=params)
            response.raise_for_status()

            data = response.json()
            # API returns {data: [...], totalCount: ..., limit: ..., offset: ...}
            if isinstance(data, dict) and 'data' in data:
                return data['data'] if isinstance(data['data'], list) else []
            return data if isinstance(data, list) else []

        except requests.RequestException as e:
            logger.error(f"Error calling street deals API: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON response: {e}")
            return []

    def get_neighborhood_deals(self, polygon_id: str, limit: int = 10,
                              start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retrieve deals within the same neighborhood as the given polygon_id.

        Args:
            polygon_id: The ID of the lot's polygon
            limit: Maximum number of deals to return (default: 10)
            start_date: Start date for search in 'YYYY-MM' format
            end_date: End date for search in 'YYYY-MM' format

        Returns:
            List of deals in the neighborhood

        Raises:
            requests.RequestException: If the API request fails
        """
        url = f"{self.base_url}/real-estate/neighborhood-deals/{polygon_id}"

        params: Dict[str, Any] = {"limit": limit}
        if start_date:
            params["startDate"] = start_date
        if end_date:
            params["endDate"] = end_date

        try:
            logger.info(f"Getting neighborhood deals for polygon: {polygon_id}")
            response = self.session.get(url, params=params)
            response.raise_for_status()

            data = response.json()
            # API returns {data: [...], totalCount: ..., limit: ..., offset: ...}
            if isinstance(data, dict) and 'data' in data:
                return data['data'] if isinstance(data['data'], list) else []
            return data if isinstance(data, list) else []

        except requests.RequestException as e:
            logger.error(f"Error calling neighborhood deals API: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON response: {e}")
            return []

    def find_recent_deals_for_address(self, address: str, years_back: int = 2, 
                                    radius: int = 30, max_deals: int = 50) -> List[Dict[str, Any]]:
        """
        Find all relevant real estate deals for a given address from the last few years.

        This is the main use case function that ties everything together.
        Street deals include deals from the same building which get highest priority.

        Args:
            address: The address to search for
            years_back: How many years back to search (default: 2)
            radius: Search radius in meters for initial coordinate search (default: 30)
                   Small radius since street deals cover the entire street anyway
            max_deals: Maximum number of deals to return (default: 200)

        Returns:
            List of deals found for the address area, with same building deals prioritized first,
            then street deals, then neighborhood deals

        Raises:
            ValueError: If address cannot be found or processed
            requests.RequestException: If API requests fail
        """
        try:
            # Step 1: Get coordinates for the address
            logger.info(f"Starting search for address: {address}")
            autocomplete_result = self.autocomplete_address(address)

            if not autocomplete_result.get('results'):
                raise ValueError(f"No results found for address: {address}")

            # Get the best match (first result)
            best_match = autocomplete_result['results'][0]
            if 'shape' not in best_match:
                raise ValueError("No coordinates found in autocomplete result")

            # Parse coordinates from WKT POINT string
            # Format: "POINT(longitude latitude)"
            shape_str = best_match['shape']
            if not shape_str.startswith('POINT('):
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
                if 'polygon_id' in deal:
                    polygon_ids.add(str(deal['polygon_id']))

            logger.info(f"Found {len(polygon_ids)} unique polygon IDs")

            # Step 3: Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=years_back * 365)
            start_date_str = start_date.strftime('%Y-%m')
            end_date_str = end_date.strftime('%Y-%m')

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
                        polygon_id, limit=max_deals // 2,  # Allocate more to street deals
                        start_date=start_date_str, end_date=end_date_str
                    )

                    # Get neighborhood deals (lower priority)
                    current_neighborhood_deals = self.get_neighborhood_deals(
                        polygon_id, limit=max_deals // 4,  # Allocate less to neighborhood deals
                        start_date=start_date_str, end_date=end_date_str
                    )

                    # Process street deals and separate building deals
                    for deal in current_street_deals:
                        deal_id = f"{deal.get('dealId', '')}{deal.get('address', '')}{deal.get('dealDate', '')}"
                        if deal_id not in seen_deals:
                            seen_deals.add(deal_id)
                            deal['source_polygon_id'] = polygon_id
                            deal['deal_source'] = 'street'
                            
                            # Check if this is from the same building
                            deal_address = deal.get('address', '').lower().strip()
                            if self._is_same_building(search_address_normalized, deal_address):
                                deal['deal_source'] = 'same_building'
                                deal['priority'] = 0  # Highest priority
                                building_deals.append(deal)
                            else:
                                deal['priority'] = 1  # Street deals priority
                                street_deals.append(deal)

                    # Add neighborhood deals with lowest priority
                    for deal in current_neighborhood_deals:
                        deal_id = f"{deal.get('dealId', '')}{deal.get('address', '')}{deal.get('dealDate', '')}"
                        if deal_id not in seen_deals:
                            seen_deals.add(deal_id)
                            deal['source_polygon_id'] = polygon_id
                            deal['deal_source'] = 'neighborhood'
                            deal['priority'] = 2  # Lowest priority
                            neighborhood_deals.append(deal)

                except Exception as e:
                    logger.warning(f"Error processing polygon {polygon_id}: {e}")
                    continue

            # Step 5: Combine and prioritize: building deals first, then street, then neighborhood
            all_deals = building_deals + street_deals + neighborhood_deals

            # Use stable sort: first by date (newest first), then by priority
            # Since Python's sort is stable, the second sort maintains date order within each priority
            all_deals.sort(key=lambda x: x.get('dealDate', '1900-01-01'), reverse=True)  # Newest first
            all_deals.sort(key=lambda x: x.get('priority', 3))  # Priority first (0=building, 1=street, 2=neighborhood)

            # Limit to max_deals
            if len(all_deals) > max_deals:
                all_deals = all_deals[:max_deals]

            # Add price per square meter calculation
            for deal in all_deals:
                price = deal.get('dealAmount', 0)
                area = deal.get('assetArea', 0)
                if isinstance(price, (int, float)) and isinstance(area, (int, float)) and area > 0:
                    deal['price_per_sqm'] = round(price / area, 2)
                else:
                    deal['price_per_sqm'] = None

            logger.info(f"Found {len(all_deals)} total deals for address: {address} "
                       f"(Building: {len(building_deals)}, Street: {len(street_deals)}, Neighborhood: {len(neighborhood_deals)})")
            return all_deals

        except Exception as e:
            logger.error(f"Error in find_recent_deals_for_address: {e}")
            raise

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
            addr_clean = addr.replace('רח\'', '').replace('רחוב', '').replace('שד\'', '').replace('שדרות', '')
            addr_clean = addr_clean.replace('  ', ' ').strip()
            
            # Try to extract number and street name
            parts = addr_clean.split()
            if len(parts) >= 2:
                # Look for number (could be at start or end)
                for i, part in enumerate(parts):
                    if part.isdigit() or any(c.isdigit() for c in part):
                        number = part
                        street_parts = parts[:i] + parts[i+1:]
                        street_name = ' '.join(street_parts).strip()
                        return (street_name, number)
            
            return (addr_clean, '')
        
        search_street, search_number = extract_address_parts(search_address)
        deal_street, deal_number = extract_address_parts(deal_address)
        
        # Same street and same number = same building
        if (search_street and deal_street and search_number and deal_number and
            search_street == deal_street and search_number == deal_number):
            return True
            
        # Check if one address is contained in the other (for different formats of same address)
        if len(search_address) > 5 and len(deal_address) > 5:
            if search_address in deal_address or deal_address in search_address:
                return True
                
        return False