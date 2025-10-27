"""
Tests for the GovmapClient class.

Updated for Phase 4.1 - Pydantic models integration.
"""

import pytest
import requests
from unittest.mock import Mock, patch
from nadlan_mcp.govmap import GovmapClient
from nadlan_mcp.govmap.models import Deal, AutocompleteResponse, AutocompleteResult, CoordinatePoint
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

        # Mock the autocomplete response with WKT POINT - now returns AutocompleteResponse model
        mock_autocomplete_result = AutocompleteResponse(
            resultsCount=1,
            results=[
                AutocompleteResult(
                    id="addr123",
                    text="test address",
                    type="address",
                    shape="POINT(3870000.123 3770000.456)",
                    coordinates=CoordinatePoint(longitude=3870000.123, latitude=3770000.456)
                )
            ]
        )

        # We'll test the coordinate parsing logic by calling the method that uses it
        with patch.object(client, 'autocomplete_address', return_value=mock_autocomplete_result):
            with patch.object(client, 'get_deals_by_radius', return_value=[]):
                with patch.object(client, 'get_street_deals', return_value=[]):
                    with patch.object(client, 'get_neighborhood_deals', return_value=[]):
                        result = client.find_recent_deals_for_address("test", years_back=1)
                        assert result == []
    
    @patch('requests.Session')
    def test_get_deals_by_radius_success(self, mock_session_class):
        """Test successful polygon metadata retrieval by radius."""
        mock_response = Mock()
        # API returns polygon metadata (not actual deals)
        mock_response.json.return_value = [
            {
                "objectid": 12345,
                "dealscount": "30",
                "settlementNameHeb": "תל אביב-יפו",
                "streetNameHeb": "דיזנגוף",
                "houseNum": 50,
                "polygon_id": "123-456"
            }
        ]
        mock_response.raise_for_status.return_value = None

        mock_session = Mock()
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = GovmapClient()
        result = client.get_deals_by_radius((3870000.123, 3770000.456), radius=50)

        # Now returns List[Dict] - polygon metadata, not Deal objects
        assert len(result) == 1
        assert isinstance(result[0], dict)
        assert result[0]["objectid"] == 12345
        assert result[0]["polygon_id"] == "123-456"
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
    
    @patch('nadlan_mcp.govmap.client.GovmapClient.get_neighborhood_deals')
    @patch('nadlan_mcp.govmap.client.GovmapClient.get_street_deals')
    @patch('nadlan_mcp.govmap.client.GovmapClient.get_deals_by_radius')
    @patch('nadlan_mcp.govmap.client.GovmapClient.autocomplete_address')
    def test_find_recent_deals_for_address_integration(self, mock_autocomplete, mock_radius, mock_street, mock_neighborhood):
        """Test the main integration function."""
        from nadlan_mcp.govmap.models import CoordinatePoint, AutocompleteResult, AutocompleteResponse

        # Mock autocomplete response - now returns AutocompleteResponse model
        mock_autocomplete.return_value = AutocompleteResponse(
            resultsCount=1,
            results=[
                AutocompleteResult(
                    text="test address",
                    id="addr123",
                    type="address",
                    coordinates=CoordinatePoint(longitude=3870000.123, latitude=3770000.456),
                    shape="POINT(3870000.123 3770000.456)"
                )
            ]
        )

        # Mock radius response - now returns List[Dict] (polygon metadata)
        mock_radius.return_value = [
            {"objectid": 1, "dealscount": "10", "polygon_id": "123-456", "settlementNameHeb": "Tel Aviv"}
        ]

        # Mock street deals response - now returns List[Deal]
        mock_street.return_value = [
            Deal(
                objectid=101,
                deal_amount=1000000,
                deal_date="2025-01-01T00:00:00.000Z",
                street_name="Test Street",
                house_number="1"
            )
        ]

        # Mock neighborhood deals response - now returns List[Deal]
        mock_neighborhood.return_value = [
            Deal(
                objectid=102,
                deal_amount=2000000,
                deal_date="2025-01-15T00:00:00.000Z",
                street_name="Test Street",
                house_number="2"
            )
        ]

        client = GovmapClient()
        result = client.find_recent_deals_for_address("test address", years_back=1)

        # Now returns List[Deal]
        assert len(result) == 2
        assert isinstance(result[0], Deal)
        assert isinstance(result[1], Deal)

        # Should be sorted by priority first (street=1 before neighborhood=2), then by date
        # Priority is set dynamically by find_recent_deals_for_address
        assert hasattr(result[0], 'priority')
        assert hasattr(result[1], 'priority')
        assert result[0].priority <= result[1].priority  # Lower priority comes first
    
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

        # Mock autocomplete response with invalid shape - now returns AutocompleteResponse model
        mock_autocomplete_result = AutocompleteResponse(
            resultsCount=1,
            results=[
                AutocompleteResult(
                    id="addr123",
                    text="test address",
                    type="address",
                    shape="INVALID_FORMAT",  # Invalid format
                    coordinates=None  # No coordinates
                )
            ]
        )

        with patch.object(client, 'autocomplete_address', return_value=mock_autocomplete_result):
            with pytest.raises(ValueError, match="No coordinates found"):
                client.find_recent_deals_for_address("test", years_back=1)


