"""
E2E tests for FastMCP tools.

Tests the MCP tool layer including JSON formatting, error handling,
and integration with the GovmapClient.
"""

import json
import pytest
from unittest.mock import Mock, patch
from nadlan_mcp import fastmcp_server


class TestAutocompleteAddress:
    """Test autocomplete_address MCP tool."""

    @patch('nadlan_mcp.fastmcp_server.client')
    def test_successful_autocomplete(self, mock_client):
        """Test successful address autocomplete with correct field mapping."""
        mock_client.autocomplete_address.return_value = {
            "resultsCount": 2,
            "results": [
                {
                    "id": "address|ADDR|123",
                    "text": "דיזנגוף 50 תל אביב-יפו",
                    "type": "address",
                    "score": 100,
                    "shape": "POINT(180000.5 650000.3)"
                },
                {
                    "id": "address|ADDR|124",
                    "text": "דיזנגוף 52 תל אביב-יפו",
                    "type": "address",
                    "score": 95,
                    "shape": "POINT(180010.2 650005.7)"
                }
            ]
        }

        result = fastmcp_server.autocomplete_address("דיזנגוף תל אביב")
        parsed = json.loads(result)

        assert len(parsed) == 2
        assert parsed[0]["text"] == "דיזנגוף 50 תל אביב-יפו"
        assert parsed[0]["id"] == "address|ADDR|123"
        assert parsed[0]["score"] == 100
        assert parsed[0]["coordinates"]["longitude"] == 180000.5
        assert parsed[0]["coordinates"]["latitude"] == 650000.3

    @patch('nadlan_mcp.fastmcp_server.client')
    def test_autocomplete_no_results(self, mock_client):
        """Test autocomplete with no results."""
        mock_client.autocomplete_address.return_value = {
            "resultsCount": 0,
            "results": []
        }

        result = fastmcp_server.autocomplete_address("nonexistent address")
        # With empty results, returns empty JSON array
        parsed = json.loads(result)
        assert len(parsed) == 0

    @patch('nadlan_mcp.fastmcp_server.client')
    def test_autocomplete_invalid_coordinates(self, mock_client):
        """Test autocomplete with invalid coordinate format."""
        mock_client.autocomplete_address.return_value = {
            "resultsCount": 1,
            "results": [
                {
                    "id": "address|ADDR|123",
                    "text": "דיזנגוף 50",
                    "type": "address",
                    "score": 100,
                    "shape": "INVALID_FORMAT"
                }
            ]
        }

        result = fastmcp_server.autocomplete_address("test")
        parsed = json.loads(result)
        assert parsed[0]["coordinates"] == {}

    @patch('nadlan_mcp.fastmcp_server.client')
    def test_autocomplete_missing_shape(self, mock_client):
        """Test autocomplete with missing shape field."""
        mock_client.autocomplete_address.return_value = {
            "resultsCount": 1,
            "results": [
                {
                    "id": "address|ADDR|123",
                    "text": "דיזנגוף 50",
                    "type": "address",
                    "score": 100
                    # No shape field
                }
            ]
        }

        result = fastmcp_server.autocomplete_address("test")
        parsed = json.loads(result)
        assert parsed[0]["coordinates"] == {}

    @patch('nadlan_mcp.fastmcp_server.client')
    def test_autocomplete_error_handling(self, mock_client):
        """Test autocomplete error handling."""
        mock_client.autocomplete_address.side_effect = Exception("API Error")

        result = fastmcp_server.autocomplete_address("test")
        assert "Error searching for address" in result
        assert "API Error" in result


