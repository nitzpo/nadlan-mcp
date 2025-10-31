#!/usr/bin/env python3
"""
Property Valuation Example

This example shows how to find comparable properties and
estimate the value of a property based on recent deals.
"""

from nadlan_mcp.govmap import GovmapClient


def main():
    client = GovmapClient()

    # Property to value
    address = "רוטשילד 10 תל אביב"
    property_details = {
        "rooms": 3.5,
        "area": 85,  # square meters
        "floor": 3,
    }

    print(f"Valuing property at: {address}")
    print("Property details:")
    print(f"  Rooms: {property_details['rooms']}")
    print(f"  Area: {property_details['area']}m²")
    print(f"  Floor: {property_details['floor']}")
    print()

    try:
        # Get comparable deals with filters
        deals = client.find_recent_deals_for_address(
            address, years_back=2, radius=200  # Wider radius for more comparables
        )

        if not deals:
            print("No comparable deals found")
            return

        # Filter for similar properties
        comparables = client.filter_deals_by_criteria(
            deals,
            min_rooms=property_details["rooms"] - 0.5,
            max_rooms=property_details["rooms"] + 0.5,
            min_area=property_details["area"] * 0.85,  # ±15%
            max_area=property_details["area"] * 1.15,
            min_floor=max(0, property_details["floor"] - 2),
            max_floor=property_details["floor"] + 2,
        )

        print(f"Found {len(comparables)} comparable properties\n")

        if not comparables:
            print("No close matches found. Try widening your criteria.")
            return

        # Calculate statistics on comparables
        stats = client.calculate_deal_statistics(comparables)

        print("=== Comparable Properties Analysis ===")
        print(f"Number of Comparables: {len(comparables)}")
        print("\nPrice Statistics:")
        print(f"  Average Price: ₪{stats.mean_price:,.0f}")
        print(f"  Median Price: ₪{stats.median_price:,.0f}")
        print(f"  Price Range: ₪{stats.min_price:,.0f} - ₪{stats.max_price:,.0f}")

        if stats.mean_price_per_sqm:
            print("\nPrice per Square Meter:")
            print(f"  Average: ₪{stats.mean_price_per_sqm:,.0f}/m²")
            print(f"  Median: ₪{stats.median_price_per_sqm:,.0f}/m²")

            # Estimate property value
            estimated_value = stats.mean_price_per_sqm * property_details["area"]
            estimated_value_low = stats.percentile_25_price_per_sqm * property_details["area"]
            estimated_value_high = stats.percentile_75_price_per_sqm * property_details["area"]

            print("\n=== Estimated Property Value ===")
            print(f"Based on {property_details['area']}m² at ₪{stats.mean_price_per_sqm:,.0f}/m²:")
            print(f"  Estimated Value: ₪{estimated_value:,.0f}")
            print("  Range (25th-75th percentile):")
            print(f"    Low: ₪{estimated_value_low:,.0f}")
            print(f"    High: ₪{estimated_value_high:,.0f}")

        # Show sample comparables
        print("\n=== Sample Comparables ===")
        for i, deal in enumerate(comparables[:5], 1):
            print(f"\n{i}. {deal.address_description or 'N/A'}")
            print(f"   Date: {deal.deal_date}")
            print(f"   Price: ₪{deal.deal_amount:,.0f}" if deal.deal_amount else "   Price: N/A")
            print(f"   Rooms: {deal.rooms}" if deal.rooms else "   Rooms: N/A")
            print(f"   Area: {deal.asset_area}m²" if deal.asset_area else "   Area: N/A")
            if deal.price_per_sqm:
                print(f"   Price/m²: ₪{deal.price_per_sqm:,.0f}")

    except ValueError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")


if __name__ == "__main__":
    main()
