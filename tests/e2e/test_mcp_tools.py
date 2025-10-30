"""
Fast E2E smoke tests for MCP tools (<30 seconds).

These tests make MINIMAL real API calls to verify the service is working.
For comprehensive E2E testing, see test_mcp_tools_comprehensive.py

Target: Complete in <30 seconds
"""

import json

import pytest

from nadlan_mcp.fastmcp_server import (
    autocomplete_address,
    find_recent_deals_for_address,
    get_deals_by_radius,
    get_street_deals,
)


@pytest.mark.integration
class TestMCPToolsSmokeTests:
    """Minimal E2E smoke tests to verify API connectivity."""

    # Known working data
    TEST_ADDRESS = "סוקולוב 38 חולון"
    TEST_POLYGON_ID = "52385050"
    TEST_LAT = 3766290.19
    TEST_LON = 3870928.84

    def test_autocomplete_works(self):
        """Smoke test: Autocomplete returns results."""
        result = autocomplete_address("חולון")
        data = json.loads(result)

        assert isinstance(data, list)
        assert len(data) > 0
        assert "text" in data[0]

    def test_get_street_deals_works(self):
        """Smoke test: Can fetch street deals."""
        # Use small limit for speed
        result = get_street_deals(self.TEST_POLYGON_ID, limit=5, deal_type=2)
        data = json.loads(result)

        assert "total_deals" in data
        assert data["total_deals"] > 0
        assert "deals" in data

    def test_get_deals_by_radius_works(self):
        """Smoke test: Can fetch polygon metadata by radius."""
        # Use small radius for speed
        result = get_deals_by_radius(self.TEST_LAT, self.TEST_LON, radius_meters=100)
        data = json.loads(result)

        assert "total_polygons" in data
        assert data["total_polygons"] > 0

    def test_find_recent_deals_minimal(self):
        """Smoke test: Main tool works with minimal data."""
        # Use very small limits to speed up
        result = find_recent_deals_for_address(
            self.TEST_ADDRESS, years_back=1, radius_meters=30, max_deals=10
        )
        data = json.loads(result)

        # Just verify structure, don't check counts
        assert "search_parameters" in data
        assert "market_statistics" in data
        assert "deals" in data
        assert isinstance(data["deals"], list)
