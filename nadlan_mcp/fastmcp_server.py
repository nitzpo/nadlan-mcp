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
def find_recent_deals_for_address(address: str, years_back: int = 2, radius_meters: int = 30, max_deals: int = 200) -> str:
    """Find recent real estate deals for a specific address.
    
    Args:
        address: The address to search for (in Hebrew or English)
        years_back: How many years back to search (default: 2)
        radius_meters: Search radius in meters from the address (default: 30)
                      Small radius since street deals cover the entire street anyway
        max_deals: Maximum number of deals to return (default: 200)
        
    Returns:
        JSON string containing recent real estate deals for the address
    """
    try:
        deals = client.find_recent_deals_for_address(address, years_back, radius_meters, max_deals)
        
        if not deals:
            return f"No deals found for address '{address}'"
        
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
        
        return json.dumps({
            "search_parameters": {
                "address": address,
                "years_back": years_back,
                "radius_meters": radius_meters,
                "max_deals": max_deals
            },
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
        
        # Add price per sqm calculation for each deal
        for deal in deals:
            price = deal.get('dealAmount', 0)
            area = deal.get('assetArea', 0)
            if isinstance(price, (int, float)) and isinstance(area, (int, float)) and area > 0:
                deal['price_per_sqm'] = round(price / area, 2)
            else:
                deal['price_per_sqm'] = None
        
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
        
        return json.dumps({
            "total_deals": len(deals),
            "polygon_id": polygon_id,
            "market_statistics": stats,
            "deals": deals
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"Error in get_neighborhood_deals: {e}")
        return f"Error fetching neighborhood deals: {str(e)}"

@mcp.tool()
def analyze_market_trends(address: str, years_back: int = 3, radius_meters: int = 300, max_deals: int = 500) -> str:
    """Analyze market trends and price patterns for an area with comprehensive data.
    
    Args:
        address: The address to analyze trends around
        years_back: How many years of data to analyze (default: 3)
        radius_meters: Search radius in meters from the address (default: 300, larger for trend analysis)
        max_deals: Maximum number of deals to analyze (default: 500)
        
    Returns:
        JSON string containing comprehensive market trend analysis including:
        - Detailed price trends over time
        - Average prices by property type
        - Market activity levels and patterns
        - Price per square meter trends
        - Seasonal patterns
        - Market velocity indicators
        - Comparative neighborhood analysis
    """
    try:
        # Get deals for the address with larger radius for trend analysis
        deals = client.find_recent_deals_for_address(address, years_back, radius_meters, max_deals)
        
        if not deals:
            return f"No deals found for comprehensive market analysis near '{address}'"
        
        # Comprehensive analysis structure
        from collections import defaultdict
        
        yearly_data = defaultdict(list)
        monthly_data = defaultdict(list)
        property_types: Dict[str, List[Dict]] = defaultdict(list)
        neighborhoods = defaultdict(list)
        quarterly_data = defaultdict(list)
        
        # Process each deal for comprehensive analysis
        for deal in deals:
            date_str = deal.get('dealDate', '')
            if not date_str:
                continue
                
            year = date_str[:4]
            month = date_str[:7]  # YYYY-MM
            quarter = f"{year}-Q{((int(date_str[5:7]) - 1) // 3) + 1}" if len(date_str) >= 7 else None
            
            price = deal.get('dealAmount')
            area = deal.get('assetArea')
            price_per_sqm = deal.get('price_per_sqm')
            prop_type = deal.get('assetTypeHeb', deal.get('propertyTypeDescription', 'לא ידוע'))
            neighborhood = deal.get('settlementNameHeb', deal.get('neighborhood', 'לא ידוע'))
            deal_source = deal.get('deal_source', 'unknown')
            
            deal_data = {
                'price': price,
                'area': area,
                'price_per_sqm': price_per_sqm,
                'property_type': prop_type,
                'neighborhood': neighborhood,
                'deal_source': deal_source,
                'date': date_str
            }
            
            if isinstance(price, (int, float)) and isinstance(area, (int, float)) and area > 0:
                yearly_data[year].append(deal_data)
                monthly_data[month].append(deal_data)
                if quarter:
                    quarterly_data[quarter].append(deal_data)
                property_types[prop_type].append(deal_data)
                neighborhoods[neighborhood].append(deal_data)
        
        # Calculate comprehensive yearly trends
        yearly_trends = {}
        for year, year_deals in yearly_data.items():
            if year_deals:
                prices = [d['price'] for d in year_deals if d['price']]
                price_per_sqm_vals = [d['price_per_sqm'] for d in year_deals if d['price_per_sqm']]
                areas = [d['area'] for d in year_deals if d['area']]
                building_deals = [d for d in year_deals if d['deal_source'] == 'same_building']
                street_deals = [d for d in year_deals if d['deal_source'] == 'street']
                neighborhood_deals = [d for d in year_deals if d['deal_source'] == 'neighborhood']
                
                yearly_trends[year] = {
                    "deal_count": len(year_deals),
                    "same_building_deals_count": len(building_deals),
                    "street_deals_count": len(street_deals),
                    "neighborhood_deals_count": len(neighborhood_deals),
                    "same_building_percentage": round((len(building_deals) / len(year_deals)) * 100, 1),
                    "street_deals_percentage": round((len(street_deals) / len(year_deals)) * 100, 1),
                    "average_price": round(sum(prices) / len(prices), 0) if prices else 0,
                    "median_price": round(sorted(prices)[len(prices)//2], 0) if prices else 0,
                    "min_price": min(prices) if prices else 0,
                    "max_price": max(prices) if prices else 0,
                    "price_std_dev": round((sum([(p - sum(prices)/len(prices))**2 for p in prices]) / len(prices))**0.5, 0) if len(prices) > 1 else 0,
                    "average_area": round(sum(areas) / len(areas), 1) if areas else 0,
                    "average_price_per_sqm": round(sum(price_per_sqm_vals) / len(price_per_sqm_vals), 0) if price_per_sqm_vals else 0,
                    "median_price_per_sqm": round(sorted(price_per_sqm_vals)[len(price_per_sqm_vals)//2], 0) if price_per_sqm_vals else 0,
                    "total_market_volume": sum(prices) if prices else 0
                }
        
        # Calculate quarterly trends for seasonality analysis
        quarterly_trends = {}
        for quarter, quarter_deals in quarterly_data.items():
            if quarter_deals:
                prices = [d['price'] for d in quarter_deals if d['price']]
                price_per_sqm_vals = [d['price_per_sqm'] for d in quarter_deals if d['price_per_sqm']]
                
                quarterly_trends[quarter] = {
                    "deal_count": len(quarter_deals),
                    "average_price": round(sum(prices) / len(prices), 0) if prices else 0,
                    "average_price_per_sqm": round(sum(price_per_sqm_vals) / len(price_per_sqm_vals), 0) if price_per_sqm_vals else 0
                }
        
        # Property type analysis
        property_type_analysis = {}
        for prop_type, type_deals in property_types.items():
            if type_deals:
                prices = [d['price'] for d in type_deals if d['price']]
                price_per_sqm_vals = [d['price_per_sqm'] for d in type_deals if d['price_per_sqm']]
                areas = [d['area'] for d in type_deals if d['area']]
                
                property_type_analysis[prop_type] = {
                    "deal_count": len(type_deals),
                    "market_share_percentage": round((len(type_deals) / len(deals)) * 100, 1),
                    "average_price": round(sum(prices) / len(prices), 0) if prices else 0,
                    "average_area": round(sum(areas) / len(areas), 1) if areas else 0,
                    "average_price_per_sqm": round(sum(price_per_sqm_vals) / len(price_per_sqm_vals), 0) if price_per_sqm_vals else 0
                }
        
        # Neighborhood comparison analysis
        neighborhood_analysis = {}
        for neighborhood, neighborhood_deals in neighborhoods.items():
            if neighborhood_deals and len(neighborhood_deals) >= 3:  # Only include neighborhoods with sufficient data
                prices = [d['price'] for d in neighborhood_deals if d['price']]
                price_per_sqm_vals = [d['price_per_sqm'] for d in neighborhood_deals if d['price_per_sqm']]
                
                neighborhood_analysis[neighborhood] = {
                    "deal_count": len(neighborhood_deals),
                    "average_price": round(sum(prices) / len(prices), 0) if prices else 0,
                    "average_price_per_sqm": round(sum(price_per_sqm_vals) / len(price_per_sqm_vals), 0) if price_per_sqm_vals else 0
                }
        
        # Market trend direction analysis
        price_trend_analysis = {}
        years_sorted = sorted(yearly_trends.keys())
        if len(years_sorted) >= 2:
            first_year_data = yearly_trends[years_sorted[0]]
            last_year_data = yearly_trends[years_sorted[-1]]
            
            # Price trend
            first_year_avg = first_year_data['average_price_per_sqm']
            last_year_avg = last_year_data['average_price_per_sqm']
            
            if first_year_avg > 0:
                price_trend_percentage = ((last_year_avg - first_year_avg) / first_year_avg) * 100
                price_trend_direction = "עולה" if price_trend_percentage > 5 else "יורד" if price_trend_percentage < -5 else "יציב"
                
                # Volume trend
                first_year_volume = first_year_data['deal_count']
                last_year_volume = last_year_data['deal_count']
                volume_trend_percentage = ((last_year_volume - first_year_volume) / first_year_volume) * 100 if first_year_volume > 0 else 0
                volume_trend_direction = "עולה" if volume_trend_percentage > 10 else "יורד" if volume_trend_percentage < -10 else "יציב"
                
                price_trend_analysis = {
                    "price_trend_direction": price_trend_direction,
                    "price_trend_percentage": round(price_trend_percentage, 1),
                    "volume_trend_direction": volume_trend_direction,
                    "volume_trend_percentage": round(volume_trend_percentage, 1),
                    "analysis_period": f"{years_sorted[0]} - {years_sorted[-1]}",
                    "first_year_avg_price_per_sqm": round(first_year_avg, 0),
                    "last_year_avg_price_per_sqm": round(last_year_avg, 0),
                    "total_price_change": round(last_year_avg - first_year_avg, 0),
                    "annualized_price_growth": round(price_trend_percentage / len(years_sorted), 1)
                }
        
        # Market velocity indicators
        market_velocity = {
            "average_deals_per_month": round(len(deals) / (years_back * 12), 1),
            "peak_activity_quarter": max(quarterly_trends.keys(), key=lambda q: quarterly_trends[q]['deal_count']) if quarterly_trends else None,
            "lowest_activity_quarter": min(quarterly_trends.keys(), key=lambda q: quarterly_trends[q]['deal_count']) if quarterly_trends else None
        }
        
        # Price distribution analysis
        all_prices_per_sqm = [deal.get('price_per_sqm', 0) for deal in deals if deal.get('price_per_sqm')]
        price_distribution = {}
        if all_prices_per_sqm:
            sorted_prices = sorted(all_prices_per_sqm)
            price_distribution = {
                "25th_percentile": round(sorted_prices[len(sorted_prices)//4], 0),
                "75th_percentile": round(sorted_prices[3*len(sorted_prices)//4], 0),
                "price_range_iqr": round(sorted_prices[3*len(sorted_prices)//4] - sorted_prices[len(sorted_prices)//4], 0),
                "coefficient_of_variation": round((yearly_trends[years_sorted[-1]]['price_std_dev'] / yearly_trends[years_sorted[-1]]['average_price']) * 100, 1) if years_sorted and yearly_trends[years_sorted[-1]]['average_price'] > 0 else 0
            }
        
        return json.dumps({
            "analysis_parameters": {
                "address": address,
                "analysis_period_years": years_back,
                "search_radius_meters": radius_meters,
                "max_deals_analyzed": max_deals
            },
            "market_overview": {
                "total_deals_analyzed": len(deals),
                "unique_neighborhoods": len(neighborhoods),
                "unique_property_types": len(property_types),
                "data_coverage_years": len(yearly_trends)
            },
            "yearly_trends": yearly_trends,
            "quarterly_trends": quarterly_trends,
            "property_type_analysis": property_type_analysis,
            "neighborhood_comparison": neighborhood_analysis,
            "market_trend_analysis": price_trend_analysis,
            "market_velocity_indicators": market_velocity,
            "price_distribution_analysis": price_distribution,
            "detailed_insights": {
                "most_active_property_type": max(property_type_analysis.keys(), key=lambda pt: property_type_analysis[pt]['deal_count']) if property_type_analysis else None,
                "highest_value_property_type": max(property_type_analysis.keys(), key=lambda pt: property_type_analysis[pt]['average_price_per_sqm']) if property_type_analysis else None,
                "most_expensive_neighborhood": max(neighborhood_analysis.keys(), key=lambda n: neighborhood_analysis[n]['average_price_per_sqm']) if neighborhood_analysis else None,
                "deal_source_breakdown": f"Same building: {len([d for d in deals if d.get('deal_source') == 'same_building'])}, Street: {len([d for d in deals if d.get('deal_source') == 'street'])}, Neighborhood: {len([d for d in deals if d.get('deal_source') == 'neighborhood'])}"
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