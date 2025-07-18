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
from nadlan_mcp.govmap import GovmapClient

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
def get_street_deals(polygon_id: str, limit: int = 100, deal_type: int = 2) -> str:
    """Get real estate deals for a specific street polygon.
    
    Args:
        polygon_id: The polygon ID of the street/area
        limit: Maximum number of deals to return (default: 100)
        deal_type: Deal type filter (1=first hand/new, 2=second hand/used, default: 2)
        
    Returns:
        JSON string containing recent real estate deals for the street
    """
    try:
        deals = client.get_street_deals(polygon_id, limit, deal_type=deal_type)
        
        if not deals:
            deal_type_desc = "first hand (new)" if deal_type == 1 else "second hand (used)"
            return f"No {deal_type_desc} deals found for polygon ID {polygon_id}"
        
        # Add price per sqm calculation for each deal
        for deal in deals:
            price = deal.get('dealAmount', 0)
            area = deal.get('assetArea', 0)
            if isinstance(price, (int, float)) and isinstance(area, (int, float)) and area > 0:
                deal['price_per_sqm'] = round(price / area, 2)
            else:
                deal['price_per_sqm'] = None
            # Add deal type info
            deal['deal_type'] = deal_type
            deal['deal_type_description'] = 'first_hand_new' if deal_type == 1 else 'second_hand_used'
        
        # Calculate basic statistics including price per sqm
        prices = [deal.get("dealAmount", 0) for deal in deals if deal.get("dealAmount")]
        price_per_sqm_values = [deal.get("price_per_sqm", 0) for deal in deals if deal.get("price_per_sqm")]
        
        stats = {}
        if price_per_sqm_values:
            stats["price_per_sqm_stats"] = {
                "average_price_per_sqm": round(sum(price_per_sqm_values) / len(price_per_sqm_values), 0),
                "min_price_per_sqm": round(min(price_per_sqm_values), 0),
                "max_price_per_sqm": round(max(price_per_sqm_values), 0)
            }
        
        deal_type_desc = "first hand (new)" if deal_type == 1 else "second hand (used)"
        return json.dumps({
            "total_deals": len(deals),
            "polygon_id": polygon_id,
            "deal_type": deal_type,
            "deal_type_description": deal_type_desc,
            "market_statistics": stats,
            "deals": deals
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"Error in get_street_deals: {e}")
        return f"Error fetching street deals: {str(e)}"

@mcp.tool()
def find_recent_deals_for_address(address: str, years_back: int = 2, radius_meters: int = 30, max_deals: int = 50, deal_type: int = 2) -> str:
    """Find recent real estate deals for a specific address.
    
    Args:
        address: The address to search for (in Hebrew or English)
        years_back: How many years back to search (default: 2)
        radius_meters: Search radius in meters from the address (default: 30)
                      Small radius since street deals cover the entire street anyway
        max_deals: Maximum number of deals to return (default: 50, optimized for LLM token limits)
        deal_type: Deal type filter (1=first hand/new, 2=second hand/used, default: 2)
        
    Returns:
        JSON string containing recent real estate deals for the address
    """
    try:
        deals = client.find_recent_deals_for_address(address, years_back, radius_meters, max_deals, deal_type)
        
        if not deals:
            deal_type_desc = "first hand (new)" if deal_type == 1 else "second hand (used)"
            return f"No {deal_type_desc} deals found for address '{address}'"
        
        # Calculate comprehensive statistics
        prices = [deal.get("dealAmount", 0) for deal in deals if deal.get("dealAmount")]
        areas = [deal.get("assetArea", 0) for deal in deals if deal.get("assetArea")]
        price_per_sqm_values = [deal.get("price_per_sqm", 0) for deal in deals if deal.get("price_per_sqm")]
        
        # Separate building, street and neighborhood deals for analysis
        building_deals = [deal for deal in deals if deal.get("deal_source") == "same_building"]
        street_deals = [deal for deal in deals if deal.get("deal_source") == "street"]
        neighborhood_deals = [deal for deal in deals if deal.get("deal_source") == "neighborhood"]
        
        stats = {
            "deal_breakdown": {
                "total_deals": len(deals),
                "same_building_deals": len(building_deals),
                "street_deals": len(street_deals),
                "neighborhood_deals": len(neighborhood_deals),
                "same_building_percentage": round((len(building_deals) / len(deals)) * 100, 1) if deals else 0,
                "street_emphasis_percentage": round((len(street_deals) / len(deals)) * 100, 1) if deals else 0,
                "neighborhood_percentage": round((len(neighborhood_deals) / len(deals)) * 100, 1) if deals else 0
            }
        }
        
        if prices:
            stats["price_stats"] = {
                "average_price": round(sum(prices) / len(prices), 0),
                "min_price": min(prices),
                "max_price": max(prices),
                "median_price": sorted(prices)[len(prices)//2] if prices else 0,
                "total_volume": sum(prices)
            }
        
        if areas:
            stats["area_stats"] = {
                "average_area": round(sum(areas) / len(areas), 1),
                "min_area": min(areas),
                "max_area": max(areas),
                "median_area": sorted(areas)[len(areas)//2] if areas else 0
            }
            
        if price_per_sqm_values:
            stats["price_per_sqm_stats"] = {
                "average_price_per_sqm": round(sum(price_per_sqm_values) / len(price_per_sqm_values), 0),
                "min_price_per_sqm": round(min(price_per_sqm_values), 0),
                "max_price_per_sqm": round(max(price_per_sqm_values), 0),
                "median_price_per_sqm": round(sorted(price_per_sqm_values)[len(price_per_sqm_values)//2], 0) if price_per_sqm_values else 0
            }
        
        deal_type_desc = "first hand (new)" if deal_type == 1 else "second hand (used)"
        return json.dumps({
            "search_parameters": {
                "address": address,
                "years_back": years_back,
                "radius_meters": radius_meters,
                "max_deals": max_deals,
                "deal_type": deal_type,
                "deal_type_description": deal_type_desc
            },
            "market_statistics": stats,
            "deals": deals
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"Error in find_recent_deals_for_address: {e}")
        return f"Error analyzing address: {str(e)}"

@mcp.tool()
def get_neighborhood_deals(polygon_id: str, limit: int = 100, deal_type: int = 2) -> str:
    """Get real estate deals for a specific neighborhood polygon.
    
    Args:
        polygon_id: The polygon ID of the neighborhood
        limit: Maximum number of deals to return (default: 100)
        deal_type: Deal type filter (1=first hand/new, 2=second hand/used, default: 2)
        
    Returns:
        JSON string containing recent real estate deals in the specified neighborhood
    """
    try:
        deals = client.get_neighborhood_deals(polygon_id, limit, deal_type=deal_type)
        
        if not deals:
            deal_type_desc = "first hand (new)" if deal_type == 1 else "second hand (used)"
            return f"No {deal_type_desc} deals found for polygon ID {polygon_id}"
        
        # Add price per sqm calculation for each deal
        for deal in deals:
            price = deal.get('dealAmount', 0)
            area = deal.get('assetArea', 0)
            if isinstance(price, (int, float)) and isinstance(area, (int, float)) and area > 0:
                deal['price_per_sqm'] = round(price / area, 2)
            else:
                deal['price_per_sqm'] = None
            # Add deal type info
            deal['deal_type'] = deal_type
            deal['deal_type_description'] = 'first_hand_new' if deal_type == 1 else 'second_hand_used'
        
        # Calculate basic statistics including price per sqm
        prices = [deal.get("dealAmount", 0) for deal in deals if deal.get("dealAmount")]
        price_per_sqm_values = [deal.get("price_per_sqm", 0) for deal in deals if deal.get("price_per_sqm")]
        
        stats = {}
        if price_per_sqm_values:
            stats["price_per_sqm_stats"] = {
                "average_price_per_sqm": round(sum(price_per_sqm_values) / len(price_per_sqm_values), 0),
                "min_price_per_sqm": round(min(price_per_sqm_values), 0),
                "max_price_per_sqm": round(max(price_per_sqm_values), 0)
            }
        
        deal_type_desc = "first hand (new)" if deal_type == 1 else "second hand (used)"
        return json.dumps({
            "total_deals": len(deals),
            "polygon_id": polygon_id,
            "deal_type": deal_type,
            "deal_type_description": deal_type_desc,
            "market_statistics": stats,
            "deals": deals
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"Error in get_neighborhood_deals: {e}")
        return f"Error fetching neighborhood deals: {str(e)}"

@mcp.tool()
def analyze_market_trends(address: str, years_back: int = 3, radius_meters: int = 100, max_deals: int = 100, deal_type: int = 2) -> str:
    """Analyze market trends and price patterns for an area with comprehensive data.
    
    Args:
        address: The address to analyze trends around
        years_back: How many years of data to analyze (default: 3)
        radius_meters: Search radius in meters from the address (default: 100, larger for trend analysis)
        max_deals: Maximum number of deals to analyze (default: 100, optimized for performance and token limits)
        deal_type: Deal type filter (1=first hand/new, 2=second hand/used, default: 2)
        
    Returns:
        JSON string containing comprehensive market trend analysis (summarized data, not raw deals)
    """
    try:
        # Get deals for the address with larger radius for trend analysis
        deals = client.find_recent_deals_for_address(address, years_back, radius_meters, max_deals, deal_type)
        
        if not deals:
            deal_type_desc = "first hand (new)" if deal_type == 1 else "second hand (used)"
            return f"No {deal_type_desc} deals found for comprehensive market analysis near '{address}'"
        
        # Efficient analysis with reduced complexity
        from collections import defaultdict
        
        yearly_data = defaultdict(list)
        property_types: Dict[str, List[float]] = defaultdict(list)  # Store only prices for efficiency
        neighborhoods = defaultdict(list)
        
        # Simplified processing - extract only essential data
        for deal in deals:
            date_str = deal.get('dealDate', '')
            if not date_str:
                continue
                
            year = date_str[:4]
            price = deal.get('dealAmount')
            area = deal.get('assetArea')
            price_per_sqm = deal.get('price_per_sqm')
            prop_type = deal.get('assetTypeHeb', deal.get('propertyTypeDescription', 'לא ידוע'))
            neighborhood = deal.get('settlementNameHeb', deal.get('neighborhood', 'לא ידוע'))
            deal_source = deal.get('deal_source', 'unknown')
            
            if isinstance(price, (int, float)) and isinstance(area, (int, float)) and area > 0 and isinstance(price_per_sqm, (int, float)):
                yearly_data[year].append({
                    'price': price, 'area': area, 'price_per_sqm': price_per_sqm, 'deal_source': deal_source
                })
                property_types[prop_type].append(price_per_sqm)
                neighborhoods[neighborhood].append(price_per_sqm)
        
        # Calculate streamlined yearly trends
        yearly_trends = {}
        for year, year_deals in yearly_data.items():
            if year_deals:
                prices = [d['price'] for d in year_deals]
                price_per_sqm_vals = [d['price_per_sqm'] for d in year_deals]
                building_deals = [d for d in year_deals if d['deal_source'] == 'same_building']
                street_deals = [d for d in year_deals if d['deal_source'] == 'street']
                
                yearly_trends[year] = {
                    "deal_count": len(year_deals),
                    "same_building_deals": len(building_deals),
                    "street_deals": len(street_deals),
                    "avg_price": round(sum(prices) / len(prices), 0),
                    "avg_price_per_sqm": round(sum(price_per_sqm_vals) / len(price_per_sqm_vals), 0),
                    "min_price_per_sqm": round(min(price_per_sqm_vals), 0),
                    "max_price_per_sqm": round(max(price_per_sqm_vals), 0),
                    "total_volume": sum(prices)
                }
        
        # Streamlined property type analysis (top 5 only)
        property_type_analysis = {}
        for prop_type, prices_per_sqm in property_types.items():
            if len(prices_per_sqm) >= 2:  # Only include types with multiple deals
                property_type_analysis[prop_type] = {
                    "deal_count": len(prices_per_sqm),
                    "avg_price_per_sqm": round(sum(prices_per_sqm) / len(prices_per_sqm), 0)
                }
        
        # Keep only top 5 property types by deal count
        property_type_analysis = dict(sorted(property_type_analysis.items(), 
                                           key=lambda x: x[1]['deal_count'], reverse=True)[:5])
        
        # Streamlined neighborhood analysis (top 5 only)
        neighborhood_analysis = {}
        for neighborhood, prices_per_sqm in neighborhoods.items():
            if len(prices_per_sqm) >= 3:  # Minimum 3 deals for statistical significance
                neighborhood_analysis[neighborhood] = {
                    "deal_count": len(prices_per_sqm),
                    "avg_price_per_sqm": round(sum(prices_per_sqm) / len(prices_per_sqm), 0)
                }
        
        # Keep only top 5 neighborhoods by deal count
        neighborhood_analysis = dict(sorted(neighborhood_analysis.items(), 
                                          key=lambda x: x[1]['deal_count'], reverse=True)[:5])
        
        # Simple trend analysis
        years_sorted = sorted(yearly_trends.keys())
        trend_analysis = {}
        if len(years_sorted) >= 2:
            first_year = yearly_trends[years_sorted[0]]
            last_year = yearly_trends[years_sorted[-1]]
            
            if first_year['avg_price_per_sqm'] > 0:
                price_change = ((last_year['avg_price_per_sqm'] - first_year['avg_price_per_sqm']) / first_year['avg_price_per_sqm']) * 100
                volume_change = ((last_year['deal_count'] - first_year['deal_count']) / first_year['deal_count']) * 100 if first_year['deal_count'] > 0 else 0
                
                trend_analysis = {
                    "price_trend_percentage": round(price_change, 1),
                    "volume_trend_percentage": round(volume_change, 1),
                    "first_year_avg_price_per_sqm": first_year['avg_price_per_sqm'],
                    "last_year_avg_price_per_sqm": last_year['avg_price_per_sqm']
                }
        
        deal_type_desc = "first hand (new)" if deal_type == 1 else "second hand (used)"
        
        # Return summarized analysis (NO raw deals to save tokens)
        return json.dumps({
            "analysis_parameters": {
                "address": address,
                "years_analyzed": years_back,
                "radius_meters": radius_meters,
                "deals_analyzed": len(deals),
                "deal_type": deal_type,
                "deal_type_description": deal_type_desc
            },
            "market_summary": {
                "total_deals": len(deals),
                "years_with_data": len(yearly_trends),
                "unique_property_types": len(property_type_analysis),
                "unique_neighborhoods": len(neighborhood_analysis)
            },
            "yearly_trends": yearly_trends,
            "top_property_types": property_type_analysis,
            "top_neighborhoods": neighborhood_analysis,
            "trend_analysis": trend_analysis,
            "key_insights": {
                "most_active_year": max(yearly_trends.keys(), key=lambda y: yearly_trends[y]['deal_count']) if yearly_trends else None,
                "highest_avg_price_year": max(yearly_trends.keys(), key=lambda y: yearly_trends[y]['avg_price_per_sqm']) if yearly_trends else None,
                "deal_source_summary": f"Building: {len([d for d in deals if d.get('deal_source') == 'same_building'])}, Street: {len([d for d in deals if d.get('deal_source') == 'street'])}, Neighborhood: {len([d for d in deals if d.get('deal_source') == 'neighborhood'])}"
            }
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
                    price_per_sqm_values = [deal.get("price_per_sqm", 0) for deal in deals if deal.get("price_per_sqm")]
                    building_deals = [deal for deal in deals if deal.get("deal_source") == "same_building"]
                    street_deals = [deal for deal in deals if deal.get("deal_source") == "street"]
                    neighborhood_deals = [deal for deal in deals if deal.get("deal_source") == "neighborhood"]
                    
                    comparison = {
                        "address": address,
                        "total_deals": len(deals),
                        "same_building_deals": len(building_deals),
                        "street_deals": len(street_deals),
                        "neighborhood_deals": len(neighborhood_deals),
                        "same_building_percentage": round((len(building_deals) / len(deals)) * 100, 1) if deals else 0,
                        "street_emphasis_percentage": round((len(street_deals) / len(deals)) * 100, 1) if deals else 0,
                        "price_stats": {
                            "average_price": round(sum(prices) / len(prices), 0) if prices else 0,
                            "min_price": min(prices) if prices else 0,
                            "max_price": max(prices) if prices else 0
                        },
                        "area_stats": {
                            "average_area": round(sum(areas) / len(areas), 1) if areas else 0,
                            "min_area": min(areas) if areas else 0,
                            "max_area": max(areas) if areas else 0
                        },
                        "price_per_sqm_stats": {
                            "average_price_per_sqm": round(sum(price_per_sqm_values) / len(price_per_sqm_values), 0) if price_per_sqm_values else 0,
                            "min_price_per_sqm": round(min(price_per_sqm_values), 0) if price_per_sqm_values else 0,
                            "max_price_per_sqm": round(max(price_per_sqm_values), 0) if price_per_sqm_values else 0
                        }
                    }
                else:
                    comparison = {
                        "address": address,
                        "total_deals": 0,
                        "same_building_deals": 0,
                        "street_deals": 0,
                        "neighborhood_deals": 0,
                        "same_building_percentage": 0,
                        "street_emphasis_percentage": 0,
                        "price_stats": {},
                        "area_stats": {},
                        "price_per_sqm_stats": {}
                    }
                
                comparisons.append(comparison)
                
            except Exception as e:
                logger.error(f"Error comparing {address}: {e}")
                comparisons.append({
                    "address": address,
                    "error": str(e)
                })
        
        # Rank addresses by average price per sqm
        valid_comparisons = []
        for comparison in comparisons:
            if (isinstance(comparison, dict) and 
                "price_per_sqm_stats" in comparison and 
                isinstance(comparison["price_per_sqm_stats"], dict) and
                comparison["price_per_sqm_stats"].get("average_price_per_sqm", 0) > 0):
                valid_comparisons.append(comparison)
        
        # Sort by price per sqm
        def get_price_per_sqm(comp: dict) -> float:
            price_stats = comp.get("price_per_sqm_stats", {})
            if isinstance(price_stats, dict):
                return price_stats.get("average_price_per_sqm", 0)
            return 0
            
        valid_comparisons.sort(key=get_price_per_sqm, reverse=True)
        
        return json.dumps({
            "addresses_compared": len(addresses),
            "ranking_by_average_price_per_sqm": valid_comparisons,
            "all_results": comparisons
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"Error in compare_addresses: {e}")
        return f"Error comparing addresses: {str(e)}"

# Run the server
if __name__ == "__main__":
    mcp.run() 