"""
Israel Real Estate MCP - Main Module

This module provides the GovmapClient class for interacting with the Israeli
government's public real estate data API (Govmap).
"""

import requests
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
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
    
    def find_recent_deals_for_address(self, address: str, years_back: int = 2) -> List[Dict[str, Any]]:
        """
        Find all relevant real estate deals for a given address from the last few years.
        
        This is the main use case function that ties everything together.
        
        Args:
            address: The address to search for
            years_back: How many years back to search (default: 2)
            
        Returns:
            List of deals found for the address area
            
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
            logger.info(f"Found coordinates: {point}")
            
            # Step 2: Get deals by radius to find polygon IDs
            nearby_deals = self.get_deals_by_radius(point, radius=30)  # Slightly larger radius
            
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
            all_deals = []
            seen_deals = set()  # For deduplication
            
            for polygon_id in polygon_ids:
                try:
                    # Get street deals
                    street_deals = self.get_street_deals(
                        polygon_id, limit=50, 
                        start_date=start_date_str, end_date=end_date_str
                    )
                    
                    # Get neighborhood deals
                    neighborhood_deals = self.get_neighborhood_deals(
                        polygon_id, limit=50,
                        start_date=start_date_str, end_date=end_date_str
                    )
                    
                    # Combine deals
                    combined_deals = street_deals + neighborhood_deals
                    
                    # Add to results with deduplication
                    for deal in combined_deals:
                        # Create a unique identifier for the deal
                        deal_id = f"{deal.get('dealId', '')}{deal.get('address', '')}{deal.get('dealDate', '')}"
                        
                        if deal_id not in seen_deals:
                            seen_deals.add(deal_id)
                            deal['source_polygon_id'] = polygon_id  # Add source for reference
                            all_deals.append(deal)
                            
                except Exception as e:
                    logger.warning(f"Error processing polygon {polygon_id}: {e}")
                    continue
            
            # Step 5: Sort by date (newest first)
            all_deals.sort(key=lambda x: x.get('dealDate', ''), reverse=True)
            
            logger.info(f"Found {len(all_deals)} total deals for address: {address}")
            return all_deals
            
        except Exception as e:
            logger.error(f"Error in find_recent_deals_for_address: {e}")
            raise


# Example usage functions
def main():
    """
    Example usage of the GovmapClient.
    """
    # Initialize client
    client = GovmapClient()
    
    # Example address search
    address = "סוקולוב 38 חולון"
    
    try:
        # Find recent deals for address
        deals = client.find_recent_deals_for_address(address, years_back=2)
        
        print(f"Found {len(deals)} deals for address: {address}")
        
        # Display first few deals
        for i, deal in enumerate(deals[:5]):
            print(f"\nDeal {i+1}:")
            
            # Build address from available fields
            address_parts = []
            if deal.get('streetNameHeb'):
                address_parts.append(deal.get('streetNameHeb'))
            if deal.get('houseNum'):
                address_parts.append(str(deal.get('houseNum')))
            if deal.get('settlementNameHeb'):
                address_parts.append(deal.get('settlementNameHeb'))
            address = ' '.join(address_parts) if address_parts else 'N/A'
            
            print(f"  Address: {address}")
            print(f"  Date: {deal.get('dealDate', 'N/A')[:10] if deal.get('dealDate') else 'N/A'}")
            print(f"  Price: {deal.get('dealAmount', 'N/A'):,} NIS" if deal.get('dealAmount') else "  Price: N/A")
            print(f"  Area: {deal.get('assetArea', 'N/A')} m²" if deal.get('assetArea') else "  Area: N/A")
            print(f"  Type: {deal.get('propertyTypeDescription', 'N/A')}")
            print(f"  Neighborhood: {deal.get('neighborhood', 'N/A')}")
            
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main() 