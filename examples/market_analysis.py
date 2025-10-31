#!/usr/bin/env python3
"""
Market Analysis Example

This example shows how to analyze market trends for a specific area,
including price trends, market activity, and liquidity metrics.
"""

from nadlan_mcp.govmap import GovmapClient


def main():
    # Initialize the client
    client = GovmapClient()

    # Address to analyze
    address = "דיזנגוף 50 תל אביב"  # Dizengoff 50, Tel Aviv
    years = 3
    print(f"Analyzing market trends for: {address}")
    print(f"Period: Last {years} years\n")

    try:
        # Get deals for analysis
        deals = client.find_recent_deals_for_address(address, years_back=years, radius=100)

        if not deals:
            print("No deals found for this address")
            return

        print(f"Found {len(deals)} deals for analysis\n")

        # Calculate statistics
        stats = client.calculate_deal_statistics(deals)
        print("=== Price Statistics ===")
        print(f"Average Price: ₪{stats.mean_price:,.0f}")
        print(f"Median Price: ₪{stats.median_price:,.0f}")
        print(f"Price Range: ₪{stats.min_price:,.0f} - ₪{stats.max_price:,.0f}")
        if stats.mean_price_per_sqm:
            print(f"Avg Price/m²: ₪{stats.mean_price_per_sqm:,.0f}")
        print()

        # Market activity analysis
        activity = client.calculate_market_activity_score(deals)
        print("=== Market Activity ===")
        print(f"Activity Score: {activity.activity_score}/100")
        print(f"Activity Level: {activity.activity_level}")
        print(f"Trend: {activity.trend}")
        print(f"Deals/Month: {activity.deals_per_month:.2f}")
        print()

        # Market liquidity
        liquidity = client.get_market_liquidity(deals)
        print("=== Market Liquidity ===")
        print(f"Liquidity Score: {liquidity.liquidity_score}/100")
        print(f"Market Level: {liquidity.market_activity_level}")
        print(f"Avg Deals/Month: {liquidity.avg_deals_per_month:.2f}")
        print()

        # Investment potential
        investment = client.analyze_investment_potential(deals)
        print("=== Investment Analysis ===")
        print(f"Investment Score: {investment.investment_score}/100")
        print(f"Price Trend: {investment.price_trend}")
        print(f"Market Stability: {investment.market_stability}")
        print(f"Appreciation Rate: {investment.price_appreciation_rate:.2f}%/year")
        print()

    except ValueError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")


if __name__ == "__main__":
    main()
