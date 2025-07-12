"""
Israel Real Estate MCP Server

An MCP server for accessing Israeli government real estate data through the Govmap API.
Provides tools for real estate agents and AI assistants to query property deals and market data.
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    ListToolsRequest,
    ListToolsResult,
    Tool,
    TextContent,
)
import mcp.types as types
import mcp.server.stdio

from .main import GovmapClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the server
server = Server("nadlan-mcp")

# Global client instance
govmap_client = GovmapClient()


@server.list_tools()
async def handle_list_tools() -> ListToolsResult:
    """List available MCP tools for Israeli real estate data."""
    return ListToolsResult(
        tools=[
            Tool(
                name="autocomplete_address",
                description="Search for Israeli addresses using autocomplete. Returns coordinates and address details.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "search_text": {
                            "type": "string",
                            "description": "Address to search for (Hebrew or English, e.g., 'בן יהודה 1 תל אביב' or 'Ben Yehuda 1 Tel Aviv')"
                        }
                    },
                    "required": ["search_text"]
                }
            ),
            Tool(
                name="get_deals_by_radius", 
                description="Find real estate deals within a specified radius of coordinates.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "longitude": {
                            "type": "number",
                            "description": "Longitude coordinate"
                        },
                        "latitude": {
                            "type": "number", 
                            "description": "Latitude coordinate"
                        },
                        "radius": {
                            "type": "integer",
                            "description": "Search radius in meters (default: 50)",
                            "default": 50
                        }
                    },
                    "required": ["longitude", "latitude"]
                }
            ),
            Tool(
                name="get_street_deals",
                description="Get detailed real estate deals for a specific street/polygon.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "polygon_id": {
                            "type": "string",
                            "description": "Polygon ID for the street/area"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of deals to return (default: 10)",
                            "default": 10
                        },
                        "start_date": {
                            "type": "string",
                            "description": "Start date in YYYY-MM format",
                            "pattern": "^\\d{4}-\\d{2}$"
                        },
                        "end_date": {
                            "type": "string", 
                            "description": "End date in YYYY-MM format",
                            "pattern": "^\\d{4}-\\d{2}$"
                        }
                    },
                    "required": ["polygon_id"]
                }
            ),
            Tool(
                name="get_neighborhood_deals",
                description="Get real estate deals within the same neighborhood as a given polygon.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "polygon_id": {
                            "type": "string",
                            "description": "Polygon ID for the area"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of deals to return (default: 10)",
                            "default": 10
                        },
                        "start_date": {
                            "type": "string",
                            "description": "Start date in YYYY-MM format",
                            "pattern": "^\\d{4}-\\d{2}$"
                        },
                        "end_date": {
                            "type": "string",
                            "description": "End date in YYYY-MM format", 
                            "pattern": "^\\d{4}-\\d{2}$"
                        }
                    },
                    "required": ["polygon_id"]
                }
            ),
            Tool(
                name="find_recent_deals_for_address",
                description="🏠 MAIN TOOL: Find all recent real estate deals for a given address. This is the primary function that combines all other tools to provide comprehensive market analysis.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "address": {
                            "type": "string",
                            "description": "Full address to search for (Hebrew or English, e.g., 'דיזנגוף 1 תל אביב')"
                        },
                        "years_back": {
                            "type": "integer",
                            "description": "How many years back to search for deals (default: 2)",
                            "default": 2,
                            "minimum": 1,
                            "maximum": 10
                        }
                    },
                    "required": ["address"]
                }
            ),
            Tool(
                name="analyze_market_trends",
                description="📊 Analyze market trends for a specific address including price trends, average prices, and market insights.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "address": {
                            "type": "string",
                            "description": "Address to analyze market trends for"
                        },
                        "years_back": {
                            "type": "integer",
                            "description": "How many years of data to analyze (default: 3)",
                            "default": 3,
                            "minimum": 1,
                            "maximum": 10
                        }
                    },
                    "required": ["address"]
                }
            ),
            Tool(
                name="compare_neighborhoods",
                description="🏘️ Compare real estate market data between multiple addresses/neighborhoods.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "addresses": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of addresses to compare",
                            "minItems": 2,
                            "maxItems": 5
                        },
                        "years_back": {
                            "type": "integer", 
                            "description": "Years of data to compare (default: 2)",
                            "default": 2
                        }
                    },
                    "required": ["addresses"]
                }
            )
        ]
    )


@server.call_tool()
async def handle_call_tool(request: CallToolRequest) -> CallToolResult:
    """Handle MCP tool calls for Israeli real estate data."""
    
    try:
        tool_name = request.params.name
        arguments = request.params.arguments or {}
        
        if tool_name == "autocomplete_address":
            search_text = arguments.get("search_text")
            if not search_text:
                raise ValueError("search_text is required")
                
            result = govmap_client.autocomplete_address(search_text)
            
            # Format the response for better readability
            formatted_results = []
            for item in result.get("results", []):
                formatted_results.append({
                    "text": item.get("text"),
                    "type": item.get("type"),
                    "coordinates": item.get("shape"),
                    "score": item.get("score")
                })
            
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"Found {result.get('resultsCount', 0)} address matches:\n" + 
                             "\n".join([f"• {r['text']} (type: {r['type']}, score: {r['score']})" 
                                       for r in formatted_results[:5]])
                    )
                ],
                isError=False
            )
            
        elif tool_name == "get_deals_by_radius":
            longitude = arguments.get("longitude")
            latitude = arguments.get("latitude") 
            radius = arguments.get("radius", 50)
            
            if longitude is None or latitude is None:
                raise ValueError("longitude and latitude are required")
                
            result = govmap_client.get_deals_by_radius((longitude, latitude), radius)
            
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"Found {len(result)} deals within {radius}m radius:\n" +
                             "\n".join([f"• Settlement: {deal.get('settlementNameHeb', 'N/A')}, Polygon: {deal.get('polygon_id', 'N/A')}" 
                                       for deal in result[:10]])
                    )
                ],
                isError=False
            )
            
        elif tool_name == "get_street_deals":
            polygon_id = arguments.get("polygon_id")
            limit = arguments.get("limit", 10)
            start_date = arguments.get("start_date")
            end_date = arguments.get("end_date")
            
            if not polygon_id:
                raise ValueError("polygon_id is required")
                
            result = govmap_client.get_street_deals(polygon_id, limit, start_date, end_date)
            
            deals_summary = []
            for deal in result[:5]:
                price = deal.get('dealAmount', 'N/A')
                area = deal.get('assetArea', 'N/A')
                date = deal.get('dealDate', 'N/A')[:10] if deal.get('dealDate') else 'N/A'
                deals_summary.append(f"• {date}: {price:,} NIS, {area} m²" if isinstance(price, (int, float)) else f"• {date}: {price}, {area} m²")
            
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"Found {len(result)} street deals for polygon {polygon_id}:\n" + "\n".join(deals_summary)
                    )
                ],
                isError=False
            )
            
        elif tool_name == "get_neighborhood_deals":
            polygon_id = arguments.get("polygon_id") 
            limit = arguments.get("limit", 10)
            start_date = arguments.get("start_date")
            end_date = arguments.get("end_date")
            
            if not polygon_id:
                raise ValueError("polygon_id is required")
                
            result = govmap_client.get_neighborhood_deals(polygon_id, limit, start_date, end_date)
            
            deals_summary = []
            for deal in result[:5]:
                price = deal.get('dealAmount', 'N/A')
                area = deal.get('assetArea', 'N/A')
                date = deal.get('dealDate', 'N/A')[:10] if deal.get('dealDate') else 'N/A'
                neighborhood = deal.get('neighborhood', 'N/A')
                deals_summary.append(f"• {date}: {price:,} NIS, {area} m² in {neighborhood}" if isinstance(price, (int, float)) else f"• {date}: {price}, {area} m² in {neighborhood}")
            
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"Found {len(result)} neighborhood deals for polygon {polygon_id}:\n" + "\n".join(deals_summary)
                    )
                ],
                isError=False
            )
            
        elif tool_name == "find_recent_deals_for_address":
            address = arguments.get("address")
            years_back = arguments.get("years_back", 2)
            
            if not address:
                raise ValueError("address is required")
                
            result = govmap_client.find_recent_deals_for_address(address, years_back)
            
            # Create comprehensive summary
            if result:
                # Calculate statistics
                amounts = [deal.get('dealAmount') for deal in result if isinstance(deal.get('dealAmount'), (int, float))]
                areas = [deal.get('assetArea') for deal in result if isinstance(deal.get('assetArea'), (int, float))]
                
                summary = [f"🏠 REAL ESTATE ANALYSIS FOR: {address}"]
                summary.append(f"📊 Total deals found: {len(result)}")
                
                if amounts:
                    avg_price = sum(amounts) / len(amounts)
                    summary.append(f"💰 Average price: {avg_price:,.0f} NIS")
                    summary.append(f"📈 Price range: {min(amounts):,} - {max(amounts):,} NIS")
                
                if areas:
                    avg_area = sum(areas) / len(areas)
                    summary.append(f"📏 Average area: {avg_area:.0f} m²")
                
                summary.append(f"\n🏡 Recent deals (last {years_back} years):")
                
                # Show first 10 deals
                for i, deal in enumerate(result[:10], 1):
                    price = deal.get('dealAmount', 'N/A')
                    area = deal.get('assetArea', 'N/A')
                    date = deal.get('dealDate', 'N/A')[:10] if deal.get('dealDate') else 'N/A'
                    prop_type = deal.get('propertyTypeDescription', 'N/A')
                    neighborhood = deal.get('neighborhood', 'N/A')
                    
                    if isinstance(price, (int, float)):
                        summary.append(f"{i}. {date} | {price:,} NIS | {area} m² | {prop_type} | {neighborhood}")
                    else:
                        summary.append(f"{i}. {date} | {price} | {area} m² | {prop_type} | {neighborhood}")
                
                if len(result) > 10:
                    summary.append(f"\n... and {len(result) - 10} more deals")
                    
            else:
                summary = [f"No recent deals found for address: {address}"]
            
            return CallToolResult(
                content=[
                    TextContent(
                        type="text", 
                        text="\n".join(summary)
                    )
                ],
                isError=False
            )
            
        elif tool_name == "analyze_market_trends":
            address = arguments.get("address")
            years_back = arguments.get("years_back", 3)
            
            if not address:
                raise ValueError("address is required")
                
            # Get deals data
            deals = govmap_client.find_recent_deals_for_address(address, years_back)
            
            if not deals:
                return CallToolResult(
                    content=[TextContent(type="text", text=f"No market data found for {address}")],
                    isError=False
                )
            
            # Analyze trends by year
            yearly_data = {}
            property_types = {}
            neighborhoods = set()
            
            for deal in deals:
                date_str = deal.get('dealDate', '')
                if date_str:
                    year = date_str[:4]
                    price = deal.get('dealAmount')
                    area = deal.get('assetArea')
                    prop_type = deal.get('propertyTypeDescription', 'Unknown')
                    neighborhood = deal.get('neighborhood')
                    
                    if neighborhood:
                        neighborhoods.add(neighborhood)
                    
                    if isinstance(price, (int, float)) and isinstance(area, (int, float)) and area > 0:
                        if year not in yearly_data:
                            yearly_data[year] = []
                        yearly_data[year].append({
                            'price': price,
                            'area': area,
                            'price_per_sqm': price / area
                        })
                        
                        property_types[prop_type] = property_types.get(prop_type, 0) + 1
            
            # Generate analysis
            analysis = [f"📊 MARKET TRENDS ANALYSIS: {address}"]
            analysis.append(f"📅 Analysis period: Last {years_back} years")
            analysis.append(f"🏘️ Neighborhoods: {', '.join(neighborhoods) if neighborhoods else 'N/A'}")
            analysis.append(f"🏠 Property types: {', '.join([f'{k} ({v})' for k, v in property_types.items()])}")
            
            if yearly_data:
                analysis.append(f"\n📈 YEARLY TRENDS:")
                
                for year in sorted(yearly_data.keys(), reverse=True):
                    year_deals = yearly_data[year]
                    avg_price = sum(d['price'] for d in year_deals) / len(year_deals)
                    avg_area = sum(d['area'] for d in year_deals) / len(year_deals)
                    avg_price_per_sqm = sum(d['price_per_sqm'] for d in year_deals) / len(year_deals)
                    
                    analysis.append(f"  {year}: {len(year_deals)} deals | Avg: {avg_price:,.0f} NIS | {avg_area:.0f} m² | {avg_price_per_sqm:,.0f} NIS/m²")
                
                # Price trend
                years_sorted = sorted(yearly_data.keys())
                if len(years_sorted) >= 2:
                    first_year_avg = sum(d['price_per_sqm'] for d in yearly_data[years_sorted[0]]) / len(yearly_data[years_sorted[0]])
                    last_year_avg = sum(d['price_per_sqm'] for d in yearly_data[years_sorted[-1]]) / len(yearly_data[years_sorted[-1]])
                    
                    trend = ((last_year_avg - first_year_avg) / first_year_avg) * 100
                    trend_direction = "📈 Rising" if trend > 0 else "📉 Declining" if trend < 0 else "➡️ Stable"
                    analysis.append(f"\n🎯 Price Trend: {trend_direction} ({trend:+.1f}% over period)")
            
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text="\n".join(analysis)
                    )
                ],
                isError=False
            )
            
        elif tool_name == "compare_neighborhoods":
            addresses = arguments.get("addresses", [])
            years_back = arguments.get("years_back", 2)
            
            if len(addresses) < 2:
                raise ValueError("At least 2 addresses are required for comparison")
            
            comparison = [f"🏘️ NEIGHBORHOOD COMPARISON"]
            comparison.append(f"📅 Comparing last {years_back} years of data\n")
            
            address_data = {}
            
            for address in addresses:
                deals = govmap_client.find_recent_deals_for_address(address, years_back)
                
                if deals:
                    amounts = [deal.get('dealAmount') for deal in deals if isinstance(deal.get('dealAmount'), (int, float))]
                    areas = [deal.get('assetArea') for deal in deals if isinstance(deal.get('assetArea'), (int, float))]
                    neighborhoods = {deal.get('neighborhood') for deal in deals if deal.get('neighborhood')}
                    
                    if amounts and areas:
                        price_per_sqm = [amounts[i] / areas[i] for i in range(min(len(amounts), len(areas))) if areas[i] > 0]
                        
                        address_data[address] = {
                            'deals_count': len(deals),
                            'avg_price': sum(amounts) / len(amounts),
                            'avg_area': sum(areas) / len(areas),
                            'avg_price_per_sqm': sum(price_per_sqm) / len(price_per_sqm) if price_per_sqm else 0,
                            'neighborhoods': neighborhoods
                        }
            
            # Generate comparison
            for address, data in address_data.items():
                comparison.append(f"📍 {address}:")
                comparison.append(f"  • {data['deals_count']} deals found")
                comparison.append(f"  • Avg price: {data['avg_price']:,.0f} NIS")
                comparison.append(f"  • Avg area: {data['avg_area']:.0f} m²")
                comparison.append(f"  • Price per m²: {data['avg_price_per_sqm']:,.0f} NIS")
                comparison.append(f"  • Neighborhoods: {', '.join(data['neighborhoods'])}")
                comparison.append("")
            
            # Ranking
            if address_data:
                comparison.append("🏆 RANKINGS:")
                by_price_per_sqm = sorted(address_data.items(), key=lambda x: x[1]['avg_price_per_sqm'], reverse=True)
                
                comparison.append("💰 Most expensive (NIS/m²):")
                for i, (addr, data) in enumerate(by_price_per_sqm, 1):
                    comparison.append(f"  {i}. {addr}: {data['avg_price_per_sqm']:,.0f} NIS/m²")
            
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text="\n".join(comparison)
                    )
                ],
                isError=False
            )
        
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
            
    except Exception as e:
        logger.error(f"Error in tool {request.params.name}: {str(e)}")
        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=f"Error: {str(e)}"
                )
            ],
            isError=True
        )


async def main():
    """Run the MCP server."""
    
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="israel-real-estate-mcp",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 