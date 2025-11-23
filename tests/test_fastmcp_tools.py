"""
E2E tests for FastMCP tools.

Tests the MCP tool layer including JSON formatting, error handling,
and integration with the GovmapClient.

Updated for Phase 4.1 - Pydantic models integration.
"""

import json
from unittest.mock import patch

from nadlan_mcp import fastmcp_server
from nadlan_mcp.govmap.models import (
    AutocompleteResponse,
    AutocompleteResult,
    CoordinatePoint,
    Deal,
    DealStatistics,
)


class TestAutocompleteAddress:
    """Test autocomplete_address MCP tool."""

    @patch("nadlan_mcp.fastmcp_server.client")
    def test_successful_autocomplete(self, mock_client):
        """Test successful address autocomplete with correct field mapping."""
        # Now returns AutocompleteResponse model
        mock_client.autocomplete_address.return_value = AutocompleteResponse(
            resultsCount=2,
            results=[
                AutocompleteResult(
                    id="address|ADDR|123",
                    text="דיזנגוף 50 תל אביב-יפו",
                    type="address",
                    score=100,
                    coordinates=CoordinatePoint(longitude=180000.5, latitude=650000.3),
                    shape="POINT(180000.5 650000.3)",
                ),
                AutocompleteResult(
                    id="address|ADDR|124",
                    text="דיזנגוף 52 תל אביב-יפו",
                    type="address",
                    score=95,
                    coordinates=CoordinatePoint(longitude=180010.2, latitude=650005.7),
                    shape="POINT(180010.2 650005.7)",
                ),
            ],
        )

        result = fastmcp_server.autocomplete_address("דיזנגוף תל אביב")
        parsed = json.loads(result)

        assert len(parsed) == 2
        assert parsed[0]["text"] == "דיזנגוף 50 תל אביב-יפו"
        assert parsed[0]["id"] == "address|ADDR|123"
        assert parsed[0]["score"] == 100
        assert parsed[0]["coordinates"]["longitude"] == 180000.5
        assert parsed[0]["coordinates"]["latitude"] == 650000.3

    @patch("nadlan_mcp.fastmcp_server.client")
    def test_autocomplete_no_results(self, mock_client):
        """Test autocomplete with no results."""
        # Now returns AutocompleteResponse model
        mock_client.autocomplete_address.return_value = AutocompleteResponse(
            resultsCount=0, results=[]
        )

        result = fastmcp_server.autocomplete_address("nonexistent address")
        # With empty results, returns a message string
        assert "No addresses found" in result

    @patch("nadlan_mcp.fastmcp_server.client")
    def test_autocomplete_invalid_coordinates(self, mock_client):
        """Test autocomplete with invalid/missing coordinate format."""
        # Now returns AutocompleteResponse model with result that has no coordinates
        mock_client.autocomplete_address.return_value = AutocompleteResponse(
            resultsCount=1,
            results=[
                AutocompleteResult(
                    id="address|ADDR|123",
                    text="דיזנגוף 50",
                    type="address",
                    score=100,
                    coordinates=None,  # No coordinates parsed
                    shape="INVALID_FORMAT",
                )
            ],
        )

        result = fastmcp_server.autocomplete_address("test")
        parsed = json.loads(result)
        # When coordinates are None, the field might be omitted or empty
        assert len(parsed) == 1
        assert parsed[0]["text"] == "דיזנגוף 50"

    @patch("nadlan_mcp.fastmcp_server.client")
    def test_autocomplete_missing_shape(self, mock_client):
        """Test autocomplete with missing shape field."""
        # Mock with AutocompleteResponse model
        mock_client.autocomplete_address.return_value = AutocompleteResponse(
            resultsCount=1,
            results=[
                AutocompleteResult(
                    id="address|ADDR|123",
                    text="דיזנגוף 50",
                    type="address",
                    score=100,
                    coordinates=None,  # No coordinates
                )
            ],
        )

        result = fastmcp_server.autocomplete_address("test")
        parsed = json.loads(result)
        # When coordinates are None, the field isn't included in the response
        assert "coordinates" not in parsed[0]

    @patch("nadlan_mcp.fastmcp_server.client")
    def test_autocomplete_error_handling(self, mock_client):
        """Test autocomplete error handling."""
        mock_client.autocomplete_address.side_effect = Exception("API Error")

        result = fastmcp_server.autocomplete_address("test")
        assert "Error searching for address" in result
        assert "API Error" in result


