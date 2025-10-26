"""
Tests for the GovmapClient class.

Updated for Phase 4.1 - Pydantic models integration.
"""

import pytest
import requests
from unittest.mock import Mock, patch
from nadlan_mcp.govmap import GovmapClient
from nadlan_mcp.govmap.models import Deal, AutocompleteResponse, AutocompleteResult
from nadlan_mcp.config import GovmapConfig


class TestGovmapClient:
    """Test cases for GovmapClient class."""
    
    def test_client_initialization(self):
        """Test that GovmapClient initializes correctly."""
        client = GovmapClient()
        assert client.base_url == "https://www.govmap.gov.il/api"
        assert client.session is not None
        assert client.session.headers['Content-Type'] == 'application/json'
        assert client.session.headers['User-Agent'] == 'NadlanMCP/1.0.0'
    
    def test_client_initialization_with_custom_url(self):
        """Test that GovmapClient can be initialized with custom URL."""
        custom_url = "https://custom-api.example.com/api/"
        custom_config = GovmapConfig(base_url=custom_url)
        client = GovmapClient(custom_config)
        assert client.base_url == "https://custom-api.example.com/api"
    
    @patch('requests.Session')
    def test_autocomplete_address_success(self, mock_session_class):
        """Test successful address autocomplete."""
        # Mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            "resultsCount": 1,
            "results": [
                {
                    "id": "address|ADDR|123|test",
                    "text": "תל אביב",
                    "type": "address",
                    "score": 100,
                    "shape": "POINT(3870000.123 3770000.456)",
                    "data": {}
                }
            ]
        }
        mock_response.raise_for_status.return_value = None

        mock_session = Mock()
        mock_session.post.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = GovmapClient()
        result = client.autocomplete_address("תל אביב")

        # Now returns AutocompleteResponse model
        assert isinstance(result, AutocompleteResponse)
        assert result.results_count == 1
        assert len(result.results) == 1
        assert result.results[0].text == "תל אביב"
        assert result.results[0].coordinates is not None
        assert result.results[0].coordinates.longitude == 3870000.123
        mock_session.post.assert_called_once()
    
    @patch('requests.Session')
    def test_autocomplete_address_empty_results(self, mock_session_class):
        """Test autocomplete with empty results - should return empty results, not raise error."""
        mock_response = Mock()
        mock_response.json.return_value = {"resultsCount": 0, "results": []}
        mock_response.raise_for_status.return_value = None

        mock_session = Mock()
        mock_session.post.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = GovmapClient()
        result = client.autocomplete_address("nonexistent")

        assert isinstance(result, AutocompleteResponse)
        assert result.results_count == 0
        assert len(result.results) == 0
    
    @patch('requests.Session')
    def test_autocomplete_address_invalid_response(self, mock_session_class):
        """Test autocomplete with truly invalid response format."""
        mock_response = Mock()
        mock_response.json.return_value = {"invalid": "response"}  # Missing 'results' key
        mock_response.raise_for_status.return_value = None
        
        mock_session = Mock()
        mock_session.post.return_value = mock_response
        mock_session_class.return_value = mock_session
        
        client = GovmapClient()
        
        with pytest.raises(ValueError, match="Invalid response format"):
            client.autocomplete_address("test")
    
    def test_coordinate_parsing_from_wkt_point(self):
        """Test coordinate parsing from WKT POINT format."""
        client = GovmapClient()
        
        # Mock the autocomplete response with WKT POINT
        mock_autocomplete_result = {
            "results": [
                {
                    "shape": "POINT(3870000.123 3770000.456)",
                    "text": "test address"
                }
            ]
        }
        
        # We'll test the coordinate parsing logic by calling the method that uses it
        with patch.object(client, 'autocomplete_address', return_value=mock_autocomplete_result):
            with patch.object(client, 'get_deals_by_radius', return_value=[]):
                with patch.object(client, 'get_street_deals', return_value=[]):
                    with patch.object(client, 'get_neighborhood_deals', return_value=[]):
                        result = client.find_recent_deals_for_address("test", years_back=1)
                        assert result == []
    
    @patch('requests.Session')
    def test_get_deals_by_radius_success(self, mock_session_class):
        """Test successful deals by radius query."""
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                "objectid": 12345,
                "dealAmount": 1500000.0,
                "dealDate": "2024-01-15",
                "settlementNameHeb": "תל אביב-יפו",
                "polygon_id": "123-456"
            }
        ]
        mock_response.raise_for_status.return_value = None

        mock_session = Mock()
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = GovmapClient()
        result = client.get_deals_by_radius((3870000.123, 3770000.456), radius=50)

        # Now returns List[Deal]
        assert len(result) == 1
        assert isinstance(result[0], Deal)
        assert result[0].objectid == 12345
        assert result[0].settlement_name_heb == "תל אביב-יפו"
        mock_session.get.assert_called_once()
    
    @patch('requests.Session')
    def test_get_street_deals_success(self, mock_session_class):
        """Test successful street deals query."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "totalCount": "1",
            "data": [
                {
                    "objectid": 123,
                    "dealAmount": 1000000,
                    "dealDate": "2025-01-01T00:00:00.000Z",
                    "assetArea": 100,
                    "settlementNameHeb": "תל אביב-יפו",
                    "propertyTypeDescription": "דירה"
                }
            ]
        }
        mock_response.raise_for_status.return_value = None
        
        mock_session = Mock()
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session
        
        client = GovmapClient()
        result = client.get_street_deals("123-456")

        # Now returns List[Deal]
        assert len(result) == 1
        assert isinstance(result[0], Deal)
        assert result[0].deal_amount == 1000000
        assert result[0].asset_area == 100
        assert result[0].price_per_sqm == 10000.0  # Computed field
        mock_session.get.assert_called_once()
    
    @patch('requests.Session')
    def test_get_neighborhood_deals_success(self, mock_session_class):
        """Test successful neighborhood deals query."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "totalCount": "1",
            "data": [
                {
                    "objectid": 456,
                    "dealAmount": 2000000,
                    "dealDate": "2025-01-15T00:00:00.000Z",
                    "assetArea": 120,
                    "settlementNameHeb": "תל אביב-יפו",
                    "propertyTypeDescription": "דירה"
                }
            ]
        }
        mock_response.raise_for_status.return_value = None
        
        mock_session = Mock()
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session
        
        client = GovmapClient()
        result = client.get_neighborhood_deals("123-456")

        # Now returns List[Deal]
        assert len(result) == 1
        assert isinstance(result[0], Deal)
        assert result[0].deal_amount == 2000000
        assert result[0].asset_area == 120
        assert result[0].price_per_sqm == round(2000000 / 120, 2)
        mock_session.get.assert_called_once()
    
    @patch('nadlan_mcp.main.GovmapClient.get_neighborhood_deals')
    @patch('nadlan_mcp.main.GovmapClient.get_street_deals')
    @patch('nadlan_mcp.main.GovmapClient.get_deals_by_radius')
    @patch('nadlan_mcp.main.GovmapClient.autocomplete_address')
    def test_find_recent_deals_for_address_integration(self, mock_autocomplete, mock_radius, mock_street, mock_neighborhood):
        """Test the main integration function."""
        # Mock autocomplete response
        mock_autocomplete.return_value = {
            "results": [
                {
                    "shape": "POINT(3870000.123 3770000.456)",
                    "text": "test address"
                }
            ]
        }
        
        # Mock radius response
        mock_radius.return_value = [
            {"polygon_id": "123-456", "objectid": 1}
        ]
        
        # Mock street deals response
        mock_street.return_value = [
            {
                "dealId": "deal1",
                "dealAmount": 1000000,
                "dealDate": "2025-01-01T00:00:00.000Z",
                "address": "Test Street 1",
                "priority": 1
            }
        ]

        # Mock neighborhood deals response
        mock_neighborhood.return_value = [
            {
                "dealId": "deal2",
                "dealAmount": 2000000,
                "dealDate": "2025-01-15T00:00:00.000Z",
                "address": "Test Street 2",
                "priority": 2
            }
        ]
        
        client = GovmapClient()
        result = client.find_recent_deals_for_address("test address", years_back=1)

        assert len(result) == 2
        # Should be sorted by priority first (street=1 before neighborhood=2), then by date
        assert result[0]["priority"] == 1  # Street deal comes first
        assert result[0]["dealDate"] == "2025-01-01T00:00:00.000Z"
        assert result[1]["priority"] == 2  # Neighborhood deal comes second
        assert result[1]["dealDate"] == "2025-01-15T00:00:00.000Z"
    
    @patch('requests.Session')
    def test_http_error_handling(self, mock_session_class):
        """Test that HTTP errors are properly handled."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = Exception("HTTP Error")
        
        mock_session = Mock()
        mock_session.post.return_value = mock_response
        mock_session_class.return_value = mock_session
        
        client = GovmapClient()
        
        with pytest.raises(Exception, match="HTTP Error"):
            client.autocomplete_address("test")
    
    def test_invalid_coordinate_format(self):
        """Test handling of invalid coordinate formats."""
        client = GovmapClient()
        
        # Mock autocomplete response with invalid shape
        mock_autocomplete_result = {
            "results": [
                {
                    "shape": "INVALID_FORMAT",
                    "text": "test address"
                }
            ]
        }
        
        with patch.object(client, 'autocomplete_address', return_value=mock_autocomplete_result):
            with pytest.raises(ValueError, match="Invalid coordinate format"):
                client.find_recent_deals_for_address("test", years_back=1)


class TestMarketAnalysisFunctions:
    """Test cases for market analysis functions."""

    def test_calculate_market_activity_score_success(self):
        """Test successful market activity score calculation."""
        client = GovmapClient()

        # Sample deals with dates
        deals = [
            {"dealDate": "2023-01-15", "dealAmount": 1000000},
            {"dealDate": "2023-01-20", "dealAmount": 1100000},
            {"dealDate": "2023-02-10", "dealAmount": 1200000},
            {"dealDate": "2023-03-05", "dealAmount": 1150000},
            {"dealDate": "2023-04-12", "dealAmount": 1250000},
        ]

        result = client.calculate_market_activity_score(deals, time_period_months=None)

        assert "total_deals" in result
        assert "deals_per_month" in result
        assert "activity_score" in result
        assert "activity_level" in result
        assert "trend" in result
        assert "monthly_distribution" in result
        assert result["total_deals"] == 5
        assert result["deals_per_month"] > 0
        assert 0 <= result["activity_score"] <= 100

    def test_calculate_market_activity_score_empty_deals(self):
        """Test market activity score with empty deals list."""
        client = GovmapClient()

        with pytest.raises(ValueError, match="Cannot calculate market activity from empty deals list"):
            client.calculate_market_activity_score([])

    def test_calculate_market_activity_score_invalid_dates(self):
        """Test market activity score with invalid dates."""
        client = GovmapClient()

        # Deals with invalid dates
        deals = [
            {"dealDate": "", "dealAmount": 1000000},
            {"dealAmount": 1100000},  # Missing dealDate
        ]

        with pytest.raises(ValueError, match="No valid deal dates found"):
            client.calculate_market_activity_score(deals)

    def test_calculate_market_activity_score_high_activity(self):
        """Test market activity score with high activity."""
        client = GovmapClient()

        # Generate many deals in short period (high activity)
        deals = [
            {"dealDate": f"2023-01-{i:02d}", "dealAmount": 1000000 + i * 10000}
            for i in range(1, 31)  # 30 deals in one month
        ]

        result = client.calculate_market_activity_score(deals, time_period_months=None)

        assert result["activity_level"] == "very_high"
        assert result["activity_score"] >= 90

    def test_analyze_investment_potential_success(self):
        """Test successful investment potential analysis."""
        client = GovmapClient()

        # Sample deals with price appreciation
        deals = [
            {"dealDate": "2022-01-15", "dealAmount": 1000000, "assetArea": 80, "price_per_sqm": 12500},
            {"dealDate": "2022-06-10", "dealAmount": 1050000, "assetArea": 80, "price_per_sqm": 13125},
            {"dealDate": "2023-01-05", "dealAmount": 1100000, "assetArea": 80, "price_per_sqm": 13750},
            {"dealDate": "2023-06-12", "dealAmount": 1150000, "assetArea": 80, "price_per_sqm": 14375},
        ]

        result = client.analyze_investment_potential(deals)

        assert "price_appreciation_rate" in result
        assert "price_volatility" in result
        assert "market_stability" in result
        assert "price_trend" in result
        assert "avg_price_per_sqm" in result
        assert "investment_score" in result
        assert "data_quality" in result
        assert 0 <= result["investment_score"] <= 100
        assert result["price_trend"] in ["increasing", "stable", "decreasing"]

    def test_analyze_investment_potential_empty_deals(self):
        """Test investment potential with empty deals list."""
        client = GovmapClient()

        with pytest.raises(ValueError, match="Cannot analyze investment potential from empty deals list"):
            client.analyze_investment_potential([])

    def test_analyze_investment_potential_insufficient_data(self):
        """Test investment potential with insufficient data."""
        client = GovmapClient()

        # Only 2 deals (need at least 3)
        deals = [
            {"dealDate": "2023-01-15", "dealAmount": 1000000, "assetArea": 80, "price_per_sqm": 12500},
            {"dealDate": "2023-06-10", "dealAmount": 1050000, "assetArea": 80, "price_per_sqm": 13125},
        ]

        with pytest.raises(ValueError, match="Insufficient data for investment analysis"):
            client.analyze_investment_potential(deals)

    def test_analyze_investment_potential_stable_market(self):
        """Test investment potential with stable market (low volatility)."""
        client = GovmapClient()

        # Deals with consistent prices (very stable)
        deals = [
            {"dealDate": f"2023-{i:02d}-15", "dealAmount": 1000000 + i * 1000, "assetArea": 80, "price_per_sqm": 12500 + i * 12.5}
            for i in range(1, 13)  # 12 months, slight increase
        ]

        result = client.analyze_investment_potential(deals)

        assert result["market_stability"] in ["very_stable", "stable"]
        assert result["price_volatility"] < 50

    def test_get_market_liquidity_success(self):
        """Test successful market liquidity calculation."""
        client = GovmapClient()

        # Sample deals across multiple quarters
        deals = [
            {"dealDate": "2023-01-15", "dealAmount": 1000000},
            {"dealDate": "2023-02-20", "dealAmount": 1100000},
            {"dealDate": "2023-05-10", "dealAmount": 1200000},
            {"dealDate": "2023-06-05", "dealAmount": 1150000},
            {"dealDate": "2023-09-12", "dealAmount": 1250000},
            {"dealDate": "2023-10-18", "dealAmount": 1300000},
        ]

        result = client.get_market_liquidity(deals, time_period_months=None)

        assert "total_deals" in result
        assert "deals_per_month" in result
        assert "deals_per_quarter" in result
        assert "quarterly_breakdown" in result
        assert "monthly_breakdown" in result
        assert "velocity_score" in result
        assert "liquidity_rating" in result
        assert "trend_direction" in result
        assert "most_active_period" in result
        assert result["total_deals"] == 6
        assert 0 <= result["velocity_score"] <= 100

    def test_get_market_liquidity_empty_deals(self):
        """Test market liquidity with empty deals list."""
        client = GovmapClient()

        with pytest.raises(ValueError, match="Cannot calculate market liquidity from empty deals list"):
            client.get_market_liquidity([])

    def test_get_market_liquidity_quarterly_breakdown(self):
        """Test market liquidity quarterly breakdown."""
        client = GovmapClient()

        # Deals spread across specific quarters
        deals = [
            {"dealDate": "2023-01-15"},  # Q1
            {"dealDate": "2023-02-20"},  # Q1
            {"dealDate": "2023-05-10"},  # Q2
            {"dealDate": "2023-08-05"},  # Q3
            {"dealDate": "2023-11-12"},  # Q4
        ]

        result = client.get_market_liquidity(deals, time_period_months=None)

        assert "2023-Q1" in result["quarterly_breakdown"]
        assert "2023-Q2" in result["quarterly_breakdown"]
        assert "2023-Q3" in result["quarterly_breakdown"]
        assert "2023-Q4" in result["quarterly_breakdown"]
        assert result["quarterly_breakdown"]["2023-Q1"] == 2

    def test_filter_deals_by_criteria_property_type(self):
        """Test filtering deals by property type."""
        client = GovmapClient()

        deals = [
            {"assetTypeHeb": "דירה", "roomsNum": 3, "dealAmount": 1000000},
            {"assetTypeHeb": "בית", "roomsNum": 5, "dealAmount": 2000000},
            {"assetTypeHeb": "דירה", "roomsNum": 4, "dealAmount": 1500000},
        ]

        filtered = client.filter_deals_by_criteria(deals, property_type="דירה")

        assert len(filtered) == 2
        assert all(d["assetTypeHeb"] == "דירה" for d in filtered)

    def test_filter_deals_by_criteria_rooms(self):
        """Test filtering deals by room count."""
        client = GovmapClient()

        deals = [
            {"assetRoomNum": 2, "dealAmount": 800000},
            {"assetRoomNum": 3, "dealAmount": 1000000},
            {"assetRoomNum": 4, "dealAmount": 1500000},
            {"assetRoomNum": 5, "dealAmount": 2000000},
        ]

        filtered = client.filter_deals_by_criteria(deals, min_rooms=3, max_rooms=4)

        assert len(filtered) == 2
        assert all(3 <= d["assetRoomNum"] <= 4 for d in filtered)

    def test_filter_deals_by_criteria_price_range(self):
        """Test filtering deals by price range."""
        client = GovmapClient()

        deals = [
            {"dealAmount": 800000},
            {"dealAmount": 1000000},
            {"dealAmount": 1500000},
            {"dealAmount": 2000000},
        ]

        filtered = client.filter_deals_by_criteria(deals, min_price=900000, max_price=1600000)

        assert len(filtered) == 2
        assert all(900000 <= d["dealAmount"] <= 1600000 for d in filtered)

    def test_calculate_deal_statistics_success(self):
        """Test successful deal statistics calculation."""
        client = GovmapClient()

        deals = [
            {"dealAmount": 1000000, "assetArea": 80, "price_per_sqm": 12500, "assetRoomNum": 3},
            {"dealAmount": 1200000, "assetArea": 90, "price_per_sqm": 13333, "assetRoomNum": 4},
            {"dealAmount": 900000, "assetArea": 70, "price_per_sqm": 12857, "assetRoomNum": 3},
        ]

        stats = client.calculate_deal_statistics(deals)

        assert "count" in stats
        assert "price_stats" in stats
        assert "area_stats" in stats
        assert "price_per_sqm_stats" in stats
        assert stats["count"] == 3
        assert stats["price_stats"]["mean"] > 0
        assert stats["area_stats"]["mean"] == pytest.approx(80.0)

    def test_is_same_building_comparisons(self):
        """Test `_is_same_building` correctly compares address strings."""
        client = GovmapClient()

        # Test that _is_same_building works with addresses constructed from API fields
        search_address = "חנקין 62"

        # Deal from same building (should match)
        deal_address_same = "חנקין 62"
        assert client._is_same_building(search_address, deal_address_same) is True

        # Deal from different building on same street (should not match)
        deal_address_different = "חנקין 50"
        assert client._is_same_building(search_address, deal_address_different) is False

        # Deal from different street (should not match)
        deal_address_other_street = "בילינסון 6"
        assert client._is_same_building(search_address, deal_address_other_street) is False

    def test_filter_excludes_missing_property_type(self):
        """Test that deals with missing property type are excluded when filter is active."""
        client = GovmapClient()
        deals = [
            {"dealId": "1", "propertyTypeDescription": "דירה"},
            {"dealId": "2", "propertyTypeDescription": None},
            {"dealId": "3", "propertyTypeDescription": "בית"},
            {"dealId": "4"},  # Missing key entirely
        ]

        filtered = client.filter_deals_by_criteria(deals, property_type="דירה")

        assert len(filtered) == 1
        assert filtered[0]["dealId"] == "1"

    def test_filter_excludes_missing_area(self):
        """Test that deals with missing area are excluded when area filter is active."""
        client = GovmapClient()
        deals = [
            {"dealId": "1", "assetArea": 65},
            {"dealId": "2", "assetArea": None},
            {"dealId": "3", "assetArea": 50},
            {"dealId": "4"},  # Missing key entirely
        ]

        filtered = client.filter_deals_by_criteria(deals, min_area=60, max_area=70)

        assert len(filtered) == 1
        assert filtered[0]["dealId"] == "1"

    def test_filter_excludes_missing_rooms(self):
        """Test that deals with missing room count are excluded when room filter is active."""
        client = GovmapClient()
        deals = [
            {"dealId": "1", "assetRoomNum": 3},
            {"dealId": "2", "assetRoomNum": None},
            {"dealId": "3", "assetRoomNum": 2},
            {"dealId": "4"},  # Missing key entirely
        ]

        filtered = client.filter_deals_by_criteria(deals, min_rooms=2.5, max_rooms=4)

        assert len(filtered) == 1
        assert filtered[0]["dealId"] == "1"

    def test_filter_excludes_missing_price(self):
        """Test that deals with missing price are excluded when price filter is active."""
        client = GovmapClient()
        deals = [
            {"dealId": "1", "dealAmount": 2000000},
            {"dealId": "2", "dealAmount": None},
            {"dealId": "3", "dealAmount": 1500000},
            {"dealId": "4"},  # Missing key entirely
        ]

        filtered = client.filter_deals_by_criteria(deals, min_price=1800000, max_price=2200000)

        assert len(filtered) == 1
        assert filtered[0]["dealId"] == "1"

    def test_filter_excludes_invalid_numeric_data(self):
        """Test that deals with invalid numeric data are excluded when filter is active."""
        client = GovmapClient()
        deals = [
            {"dealId": "1", "assetArea": 65, "assetRoomNum": 3, "dealAmount": 2000000},
            {"dealId": "2", "assetArea": "invalid", "assetRoomNum": 3, "dealAmount": 2000000},
            {"dealId": "3", "assetArea": 65, "assetRoomNum": "bad", "dealAmount": 2000000},
            {"dealId": "4", "assetArea": 65, "assetRoomNum": 3, "dealAmount": "wrong"},
        ]

        # Area filter should exclude deal 2
        filtered_area = client.filter_deals_by_criteria(deals, min_area=60, max_area=70)
        assert len(filtered_area) == 3
        assert all(d["dealId"] in ["1", "3", "4"] for d in filtered_area)

        # Room filter should exclude deal 3
        filtered_rooms = client.filter_deals_by_criteria(deals, min_rooms=2, max_rooms=4)
        assert len(filtered_rooms) == 3
        assert all(d["dealId"] in ["1", "2", "4"] for d in filtered_rooms)

        # Price filter should exclude deal 4
        filtered_price = client.filter_deals_by_criteria(deals, min_price=1500000, max_price=2500000)
        assert len(filtered_price) == 3
        assert all(d["dealId"] in ["1", "2", "3"] for d in filtered_price)

    def test_filter_allows_missing_data_when_no_filter(self):
        """Test that deals with missing data pass through when no filter is active for that field."""
        client = GovmapClient()
        deals = [
            {"dealId": "1", "propertyTypeDescription": "דירה", "assetArea": 65},
            {"dealId": "2", "propertyTypeDescription": "דירה", "assetArea": None},
            {"dealId": "3", "propertyTypeDescription": "דירה"},  # Missing assetArea entirely
        ]

        # Filter by property type only - missing area should pass through
        filtered = client.filter_deals_by_criteria(deals, property_type="דירה")

        assert len(filtered) == 3  # All should pass since we're not filtering by area
