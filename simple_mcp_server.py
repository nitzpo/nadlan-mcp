#!/usr/bin/env python3
"""
Simple Israel Real Estate MCP Server

A simplified MCP server that provides access to Israeli real estate data.
Focuses on the main use cases for AI agents.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List

# Simple MCP server implementation
class SimpleMCPServer:
    def __init__(self):
        from nadlan_mcp.govmap import GovmapClient
        self.client = GovmapClient()
        self.tools = {
            "find_recent_deals_for_address": {
                "description": "🏠 Find all recent real estate deals for a given address. Main function for comprehensive market analysis.",
                "parameters": {
                    "address": "Full address to search for (Hebrew or English)",
                    "years_back": "How many years back to search (default: 2)"
                }
            },
            "analyze_market_trends": {
                "description": "📊 Analyze market trends for a specific address with price analysis and insights",
                "parameters": {
                    "address": "Address to analyze",
                    "years_back": "Years of data to analyze (default: 3)"
                }
            },
            "compare_neighborhoods": {
                "description": "🏘️ Compare real estate market data between multiple addresses",
                "parameters": {
                    "addresses": "List of addresses to compare (2-5 addresses)",
                    "years_back": "Years of data to compare (default: 2)"
                }
            },
            "autocomplete_address": {
                "description": "🔍 Search for Israeli addresses using autocomplete",
                "parameters": {
                    "search_text": "Address to search for"
                }
            }
        }
    
    def list_tools(self) -> str:
        """List available tools."""
        tools_list = ["📋 Available Real Estate Tools:"]
        for name, info in self.tools.items():
            tools_list.append(f"\n🔧 {name}")
            tools_list.append(f"   {info['description']}")
            tools_list.append("   Parameters:")
            for param, desc in info['parameters'].items():
                tools_list.append(f"     • {param}: {desc}")
        
        return "\n".join(tools_list)
    
    def call_tool(self, tool_name: str, **kwargs) -> str:
        """Call a specific tool."""
        try:
            if tool_name == "find_recent_deals_for_address":
                return self._find_recent_deals(**kwargs)
            elif tool_name == "analyze_market_trends":
                return self._analyze_trends(**kwargs)
            elif tool_name == "compare_neighborhoods":
                return self._compare_neighborhoods(**kwargs)
            elif tool_name == "autocomplete_address":
                return self._autocomplete_address(**kwargs)
            else:
                return f"❌ Unknown tool: {tool_name}"
        except Exception as e:
            return f"❌ Error in {tool_name}: {str(e)}"
    
    def _find_recent_deals(self, address: str, years_back: int = 2) -> str:
        """Find recent deals for an address."""
        deals = self.client.find_recent_deals_for_address(address, years_back)
        
        if not deals:
            return f"No recent deals found for: {address}"
        
        # Calculate statistics
        amounts = [deal.get('dealAmount') for deal in deals if isinstance(deal.get('dealAmount'), (int, float))]
        areas = [deal.get('assetArea') for deal in deals if isinstance(deal.get('assetArea'), (int, float))]
        
        result = [f"🏠 REAL ESTATE ANALYSIS FOR: {address}"]
        result.append(f"📊 Total deals found: {len(deals)}")
        
        if amounts:
            avg_price = sum(amounts) / len(amounts)
            result.append(f"💰 Average price: {avg_price:,.0f} NIS")
            result.append(f"📈 Price range: {min(amounts):,} - {max(amounts):,} NIS")
        
        if areas:
            avg_area = sum(areas) / len(areas)
            result.append(f"📏 Average area: {avg_area:.0f} m²")
        
        result.append(f"\n🏡 Recent deals (last {years_back} years):")
        
        # Show first 10 deals
        for i, deal in enumerate(deals[:10], 1):
            price = deal.get('dealAmount', 'N/A')
            area = deal.get('assetArea', 'N/A')
            date = deal.get('dealDate', 'N/A')[:10] if deal.get('dealDate') else 'N/A'
            prop_type = deal.get('propertyTypeDescription', 'N/A')
            neighborhood = deal.get('neighborhood', 'N/A')
            
            if isinstance(price, (int, float)):
                result.append(f"{i}. {date} | {price:,} NIS | {area} m² | {prop_type} | {neighborhood}")
            else:
                result.append(f"{i}. {date} | {price} | {area} m² | {prop_type} | {neighborhood}")
        
        if len(deals) > 10:
            result.append(f"\n... and {len(deals) - 10} more deals")
        
        return "\n".join(result)
    
    def _analyze_trends(self, address: str, years_back: int = 3) -> str:
        """Analyze market trends."""
        deals = self.client.find_recent_deals_for_address(address, years_back)
        
        if not deals:
            return f"No market data found for {address}"
        
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
        
        return "\n".join(analysis)
    
    def _compare_neighborhoods(self, addresses: List[str], years_back: int = 2) -> str:
        """Compare neighborhoods."""
        if len(addresses) < 2:
            return "❌ At least 2 addresses are required for comparison"
        
        comparison = [f"🏘️ NEIGHBORHOOD COMPARISON"]
        comparison.append(f"📅 Comparing last {years_back} years of data\n")
        
        address_data = {}
        
        for address in addresses:
            deals = self.client.find_recent_deals_for_address(address, years_back)
            
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
        
        return "\n".join(comparison)
    
    def _autocomplete_address(self, search_text: str) -> str:
        """Autocomplete address search."""
        result = self.client.autocomplete_address(search_text)
        
        formatted_results = []
        for item in result.get("results", []):
            formatted_results.append(f"• {item.get('text')} (type: {item.get('type')}, score: {item.get('score')})")
        
        return f"Found {result.get('resultsCount', 0)} address matches:\n" + "\n".join(formatted_results[:5])


def main():
    """Interactive demo of the MCP server functionality."""
    print("🏠 Israel Real Estate MCP Server - Demo Mode")
    print("=" * 50)
    
    server = SimpleMCPServer()
    
    while True:
        print("\n" + "=" * 50)
        print("🔧 Available commands:")
        print("1. list - List all available tools")
        print("2. find - Find recent deals for address")
        print("3. trends - Analyze market trends")
        print("4. compare - Compare neighborhoods")
        print("5. search - Search for addresses")
        print("6. quit - Exit")
        
        choice = input("\nSelect a command (1-6): ").strip()
        
        if choice == "1":
            print(server.list_tools())
        
        elif choice == "2":
            address = input("Enter address: ").strip()
            years = input("Years back (default 2): ").strip()
            years_back = int(years) if years.isdigit() else 2
            
            print("\n🔍 Searching for deals...")
            result = server.call_tool("find_recent_deals_for_address", address=address, years_back=years_back)
            print(result)
        
        elif choice == "3":
            address = input("Enter address: ").strip()
            years = input("Years back (default 3): ").strip()
            years_back = int(years) if years.isdigit() else 3
            
            print("\n📊 Analyzing trends...")
            result = server.call_tool("analyze_market_trends", address=address, years_back=years_back)
            print(result)
        
        elif choice == "4":
            addresses_input = input("Enter addresses (comma separated): ").strip()
            addresses = [addr.strip() for addr in addresses_input.split(",")]
            years = input("Years back (default 2): ").strip()
            years_back = int(years) if years.isdigit() else 2
            
            print("\n🏘️ Comparing neighborhoods...")
            result = server.call_tool("compare_neighborhoods", addresses=addresses, years_back=years_back)
            print(result)
        
        elif choice == "5":
            search_text = input("Enter search text: ").strip()
            
            print("\n🔍 Searching addresses...")
            result = server.call_tool("autocomplete_address", search_text=search_text)
            print(result)
        
        elif choice == "6":
            print("👋 Goodbye!")
            break
        
        else:
            print("❌ Invalid choice. Please select 1-6.")


if __name__ == "__main__":
    main() 