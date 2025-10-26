"""
Comprehensive tests for Pydantic models.

This module tests all Pydantic model validation, serialization,
and computed fields to ensure type safety and correctness.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from nadlan_mcp.govmap.models import (
    CoordinatePoint,
    Address,
    AutocompleteResult,
    AutocompleteResponse,
    Deal,
    DealStatistics,
    MarketActivityScore,
    InvestmentAnalysis,
    LiquidityMetrics,
    DealFilters,
)


class TestCoordinatePoint:
    """Tests for CoordinatePoint model."""

    def test_valid_coordinate(self):
        """Test creating valid coordinate point."""
        coord = CoordinatePoint(longitude=180000.0, latitude=650000.0)
        assert coord.longitude == 180000.0
        assert coord.latitude == 650000.0

    def test_coordinate_immutable(self):
        """Test that coordinates are immutable (frozen)."""
        coord = CoordinatePoint(longitude=180000.0, latitude=650000.0)
        with pytest.raises(ValidationError):
            coord.longitude = 180001.0

    def test_coordinate_invalid_type(self):
        """Test that invalid types raise ValidationError."""
        with pytest.raises(ValidationError):
            CoordinatePoint(longitude="invalid", latitude=650000.0)


class TestAddress:
    """Tests for Address model."""

    def test_valid_address(self):
        """Test creating valid address."""
        coord = CoordinatePoint(longitude=180000.0, latitude=650000.0)
        address = Address(
            text="סוקולוב 38 חולון",
            id="addr123",
            type="address",
            score=95.5,
            coordinates=coord
        )
        assert address.text == "סוקולוב 38 חולון"
        assert address.score == 95.5
        assert address.coordinates.longitude == 180000.0

    def test_address_without_coordinates(self):
        """Test creating address without coordinates."""
        address = Address(
            text="סוקולוב 38 חולון",
            id="addr123",
            type="address"
        )
        assert address.coordinates is None
        assert address.score == 0  # Default value


class TestAutocompleteResult:
    """Tests for AutocompleteResult model."""

    def test_valid_result_with_coordinates(self):
        """Test autocomplete result with parsed coordinates."""
        coord = CoordinatePoint(longitude=180000.0, latitude=650000.0)
        result = AutocompleteResult(
            text="חולון",
            id="city123",
            type="city",
            score=100.0,
            coordinates=coord,
            shape="POINT(180000.0 650000.0)"
        )
        assert result.text == "חולון"
        assert result.coordinates.longitude == 180000.0
        assert result.shape == "POINT(180000.0 650000.0)"

    def test_result_without_shape(self):
        """Test result without shape data."""
        result = AutocompleteResult(
            text="חולון",
            id="city123",
            type="city"
        )
        assert result.shape is None
        assert result.coordinates is None


class TestAutocompleteResponse:
    """Tests for AutocompleteResponse model."""

    def test_valid_response(self):
        """Test creating valid autocomplete response."""
        results = [
            AutocompleteResult(text="חולון", id="city1", type="city"),
            AutocompleteResult(text="חולון סוקולוב", id="street1", type="street")
        ]
        response = AutocompleteResponse(resultsCount=2, results=results)
        assert response.results_count == 2
        assert len(response.results) == 2

    def test_response_with_alias(self):
        """Test that camelCase alias works."""
        response = AutocompleteResponse.model_validate({
            "resultsCount": 5,
            "results": []
        })
        assert response.results_count == 5

    def test_empty_response(self):
        """Test empty autocomplete response."""
        response = AutocompleteResponse(resultsCount=0)
        assert response.results_count == 0
        assert response.results == []


class TestDeal:
    """Tests for Deal model."""

    def test_valid_deal(self):
        """Test creating valid deal."""
        deal = Deal(
            objectid=12345,
            deal_amount=1500000.0,
            deal_date="2024-01-15",
            asset_area=85.0,
            settlement_name_heb="חולון",
            property_type_description="דירה",
            street_name="סוקולוב",
            house_number="38",
            rooms=3.5
        )
        assert deal.objectid == 12345
        assert deal.deal_amount == 1500000.0
        assert deal.asset_area == 85.0

    def test_deal_with_aliases(self):
        """Test creating deal using API camelCase field names."""
        deal = Deal.model_validate({
            "objectid": 12345,
            "dealAmount": 1500000.0,
            "dealDate": "2024-01-15",
            "assetArea": 85.0,
            "propertyTypeDescription": "דירה"
        })
        assert deal.deal_amount == 1500000.0
        assert deal.property_type_description == "דירה"

    def test_deal_price_per_sqm_computed(self):
        """Test price_per_sqm computed field."""
        deal = Deal(
            objectid=12345,
            deal_amount=1500000.0,
            deal_date="2024-01-15",
            asset_area=85.0
        )
        assert deal.price_per_sqm == round(1500000.0 / 85.0, 2)

    def test_deal_price_per_sqm_no_area(self):
        """Test price_per_sqm returns None when area is missing."""
        deal = Deal(
            objectid=12345,
            deal_amount=1500000.0,
            deal_date="2024-01-15"
        )
        assert deal.price_per_sqm is None

    def test_deal_price_per_sqm_zero_area(self):
        """Test price_per_sqm returns None when area is zero."""
        deal = Deal(
            objectid=12345,
            deal_amount=1500000.0,
            deal_date="2024-01-15",
            asset_area=0.0
        )
        assert deal.price_per_sqm is None

    def test_deal_extra_fields_allowed(self):
        """Test that extra fields are allowed."""
        deal_data = {
            "objectid": 12345,
            "dealAmount": 1500000.0,
            "dealDate": "2024-01-15",
            "extra_field": "extra_value",
            "another_field": 123
        }
        deal = Deal.model_validate(deal_data)
        # Extra fields should be stored
        assert deal.objectid == 12345

    def test_deal_serialization(self):
        """Test deal serialization to dict."""
        deal = Deal(
            objectid=12345,
            deal_amount=1500000.0,
            deal_date="2024-01-15",
            asset_area=85.0
        )
        deal_dict = deal.model_dump()
        assert deal_dict["objectid"] == 12345
        assert deal_dict["deal_amount"] == 1500000.0
        assert "price_per_sqm" in deal_dict  # Computed field included

    def test_deal_serialization_exclude_none(self):
        """Test deal serialization excluding None values."""
        deal = Deal(
            objectid=12345,
            deal_amount=1500000.0,
            deal_date="2024-01-15"
        )
        deal_dict = deal.model_dump(exclude_none=True)
        assert "asset_area" not in deal_dict
        assert "rooms" not in deal_dict

    def test_deal_required_fields(self):
        """Test that required fields are enforced."""
        with pytest.raises(ValidationError):
            Deal(objectid=12345)  # Missing deal_amount and deal_date


class TestDealStatistics:
    """Tests for DealStatistics model."""

    def test_valid_statistics(self):
        """Test creating valid deal statistics."""
        stats = DealStatistics(
            total_deals=100,
            price_statistics={
                "mean": 1500000.0,
                "median": 1400000.0,
                "std_dev": 200000.0
            },
            area_statistics={
                "mean": 85.5,
                "median": 82.0
            },
            price_per_sqm_statistics={
                "mean": 17500.0,
                "median": 17200.0
            },
            property_type_distribution={
                "דירה": 80,
                "דירת גן": 15,
                "פנטהאוז": 5
            },
            date_range={
                "earliest": "2022-01-01",
                "latest": "2024-12-31"
            }
        )
        assert stats.total_deals == 100
        assert stats.price_statistics["mean"] == 1500000.0
        assert stats.property_type_distribution["דירה"] == 80

    def test_empty_statistics(self):
        """Test creating empty statistics."""
        stats = DealStatistics(total_deals=0)
        assert stats.total_deals == 0
        assert stats.price_statistics == {}
        assert stats.date_range is None


class TestMarketActivityScore:
    """Tests for MarketActivityScore model."""

    def test_valid_activity_score(self):
        """Test creating valid activity score."""
        score = MarketActivityScore(
            activity_score=75.5,
            total_deals=120,
            deals_per_month=10.0,
            trend="increasing",
            time_period_months=12,
            monthly_distribution={"2024-01": 8, "2024-02": 12}
        )
        assert score.activity_score == 75.5
        assert score.trend == "increasing"
        assert score.monthly_distribution["2024-02"] == 12

    def test_activity_score_bounds(self):
        """Test that activity_score is bounded 0-100."""
        with pytest.raises(ValidationError):
            MarketActivityScore(
                activity_score=150.0,  # Invalid: > 100
                total_deals=100,
                deals_per_month=8.0,
                trend="stable",
                time_period_months=12
            )

        with pytest.raises(ValidationError):
            MarketActivityScore(
                activity_score=-10.0,  # Invalid: < 0
                total_deals=100,
                deals_per_month=8.0,
                trend="stable",
                time_period_months=12
            )


class TestInvestmentAnalysis:
    """Tests for InvestmentAnalysis model."""

    def test_valid_investment_analysis(self):
        """Test creating valid investment analysis."""
        analysis = InvestmentAnalysis(
            investment_score=68.5,
            price_trend="increasing",
            price_appreciation_rate=5.2,
            price_volatility=25.3,
            market_stability="moderate",
            avg_price_per_sqm=17500.0,
            price_change_pct=12.5,
            total_deals=85,
            data_quality="good"
        )
        assert analysis.investment_score == 68.5
        assert analysis.price_trend == "increasing"
        assert analysis.data_quality == "good"

    def test_investment_score_bounds(self):
        """Test that investment_score is bounded 0-100."""
        with pytest.raises(ValidationError):
            InvestmentAnalysis(
                investment_score=105.0,  # Invalid
                price_trend="stable",
                price_appreciation_rate=2.0,
                price_volatility=15.0,
                market_stability="stable",
                avg_price_per_sqm=17000.0,
                price_change_pct=5.0,
                total_deals=100,
                data_quality="excellent"
            )


class TestLiquidityMetrics:
    """Tests for LiquidityMetrics model."""

    def test_valid_liquidity_metrics(self):
        """Test creating valid liquidity metrics."""
        metrics = LiquidityMetrics(
            liquidity_score=82.3,
            total_deals=150,
            time_period_months=12,
            avg_deals_per_month=12.5,
            deal_velocity=12.5,
            market_activity_level="high"
        )
        assert metrics.liquidity_score == 82.3
        assert metrics.market_activity_level == "high"
        assert metrics.deal_velocity == 12.5


class TestDealFilters:
    """Tests for DealFilters model."""

    def test_valid_filters(self):
        """Test creating valid deal filters."""
        filters = DealFilters(
            property_type="דירה",
            min_rooms=2.0,
            max_rooms=4.0,
            min_price=1000000.0,
            max_price=2000000.0,
            min_area=60.0,
            max_area=100.0,
            min_floor=1,
            max_floor=5
        )
        assert filters.property_type == "דירה"
        assert filters.min_rooms == 2.0
        assert filters.max_floor == 5

    def test_empty_filters(self):
        """Test creating filters with no criteria."""
        filters = DealFilters()
        assert filters.property_type is None
        assert filters.min_rooms is None

    def test_filter_validation_max_rooms(self):
        """Test that max_rooms must be >= min_rooms."""
        with pytest.raises(ValidationError):
            DealFilters(min_rooms=4.0, max_rooms=2.0)

    def test_filter_validation_max_price(self):
        """Test that max_price must be >= min_price."""
        with pytest.raises(ValidationError):
            DealFilters(min_price=2000000.0, max_price=1000000.0)

    def test_filter_validation_max_area(self):
        """Test that max_area must be >= min_area."""
        with pytest.raises(ValidationError):
            DealFilters(min_area=100.0, max_area=60.0)

    def test_filter_validation_max_floor(self):
        """Test that max_floor must be >= min_floor."""
        with pytest.raises(ValidationError):
            DealFilters(min_floor=5, max_floor=1)

    def test_filter_negative_values(self):
        """Test that negative values are rejected."""
        with pytest.raises(ValidationError):
            DealFilters(min_rooms=-1.0)

        with pytest.raises(ValidationError):
            DealFilters(min_price=-1000.0)


class TestModelIntegration:
    """Integration tests for models working together."""

    def test_deal_to_statistics_workflow(self):  
        """Test creating deals and calculating statistics."""  
        # Import the function to test integration  
        from nadlan_mcp.govmap.statistics import calculate_deal_statistics  

        deals = [  
            Deal(  
                objectid=1,  
                deal_amount=1000000.0,  
                deal_date="2024-01-01",  
                asset_area=100.0,  
                property_type_description="דירה"  
            ),  
            Deal(  
                objectid=2,  
                deal_amount=2000000.0,  
                deal_date="2024-01-02",  
                asset_area=100.0,  
                property_type_description="דירה"  
            ),  
        ]  

        stats = calculate_deal_statistics(deals)  

        assert isinstance(stats, DealStatistics)  
        assert stats.total_deals == 2  
        assert stats.price_statistics["mean"] == 1500000.0  
        assert stats.price_per_sqm_statistics["mean"] == 15000.0  
        assert stats.property_type_distribution["דירה"] == 2 

    def test_autocomplete_to_deals_workflow(self):
        """Test autocomplete response leading to deal search."""
        # Simulate autocomplete response
        coord = CoordinatePoint(longitude=180000.0, latitude=650000.0)
        result = AutocompleteResult(
            text="סוקולוב 38 חולון",
            id="addr123",
            type="address",
            coordinates=coord
        )
        response = AutocompleteResponse(resultsCount=1, results=[result])

        # Verify we can extract coordinates for deal search
        assert response.results[0].coordinates is not None
        assert response.results[0].coordinates.longitude == 180000.0

    def test_filter_application(self):
        """Test that filters can be created and used."""
        filters = DealFilters(
            property_type="דירה",
            min_rooms=3.0,
            max_rooms=4.0,
            min_price=1000000.0,
            max_price=2000000.0
        )

        # Create test deals
        deals = [
            Deal(objectid=1, deal_amount=1200000.0, deal_date="2024-01-01", rooms=3.0),
            Deal(objectid=2, deal_amount=2500000.0, deal_date="2024-01-02", rooms=4.0),  # Price too high
            Deal(objectid=3, deal_amount=1500000.0, deal_date="2024-01-03", rooms=2.0),  # Too few rooms
        ]

        # Manually check which deals would pass
        # (actual filtering is done by filter_deals_by_criteria function)
        assert filters.min_rooms <= deals[0].rooms <= filters.max_rooms
        assert filters.min_price <= deals[0].deal_amount <= filters.max_price
