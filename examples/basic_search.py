#!/usr/bin/env python3
"""
Basic Address Search Example

This example demonstrates how to search for recent real estate deals
for a specific Israeli address using the Nadlan-MCP library.
"""

from nadlan_mcp.govmap import GovmapClient


def main():
    # Initialize the client
    client = GovmapClient()

    # Search for an address (Hebrew works best)
    address = "רוטשילד 1 תל אביב"  # Rothschild Blvd 1, Tel Aviv
    print(f"Searching for recent deals near: {address}\n")

    try:
        # Find recent deals (last 2 years by default)
        deals = client.find_recent_deals_for_address(address, years_back=2)

        print(f"Found {len(deals)} deals\n")

        # Display the first 5 deals
        for i, deal in enumerate(deals[:5], 1):
            print(f"Deal #{i}:")
            print(f"  Address: {deal.address_description or 'N/A'}")
            print(f"  Date: {deal.deal_date}")
            print(f"  Price: ₪{deal.deal_amount:,.0f}" if deal.deal_amount else "  Price: N/A")
            print(f"  Rooms: {deal.rooms}" if deal.rooms else "  Rooms: N/A")
            print(f"  Area: {deal.asset_area}m²" if deal.asset_area else "  Area: N/A")
            if deal.price_per_sqm:
                print(f"  Price/m²: ₪{deal.price_per_sqm:,.0f}")
            print()

    except ValueError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")


if __name__ == "__main__":
    main()
