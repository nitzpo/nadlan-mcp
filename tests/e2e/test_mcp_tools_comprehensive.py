"""
End-to-end tests for all MCP tools.

These tests make real API calls to verify the complete functionality
of each MCP tool from end to end.

Mark as integration tests since they hit real APIs.
"""

import json

import pytest

from nadlan_mcp.fastmcp_server import (
    analyze_market_trends,
    autocomplete_address,
    compare_addresses,
    find_recent_deals_for_address,
    get_deal_statistics,
    get_deals_by_radius,
    get_market_activity_metrics,
    get_neighborhood_deals,
    get_street_deals,
    get_valuation_comparables,
)


@pytest.mark.integration
class TestMCPToolsE2E:
    """End-to-end tests for all 10 MCP tools."""

    # Test addresses
    TEST_ADDRESS_1 = "סוקולוב 38 חולון"
    TEST_ADDRESS_2 = "דיזנגוף 50 תל אביב"
    TEST_POLYGON_ID = "52385050"  # Known polygon with data
    # ITM coordinates for Holon (lat, lon format for MCP tool)
    TEST_LAT = 3766290.19
    TEST_LON = 3870928.84

    def test_autocomplete_address(self):
        """Test address autocomplete returns results."""
        result = autocomplete_address("חולון סוקולוב")
        data = json.loads(result)

        assert isinstance(data, list)
        assert len(data) > 0

        # Check first result has expected structure
        first = data[0]
        assert "text" in first
        assert "coordinates" in first or "id" in first

    def test_find_recent_deals_for_address(self):
        """Test finding recent deals for an address."""
        result = find_recent_deals_for_address(self.TEST_ADDRESS_1, max_deals=100)
        data = json.loads(result)

        # Check response structure
        assert "search_parameters" in data
        assert "market_statistics" in data
        assert "deals" in data

        # Verify some deals were found
        assert isinstance(data["deals"], list)
        assert len(data["deals"]) > 0

        # Check deal structure
        deal = data["deals"][0]
        assert "deal_amount" in deal
        assert "deal_date" in deal
        assert "settlement_name_heb" in deal

    def test_analyze_market_trends(self):
        """Test market trend analysis."""
        result = analyze_market_trends(self.TEST_ADDRESS_1, years_back=3, radius_meters=100)
        data = json.loads(result)

        # Check response structure
        assert "market_summary" in data
        assert "total_deals" in data["market_summary"]
        assert isinstance(data["market_summary"]["total_deals"], int)
        assert data["market_summary"]["total_deals"] >= 0

    def test_get_valuation_comparables(self):
        """Test getting valuation comparables."""
        result = get_valuation_comparables(
            self.TEST_ADDRESS_1, years_back=3, min_rooms=3.0, max_rooms=5.0
        )
        data = json.loads(result)

        assert "total_comparables" in data
        assert isinstance(data["total_comparables"], int)
        assert data["total_comparables"] >= 0

        if data["total_comparables"] > 0:
            assert "comparables" in data
            comp = data["comparables"][0]
            assert "deal_amount" in comp
            assert "asset_room_num" in comp

    def test_get_deal_statistics(self):
        """Test deal statistics calculation."""
        result = get_deal_statistics(self.TEST_ADDRESS_1, years_back=3)
        data = json.loads(result)

        # Check response structure
        assert "statistics" in data
        if "sample_size" in data["statistics"]:
            assert isinstance(data["statistics"]["sample_size"], int)
            assert data["statistics"]["sample_size"] >= 0

    def test_get_market_activity_metrics(self):
        """Test market activity metrics."""
        result = get_market_activity_metrics(self.TEST_ADDRESS_1, years_back=3)
        data = json.loads(result)

        # Check response structure
        assert "market_activity" in data
        if data["market_activity"] is not None:
            assert "activity_score" in data["market_activity"]

    def test_compare_addresses(self):
        """Test comparing multiple addresses."""
        result = compare_addresses([self.TEST_ADDRESS_1, self.TEST_ADDRESS_2])
        data = json.loads(result)

        assert isinstance(data, dict)
        assert "addresses_compared" in data
        assert "all_results" in data

    def test_get_street_deals(self):
        """Test getting street-level deals."""
        result = get_street_deals(self.TEST_POLYGON_ID, limit=100, deal_type=2)
        data = json.loads(result)

        assert "total_deals" in data
        assert isinstance(data["total_deals"], int)
        assert data["total_deals"] > 0  # Known polygon should have deals

        assert "deals" in data
        assert len(data["deals"]) > 0

        # Check deal structure
        deal = data["deals"][0]
        assert "deal_amount" in deal
        assert "deal_date" in deal

    def test_get_neighborhood_deals(self):
        """Test getting neighborhood-level deals."""
        result = get_neighborhood_deals(self.TEST_POLYGON_ID, limit=100, deal_type=2)
        data = json.loads(result)

        assert "total_deals" in data
        assert isinstance(data["total_deals"], int)
        assert data["total_deals"] > 0  # Known polygon should have deals

        assert "deals" in data
        assert len(data["deals"]) > 0

    def test_get_deals_by_radius(self):
        """Test getting polygon metadata by radius."""
        result = get_deals_by_radius(self.TEST_LAT, self.TEST_LON, radius_meters=500)
        data = json.loads(result)

        assert "total_polygons" in data
        assert isinstance(data["total_polygons"], int)
        assert data["total_polygons"] > 0  # Known coords should have polygons

        assert "polygons" in data
        assert len(data["polygons"]) > 0

        # Check polygon metadata structure
        polygon = data["polygons"][0]
        assert "polygon_id" in polygon or "objectid" in polygon

    def test_get_deals_by_radius_no_results(self):
        """Test get_deals_by_radius with coords that have no data."""
        # Use coordinates unlikely to have data
        result = get_deals_by_radius(37.66, 38.71, radius_meters=10)

        # Should return a message string, not JSON
        assert isinstance(result, str)
        assert "No polygons found" in result or "total_polygons" in result