class TestGetDealsByRadius:
    """Test get_deals_by_radius MCP tool."""

    @patch('nadlan_mcp.fastmcp_server.client')
    def test_successful_get_deals(self, mock_client):
        """Test successful deal retrieval."""
        mock_deals = [
            {
                "dealId": 123,
                "dealAmount": 2000000,
                "assetArea": 80,
                "streetNameHeb": "דיזנגוף"
            }
        ]
        mock_client.get_deals_by_radius.return_value = mock_deals

        result = fastmcp_server.get_deals_by_radius(650000.0, 180000.0, 500)
        parsed = json.loads(result)

        assert len(parsed["deals"]) == 1
        assert parsed["deals"][0]["dealAmount"] == 2000000
        assert parsed["total_deals"] == 1
        mock_client.get_deals_by_radius.assert_called_once()

    @patch('nadlan_mcp.fastmcp_server.client')
    def test_get_deals_no_results(self, mock_client):
        """Test deal retrieval with no results."""
        mock_client.get_deals_by_radius.return_value = []

        result = fastmcp_server.get_deals_by_radius(650000.0, 180000.0, 500)
        assert "No deals found" in result or json.loads(result)["total_deals"] == 0

    @patch('nadlan_mcp.fastmcp_server.client')
    def test_get_deals_strips_bloat_fields(self, mock_client):
        """Test that bloat fields are stripped from response."""
        mock_deals = [
            {
                "dealId": 123,
                "dealAmount": 2000000,
                "shape": "MULTIPOLYGON(...huge data...)",
                "sourceorder": 1,
                "source_polygon_id": "abc123"
            }
        ]
        mock_client.get_deals_by_radius.return_value = mock_deals

        result = fastmcp_server.get_deals_by_radius(650000.0, 180000.0, 500)
        parsed = json.loads(result)

        # Verify bloat fields are removed
        deal = parsed["deals"][0]
        assert "shape" not in deal
        assert "sourceorder" not in deal
        assert "source_polygon_id" not in deal

    @patch('nadlan_mcp.fastmcp_server.client')
    def test_get_deals_error_handling(self, mock_client):
        """Test error handling for deal retrieval."""
        mock_client.get_deals_by_radius.side_effect = ValueError("Invalid coordinates")

        result = fastmcp_server.get_deals_by_radius(999999.0, 999999.0, 500)
        assert "Error" in result


class TestFindRecentDealsForAddress:
    """Test find_recent_deals_for_address MCP tool."""

    @patch('nadlan_mcp.fastmcp_server.client')
    def test_successful_find_deals(self, mock_client):
        """Test successful deal finding with statistics."""
        mock_deals = [
            {
                "dealId": 123,
                "dealAmount": 2000000,
                "assetArea": 80,
                "price_per_sqm": 25000,
                "priority": 0,
                "deal_source": "same_building"
            },
            {
                "dealId": 124,
                "dealAmount": 1800000,
                "assetArea": 70,
                "price_per_sqm": 25714,
                "priority": 1,
                "deal_source": "street"
            }
        ]
        mock_client.find_recent_deals_for_address.return_value = mock_deals

        result = fastmcp_server.find_recent_deals_for_address(
            "דיזנגוף 50 תל אביב", 2, 100, 100
        )
        parsed = json.loads(result)

        assert "search_parameters" in parsed
        assert "market_statistics" in parsed
        assert "deals" in parsed
        assert len(parsed["deals"]) == 2
        assert parsed["market_statistics"]["deal_breakdown"]["total_deals"] == 2

    @patch('nadlan_mcp.fastmcp_server.client')
    def test_find_deals_no_results(self, mock_client):
        """Test deal finding with no results."""
        mock_client.find_recent_deals_for_address.return_value = []

        result = fastmcp_server.find_recent_deals_for_address(
            "nonexistent address", 2, 100, 100
        )

        # When no deals, returns a text message, not JSON
        assert "No second hand (used) deals found" in result
        assert "nonexistent address" in result

    @patch('nadlan_mcp.fastmcp_server.client')
    def test_find_deals_strips_bloat(self, mock_client):
        """Test that bloat fields are stripped."""
        mock_deals = [
            {
                "dealId": 123,
                "dealAmount": 2000000,
                "shape": "MULTIPOLYGON(...)",
                "sourceorder": 1
            }
        ]
        mock_client.find_recent_deals_for_address.return_value = mock_deals

        result = fastmcp_server.find_recent_deals_for_address(
            "test address", 2, 100, 100
        )
        parsed = json.loads(result)

        assert "shape" not in parsed["deals"][0]
        assert "sourceorder" not in parsed["deals"][0]