class TestMarketAnalysisFunctions:
    """Test cases for market analysis functions."""

    def test_calculate_market_activity_score_success(self):
        """Test successful market activity score calculation."""
        from nadlan_mcp.govmap.models import MarketActivityScore
        client = GovmapClient()

        # Sample deals with dates - now using Deal models
        deals = [
            Deal(objectid=i, deal_date=date, deal_amount=amount)
            for i, (date, amount) in enumerate([
                ("2023-01-15", 1000000),
                ("2023-01-20", 1100000),
                ("2023-02-10", 1200000),
                ("2023-03-05", 1150000),
                ("2023-04-12", 1250000),
            ])
        ]

        result = client.calculate_market_activity_score(deals, time_period_months=None)

        # Now returns MarketActivityScore model
        assert isinstance(result, MarketActivityScore)
        assert result.total_deals == 5
        assert result.deals_per_month > 0
        assert 0 <= result.activity_score <= 100
        assert result.trend in ["increasing", "stable", "decreasing"]
        assert isinstance(result.monthly_distribution, dict)

    def test_calculate_market_activity_score_empty_deals(self):
        """Test market activity score with empty deals list."""
        client = GovmapClient()

        with pytest.raises(ValueError, match="Cannot calculate market activity from empty deals list"):
            client.calculate_market_activity_score([])

    def test_calculate_market_activity_score_with_time_filter(self):
        """Test market activity score with time period filtering."""
        # Note: With Pydantic models, deal_date is required and validated
        from datetime import datetime, timedelta
        from nadlan_mcp.govmap.models import MarketActivityScore
        client = GovmapClient()

        # Create deals spanning several months using recent dates
        today = datetime.now()
        deals = [
            Deal(
                objectid=i,
                deal_date=(today - timedelta(days=30 * month)).strftime("%Y-%m-%d"),
                deal_amount=1000000 + i * 10000
            )
            for i, month in enumerate([1, 1, 2, 3, 3, 3, 6, 11], 1)  # All within last 12 months
        ]

        # Get activity score with default 12-month filter
        result = client.calculate_market_activity_score(deals)
        assert isinstance(result, MarketActivityScore)
        assert result.total_deals == 8

    def test_calculate_market_activity_score_high_activity(self):
        """Test market activity score with high activity."""
        client = GovmapClient()

        # Generate many deals across multiple months for trend analysis - now using Deal models
        deals = [
            Deal(objectid=i, deal_date=f"2023-{(i % 6) + 1:02d}-15", deal_amount=1000000 + i * 10000)
            for i in range(1, 31)  # 30 deals spread across 6 months
        ]

        result = client.calculate_market_activity_score(deals, time_period_months=None)

        # Result is now a MarketActivityScore model
        assert result.trend in ["stable", "increasing", "decreasing"]  # Any valid trend
        assert result.activity_score >= 50  # High activity (5 deals/month)

    def test_analyze_investment_potential_success(self):
        """Test successful investment potential analysis."""
        from nadlan_mcp.govmap.models import InvestmentAnalysis
        client = GovmapClient()

        # Sample deals with price appreciation - now using Deal models
        # Note: price_per_sqm is computed automatically from deal_amount / asset_area
        deals = [
            Deal(objectid=i, deal_date=date, deal_amount=amount, asset_area=80.0)
            for i, (date, amount) in enumerate([
                ("2022-01-15", 1000000),
                ("2022-06-10", 1050000),
                ("2023-01-05", 1100000),
                ("2023-06-12", 1150000),
            ])
        ]

        result = client.analyze_investment_potential(deals)

        # Now returns InvestmentAnalysis model
        assert isinstance(result, InvestmentAnalysis)
        assert hasattr(result, 'price_appreciation_rate')
        assert hasattr(result, 'price_volatility')
        assert hasattr(result, 'market_stability')
        assert hasattr(result, 'price_trend')
        assert hasattr(result, 'avg_price_per_sqm')
        assert hasattr(result, 'investment_score')
        assert hasattr(result, 'data_quality')
        assert 0 <= result.investment_score <= 100
        assert result.price_trend in ["increasing", "stable", "decreasing"]

    def test_analyze_investment_potential_empty_deals(self):
        """Test investment potential with empty deals list."""
        client = GovmapClient()

        with pytest.raises(ValueError, match="Cannot analyze investment potential from empty deals list"):
            client.analyze_investment_potential([])

    def test_analyze_investment_potential_insufficient_data(self):
        """Test investment potential with insufficient data."""
        client = GovmapClient()

        # Only 2 deals (need at least 3) - now using Deal models
        deals = [
            Deal(objectid=1, deal_date="2023-01-15", deal_amount=1000000, asset_area=80.0),
            Deal(objectid=2, deal_date="2023-06-10", deal_amount=1050000, asset_area=80.0),
        ]

        with pytest.raises(ValueError, match="Insufficient data for investment analysis"):
            client.analyze_investment_potential(deals)

    def test_analyze_investment_potential_stable_market(self):
        """Test investment potential with stable market (low volatility)."""
        client = GovmapClient()

        # Deals with consistent prices (very stable) - now using Deal models
        deals = [
            Deal(objectid=i, deal_date=f"2023-{i:02d}-15", deal_amount=1000000 + i * 1000, asset_area=80.0)
            for i in range(1, 13)  # 12 months, slight increase
        ]

        result = client.analyze_investment_potential(deals)

        # Now returns InvestmentAnalysis model
        assert result.market_stability in ["very_stable", "stable", "moderate"]
        assert result.price_volatility < 50

    def test_get_market_liquidity_success(self):
        """Test successful market liquidity calculation."""
        from nadlan_mcp.govmap.models import LiquidityMetrics
        client = GovmapClient()

        # Sample deals across multiple quarters - now using Deal models
        deals = [
            Deal(objectid=i, deal_date=date, deal_amount=amount)
            for i, (date, amount) in enumerate([
                ("2023-01-15", 1000000),
                ("2023-02-20", 1100000),
                ("2023-05-10", 1200000),
                ("2023-06-05", 1150000),
                ("2023-09-12", 1250000),
                ("2023-10-18", 1300000),
            ])
        ]

        result = client.get_market_liquidity(deals, time_period_months=None)

        # Now returns LiquidityMetrics model
        assert isinstance(result, LiquidityMetrics)
        assert result.total_deals == 6
        assert result.avg_deals_per_month > 0
        assert 0 <= result.liquidity_score <= 100
        assert result.market_activity_level in ["very_low", "low", "moderate", "high", "very_high"]

    def test_get_market_liquidity_empty_deals(self):
        """Test market liquidity with empty deals list."""
        client = GovmapClient()

        with pytest.raises(ValueError, match="Cannot calculate market liquidity from empty deals list"):
            client.get_market_liquidity([])

    def test_get_market_liquidity_varied_periods(self):
        """Test market liquidity with varied time periods."""
        from datetime import datetime, timedelta
        client = GovmapClient()

        # Deals spread across recent quarters - now using Deal models
        today = datetime.now()
        deals = [
            Deal(
                objectid=i,
                deal_date=(today - timedelta(days=days)).strftime("%Y-%m-%d"),
                deal_amount=1000000
            )
            for i, days in enumerate([30, 60, 150, 240, 330])  # Spread across ~11 months
        ]

        result = client.get_market_liquidity(deals, time_period_months=12)

        # Now returns LiquidityMetrics model
        assert result.total_deals == 5
        assert result.time_period_months == 12
        assert result.deal_velocity > 0

    def test_filter_deals_by_criteria_property_type(self):
        """Test filtering deals by property type."""
        client = GovmapClient()

        # Now using Deal models
        deals = [
            Deal(objectid=1, property_type_description="דירה", rooms=3, deal_amount=1000000, deal_date="2023-01-01"),
            Deal(objectid=2, property_type_description="בית", rooms=5, deal_amount=2000000, deal_date="2023-01-01"),
            Deal(objectid=3, property_type_description="דירה", rooms=4, deal_amount=1500000, deal_date="2023-01-01"),
        ]

        filtered = client.filter_deals_by_criteria(deals, property_type="דירה")

        # Returns List[Deal]
        assert len(filtered) == 2
        assert all(isinstance(d, Deal) for d in filtered)
        assert all(d.property_type_description == "דירה" for d in filtered)

    def test_filter_deals_by_criteria_rooms(self):
        """Test filtering deals by room count."""
        client = GovmapClient()

        # Now using Deal models
        deals = [
            Deal(objectid=i, rooms=rooms, deal_amount=amount, deal_date="2023-01-01")
            for i, (rooms, amount) in enumerate([(2, 800000), (3, 1000000), (4, 1500000), (5, 2000000)])
        ]

        filtered = client.filter_deals_by_criteria(deals, min_rooms=3, max_rooms=4)

        # Returns List[Deal]
        assert len(filtered) == 2
        assert all(3 <= d.rooms <= 4 for d in filtered)

    def test_filter_deals_by_criteria_price_range(self):
        """Test filtering deals by price range."""
        client = GovmapClient()

        # Now using Deal models
        deals = [
            Deal(objectid=i, deal_amount=amount, deal_date="2023-01-01")
            for i, amount in enumerate([800000, 1000000, 1500000, 2000000])
        ]

        filtered = client.filter_deals_by_criteria(deals, min_price=900000, max_price=1600000)

        # Returns List[Deal]
        assert len(filtered) == 2
        assert all(900000 <= d.deal_amount <= 1600000 for d in filtered)

    def test_calculate_deal_statistics_success(self):
        """Test successful deal statistics calculation."""
        from nadlan_mcp.govmap.models import DealStatistics
        client = GovmapClient()

        # Now using Deal models - price_per_sqm computed automatically
        deals = [
            Deal(objectid=1, deal_amount=1000000, asset_area=80.0, rooms=3, deal_date="2023-01-01"),
            Deal(objectid=2, deal_amount=1200000, asset_area=90.0, rooms=4, deal_date="2023-01-01"),
            Deal(objectid=3, deal_amount=900000, asset_area=70.0, rooms=3, deal_date="2023-01-01"),
        ]

        stats = client.calculate_deal_statistics(deals)

        # Now returns DealStatistics model
        assert isinstance(stats, DealStatistics)
        assert stats.total_deals == 3
        assert "mean" in stats.price_statistics
        assert stats.price_statistics["mean"] > 0
        assert stats.area_statistics["mean"] == pytest.approx(80.0)

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
            Deal(objectid=1, deal_amount=1000000, deal_date="2023-01-01", property_type_description="דירה"),
            Deal(objectid=2, deal_amount=1000000, deal_date="2023-01-01", property_type_description=None),
            Deal(objectid=3, deal_amount=1000000, deal_date="2023-01-01", property_type_description="בית"),
            Deal(objectid=4, deal_amount=1000000, deal_date="2023-01-01"),  # Missing property_type_description
        ]

        filtered = client.filter_deals_by_criteria(deals, property_type="דירה")

        assert len(filtered) == 1
        assert filtered[0].objectid == 1

    def test_filter_excludes_missing_area(self):
        """Test that deals with missing area are excluded when area filter is active."""
        client = GovmapClient()
        deals = [
            Deal(objectid=1, deal_amount=1000000, deal_date="2023-01-01", asset_area=65.0),
            Deal(objectid=2, deal_amount=1000000, deal_date="2023-01-01", asset_area=None),
            Deal(objectid=3, deal_amount=1000000, deal_date="2023-01-01", asset_area=50.0),
            Deal(objectid=4, deal_amount=1000000, deal_date="2023-01-01"),  # Missing asset_area
        ]

        filtered = client.filter_deals_by_criteria(deals, min_area=60, max_area=70)

        assert len(filtered) == 1
        assert filtered[0].objectid == 1

    def test_filter_excludes_missing_rooms(self):
        """Test that deals with missing room count are excluded when room filter is active."""
        client = GovmapClient()
        deals = [
            Deal(objectid=1, deal_amount=1000000, deal_date="2023-01-01", rooms=3.0),
            Deal(objectid=2, deal_amount=1000000, deal_date="2023-01-01", rooms=None),
            Deal(objectid=3, deal_amount=1000000, deal_date="2023-01-01", rooms=2.0),
            Deal(objectid=4, deal_amount=1000000, deal_date="2023-01-01"),  # Missing rooms
        ]

        filtered = client.filter_deals_by_criteria(deals, min_rooms=2.5, max_rooms=4)

        assert len(filtered) == 1
        assert filtered[0].objectid == 1

    def test_filter_excludes_missing_price(self):
        """Test that deals with missing price are excluded when price filter is active."""
        client = GovmapClient()
        # Note: deal_amount is required in Deal model, so we can't test None or missing
        # This test now verifies that only deals within the price range are returned
        deals = [
            Deal(objectid=1, deal_amount=2000000, deal_date="2023-01-01"),
            Deal(objectid=2, deal_amount=1000000, deal_date="2023-01-01"),  # Below range
            Deal(objectid=3, deal_amount=1500000, deal_date="2023-01-01"),  # Below range
            Deal(objectid=4, deal_amount=2500000, deal_date="2023-01-01"),  # Above range
        ]

        filtered = client.filter_deals_by_criteria(deals, min_price=1800000, max_price=2200000)

        assert len(filtered) == 1
        assert filtered[0].objectid == 1

    def test_filter_excludes_invalid_numeric_data(self):
        """Test that deals with out-of-range numeric data are excluded when filter is active."""
        # Note: Pydantic validates types on model creation, so we can't test invalid types
        # This test now verifies filtering based on numeric ranges
        client = GovmapClient()
        deals = [
            Deal(objectid=1, deal_amount=2000000, deal_date="2023-01-01", asset_area=65.0, rooms=3.0),
            Deal(objectid=2, deal_amount=2000000, deal_date="2023-01-01", asset_area=80.0, rooms=3.0),  # Area too high
            Deal(objectid=3, deal_amount=2000000, deal_date="2023-01-01", asset_area=65.0, rooms=5.0),  # Rooms too high
            Deal(objectid=4, deal_amount=3000000, deal_date="2023-01-01", asset_area=65.0, rooms=3.0),  # Price too high
        ]

        # Area filter should exclude deal 2
        filtered_area = client.filter_deals_by_criteria(deals, min_area=60, max_area=70)
        assert len(filtered_area) == 3
        assert all(d.objectid in [1, 3, 4] for d in filtered_area)

        # Room filter should exclude deal 3
        filtered_rooms = client.filter_deals_by_criteria(deals, min_rooms=2, max_rooms=4)
        assert len(filtered_rooms) == 3
        assert all(d.objectid in [1, 2, 4] for d in filtered_rooms)

        # Price filter should exclude deal 4
        filtered_price = client.filter_deals_by_criteria(deals, min_price=1500000, max_price=2500000)
        assert len(filtered_price) == 3
        assert all(d.objectid in [1, 2, 3] for d in filtered_price)

    def test_filter_allows_missing_data_when_no_filter(self):
        """Test that deals with missing data pass through when no filter is active for that field."""
        client = GovmapClient()
        deals = [
            Deal(objectid=1, deal_amount=1000000, deal_date="2023-01-01", property_type_description="דירה", asset_area=65.0),
            Deal(objectid=2, deal_amount=1000000, deal_date="2023-01-01", property_type_description="דירה", asset_area=None),
            Deal(objectid=3, deal_amount=1000000, deal_date="2023-01-01", property_type_description="דירה"),  # Missing asset_area
        ]

        # Filter by property type only - missing area should pass through
        filtered = client.filter_deals_by_criteria(deals, property_type="דירה")

        assert len(filtered) == 3  # All should pass since we're not filtering by area
