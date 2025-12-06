"""
Fast unit tests for MCP tools using cached fixtures.

These tests use pre-recorded API responses to run quickly (~1s)
without hitting the real Govmap API.

For full E2E tests with real API calls, see tests/e2e/test_mcp_tools.py
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from nadlan_mcp.config import get_config
from nadlan_mcp.fastmcp_server import (
    autocomplete_address,
    get_deals_by_radius,
    get_neighborhood_deals,
    get_street_deals,
)
from nadlan_mcp.govmap.models import AutocompleteResponse, AutocompleteResult, Deal

# Load fixtures
FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(filename):
    """Load a JSON fixture file."""
    with open(FIXTURES_DIR / filename, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def mock_autocomplete_data():
    """Cached autocomplete response."""
    data = load_fixture("autocomplete_response.json")
    results = [AutocompleteResult.model_validate(r) for r in data]
    return AutocompleteResponse(results=results, resultsCount=len(results))


@pytest.fixture
def mock_street_deals_data():
    """Cached street deals response."""
    data = load_fixture("street_deals.json")
    return [Deal.model_validate(d) for d in data]


@pytest.fixture
def mock_neighborhood_deals_data():
    """Cached neighborhood deals response."""
    data = load_fixture("neighborhood_deals.json")
    return [Deal.model_validate(d) for d in data]


@pytest.fixture
def mock_polygon_metadata_data():
    """Cached polygon metadata response."""
    return load_fixture("polygon_metadata.json")


class TestMCPToolsFast:
    """Fast unit tests for MCP tools using mocked data."""

    @patch("nadlan_mcp.fastmcp_server.client")
    def test_autocomplete_address_fast(self, mock_client, mock_autocomplete_data):
        """Test autocomplete with cached data."""
        mock_client.autocomplete_address.return_value = mock_autocomplete_data

        result = autocomplete_address("חולון סוקולוב")
        data = json.loads(result)

        assert isinstance(data, list)
        assert len(data) > 0
        assert "text" in data[0]
        assert "coordinates" in data[0]

    @patch("nadlan_mcp.fastmcp_server.client")
    def test_get_street_deals_fast(self, mock_client, mock_street_deals_data):
        """Test street deals with cached data."""
        if not get_config().tool_get_street_deals_enabled:
            pytest.skip("get_street_deals tool is disabled")

        mock_client.get_street_deals.return_value = mock_street_deals_data

        result = get_street_deals("52385050", limit=100, deal_type=2)
        data = json.loads(result)

        assert "total_deals" in data
        assert data["total_deals"] == len(mock_street_deals_data)
        assert "deals" in data
        assert len(data["deals"]) > 0

        # Verify deal structure
        deal = data["deals"][0]
        assert "deal_amount" in deal
        assert "deal_date" in deal

    @patch("nadlan_mcp.fastmcp_server.client")
    def test_get_neighborhood_deals_fast(self, mock_client, mock_neighborhood_deals_data):
        """Test neighborhood deals with cached data."""
        mock_client.get_neighborhood_deals.return_value = mock_neighborhood_deals_data

        result = get_neighborhood_deals("52385050", limit=100, deal_type=2)
        data = json.loads(result)

        assert "total_deals" in data
        assert data["total_deals"] == len(mock_neighborhood_deals_data)
        assert "deals" in data

    @patch("nadlan_mcp.fastmcp_server.client")
    def test_get_deals_by_radius_fast(self, mock_client, mock_polygon_metadata_data):
        """Test deals by radius with cached data."""

        if not get_config().tool_get_deals_by_radius_enabled:
            pytest.skip("test_get_deals_by_radius tool is disabled")
        mock_client.get_deals_by_radius.return_value = mock_polygon_metadata_data

        result = get_deals_by_radius(37.6629, 38.7093, radius_meters=500)
        data = json.loads(result)

        assert "total_polygons" in data
        assert data["total_polygons"] == len(mock_polygon_metadata_data)
        assert "polygons" in data

    @pytest.mark.skip(reason="Complex workflow with statistics - tested in E2E suite")
    @patch("nadlan_mcp.fastmcp_server.client")
    def test_find_recent_deals_fast(
        self,
        mock_client,
        mock_street_deals_data,
        mock_neighborhood_deals_data,
        mock_polygon_metadata_data,
        mock_autocomplete_data,
    ):
        """Test find_recent_deals with fully mocked workflow.

        NOTE: This test is skipped because find_recent_deals_for_address has complex
        statistics calculations that require specific data structure. Use E2E tests
        in tests/e2e/test_mcp_tools.py for full integration testing.
        """
        pass

    @patch("nadlan_mcp.fastmcp_server.client")
    def test_no_deals_found(self, mock_client):
        """Test handling when no deals are found."""
        if not get_config().tool_get_street_deals_enabled:
            pytest.skip("get_street_deals tool is disabled")

        mock_client.get_street_deals.return_value = []

        result = get_street_deals("999999", limit=100, deal_type=2)

        # Should return a message string when no deals found
        assert isinstance(result, str)
        assert "No" in result or "found" in result.lower()

    @patch("nadlan_mcp.fastmcp_server.client")
    def test_deal_type_filtering(self, mock_client, mock_street_deals_data):
        """Test that deal_type parameter is passed correctly."""
        if not get_config().tool_get_street_deals_enabled:
            pytest.skip("get_street_deals tool is disabled")

        mock_client.get_street_deals.return_value = mock_street_deals_data

        # Test with deal_type=1 (first hand)
        result = get_street_deals("52385050", limit=100, deal_type=1)
        data = json.loads(result)

        # Verify client was called with correct deal_type
        mock_client.get_street_deals.assert_called_once_with("52385050", 100, deal_type=1)
        assert "deal_type" in data
        assert data["deal_type"] == 1