class TestAnalyzeMarketTrends:
    """Test analyze_market_trends MCP tool."""

    @patch('nadlan_mcp.fastmcp_server.client')
    def test_successful_market_analysis(self, mock_client):
        """Test successful market trend analysis."""
        mock_deals = [
            {
                "dealAmount": 2000000,
                "assetArea": 80,
                "price_per_sqm": 25000,
                "dealDate": "2024-01-15T00:00:00.000Z",
                "propertyTypeDescription": "דירה",
                "neighborhood": "תל אביב",
                "priority": 1
            }
        ]
        mock_client.find_recent_deals_for_address.return_value = mock_deals

        result = fastmcp_server.analyze_market_trends("דיזנגוף 50 תל אביב", 2, 100)
        parsed = json.loads(result)

        assert "analysis_parameters" in parsed
        assert "market_summary" in parsed
        assert "yearly_trends" in parsed
        assert "top_property_types" in parsed

    @patch('nadlan_mcp.fastmcp_server.client')
    def test_market_analysis_no_data(self, mock_client):
        """Test market analysis with no data."""
        mock_client.find_recent_deals_for_address.return_value = []

        result = fastmcp_server.analyze_market_trends("test", 2, 100)

        # When no deals, returns a text message, not JSON
        assert "No second hand (used) deals found for comprehensive market analysis" in result
        assert "test" in result


class TestCompareAddresses:
    """Test compare_addresses MCP tool."""

    @patch('nadlan_mcp.fastmcp_server.client')
    def test_successful_comparison(self, mock_client):
        """Test successful address comparison."""
        # Mock different deals for each address
        mock_client.find_recent_deals_for_address.side_effect = [
            [{"dealAmount": 2000000, "assetArea": 80, "price_per_sqm": 25000}],
            [{"dealAmount": 1500000, "assetArea": 60, "price_per_sqm": 25000}]
        ]

        result = fastmcp_server.compare_addresses(
            ["דיזנגוף 50 תל אביב", "הרצל 1 חולון"]
        )
        parsed = json.loads(result)

        assert "addresses_compared" in parsed
        assert parsed["addresses_compared"] == 2
        assert "all_results" in parsed

    @patch('nadlan_mcp.fastmcp_server.client')
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

    @patch('nadlan_mcp.fastmcp_server.client')
    def test_successful_get_comparables(self, mock_client):
        """Test successful comparable retrieval with filtering."""
        mock_deals = [
            {
                "dealAmount": 2000000,
                "assetArea": 80,
                "assetRoomNum": 3,
                "propertyTypeDescription": "דירה",
                "price_per_sqm": 25000
            }
        ]
        mock_client.find_recent_deals_for_address.return_value = mock_deals
        mock_client.filter_deals_by_criteria.return_value = mock_deals
        mock_client.calculate_deal_statistics.return_value = {
            "count": 1,
            "price_stats": {"mean": 2000000},
            "area_stats": {"mean": 80},
            "price_per_sqm_stats": {"mean": 25000}
        }

        result = fastmcp_server.get_valuation_comparables(
            "דיזנגוף 50 תל אביב",
            property_type="דירה",
            min_rooms=2,
            max_rooms=4
        )
        parsed = json.loads(result)

        assert "filters_applied" in parsed
        assert "statistics" in parsed
        assert "comparables" in parsed
        assert parsed["filters_applied"]["property_type"] == "דירה"

    @patch('nadlan_mcp.fastmcp_server.client')
    def test_comparables_strips_bloat(self, mock_client):
        """Test that bloat fields are stripped from comparables."""
        mock_deals = [
            {
                "dealAmount": 2000000,
                "shape": "MULTIPOLYGON(...)",
                "sourceorder": 1,
                "source_polygon_id": "abc"
            }
        ]
        mock_client.find_recent_deals_for_address.return_value = mock_deals
        mock_client.filter_deals_by_criteria.return_value = mock_deals
        mock_client.calculate_deal_statistics.return_value = {
            "count": 1,
            "price_stats": {"mean": 2000000}
        }

        result = fastmcp_server.get_valuation_comparables("test address")
        parsed = json.loads(result)

        comparable = parsed["comparables"][0]
        assert "shape" not in comparable
        assert "sourceorder" not in comparable
        assert "source_polygon_id" not in comparable


