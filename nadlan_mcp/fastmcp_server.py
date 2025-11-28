#!/usr/bin/env python3
"""
Simple FastMCP Server for Israeli Real Estate Data

This server provides access to Israeli government real estate data through the Govmap API
using the FastMCP library with simplified, working functions.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP
from starlette.responses import JSONResponse

from nadlan_mcp.config import get_config
from nadlan_mcp.govmap import GovmapClient
from nadlan_mcp.govmap.models import Deal
from nadlan_mcp.govmap.outlier_detection import filter_deals_for_analysis

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("nadlan-mcp")

# Initialize the Govmap client
client = GovmapClient()


def log_mcp_call(func_name: str, **params):
    """
    Log MCP tool function calls with their parameters for debugging and monitoring.

    Args:
        func_name: Name of the MCP tool function being called
        **params: Keyword arguments passed to the function
    """
    # Format parameters for logging (truncate long strings)
    formatted_params = {}
    for key, value in params.items():
        if isinstance(value, str) and len(value) > 100:
            formatted_params[key] = f"{value[:97]}..."
        elif isinstance(value, list) and len(value) > 5:
            formatted_params[key] = f"[{len(value)} items]"
        else:
            formatted_params[key] = value

    logger.info(
        f"MCP tool called: {func_name}({', '.join(f'{k}={v}' for k, v in formatted_params.items())})"
    )


def strip_bloat_fields(deals: List[Deal]) -> List[Dict[str, Any]]:
    """
    Remove bloat fields from Deal models to reduce token usage in MCP responses.

    Converts Deal models to dictionaries and removes:
    - shape: Large MULTIPOLYGON coordinate data (~40-50% of tokens, not useful for LLM analysis)
    - sourceorder: Internal ordering field
    - source_polygon_id: Internal reference field (only when it's a UUID string)

    Args:
        deals: List of Deal model instances

    Returns:
        List of deal dictionaries with bloat fields removed
    """
    bloat_fields = {"shape", "sourceorder"}
    # Note: We keep source_polygon_id if it was added by our processing logic

    result = []
    for deal in deals:
        # Convert Deal model to dict, excluding None values for cleaner output
        # Use mode='json' to serialize dates as ISO strings
        deal_dict = deal.model_dump(mode="json", exclude_none=True)

        # Remove bloat fields
        filtered_dict = {k: v for k, v in deal_dict.items() if k not in bloat_fields}
        result.append(filtered_dict)

    return result


@mcp.tool()
def autocomplete_address(search_text: str) -> str:
    """Search and autocomplete Israeli addresses.

    Args:
        search_text: The partial address to search for (in Hebrew or English)

    Returns:
        JSON string containing matching addresses with their coordinates
    """
    log_mcp_call("autocomplete_address", search_text=search_text)
    try:
        response = client.autocomplete_address(search_text)

        if not response.results:
            return f"No addresses found for '{search_text}'"

        # Format results for better readability
        formatted_results = []
        for result in response.results:
            result_dict = {
                "text": result.text,
                "id": result.id,
                "type": result.type,
                "score": result.score,
            }

            # Add coordinates if available
            if result.coordinates:
                result_dict["coordinates"] = {
                    "longitude": result.coordinates.longitude,
                    "latitude": result.coordinates.latitude,
                }

            formatted_results.append(result_dict)

        return json.dumps(formatted_results, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"Error in autocomplete_address: {e}")
        return f"Error searching for address: {str(e)}"


@mcp.tool()
def get_deals_by_radius(latitude: float, longitude: float, radius_meters: int = 500) -> str:
    """Get polygon metadata within a radius of coordinates.

    **NOTE**: This returns polygon/area metadata, NOT individual deal transactions!
    Use find_recent_deals_for_address() to get actual deals.

    Args:
        latitude: Latitude coordinate
        longitude: Longitude coordinate
        radius_meters: Search radius in meters (default: 500)

    Returns:
        JSON string containing polygon metadata (areas with deals nearby)
    """
    log_mcp_call(
        "get_deals_by_radius", latitude=latitude, longitude=longitude, radius_meters=radius_meters
    )
    try:
        # Note: GovmapClient expects (longitude, latitude) tuple
        # Returns polygon metadata dicts, not Deal objects
        polygons = client.get_deals_by_radius((longitude, latitude), radius_meters)

        if not polygons:
            return f"No polygons found within {radius_meters}m of coordinates ({latitude}, {longitude})"

        return json.dumps(
            {
                "total_polygons": len(polygons),
                "search_radius_meters": radius_meters,
                "center_coordinates": {"latitude": latitude, "longitude": longitude},
                "polygons": polygons,  # Return dicts directly, no stripping needed
            },
            ensure_ascii=False,
            indent=2,
        )

    except Exception as e:
        logger.error(f"Error in get_deals_by_radius: {e}")
        return f"Error fetching polygons by radius: {str(e)}"


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
    log_mcp_call("get_street_deals", polygon_id=polygon_id, limit=limit, deal_type=deal_type)
    try:
        deals = client.get_street_deals(polygon_id, limit, deal_type=deal_type)

        if not deals:
            deal_type_desc = "first hand (new)" if deal_type == 1 else "second hand (used)"
            return f"No {deal_type_desc} deals found for polygon ID {polygon_id}"

        # Add deal type metadata
        for deal in deals:
            deal.deal_type = deal_type
            deal.deal_type_description = "first_hand_new" if deal_type == 1 else "second_hand_used"

        # Calculate basic statistics using computed fields from models
        price_per_sqm_values = [deal.price_per_sqm for deal in deals if deal.price_per_sqm]

        stats = {}
        if price_per_sqm_values:
            stats["price_per_sqm_stats"] = {
                "average_price_per_sqm": round(
                    sum(price_per_sqm_values) / len(price_per_sqm_values), 0
                ),
                "min_price_per_sqm": round(min(price_per_sqm_values), 0),
                "max_price_per_sqm": round(max(price_per_sqm_values), 0),
            }

        deal_type_desc = "first hand (new)" if deal_type == 1 else "second hand (used)"
        return json.dumps(
            {
                "total_deals": len(deals),
                "polygon_id": polygon_id,
                "deal_type": deal_type,
                "deal_type_description": deal_type_desc,
                "market_statistics": stats,
                "deals": strip_bloat_fields(deals),
            },
            ensure_ascii=False,
            indent=2,
        )

    except Exception as e:
        logger.error(f"Error in get_street_deals: {e}")
        return f"Error fetching street deals: {str(e)}"


@mcp.tool()
def find_recent_deals_for_address(
    address: str,
    years_back: int = 2,
    radius_meters: int = 30,
    max_deals: int = 100,
    deal_type: int = 2,
) -> str:
    """Find recent real estate deals for a specific address.

    Args:
        address: The address to search for (in Hebrew or English)
        years_back: How many years back to search (default: 2)
        radius_meters: Search radius in meters from the address (default: 30)
                      Small radius since street deals cover the entire street anyway
        max_deals: Maximum number of deals to return (default: 100, provides good context for LLM analysis)
        deal_type: Deal type filter (1=first hand/new, 2=second hand/used, default: 2)

    Returns:
        JSON string containing recent real estate deals for the address
    """
    log_mcp_call(
        "find_recent_deals_for_address",
        address=address,
        years_back=years_back,
        radius_meters=radius_meters,
        max_deals=max_deals,
        deal_type=deal_type,
    )
    try:
        deals = client.find_recent_deals_for_address(
            address, years_back, radius_meters, max_deals, deal_type
        )

        if not deals:
            deal_type_desc = "first hand (new)" if deal_type == 1 else "second hand (used)"
            return f"No {deal_type_desc} deals found for address '{address}'"

        # Calculate comprehensive statistics using model attributes
        prices = [deal.deal_amount for deal in deals if deal.deal_amount]
        areas = [deal.asset_area for deal in deals if deal.asset_area]
        price_per_sqm_values = [deal.price_per_sqm for deal in deals if deal.price_per_sqm]

        # Separate building, street and neighborhood deals for analysis
        # deal_source is added dynamically in find_recent_deals_for_address
        building_deals = [
            deal for deal in deals if getattr(deal, "deal_source", None) == "same_building"
        ]
        street_deals = [deal for deal in deals if getattr(deal, "deal_source", None) == "street"]
        neighborhood_deals = [
            deal for deal in deals if getattr(deal, "deal_source", None) == "neighborhood"
        ]

        stats = {
            "deal_breakdown": {
                "total_deals": len(deals),
                "same_building_deals": len(building_deals),
                "street_deals": len(street_deals),
                "neighborhood_deals": len(neighborhood_deals),
                "same_building_percentage": round((len(building_deals) / len(deals)) * 100, 1)
                if deals
                else 0,
                "street_emphasis_percentage": round((len(street_deals) / len(deals)) * 100, 1)
                if deals
                else 0,
                "neighborhood_percentage": round((len(neighborhood_deals) / len(deals)) * 100, 1)
                if deals
                else 0,
            }
        }

        # Standardize field names to match other tools
        if prices:
            stats["price_statistics"] = {
                "mean": round(sum(prices) / len(prices), 0),
                "min": min(prices),
                "max": max(prices),
                "median": sorted(prices)[len(prices) // 2] if prices else 0,
                "total": sum(prices),
            }

        if areas:
            stats["area_statistics"] = {
                "mean": round(sum(areas) / len(areas), 1),
                "min": min(areas),
                "max": max(areas),
                "median": sorted(areas)[len(areas) // 2] if areas else 0,
            }

        if price_per_sqm_values:
            stats["price_per_sqm_statistics"] = {
                "mean": round(sum(price_per_sqm_values) / len(price_per_sqm_values), 0),
                "min": round(min(price_per_sqm_values), 0),
                "max": round(max(price_per_sqm_values), 0),
                "median": round(sorted(price_per_sqm_values)[len(price_per_sqm_values) // 2], 0)
                if price_per_sqm_values
                else 0,
            }

        deal_type_desc = "first hand (new)" if deal_type == 1 else "second hand (used)"
        return json.dumps(
            {
                "search_parameters": {
                    "address": address,
                    "years_back": years_back,
                    "radius_meters": radius_meters,
                    "max_deals": max_deals,
                    "deal_type": deal_type,
                    "deal_type_description": deal_type_desc,
                },
                "market_statistics": stats,
                "deals": strip_bloat_fields(deals),
            },
            ensure_ascii=False,
            indent=2,
        )

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
    log_mcp_call("get_neighborhood_deals", polygon_id=polygon_id, limit=limit, deal_type=deal_type)
    try:
        deals = client.get_neighborhood_deals(polygon_id, limit, deal_type=deal_type)

        if not deals:
            deal_type_desc = "first hand (new)" if deal_type == 1 else "second hand (used)"
            return f"No {deal_type_desc} deals found for polygon ID {polygon_id}"

        # Add deal type metadata
        for deal in deals:
            deal.deal_type = deal_type
            deal.deal_type_description = "first_hand_new" if deal_type == 1 else "second_hand_used"

        # Calculate basic statistics using computed fields from models
        price_per_sqm_values = [deal.price_per_sqm for deal in deals if deal.price_per_sqm]

        stats = {}
        if price_per_sqm_values:
            stats["price_per_sqm_stats"] = {
                "average_price_per_sqm": round(
                    sum(price_per_sqm_values) / len(price_per_sqm_values), 0
                ),
                "min_price_per_sqm": round(min(price_per_sqm_values), 0),
                "max_price_per_sqm": round(max(price_per_sqm_values), 0),
            }

        deal_type_desc = "first hand (new)" if deal_type == 1 else "second hand (used)"
        return json.dumps(
            {
                "total_deals": len(deals),
                "polygon_id": polygon_id,
                "deal_type": deal_type,
                "deal_type_description": deal_type_desc,
                "market_statistics": stats,
                "deals": strip_bloat_fields(deals),
            },
            ensure_ascii=False,
            indent=2,
        )

    except Exception as e:
        logger.error(f"Error in get_neighborhood_deals: {e}")
        return f"Error fetching neighborhood deals: {str(e)}"


@mcp.tool()
def analyze_market_trends(
    address: str,
    years_back: int = 3,
    radius_meters: int = 100,
    max_deals: int = 100,
    deal_type: int = 2,
) -> str:
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
    log_mcp_call(
        "analyze_market_trends",
        address=address,
        years_back=years_back,
        radius_meters=radius_meters,
        max_deals=max_deals,
        deal_type=deal_type,
    )
    try:
        # Get deals for the address with larger radius for trend analysis
        deals = client.find_recent_deals_for_address(
            address, years_back, radius_meters, max_deals, deal_type
        )

        if not deals:
            deal_type_desc = "first hand (new)" if deal_type == 1 else "second hand (used)"
            return f"No {deal_type_desc} deals found for comprehensive market analysis near '{address}'"

        # Efficient analysis with reduced complexity
        from collections import defaultdict

        yearly_data = defaultdict(list)
        property_types: Dict[str, List[float]] = defaultdict(
            list
        )  # Store only prices for efficiency
        neighborhoods = defaultdict(list)

        # Simplified processing - extract only essential data
        for deal in deals:
            if not deal.deal_date:
                continue

            # Convert date to string for parsing
            from datetime import date as date_type

            date_str = (
                deal.deal_date.isoformat()
                if isinstance(deal.deal_date, date_type)
                else str(deal.deal_date)
            )
            year = date_str[:4]
            price = deal.deal_amount
            area = deal.asset_area
            price_per_sqm = deal.price_per_sqm
            prop_type = deal.property_type_description or "לא ידוע"
            neighborhood = deal.settlement_name_heb or deal.neighborhood or "לא ידוע"
            deal_source = getattr(deal, "deal_source", "unknown")

            if (
                isinstance(price, (int, float))
                and isinstance(area, (int, float))
                and area > 0
                and isinstance(price_per_sqm, (int, float))
            ):
                yearly_data[year].append(
                    {
                        "price": price,
                        "area": area,
                        "price_per_sqm": price_per_sqm,
                        "deal_source": deal_source,
                    }
                )
                property_types[prop_type].append(price_per_sqm)
                neighborhoods[neighborhood].append(price_per_sqm)

        # Calculate streamlined yearly trends
        yearly_trends = {}
        for year, year_deals in yearly_data.items():
            if year_deals:
                prices = [d["price"] for d in year_deals]
                price_per_sqm_vals = [d["price_per_sqm"] for d in year_deals]
                building_deals = [d for d in year_deals if d["deal_source"] == "same_building"]
                street_deals = [d for d in year_deals if d["deal_source"] == "street"]

                yearly_trends[year] = {
                    "deal_count": len(year_deals),
                    "same_building_deals": len(building_deals),
                    "street_deals": len(street_deals),
                    "avg_price": round(sum(prices) / len(prices), 0),
                    "avg_price_per_sqm": round(
                        sum(price_per_sqm_vals) / len(price_per_sqm_vals), 0
                    ),
                    "min_price_per_sqm": round(min(price_per_sqm_vals), 0),
                    "max_price_per_sqm": round(max(price_per_sqm_vals), 0),
                    "total_volume": sum(prices),
                }

        # Streamlined property type analysis (top 5 only)
        property_type_analysis = {}
        for prop_type, prices_per_sqm in property_types.items():
            if len(prices_per_sqm) >= 2:  # Only include types with multiple deals
                property_type_analysis[prop_type] = {
                    "deal_count": len(prices_per_sqm),
                    "avg_price_per_sqm": round(sum(prices_per_sqm) / len(prices_per_sqm), 0),
                }

        # Keep only top 5 property types by deal count
        property_type_analysis = dict(
            sorted(property_type_analysis.items(), key=lambda x: x[1]["deal_count"], reverse=True)[
                :5
            ]
        )

        # Streamlined neighborhood analysis (top 5 only)
        neighborhood_analysis = {}
        for neighborhood, prices_per_sqm in neighborhoods.items():
            if len(prices_per_sqm) >= 3:  # Minimum 3 deals for statistical significance
                neighborhood_analysis[neighborhood] = {
                    "deal_count": len(prices_per_sqm),
                    "avg_price_per_sqm": round(sum(prices_per_sqm) / len(prices_per_sqm), 0),
                }

        # Keep only top 5 neighborhoods by deal count
        neighborhood_analysis = dict(
            sorted(neighborhood_analysis.items(), key=lambda x: x[1]["deal_count"], reverse=True)[
                :5
            ]
        )

        # Simple trend analysis
        years_sorted = sorted(yearly_trends.keys())
        trend_analysis = {}
        if len(years_sorted) >= 2:
            first_year = yearly_trends[years_sorted[0]]
            last_year = yearly_trends[years_sorted[-1]]

            if first_year["avg_price_per_sqm"] > 0:
                price_change = (
                    (last_year["avg_price_per_sqm"] - first_year["avg_price_per_sqm"])
                    / first_year["avg_price_per_sqm"]
                ) * 100
                volume_change = (
                    (
                        (last_year["deal_count"] - first_year["deal_count"])
                        / first_year["deal_count"]
                    )
                    * 100
                    if first_year["deal_count"] > 0
                    else 0
                )

                trend_analysis = {
                    "price_trend_percentage": round(price_change, 1),
                    "volume_trend_percentage": round(volume_change, 1),
                    "first_year_avg_price_per_sqm": first_year["avg_price_per_sqm"],
                    "last_year_avg_price_per_sqm": last_year["avg_price_per_sqm"],
                }

        deal_type_desc = "first hand (new)" if deal_type == 1 else "second hand (used)"

        # Return summarized analysis (NO raw deals to save tokens)
        # Normalize structure with standard market_statistics while keeping tool-specific analysis
        return json.dumps(
            {
                "analysis_parameters": {
                    "address": address,
                    "years_analyzed": years_back,
                    "radius_meters": radius_meters,
                    "deals_analyzed": len(deals),
                    "deal_type": deal_type,
                    "deal_type_description": deal_type_desc,
                },
                "market_statistics": {
                    "deal_breakdown": {
                        "total_deals": len(deals),
                    },
                },
                "market_summary": {
                    "years_with_data": len(yearly_trends),
                    "unique_property_types": len(property_type_analysis),
                    "unique_neighborhoods": len(neighborhood_analysis),
                },
                "yearly_trends": yearly_trends,
                "top_property_types": property_type_analysis,
                "top_neighborhoods": neighborhood_analysis,
                "trend_analysis": trend_analysis,
                "key_insights": {
                    "most_active_year": max(
                        yearly_trends.keys(), key=lambda y: yearly_trends[y]["deal_count"]
                    )
                    if yearly_trends
                    else None,
                    "highest_avg_price_year": max(
                        yearly_trends.keys(), key=lambda y: yearly_trends[y]["avg_price_per_sqm"]
                    )
                    if yearly_trends
                    else None,
                    "deal_source_summary": f"Building: {len([d for d in deals if getattr(d, 'deal_source', None) == 'same_building'])}, Street: {len([d for d in deals if getattr(d, 'deal_source', None) == 'street'])}, Neighborhood: {len([d for d in deals if getattr(d, 'deal_source', None) == 'neighborhood'])}",
                },
                "deals": [],  # Trend analysis doesn't return raw deals to save tokens
            },
            ensure_ascii=False,
            indent=2,
        )

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
    log_mcp_call("compare_addresses", addresses=addresses)
    try:
        comparisons = []

        for address in addresses:
            try:
                deals = client.find_recent_deals_for_address(address, 2)

                if deals:
                    prices = [deal.deal_amount for deal in deals if deal.deal_amount]
                    areas = [deal.asset_area for deal in deals if deal.asset_area]
                    price_per_sqm_values = [
                        deal.price_per_sqm for deal in deals if deal.price_per_sqm
                    ]
                    building_deals = [
                        deal
                        for deal in deals
                        if getattr(deal, "deal_source", None) == "same_building"
                    ]
                    street_deals = [
                        deal for deal in deals if getattr(deal, "deal_source", None) == "street"
                    ]
                    neighborhood_deals = [
                        deal
                        for deal in deals
                        if getattr(deal, "deal_source", None) == "neighborhood"
                    ]

                    comparison = {
                        "address": address,
                        "total_deals": len(deals),
                        "same_building_deals": len(building_deals),
                        "street_deals": len(street_deals),
                        "neighborhood_deals": len(neighborhood_deals),
                        "same_building_percentage": round(
                            (len(building_deals) / len(deals)) * 100, 1
                        )
                        if deals
                        else 0,
                        "street_emphasis_percentage": round(
                            (len(street_deals) / len(deals)) * 100, 1
                        )
                        if deals
                        else 0,
                        "price_stats": {
                            "average_price": round(sum(prices) / len(prices), 0) if prices else 0,
                            "min_price": min(prices) if prices else 0,
                            "max_price": max(prices) if prices else 0,
                        },
                        "area_stats": {
                            "average_area": round(sum(areas) / len(areas), 1) if areas else 0,
                            "min_area": min(areas) if areas else 0,
                            "max_area": max(areas) if areas else 0,
                        },
                        "price_per_sqm_stats": {
                            "average_price_per_sqm": round(
                                sum(price_per_sqm_values) / len(price_per_sqm_values), 0
                            )
                            if price_per_sqm_values
                            else 0,
                            "min_price_per_sqm": round(min(price_per_sqm_values), 0)
                            if price_per_sqm_values
                            else 0,
                            "max_price_per_sqm": round(max(price_per_sqm_values), 0)
                            if price_per_sqm_values
                            else 0,
                        },
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
                        "price_per_sqm_stats": {},
                    }

                comparisons.append(comparison)

            except Exception as e:
                logger.error(f"Error comparing {address}: {e}")
                comparisons.append({"address": address, "error": str(e)})

        # Rank addresses by average price per sqm
        valid_comparisons = []
        for comparison in comparisons:
            if (
                isinstance(comparison, dict)
                and "price_per_sqm_stats" in comparison
                and isinstance(comparison["price_per_sqm_stats"], dict)
                and comparison["price_per_sqm_stats"].get("average_price_per_sqm", 0) > 0
            ):
                valid_comparisons.append(comparison)

        # Sort by price per sqm
        def get_price_per_sqm(comp: dict) -> float:
            price_stats = comp.get("price_per_sqm_stats", {})
            if isinstance(price_stats, dict):
                return price_stats.get("average_price_per_sqm", 0)
            return 0

        valid_comparisons.sort(key=get_price_per_sqm, reverse=True)

        return json.dumps(
            {
                "addresses_compared": len(addresses),
                "ranking_by_average_price_per_sqm": valid_comparisons,
                "all_results": comparisons,
            },
            ensure_ascii=False,
            indent=2,
        )

    except Exception as e:
        logger.error(f"Error in compare_addresses: {e}")
        return f"Error comparing addresses: {str(e)}"


@mcp.tool()
def get_valuation_comparables(
    address: str,
    years_back: int = 2,
    property_type: Optional[str] = None,
    min_rooms: Optional[float] = None,
    max_rooms: Optional[float] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    min_area: Optional[float] = None,
    max_area: Optional[float] = None,
    min_floor: Optional[int] = None,
    max_floor: Optional[int] = None,
    radius_meters: int = 100,
    max_comparables: int = 50,
    iqr_multiplier: Optional[float] = None,
) -> str:
    """Get comparable properties for valuation analysis.

    This tool provides detailed comparable deals filtered by your criteria.
    Automatically applies IQR outlier filtering (k=1.0 default) to remove statistical outliers
    and improve data quality. The response includes metadata about filtering so you can
    inform users about removed outliers.

    Args:
        address: The address to find comparables for (in Hebrew or English)
        years_back: How many years back to search (default: 2)
        property_type: Filter by property type (e.g., "דירה", "בית", "פנטהאוז")
        min_rooms: Minimum number of rooms
        max_rooms: Maximum number of rooms
        min_price: Minimum deal amount (NIS)
        max_price: Maximum deal amount (NIS)
        min_area: Minimum asset area (square meters)
        max_area: Maximum asset area (square meters)
        min_floor: Minimum floor number
        max_floor: Maximum floor number
        radius_meters: Search radius in meters (default: 100, larger than find_recent_deals to get more comparables)
        max_comparables: Maximum number of deals to return (default: 50, optimized for MCP token limits)
        iqr_multiplier: Override IQR multiplier for outlier detection (default: 1.0). Lower = more aggressive filtering

    Returns:
        JSON string containing:
        - Filtered comparable deals with full details
        - deal_breakdown with outlier filtering metadata:
          - total_deals: Count after filtering
          - total_deals_before_filtering: Count before filtering
          - outliers_removed: Number of deals filtered out
          - filtering_method: Method used (e.g., "iqr")
          - iqr_multiplier: IQR multiplier used (e.g., 1.0)
    """
    log_mcp_call(
        "get_valuation_comparables",
        address=address,
        years_back=years_back,
        property_type=property_type,
        min_rooms=min_rooms,
        max_rooms=max_rooms,
        min_price=min_price,
        max_price=max_price,
        min_area=min_area,
        max_area=max_area,
        min_floor=min_floor,
        max_floor=max_floor,
        radius_meters=radius_meters,
        max_comparables=max_comparables,
        iqr_multiplier=iqr_multiplier,
    )
    try:
        # Get all deals for the address with higher limits for valuation
        deals = client.find_recent_deals_for_address(
            address, years_back, radius=radius_meters, max_deals=max_comparables
        )

        if not deals:
            return json.dumps(
                {
                    "search_parameters": {
                        "address": address,
                        "years_back": years_back,
                        "radius_meters": radius_meters,
                        "max_comparables": max_comparables,
                    },
                    "market_statistics": {
                        "deal_breakdown": {
                            "total_deals": 0,
                        },
                    },
                    "deals": [],
                    "message": "No deals found for this address",
                },
                ensure_ascii=False,
                indent=2,
            )

        # Apply filters
        logger.info(f"Applying criteria filters to {len(deals)} deals")
        filtered_deals = client.filter_deals_by_criteria(
            deals,
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
        logger.info(
            f"After criteria filtering: {len(filtered_deals)} deals "
            f"(removed {len(deals) - len(filtered_deals)} deals)"
        )

        # Apply outlier filtering to remove statistical outliers
        config = get_config()
        outlier_report = None
        if (
            config.analysis_outlier_method != "none"
            and len(filtered_deals) >= config.analysis_min_deals_for_outlier_detection
        ):
            deals_before_outlier_filter = len(filtered_deals)
            filtered_deals, outlier_report = filter_deals_for_analysis(
                filtered_deals, config, metric="price_per_sqm", iqr_multiplier=iqr_multiplier
            )
            effective_k = (
                iqr_multiplier if iqr_multiplier is not None else config.analysis_iqr_multiplier
            )
            logger.info(
                f"After outlier filtering ({config.analysis_outlier_method}, k={effective_k}): "
                f"{len(filtered_deals)} deals (removed {deals_before_outlier_filter - len(filtered_deals)} outliers)"
            )
        else:
            logger.info(
                f"Skipping outlier filtering: only {len(filtered_deals)} deals "
                f"(minimum {config.analysis_min_deals_for_outlier_detection} required)"
            )

        # Calculate statistics on filtered comparables
        stats = client.calculate_deal_statistics(filtered_deals)

        # Build deal breakdown with outlier filtering information
        deal_breakdown = {
            "total_deals": len(filtered_deals),
        }

        # Add outlier filtering metadata if filtering was applied
        if outlier_report:
            deal_breakdown["total_deals_before_filtering"] = outlier_report["total_deals"]
            deal_breakdown["outliers_removed"] = outlier_report["outliers_removed"]
            deal_breakdown["filtering_method"] = outlier_report["method_used"]
            if outlier_report["method_used"] == "iqr":
                deal_breakdown["iqr_multiplier"] = outlier_report["parameters"]["iqr_multiplier"]

        # Normalize response structure to match other tools
        return json.dumps(
            {
                "search_parameters": {
                    "address": address,
                    "years_back": years_back,
                    "radius_meters": radius_meters,
                    "max_comparables": max_comparables,
                    "filters_applied": {
                        "property_type": property_type,
                        "rooms": f"{min_rooms}-{max_rooms}" if min_rooms or max_rooms else None,
                        "price": f"{min_price}-{max_price}" if min_price or max_price else None,
                        "area": f"{min_area}-{max_area}" if min_area or max_area else None,
                        "floor": f"{min_floor}-{max_floor}" if min_floor or max_floor else None,
                    },
                },
                "market_statistics": {
                    "deal_breakdown": deal_breakdown,
                    "price_statistics": stats.price_statistics,
                    "area_statistics": stats.area_statistics,
                    "price_per_sqm_statistics": stats.price_per_sqm_statistics,
                    "property_type_distribution": stats.property_type_distribution,
                    "date_range": stats.date_range,
                },
                "deals": strip_bloat_fields(filtered_deals),
            },
            ensure_ascii=False,
            indent=2,
        )

    except Exception as e:
        logger.error(f"Error in get_valuation_comparables: {e}")
        return f"Error getting valuation comparables: {str(e)}"


@mcp.tool()
def get_deal_statistics(
    address: str,
    years_back: int = 2,
    property_type: Optional[str] = None,
    min_rooms: Optional[float] = None,
    max_rooms: Optional[float] = None,
    iqr_multiplier: Optional[float] = None,
) -> str:
    """Calculate statistical aggregations on deal data for an address.

    This tool provides quick statistical summaries without returning all raw deals.
    Useful when LLM needs calculations on large datasets without full details.

    Args:
        address: The address to analyze (in Hebrew or English)
        years_back: How many years back to analyze (default: 2)
        property_type: Filter by property type (e.g., "דירה", "בית")
        min_rooms: Minimum number of rooms
        max_rooms: Maximum number of rooms
        iqr_multiplier: Override IQR multiplier for outlier detection (default: 1.0). Lower = more aggressive filtering

    Returns:
        JSON string containing statistical metrics (mean, median, percentiles, etc.)
    """
    log_mcp_call(
        "get_deal_statistics",
        address=address,
        years_back=years_back,
        property_type=property_type,
        min_rooms=min_rooms,
        max_rooms=max_rooms,
        iqr_multiplier=iqr_multiplier,
    )
    try:
        # Get all deals for the address
        deals = client.find_recent_deals_for_address(address, years_back)

        if not deals:
            return json.dumps(
                {
                    "search_parameters": {
                        "address": address,
                        "years_back": years_back,
                    },
                    "market_statistics": {
                        "deal_breakdown": {"total_deals": 0},
                        "message": "No deals found for this address",
                    },
                    "deals": [],
                },
                ensure_ascii=False,
                indent=2,
            )

        # Apply filters if provided
        if property_type or min_rooms or max_rooms:
            deals = client.filter_deals_by_criteria(
                deals, property_type=property_type, min_rooms=min_rooms, max_rooms=max_rooms
            )

        # Calculate statistics
        stats = client.calculate_deal_statistics(deals, iqr_multiplier=iqr_multiplier)

        # Normalize response structure to match other tools
        return json.dumps(
            {
                "search_parameters": {
                    "address": address,
                    "years_back": years_back,
                    "filters_applied": {
                        "property_type": property_type,
                        "rooms": f"{min_rooms}-{max_rooms}" if min_rooms or max_rooms else None,
                    },
                },
                "market_statistics": {
                    "deal_breakdown": {
                        "total_deals": stats.total_deals,
                    },
                    "price_statistics": stats.price_statistics,
                    "area_statistics": stats.area_statistics,
                    "price_per_sqm_statistics": stats.price_per_sqm_statistics,
                    "property_type_distribution": stats.property_type_distribution,
                    "date_range": stats.date_range,
                },
                "deals": [],  # Statistics-only query, no full deals returned
            },
            ensure_ascii=False,
            indent=2,
        )

    except Exception as e:
        logger.error(f"Error in get_deal_statistics: {e}")
        return f"Error calculating deal statistics: {str(e)}"


def _safe_calculate_metric(metric_func, deals):
    """
    Safely execute a metric calculation function.

    Helper function to reduce code duplication in try-except blocks
    for market metric calculations.

    Args:
        metric_func: Function to call with deals as argument
        deals: List of Deal model instances to analyze

    Returns:
        Result dictionary from metric_func (serialized from Pydantic model),
        or error dictionary if any exception raised
    """
    try:
        result = metric_func(deals)
        # Serialize Pydantic model to dict
        if hasattr(result, "model_dump"):
            return result.model_dump(exclude_none=True)
        return result
    except Exception as e:
        logger.warning(f"Error calculating metric {metric_func.__name__}: {e}")
        return {"error": str(e)}


@mcp.tool()
def get_market_activity_metrics(address: str, years_back: int = 2, radius_meters: int = 100) -> str:
    """Get comprehensive market activity and investment potential analysis.

    This tool provides detailed market liquidity, activity scores, and investment
    potential metrics. It combines activity scoring, liquidity analysis, and
    investment potential into a single comprehensive report.

    Args:
        address: The address to analyze (in Hebrew or English)
        years_back: How many years back to analyze (default: 2)
        radius_meters: Search radius in meters (default: 100)

    Returns:
        JSON string containing:
            - Market activity score and trends
            - Market liquidity and velocity metrics
            - Investment potential analysis
            - Price appreciation and volatility
    """
    log_mcp_call(
        "get_market_activity_metrics",
        address=address,
        years_back=years_back,
        radius_meters=radius_meters,
    )
    try:
        # Get deals for the address
        deals = client.find_recent_deals_for_address(address, years_back, radius_meters)

        if not deals:
            return json.dumps(
                {
                    "analysis_parameters": {
                        "address": address,
                        "years_back": years_back,
                        "radius_meters": radius_meters,
                    },
                    "market_statistics": {
                        "deal_breakdown": {
                            "total_deals": 0,
                        },
                    },
                    "deals": [],
                    "error": "No deals found for analysis",
                },
                ensure_ascii=False,
                indent=2,
            )

        # Calculate market metrics using helper to reduce duplication
        activity_metrics = _safe_calculate_metric(client.calculate_market_activity_score, deals)
        liquidity_metrics = _safe_calculate_metric(client.get_market_liquidity, deals)
        investment_metrics = _safe_calculate_metric(client.analyze_investment_potential, deals)

        # Combine all metrics with normalized structure
        return json.dumps(
            {
                "analysis_parameters": {
                    "address": address,
                    "years_back": years_back,
                    "radius_meters": radius_meters,
                },
                "market_statistics": {
                    "deal_breakdown": {
                        "total_deals": len(deals),
                    },
                },
                "market_activity": activity_metrics,
                "market_liquidity": liquidity_metrics,
                "investment_potential": investment_metrics,
                "summary": {
                    "activity_score": activity_metrics.get("activity_score"),
                    "activity_trend": activity_metrics.get("trend"),
                    "liquidity_score": liquidity_metrics.get("liquidity_score"),
                    "market_activity_level": liquidity_metrics.get("market_activity_level"),
                    "investment_score": investment_metrics.get("investment_score"),
                    "price_trend": investment_metrics.get("price_trend"),
                    "market_stability": investment_metrics.get("market_stability"),
                },
                "deals": [],  # Activity metrics don't return raw deals
            },
            ensure_ascii=False,
            indent=2,
        )

    except Exception as e:
        logger.error(f"Error in get_market_activity_metrics: {e}")
        return f"Error analyzing market activity: {str(e)}"


# Health check endpoint for HTTP deployments
@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    """
    Health check endpoint for container orchestration platforms (Render, Railway, etc.).

    Returns a simple OK status to indicate the server is running.
    This endpoint is accessible at GET /health when using HTTP transport.
    """
    return JSONResponse({"status": "ok", "service": "nadlan-mcp"})


# Run the server
if __name__ == "__main__":
    mcp.run()
