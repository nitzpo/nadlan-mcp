#!/usr/bin/env python3
"""
FastMCP Server for Israeli Real Estate Data (Nadlan)

This server provides access to Israeli government real estate data through the Govmap API
using the FastMCP library for better compatibility and reliability.
"""

import logging
from typing import List, Dict, Any, Optional
from mcp.server.fastmcp import FastMCP
from .main import GovmapClient  # type: ignore

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("nadlan-mcp")

# Initialize the Govmap client
client = GovmapClient()

@mcp.tool()
async def autocomplete_address(search_text: str) -> str:
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
        
        import json
        return json.dumps(formatted_results, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"Error in autocomplete_address: {e}")
        return f"Error searching for address: {str(e)}"

@mcp.tool()
async def get_deals_by_radius(
    latitude: float, 
    longitude: float, 
    radius_meters: int = 500,
    limit: int = 100
) -> str:
    """Get real estate deals within a radius of coordinates.
    
    Args:
        latitude: Latitude coordinate
        longitude: Longitude coordinate  
        radius_meters: Search radius in meters (default: 500)
        limit: Maximum number of deals to return (default: 100)
        
    Returns:
        JSON string containing recent real estate deals in the area
    """
    try:
        deals = client.get_deals_by_radius((longitude, latitude), radius_meters)
        
        if not deals:
            return f"No deals found within {radius_meters}m of coordinates ({latitude}, {longitude})"
        
        # Format deals for better readability
        formatted_deals = []
        for deal in deals:
            formatted_deals.append({
                "address": deal.get("addressLabel", ""),
                "settlement": deal.get("settlementNameHeb", ""),
                "deal_amount": deal.get("dealAmount"),
                "deal_date": deal.get("dealDate", ""),
                "asset_area": deal.get("assetArea"),
                "asset_type": deal.get("assetTypeHeb", ""),
                "coordinates": deal.get("coordinates", {})
            })
        
        import json
        return json.dumps({
            "total_deals": len(formatted_deals),
            "search_radius_meters": radius_meters,
            "center_coordinates": {"latitude": latitude, "longitude": longitude},
            "deals": formatted_deals
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"Error in get_deals_by_radius: {e}")
        return f"Error fetching deals by radius: {str(e)}"

@mcp.tool()
async def get_street_deals(street_name: str, settlement_name: str, limit: int = 100) -> str:
    """Get real estate deals for a specific street.
    
    Args:
        street_name: Name of the street (in Hebrew)
        settlement_name: Name of the city/settlement (in Hebrew)
        limit: Maximum number of deals to return (default: 100)
        
    Returns:
        JSON string containing recent real estate deals on the specified street
    """
    try:
        deals = await client.get_street_deals(street_name, settlement_name, limit)
        
        if not deals:
            return f"No deals found for {street_name}, {settlement_name}"
        
        # Format deals for better readability
        formatted_deals = []
        for deal in deals:
            formatted_deals.append({
                "address": deal.get("addressLabel", ""),
                "settlement": deal.get("settlementNameHeb", ""),
                "deal_amount": deal.get("dealAmount"),
                "deal_date": deal.get("dealDate", ""),
                "asset_area": deal.get("assetArea"),
                "asset_type": deal.get("assetTypeHeb", ""),
                "coordinates": deal.get("coordinates", {})
            })
        
        import json
        return json.dumps({
            "total_deals": len(formatted_deals),
            "street": street_name,
            "settlement": settlement_name,
            "deals": formatted_deals
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"Error in get_street_deals: {e}")
        return f"Error fetching street deals: {str(e)}"

@mcp.tool()
async def get_neighborhood_deals(polygon_id: str, limit: int = 100) -> str:
    """Get real estate deals for a specific neighborhood polygon.
    
    Args:
        polygon_id: The polygon ID of the neighborhood
        limit: Maximum number of deals to return (default: 100)
        
    Returns:
        JSON string containing recent real estate deals in the specified neighborhood
    """
    try:
        deals = await client.get_neighborhood_deals(polygon_id, limit)
        
        if not deals:
            return f"No deals found for polygon ID {polygon_id}"
        
        # Format deals for better readability
        formatted_deals = []
        for deal in deals:
            formatted_deals.append({
                "address": deal.get("addressLabel", ""),
                "settlement": deal.get("settlementNameHeb", ""),
                "deal_amount": deal.get("dealAmount"),
                "deal_date": deal.get("dealDate", ""),
                "asset_area": deal.get("assetArea"),
                "asset_type": deal.get("assetTypeHeb", ""),
                "coordinates": deal.get("coordinates", {})
            })
        
        import json
        return json.dumps({
            "total_deals": len(formatted_deals),
            "polygon_id": polygon_id,
            "deals": formatted_deals
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"Error in get_neighborhood_deals: {e}")
        return f"Error fetching neighborhood deals: {str(e)}"

@mcp.tool()
async def find_recent_deals_for_address(
    address: str, 
    radius_meters: int = 500, 
    limit: int = 100
) -> str:
    """Comprehensive analysis of recent real estate deals for an address.
    
    This is the main tool for getting detailed market analysis around a specific address.
    It finds the coordinates for the address and then searches for deals in the area.
    
    Args:
        address: The address to analyze (in Hebrew or English)
        radius_meters: Search radius in meters (default: 500)
        limit: Maximum number of deals to return (default: 100)
        
    Returns:
        JSON string containing comprehensive real estate analysis including:
        - Address details and coordinates
        - Recent deals in the area
        - Market statistics and trends
    """
    try:
        deals = await client.find_recent_deals_for_address(address, radius_meters, limit)
        
        if not deals:
            return f"No deals found for address '{address}'"
        
        # Calculate market statistics
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
        
        # Format deals for better readability
        formatted_deals = []
        for deal in deals:
            formatted_deals.append({
                "address": deal.get("addressLabel", ""),
                "settlement": deal.get("settlementNameHeb", ""),
                "deal_amount": deal.get("dealAmount"),
                "deal_date": deal.get("dealDate", ""),
                "asset_area": deal.get("assetArea"),
                "asset_type": deal.get("assetTypeHeb", ""),
                "coordinates": deal.get("coordinates", {})
            })
        
        import json
        return json.dumps({
            "search_address": address,
            "search_radius_meters": radius_meters,
            "total_deals": len(formatted_deals),
            "market_statistics": stats,
            "deals": formatted_deals
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"Error in find_recent_deals_for_address: {e}")
        return f"Error analyzing address: {str(e)}"

@mcp.tool()
async def analyze_market_trends(
    address: str, 
    radius_meters: int = 1000, 
    limit: int = 200
) -> str:
    """Analyze market trends and price patterns for an area.
    
    Args:
        address: The address to analyze trends around
        radius_meters: Search radius in meters (default: 1000)
        limit: Maximum number of deals to analyze (default: 200)
        
    Returns:
        JSON string containing market trend analysis including:
        - Price trends over time
        - Average prices by property type
        - Market activity levels
    """
    try:
        # Get deals for the address
        deals = await client.find_recent_deals_for_address(address, radius_meters, limit)
        
        if not deals:
            return f"No deals found for market analysis near '{address}'"
        
        # Analyze trends by year
        from collections import defaultdict
        import json
        
        trends_by_year = defaultdict(list)
        trends_by_type = defaultdict(list)
        
        for deal in deals:
            deal_date = deal.get("dealDate", "")
            deal_amount = deal.get("dealAmount", 0)
            asset_type = deal.get("assetTypeHeb", "Unknown")
            
            if deal_date and deal_amount:
                year = deal_date.split('-')[0] if '-' in deal_date else deal_date[:4]
                trends_by_year[year].append(deal_amount)
                trends_by_type[asset_type].append(deal_amount)
        
        # Calculate yearly trends
        yearly_trends = {}
        for year, prices in trends_by_year.items():
            yearly_trends[year] = {
                "average_price": sum(prices) / len(prices),
                "min_price": min(prices),
                "max_price": max(prices),
                "deal_count": len(prices)
            }
        
        # Calculate type trends
        type_trends = {}
        for asset_type, prices in trends_by_type.items():
            type_trends[asset_type] = {
                "average_price": sum(prices) / len(prices),
                "min_price": min(prices),
                "max_price": max(prices),
                "deal_count": len(prices)
            }
        
        return json.dumps({
            "analysis_address": address,
            "analysis_radius_meters": radius_meters,
            "total_deals_analyzed": len(deals),
            "yearly_trends": yearly_trends,
            "property_type_trends": type_trends
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"Error in analyze_market_trends: {e}")
        return f"Error analyzing market trends: {str(e)}"

@mcp.tool()
async def compare_neighborhoods(addresses: List[str], radius_meters: int = 500) -> str:
    """Compare real estate markets between multiple neighborhoods.
    
    Args:
        addresses: List of addresses to compare (in Hebrew or English)
        radius_meters: Search radius for each address (default: 500)
        
    Returns:
        JSON string containing comparative analysis of multiple neighborhoods
    """
    try:
        import json
        
        comparisons = []
        
        for address in addresses:
            try:
                deals = await client.find_recent_deals_for_address(address, radius_meters, 100)
                
                if deals:
                    prices = []
                    areas = []
                    for deal in deals:
                        if isinstance(deal, dict):
                            if deal.get("dealAmount"):
                                prices.append(deal.get("dealAmount", 0))
                            if deal.get("assetArea"):
                                areas.append(deal.get("assetArea", 0))
                    
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
        
        # Rank neighborhoods by average price
        valid_comparisons = [c for c in comparisons if c.get("price_stats", {}).get("average_price", 0) > 0]
        valid_comparisons.sort(key=lambda x: x["price_stats"]["average_price"], reverse=True)
        
        return json.dumps({
            "comparison_radius_meters": radius_meters,
            "neighborhoods_compared": len(addresses),
            "ranking_by_average_price": valid_comparisons,
            "all_results": comparisons
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"Error in compare_neighborhoods: {e}")
        return f"Error comparing neighborhoods: {str(e)}"

# Run the server
if __name__ == "__main__":
    mcp.run() 