class TestGetDealsByRadius:
    """Test get_deals_by_radius MCP tool."""

    @patch("nadlan_mcp.fastmcp_server.client")
    def test_successful_get_deals(self, mock_client):
        """Test successful polygon metadata retrieval."""
        # Mock with polygon metadata dicts (not Deal objects)
        mock_polygons = [
            {
                "objectid": 123,
                "dealscount": "30",
                "settlementNameHeb": "תל אביב-יפו",
                "streetNameHeb": "דיזנגוף",
                "houseNum": 50,
                "polygon_id": "123-456",
            }
        ]
        mock_client.get_deals_by_radius.return_value = mock_polygons

        result = fastmcp_server.get_deals_by_radius(650000.0, 180000.0, 500)
        parsed = json.loads(result)

        assert len(parsed["polygons"]) == 1
        assert parsed["polygons"][0]["dealscount"] == "30"
        assert parsed["total_polygons"] == 1
        mock_client.get_deals_by_radius.assert_called_once()

    @patch("nadlan_mcp.fastmcp_server.client")
    def test_get_deals_no_results(self, mock_client):
        """Test polygon metadata retrieval with no results."""
        mock_client.get_deals_by_radius.return_value = []

        result = fastmcp_server.get_deals_by_radius(650000.0, 180000.0, 500)
        assert "No polygons found" in result

    @patch("nadlan_mcp.fastmcp_server.client")
    def test_get_deals_strips_bloat_fields(self, mock_client):
        """Test that polygon metadata is returned as-is."""
        # Mock with polygon metadata dicts
        mock_polygons = [
            {
                "objectid": 123,
                "dealscount": "10",
                "polygon_id": "abc123",
                "settlementNameHeb": "Tel Aviv",
            }
        ]
        mock_client.get_deals_by_radius.return_value = mock_polygons

        result = fastmcp_server.get_deals_by_radius(650000.0, 180000.0, 500)
        parsed = json.loads(result)

        # Polygon metadata is returned as-is (no stripping needed)
        polygon = parsed["polygons"][0]
        assert polygon["polygon_id"] == "abc123"
        assert polygon["dealscount"] == "10"

    @patch("nadlan_mcp.fastmcp_server.client")
    def test_get_deals_error_handling(self, mock_client):
        """Test error handling for deal retrieval."""
        mock_client.get_deals_by_radius.side_effect = ValueError("Invalid coordinates")

        result = fastmcp_server.get_deals_by_radius(999999.0, 999999.0, 500)
        assert "Error" in result


class TestFindRecentDealsForAddress:
    """Test find_recent_deals_for_address MCP tool."""

    @patch("nadlan_mcp.fastmcp_server.client")
    def test_successful_find_deals(self, mock_client):
        """Test successful deal finding with statistics."""
        # Mock with Deal models
        mock_deals = [
            Deal(
                objectid=123,
                deal_amount=2000000,
                deal_date="2023-01-01",
                asset_area=80.0,
                priority=0,
            ),
            Deal(
                objectid=124,
                deal_amount=1800000,
                deal_date="2023-01-02",
                asset_area=70.0,
                priority=1,
            ),
        ]
        mock_client.find_recent_deals_for_address.return_value = mock_deals

        result = fastmcp_server.find_recent_deals_for_address("דיזנגוף 50 תל אביב", 2, 100, 100)
        parsed = json.loads(result)

        assert "search_parameters" in parsed
        assert "market_statistics" in parsed
        assert "deals" in parsed
        assert len(parsed["deals"]) == 2
        assert parsed["market_statistics"]["deal_breakdown"]["total_deals"] == 2

    @patch("nadlan_mcp.fastmcp_server.client")
    def test_find_deals_no_results(self, mock_client):
        """Test deal finding with no results."""
        mock_client.find_recent_deals_for_address.return_value = []

        result = fastmcp_server.find_recent_deals_for_address("nonexistent address", 2, 100, 100)

        # When no deals, returns a text message, not JSON
        assert "No second hand (used) deals found" in result
        assert "nonexistent address" in result

    @patch("nadlan_mcp.fastmcp_server.client")
    def test_find_deals_strips_bloat(self, mock_client):
        """Test that bloat fields are stripped."""
        # Mock with Deal models
        mock_deals = [
            Deal(
                objectid=123,
                deal_amount=2000000,
                deal_date="2023-01-01",
                shape="MULTIPOLYGON(...)",
                sourceorder=1,
            )
        ]
        mock_client.find_recent_deals_for_address.return_value = mock_deals

        result = fastmcp_server.find_recent_deals_for_address("test address", 2, 100, 100)
        parsed = json.loads(result)

        assert "shape" not in parsed["deals"][0]
        assert "sourceorder" not in parsed["deals"][0]


