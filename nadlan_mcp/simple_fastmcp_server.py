#!/usr/bin/env python3
"""
Simple FastMCP Server for Israeli Real Estate Data

This server provides access to Israeli government real estate data through the Govmap API
using the FastMCP library with simplified, working functions.
"""

import json
import logging
from typing import List, Dict
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
def get_neighborhood_deals(polygon_id: str, limit: int = 100) -> str:
    """Get real estate deals for a specific neighborhood polygon.
    
    Args:
        polygon_id: The polygon ID of the neighborhood
        limit: Maximum number of deals to return (default: 100)
        
    Returns:
        JSON string containing recent real estate deals in the specified neighborhood
    """
    try:
        deals = client.get_neighborhood_deals(polygon_id, limit)
        
        if not deals:
            return f"No deals found for polygon ID {polygon_id}"
        
        return json.dumps({
            "total_deals": len(deals),
            "polygon_id": polygon_id,
            "deals": deals
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"Error in get_neighborhood_deals: {e}")
        return f"Error fetching neighborhood deals: {str(e)}"

@mcp.tool()
def analyze_market_trends(address: str, years_back: int = 3) -> str:
    """Analyze market trends and price patterns for an area.
    
    Args:
        address: The address to analyze trends around
        years_back: How many years of data to analyze (default: 3)
        
    Returns:
        JSON string containing market trend analysis including:
        - Price trends over time
        - Average prices by property type
        - Market activity levels
        - Price per square meter trends
    """
    try:
        # Get deals for the address
        deals = client.find_recent_deals_for_address(address, years_back)
        
        if not deals:
            return f"No deals found for market analysis near '{address}'"
        
        # Analyze trends by year
        from collections import defaultdict
        
        yearly_data = defaultdict(list)
        property_types: Dict[str, int] = defaultdict(int)
        neighborhoods = set()
        
        for deal in deals:
            date_str = deal.get('dealDate', '')
            if date_str:
                year = date_str[:4]
                price = deal.get('dealAmount')
                area = deal.get('assetArea')
                prop_type = deal.get('assetTypeHeb', deal.get('propertyTypeDescription', 'Unknown'))
                neighborhood = deal.get('settlementNameHeb', deal.get('neighborhood'))
                
                if neighborhood:
                    neighborhoods.add(neighborhood)
                
                if isinstance(price, (int, float)) and isinstance(area, (int, float)) and area > 0:
                    yearly_data[year].append({
                        'price': price,
                        'area': area,
                        'price_per_sqm': price / area
                    })
                    property_types[prop_type] += 1
        
        # Calculate yearly trends
        yearly_trends = {}
        for year, year_deals in yearly_data.items():
            if year_deals:
                yearly_trends[year] = {
                    "average_price": sum(d['price'] for d in year_deals) / len(year_deals),
                    "min_price": min(d['price'] for d in year_deals),
                    "max_price": max(d['price'] for d in year_deals),
                    "average_area": sum(d['area'] for d in year_deals) / len(year_deals),
                    "average_price_per_sqm": sum(d['price_per_sqm'] for d in year_deals) / len(year_deals),
                    "deal_count": len(year_deals)
                }
        
        # Calculate price trend direction
        price_trend_analysis = {}
        years_sorted = sorted(yearly_trends.keys())
        if len(years_sorted) >= 2:
            first_year_avg = yearly_trends[years_sorted[0]]['average_price_per_sqm']
            last_year_avg = yearly_trends[years_sorted[-1]]['average_price_per_sqm']
            
            trend_percentage = ((last_year_avg - first_year_avg) / first_year_avg) * 100
            trend_direction = "rising" if trend_percentage > 5 else "declining" if trend_percentage < -5 else "stable"
            
            price_trend_analysis = {
                "trend_direction": trend_direction,
                "trend_percentage": round(trend_percentage, 1),
                "first_year": years_sorted[0],
                "last_year": years_sorted[-1],
                "first_year_avg_price_per_sqm": round(first_year_avg, 0),
                "last_year_avg_price_per_sqm": round(last_year_avg, 0)
            }
        
        return json.dumps({
            "analysis_address": address,
            "analysis_period_years": years_back,
            "total_deals_analyzed": len(deals),
            "neighborhoods": list(neighborhoods),
            "property_types": dict(property_types),
            "yearly_trends": yearly_trends,
            "price_trend_analysis": price_trend_analysis
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"Error in analyze_market_trends: {e}")
        return f"Error analyzing market trends: {str(e)}"

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