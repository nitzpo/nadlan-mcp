#!/usr/bin/env python3
"""
Simple FastMCP Server for Israeli Real Estate Data

This server provides access to Israeli government real estate data through the Govmap API
using the FastMCP library with simplified, working functions.
"""

import json
import logging
from typing import List
from mcp.server.fastmcp import FastMCP
from .main import GovmapClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("nadlan-mcp")

# Initialize the Govmap client
client = GovmapClient()

@mcp.tool()
def autocomplete_address(search_text: str) -> str:
    """Search and autocomplete Israeli addresses.
    
    Args:
        search_text: The partial address to search for (in Hebrew or English)
        
    Returns:
        JSON string containing matching addresses with their coordinates
    """
    try:
        response = client.autocomplete_address(search_text)
        
        if not response or 'results' not in response:
            return f"No addresses found for '{search_text}'"
        
        # Format results for better readability
        formatted_results = []
        for result in response['results']:
            formatted_results.append({
                "address": result.get("addressLabel", ""),
                "settlement": result.get("settlementNameHeb", ""),
                "coordinates": result.get("coordinates", {}),
                "polygon_id": result.get("polygon_id")
            })
        
        return json.dumps(formatted_results, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"Error in autocomplete_address: {e}")
        return f"Error searching for address: {str(e)}"

@mcp.tool()
def get_deals_by_radius(latitude: float, longitude: float, radius_meters: int = 500) -> str:
    """Get real estate deals within a radius of coordinates.
    
    Args:
        latitude: Latitude coordinate
        longitude: Longitude coordinate  
        radius_meters: Search radius in meters (default: 500)
        
    Returns:
        JSON string containing recent real estate deals in the area
    """
    try:
        # Note: GovmapClient expects (longitude, latitude) tuple
        deals = client.get_deals_by_radius((longitude, latitude), radius_meters)
        
        if not deals:
            return f"No deals found within {radius_meters}m of coordinates ({latitude}, {longitude})"
        
        return json.dumps({
            "total_deals": len(deals),
            "search_radius_meters": radius_meters,
            "center_coordinates": {"latitude": latitude, "longitude": longitude},
            "deals": deals
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"Error in get_deals_by_radius: {e}")
        return f"Error fetching deals by radius: {str(e)}"

@mcp.tool()
def get_street_deals(polygon_id: str, limit: int = 100) -> str:
    """Get real estate deals for a specific street polygon.
    
    Args:
        polygon_id: The polygon ID of the street/area
        limit: Maximum number of deals to return (default: 100)
        
    Returns:
        JSON string containing recent real estate deals for the street
    """
    try:
        deals = client.get_street_deals(polygon_id, limit)
        
        if not deals:
            return f"No deals found for polygon ID {polygon_id}"
        
        return json.dumps({
            "total_deals": len(deals),
            "polygon_id": polygon_id,
            "deals": deals
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"Error in get_street_deals: {e}")
        return f"Error fetching street deals: {str(e)}"

@mcp.tool()
def find_recent_deals_for_address(address: str, years_back: int = 2) -> str:
    """Find recent real estate deals for a specific address.
    
    Args:
        address: The address to search for (in Hebrew or English)
        years_back: How many years back to search (default: 2)
        
    Returns:
        JSON string containing recent real estate deals for the address
    """
    try:
        deals = client.find_recent_deals_for_address(address, years_back)
        
        if not deals:
            return f"No deals found for address '{address}'"
        
        # Calculate basic statistics
        prices = [deal.get("dealAmount", 0) for deal in deals if deal.get("dealAmount")]
        areas = [deal.get("assetArea", 0) for deal in deals if deal.get("assetArea")]
        
        stats = {}
        if prices:
            stats["price_stats"] = {
                "average_price": sum(prices) / len(prices),
                "min_price": min(prices),
                "max_price": max(prices),
                "total_deals": len(prices)
            }
        
        if areas:
            stats["area_stats"] = {
                "average_area": sum(areas) / len(areas),
                "min_area": min(areas),
                "max_area": max(areas)
            }
        
        return json.dumps({
            "search_address": address,
            "years_back": years_back,
            "total_deals": len(deals),
            "market_statistics": stats,
            "deals": deals
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"Error in find_recent_deals_for_address: {e}")
        return f"Error analyzing address: {str(e)}"

@mcp.tool()
def compare_addresses(addresses: List[str]) -> str:
    """Compare real estate markets between multiple addresses.
    
    Args:
        addresses: List of addresses to compare (in Hebrew or English)
        
    Returns:
        JSON string containing comparative analysis of multiple addresses
    """
    try:
        comparisons = []
        
        for address in addresses:
            try:
                deals = client.find_recent_deals_for_address(address, 2)
                
                if deals:
                    prices = [deal.get("dealAmount", 0) for deal in deals if deal.get("dealAmount")]
                    areas = [deal.get("assetArea", 0) for deal in deals if deal.get("assetArea")]
                    
                    comparison = {
                        "address": address,
                        "total_deals": len(deals),
                        "price_stats": {
                            "average_price": sum(prices) / len(prices) if prices else 0,
                            "min_price": min(prices) if prices else 0,
                            "max_price": max(prices) if prices else 0
                        },
                        "area_stats": {
                            "average_area": sum(areas) / len(areas) if areas else 0,
                            "min_area": min(areas) if areas else 0,
                            "max_area": max(areas) if areas else 0
                        }
                    }
                else:
                    comparison = {
                        "address": address,
                        "total_deals": 0,
                        "price_stats": {},
                        "area_stats": {}
                    }
                
                comparisons.append(comparison)
                
            except Exception as e:
                logger.error(f"Error comparing {address}: {e}")
                comparisons.append({
                    "address": address,
                    "error": str(e)
                })
        
        # Rank addresses by average price
        valid_comparisons = [c for c in comparisons if c.get("price_stats", {}).get("average_price", 0) > 0]
        valid_comparisons.sort(key=lambda x: x["price_stats"]["average_price"], reverse=True)
        
        return json.dumps({
            "addresses_compared": len(addresses),
            "ranking_by_average_price": valid_comparisons,
            "all_results": comparisons
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"Error in compare_addresses: {e}")
        return f"Error comparing addresses: {str(e)}"

# Run the server
if __name__ == "__main__":
    mcp.run() 