class TestAnalyzeMarketTrends:
    """Test analyze_market_trends MCP tool."""

    @patch("nadlan_mcp.fastmcp_server.client")
    def test_successful_market_analysis(self, mock_client):
        """Test successful market trend analysis."""
        # Mock with Deal models
        mock_deals = [
            Deal(
                objectid=1,
                deal_amount=2000000,
                deal_date="2024-01-15",
                asset_area=80.0,
                property_type_description="דירה",
                neighborhood="תל אביב",
                priority=1,
            )
        ]
        mock_client.find_recent_deals_for_address.return_value = mock_deals

        result = fastmcp_server.analyze_market_trends("דיזנגוף 50 תל אביב", 2, 100)
        parsed = json.loads(result)

        assert "analysis_parameters" in parsed
        assert "market_summary" in parsed
        assert "yearly_trends" in parsed
        assert "top_property_types" in parsed

    @patch("nadlan_mcp.fastmcp_server.client")
    def test_market_analysis_no_data(self, mock_client):
        """Test market analysis with no data."""
        mock_client.find_recent_deals_for_address.return_value = []

        result = fastmcp_server.analyze_market_trends("test", 2, 100)

        # When no deals, returns a text message, not JSON
        assert "No second hand (used) deals found for comprehensive market analysis" in result
        assert "test" in result


class TestCompareAddresses:
    """Test compare_addresses MCP tool."""

    @patch("nadlan_mcp.fastmcp_server.client")
    def test_successful_comparison(self, mock_client):
        """Test successful address comparison."""
        # Mock different deals for each address
        mock_client.find_recent_deals_for_address.side_effect = [
            [{"dealAmount": 2000000, "assetArea": 80, "price_per_sqm": 25000}],
            [{"dealAmount": 1500000, "assetArea": 60, "price_per_sqm": 25000}],
        ]

        result = fastmcp_server.compare_addresses(["דיזנגוף 50 תל אביב", "הרצל 1 חולון"])
        parsed = json.loads(result)

        assert "addresses_compared" in parsed
        assert parsed["addresses_compared"] == 2
        assert "all_results" in parsed

    @patch("nadlan_mcp.fastmcp_server.client")
    def test_comparison_error_handling(self, mock_client):
        """Test error handling in address comparison."""
        mock_client.find_recent_deals_for_address.side_effect = ValueError("Invalid address")

        result = fastmcp_server.compare_addresses(["invalid address"])
        parsed = json.loads(result)
        # Error is included in the result for that address
        assert "all_results" in parsed
        assert "error" in parsed["all_results"][0]


class TestGetValuationComparables:
    """Test get_valuation_comparables MCP tool."""

    @patch("nadlan_mcp.fastmcp_server.client")
    def test_successful_get_comparables(self, mock_client):
        """Test successful comparable retrieval with filtering."""

        # Mock with Deal models
        mock_deals = [
            Deal(
                objectid=1,
                deal_amount=2000000,
                deal_date="2023-01-01",
                asset_area=80.0,
                rooms=3.0,
                property_type_description="דירה",
            )
        ]
        mock_stats = DealStatistics(
            total_deals=1,
            price_statistics={"mean": 2000000},
            area_statistics={"mean": 80},
            price_per_sqm_statistics={"mean": 25000},
        )
        mock_client.find_recent_deals_for_address.return_value = mock_deals
        mock_client.filter_deals_by_criteria.return_value = mock_deals
        mock_client.calculate_deal_statistics.return_value = mock_stats

        result = fastmcp_server.get_valuation_comparables(
            "דיזנגוף 50 תל אביב", property_type="דירה", min_rooms=2, max_rooms=4
        )
        parsed = json.loads(result)

        # Normalized structure: filters_applied is now in search_parameters
        assert "search_parameters" in parsed
        assert "filters_applied" in parsed["search_parameters"]
        assert parsed["search_parameters"]["filters_applied"]["property_type"] == "דירה"
        # Normalized structure: comparables -> deals
        assert "deals" in parsed
        assert "market_statistics" in parsed

    @patch("nadlan_mcp.fastmcp_server.client")
    def test_comparables_strips_bloat(self, mock_client):
        """Test that bloat fields are stripped from comparables."""

        # Mock with Deal models
        mock_deals = [
            Deal(
                objectid=1,
                deal_amount=2000000,
                deal_date="2023-01-01",
                shape="MULTIPOLYGON(...)",
                sourceorder=1,
                source_polygon_id="abc",
            )
        ]
        mock_stats = DealStatistics(total_deals=1, price_statistics={"mean": 2000000})
        mock_client.find_recent_deals_for_address.return_value = mock_deals
        mock_client.filter_deals_by_criteria.return_value = mock_deals
        mock_client.calculate_deal_statistics.return_value = mock_stats

        result = fastmcp_server.get_valuation_comparables("test address")
        parsed = json.loads(result)

        # Normalized structure: comparables -> deals
        comparable = parsed["deals"][0]
        assert "shape" not in comparable
        assert "sourceorder" not in comparable
        # source_polygon_id is kept when added by processing