class TestGetDealStatistics:
    """Test get_deal_statistics MCP tool."""

    @patch('nadlan_mcp.fastmcp_server.client')
    def test_successful_statistics_calculation(self, mock_client):
        """Test successful statistics calculation."""
        mock_deals = [
            {"dealAmount": 2000000, "assetArea": 80},
            {"dealAmount": 1800000, "assetArea": 70}
        ]
        mock_client.find_recent_deals_for_address.return_value = mock_deals
        mock_client.filter_deals_by_criteria.return_value = mock_deals
        mock_client.calculate_deal_statistics.return_value = {
            "count": 2,
            "price_stats": {
                "mean": 1900000,
                "median": 1900000,
                "min": 1800000,
                "max": 2000000
            }
        }

        result = fastmcp_server.get_deal_statistics("test address")
        parsed = json.loads(result)

        assert "address" in parsed
        assert "statistics" in parsed
        assert parsed["statistics"]["count"] == 2


class TestGetMarketActivityMetrics:
    """Test get_market_activity_metrics MCP tool."""

    @patch('nadlan_mcp.fastmcp_server.client')
    def test_successful_activity_metrics(self, mock_client):
        """Test successful market activity calculation."""
        mock_deals = [
            {
                "dealDate": "2024-01-15T00:00:00.000Z",
                "dealAmount": 2000000,
                "assetArea": 80
            }
        ]
        mock_client.find_recent_deals_for_address.return_value = mock_deals
        mock_client.calculate_market_activity_score.return_value = {
            "activity_score": 75,
            "activity_level": "high"
        }
        mock_client.get_market_liquidity.return_value = {
            "velocity_score": 8.5,
            "liquidity_rating": "high"
        }
        mock_client.analyze_investment_potential.return_value = {
            "investment_score": 80,
            "recommendation": "positive"
        }

        result = fastmcp_server.get_market_activity_metrics("test address")
        parsed = json.loads(result)

        assert "market_activity" in parsed
        assert "market_liquidity" in parsed
        assert "investment_potential" in parsed


class TestGetStreetDeals:
    """Test get_street_deals MCP tool."""

    @patch('nadlan_mcp.fastmcp_server.client')
    def test_successful_street_deals(self, mock_client):
        """Test successful street deal retrieval."""
        mock_deals = [
            {"dealId": 123, "dealAmount": 2000000}
        ]
        mock_client.get_street_deals.return_value = mock_deals

        result = fastmcp_server.get_street_deals("12345", 100)
        parsed = json.loads(result)

        assert len(parsed["deals"]) == 1
        assert "shape" not in parsed["deals"][0]


class TestGetNeighborhoodDeals:
    """Test get_neighborhood_deals MCP tool."""

    @patch('nadlan_mcp.fastmcp_server.client')
    def test_successful_neighborhood_deals(self, mock_client):
        """Test successful neighborhood deal retrieval."""
        mock_deals = [
            {"dealId": 123, "dealAmount": 2000000}
        ]
        mock_client.get_neighborhood_deals.return_value = mock_deals

        result = fastmcp_server.get_neighborhood_deals("12345", 100)
        parsed = json.loads(result)

        assert len(parsed["deals"]) == 1
        assert "shape" not in parsed["deals"][0]
