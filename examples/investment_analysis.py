#!/usr/bin/env python3
"""
Investment Comparison Example

This example compares multiple neighborhoods to help identify
the best investment opportunities based on various metrics.
"""

from nadlan_mcp.govmap import GovmapClient


def analyze_location(client, address, years=2):
    """Analyze a single location and return key metrics."""
    try:
        deals = client.find_recent_deals_for_address(address, years_back=years, radius=150)

        if not deals:
            return None

        stats = client.calculate_deal_statistics(deals)
        activity = client.calculate_market_activity_score(deals)
        liquidity = client.get_market_liquidity(deals)
        investment = client.analyze_investment_potential(deals)

        return {
            "address": address,
            "deal_count": len(deals),
            "avg_price": stats.mean_price,
            "avg_price_per_sqm": stats.mean_price_per_sqm,
            "activity_score": activity.activity_score,
            "activity_level": activity.activity_level,
            "liquidity_score": liquidity.liquidity_score,
            "investment_score": investment.investment_score,
            "price_trend": investment.price_trend,
            "appreciation_rate": investment.price_appreciation_rate,
            "volatility": investment.volatility_score,
        }
    except Exception as e:
        print(f"Error analyzing {address}: {e}")
        return None


def main():
    client = GovmapClient()

    # Addresses to compare
    locations = [
        "רוטשילד 1 תל אביב",  # Rothschild, Tel Aviv - Prestigious
        "ז'בוטינסקי 1 רמת גן",  # Jabotinsky, Ramat Gan - Business district
        "הרצל 1 חיפה",  # Herzl, Haifa - Northern city
    ]

    print("=== Investment Comparison ===\n")
    print("Analyzing multiple neighborhoods...\n")

    results = []
    for location in locations:
        print(f"Analyzing: {location}")
        result = analyze_location(client, location, years=3)
        if result:
            results.append(result)
        print()

    if not results:
        print("No data available for comparison")
        return

    # Display comparison table
    print("\n" + "=" * 100)
    print("COMPARISON SUMMARY")
    print("=" * 100)

    for result in results:
        print(f"\n{result['address']}")
        print("-" * 80)
        print(f"  Deal Count: {result['deal_count']}")
        print(f"  Avg Price: ₪{result['avg_price']:,.0f}")
        if result['avg_price_per_sqm']:
            print(f"  Avg Price/m²: ₪{result['avg_price_per_sqm']:,.0f}")
        print(f"  Activity: {result['activity_score']:.0f}/100 ({result['activity_level']})")
        print(f"  Liquidity: {result['liquidity_score']:.0f}/100")
        print(f"  Investment Score: {result['investment_score']:.0f}/100")
        print(f"  Price Trend: {result['price_trend']}")
        print(f"  Appreciation: {result['appreciation_rate']:.2f}%/year")
        print(f"  Volatility: {result['volatility']:.0f}/100")

    # Find best investment based on investment score
    best_investment = max(results, key=lambda x: x["investment_score"])
    print("\n" + "=" * 100)
    print("RECOMMENDATION")
    print("=" * 100)
    print(f"\nBest Investment Opportunity: {best_investment['address']}")
    print(f"Investment Score: {best_investment['investment_score']:.0f}/100")
    print(f"Price Appreciation: {best_investment['appreciation_rate']:.2f}%/year")


if __name__ == "__main__":
    main()