class TestGetDealStatistics:
    """Test get_deal_statistics MCP tool."""

    @patch("nadlan_mcp.fastmcp_server.client")
    def test_successful_statistics_calculation(self, mock_client):
        """Test successful statistics calculation."""

        # Mock with Deal models
        mock_deals = [
            Deal(objectid=1, deal_amount=2000000, deal_date="2023-01-01", asset_area=80.0),
            Deal(objectid=2, deal_amount=1800000, deal_date="2023-01-02", asset_area=70.0),
        ]
        mock_stats = DealStatistics(
            total_deals=2,
            price_statistics={"mean": 1900000, "median": 1900000, "min": 1800000, "max": 2000000},
        )
        mock_client.find_recent_deals_for_address.return_value = mock_deals
        mock_client.filter_deals_by_criteria.return_value = mock_deals
        mock_client.calculate_deal_statistics.return_value = mock_stats

        result = fastmcp_server.get_deal_statistics("test address")
        parsed = json.loads(result)

        # Normalized structure: address is now in search_parameters, statistics -> market_statistics
        assert "search_parameters" in parsed
        assert "address" in parsed["search_parameters"]
        assert "market_statistics" in parsed
        assert "deal_breakdown" in parsed["market_statistics"]
        assert parsed["market_statistics"]["deal_breakdown"]["total_deals"] == 2


class TestGetMarketActivityMetrics:
    """Test get_market_activity_metrics MCP tool."""

    @patch("nadlan_mcp.fastmcp_server.client")
    def test_successful_activity_metrics(self, mock_client):
        """Test successful market activity calculation."""
        mock_deals = [
            {"dealDate": "2024-01-15T00:00:00.000Z", "dealAmount": 2000000, "assetArea": 80}
        ]
        mock_client.find_recent_deals_for_address.return_value = mock_deals
        mock_client.calculate_market_activity_score.return_value = {
            "activity_score": 75,
            "activity_level": "high",
        }
        mock_client.get_market_liquidity.return_value = {
            "velocity_score": 8.5,
            "liquidity_rating": "high",
        }
        mock_client.analyze_investment_potential.return_value = {
            "investment_score": 80,
            "recommendation": "positive",
        }

        result = fastmcp_server.get_market_activity_metrics("test address")
        parsed = json.loads(result)

        assert "market_activity" in parsed
        assert "market_liquidity" in parsed
        assert "investment_potential" in parsed


class TestGetStreetDeals:
    """Test get_street_deals MCP tool."""

    @patch("nadlan_mcp.fastmcp_server.client")
    def test_successful_street_deals(self, mock_client):
        """Test successful street deal retrieval."""
        # Mock with Deal models
        mock_deals = [Deal(objectid=123, deal_amount=2000000, deal_date="2023-01-01")]
        mock_client.get_street_deals.return_value = mock_deals

        result = fastmcp_server.get_street_deals("12345", 100)
        parsed = json.loads(result)

        assert len(parsed["deals"]) == 1
        assert "shape" not in parsed["deals"][0]


class TestGetNeighborhoodDeals:
    """Test get_neighborhood_deals MCP tool."""

    @patch("nadlan_mcp.fastmcp_server.client")
    def test_successful_neighborhood_deals(self, mock_client):
        """Test successful neighborhood deal retrieval."""
        # Mock with Deal models
        mock_deals = [Deal(objectid=123, deal_amount=2000000, deal_date="2023-01-01")]
        mock_client.get_neighborhood_deals.return_value = mock_deals

        result = fastmcp_server.get_neighborhood_deals("12345", 100)
        parsed = json.loads(result)

        assert len(parsed["deals"]) == 1
        assert "shape" not in parsed["deals"][0]
