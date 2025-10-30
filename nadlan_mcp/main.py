"""
Israel Real Estate MCP - Main Module

This module provides the GovmapClient class for interacting with the Israeli
government's public real estate data API (Govmap).
"""

from nadlan_mcp.govmap import GovmapClient


# Example usage functions
def main():
    """
    Example usage of the GovmapClient.
    """
    # Initialize client
    client = GovmapClient()

    # Example address search
    address = "סוקולוב 38 חולון"

    try:
        # Find recent deals for address
        deals = client.find_recent_deals_for_address(address, years_back=2)

        print(f"Found {len(deals)} deals for address: {address}")

        # Display first few deals
        for i, deal in enumerate(deals[:5]):
            print(f"\nDeal {i + 1}:")

            # Build address from available fields
            address_parts = []
            if deal.get("streetNameHeb"):
                address_parts.append(deal.get("streetNameHeb"))
            if deal.get("houseNum"):
                address_parts.append(str(deal.get("houseNum")))
            if deal.get("settlementNameHeb"):
                address_parts.append(deal.get("settlementNameHeb"))
            address = " ".join(address_parts) if address_parts else "N/A"

            print(f"  Address: {address}")
            print(f"  Date: {deal.get('dealDate', 'N/A')[:10] if deal.get('dealDate') else 'N/A'}")
            print(
                f"  Price: {deal.get('dealAmount', 'N/A'):,} NIS"
                if deal.get("dealAmount")
                else "  Price: N/A"
            )
            print(
                f"  Area: {deal.get('assetArea', 'N/A')} m²"
                if deal.get("assetArea")
                else "  Area: N/A"
            )
            print(f"  Type: {deal.get('propertyTypeDescription', 'N/A')}")
            print(f"  Neighborhood: {deal.get('neighborhood', 'N/A')}")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
