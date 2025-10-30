"""
Tests for nadlan_mcp.govmap.market_analysis module.

Comprehensive tests for market analysis functions.
"""

from datetime import datetime, timedelta

import pytest

from nadlan_mcp.govmap.market_analysis import (
    analyze_investment_potential,
    calculate_market_activity_score,
    get_market_liquidity,
    parse_deal_dates,
)
from nadlan_mcp.govmap.models import Deal, InvestmentAnalysis, LiquidityMetrics, MarketActivityScore


def get_recent_date(months_ago=0, days_ago=0):
    """Helper to get recent dates for testing."""
    return (datetime.now() - timedelta(days=months_ago * 30 + days_ago)).date()


class TestParseDealDates:
    """Test cases for parse_deal_dates helper function."""

    @pytest.fixture
    def sample_deals(self):
        """Create sample deals spanning multiple months (recent dates)."""
        return [
            Deal(
                objectid=1,
                deal_amount=1000000,
                deal_date=get_recent_date(months_ago=4, days_ago=15),
                asset_area=80,
            ),
            Deal(
                objectid=2,
                deal_amount=1100000,
                deal_date=get_recent_date(months_ago=4, days_ago=10),
                asset_area=85,
            ),
            Deal(
                objectid=3,
                deal_amount=1200000,
                deal_date=get_recent_date(months_ago=3, days_ago=20),
                asset_area=90,
            ),
            Deal(
                objectid=4,
                deal_amount=1300000,
                deal_date=get_recent_date(months_ago=2, days_ago=25),
                asset_area=95,
            ),
            Deal(
                objectid=5,
                deal_amount=1400000,
                deal_date=get_recent_date(months_ago=1, days_ago=18),
                asset_area=100,
            ),
        ]

    def test_parse_deal_dates_basic(self, sample_deals):
        """Test basic date parsing functionality."""
        deal_dates, monthly, quarterly = parse_deal_dates(sample_deals)

        assert len(deal_dates) == 5
        assert len(monthly) >= 4  # At least 4 different months
        assert len(quarterly) >= 1  # At least 1 quarter

    def test_parse_deal_dates_quarterly_grouping(self, sample_deals):
        """Test quarterly grouping."""
        _, _, quarterly = parse_deal_dates(sample_deals)

        assert len(quarterly) >= 1  # At least one quarter represented

    def test_parse_deal_dates_with_time_filter(self, sample_deals):
        """Test filtering by time period."""
        # Filter to last 6 months (should include all our recent sample deals)
        deal_dates, monthly, _ = parse_deal_dates(sample_deals, time_period_months=6)

        # All sample deals are within last 5 months, so should all be included
        assert len(deal_dates) == 5

    def test_parse_deal_dates_with_date_objects(self):
        """Test parsing with date objects instead of strings."""
        recent = datetime.now().date()
        deals = [
            Deal(
                objectid=1,
                deal_amount=1000000,
                deal_date=recent - timedelta(days=30),
                asset_area=80,
            ),
            Deal(
                objectid=2,
                deal_amount=1100000,
                deal_date=recent - timedelta(days=60),
                asset_area=85,
            ),
        ]
        deal_dates, monthly, _ = parse_deal_dates(deals)

        assert len(deal_dates) == 2
        assert len(monthly) >= 1

    def test_parse_deal_dates_all_valid(self):
        """Test that all valid dates are parsed."""
        deals = [
            Deal(
                objectid=1,
                deal_amount=1000000,
                deal_date=get_recent_date(months_ago=1),
                asset_area=80,
            ),
            Deal(
                objectid=2,
                deal_amount=1100000,
                deal_date=get_recent_date(months_ago=2),
                asset_area=85,
            ),
        ]
        deal_dates, _, _ = parse_deal_dates(deals)
        assert len(deal_dates) == 2

    def test_parse_deal_dates_empty_list_raises_error(self):
        """Test that empty list raises error."""
        with pytest.raises(ValueError, match="No valid deal dates"):
            parse_deal_dates([])


class TestCalculateMarketActivityScore:
    """Test cases for calculate_market_activity_score function."""

    def test_market_activity_basic(self):
        """Test basic market activity calculation."""
        # Create 12 deals spread across last 12 months
        deals = [
            Deal(
                objectid=i,
                deal_amount=1000000,
                deal_date=get_recent_date(months_ago=i),
                asset_area=80,
            )
            for i in range(12)
        ]
        score = calculate_market_activity_score(deals, time_period_months=12)

        assert isinstance(score, MarketActivityScore)
        assert score.total_deals == 12
        assert 0.9 <= score.deals_per_month <= 1.2  # Approximately 1 deal/month
        assert score.time_period_months == 12
        assert len(score.monthly_distribution) > 0

    def test_market_activity_high_volume(self):
        """Test activity score with high volume."""
        # Create 120 deals spread across last 10 months = ~12 deals/month (very high)
        deals = []
        for i in range(120):
            month_ago = i % 10
            day = (i % 28) + 1
            deals.append(
                Deal(
                    objectid=i,
                    deal_amount=1000000,
                    deal_date=get_recent_date(months_ago=month_ago, days_ago=day),
                    asset_area=80,
                )
            )
        score = calculate_market_activity_score(deals, time_period_months=12)

        assert score.activity_score == 100.0  # Should max out at 100

    def test_market_activity_low_volume(self):
        """Test activity score with low volume."""
        deals = [
            Deal(
                objectid=1,
                deal_amount=1000000,
                deal_date=get_recent_date(months_ago=1),
                asset_area=80,
            ),
            Deal(
                objectid=2,
                deal_amount=1100000,
                deal_date=get_recent_date(months_ago=6),
                asset_area=85,
            ),
        ]
        score = calculate_market_activity_score(deals, time_period_months=12)

        assert score.total_deals == 2
        assert score.activity_score < 50  # Low activity

    def test_market_activity_trend_increasing(self):
        """Test trend detection - increasing activity."""
        # More deals in recent months (month 0 is most recent)
        deals = []
        for i in range(12):
            months_ago = 11 - i  # Start from 11 months ago
            num_deals = i + 1  # Increasing: 1 deal earliest, 12 deals most recent
            for j in range(num_deals):
                deals.append(
                    Deal(
                        objectid=len(deals),
                        deal_amount=1000000,
                        deal_date=get_recent_date(months_ago=months_ago, days_ago=j),
                        asset_area=80,
                    )
                )

        score = calculate_market_activity_score(deals, time_period_months=12)
        assert score.trend == "increasing"

    def test_market_activity_trend_decreasing(self):
        """Test trend detection - decreasing activity."""
        # Fewer deals in recent months
        deals = []
        for i in range(12):
            months_ago = 11 - i  # Start from 11 months ago
            num_deals = 12 - i  # Decreasing: 12 deals earliest, 1 deal most recent
            for j in range(num_deals):
                deals.append(
                    Deal(
                        objectid=len(deals),
                        deal_amount=1000000,
                        deal_date=get_recent_date(months_ago=months_ago, days_ago=j),
                        asset_area=80,
                    )
                )

        score = calculate_market_activity_score(deals, time_period_months=12)
        assert score.trend == "decreasing"

    def test_market_activity_trend_stable(self):
        """Test trend detection - stable activity."""
        # Same number of deals each month
        deals = [
            Deal(
                objectid=i,
                deal_amount=1000000,
                deal_date=get_recent_date(months_ago=i),
                asset_area=80,
            )
            for i in range(12)
        ]
        score = calculate_market_activity_score(deals, time_period_months=12)

        # With evenly distributed deals, trend could be stable or slightly increasing
        assert score.trend in ["stable", "increasing"]

    def test_market_activity_insufficient_data_for_trend(self):
        """Test trend with insufficient data."""
        deals = [
            Deal(
                objectid=1,
                deal_amount=1000000,
                deal_date=get_recent_date(months_ago=1),
                asset_area=80,
            ),
            Deal(
                objectid=2,
                deal_amount=1100000,
                deal_date=get_recent_date(months_ago=2),
                asset_area=85,
            ),
        ]
        score = calculate_market_activity_score(deals, time_period_months=12)

        assert score.trend == "insufficient_data"

    def test_market_activity_empty_raises_error(self):
        """Test that empty deals list raises error."""
        with pytest.raises(ValueError, match="Cannot calculate market activity"):
            calculate_market_activity_score([])

    @pytest.mark.parametrize(
        "num_deals,months,expected_dpm_range",
        [
            (10, 10, (0.8, 1.2)),  # ~1 deal/month
            (50, 10, (4.5, 5.5)),  # ~5 deals/month
            (100, 10, (9.5, 10.5)),  # ~10 deals/month
        ],
    )
    def test_market_activity_deals_per_month(self, num_deals, months, expected_dpm_range):
        """Parametrized test for deals per month calculation."""
        deals = []
        for i in range(num_deals):
            month_ago = i % months
            day = (i // months) % 28
            deals.append(
                Deal(
                    objectid=i,
                    deal_amount=1000000,
                    deal_date=get_recent_date(months_ago=month_ago, days_ago=day),
                    asset_area=80,
                )
            )
        score = calculate_market_activity_score(deals, time_period_months=12)

        assert expected_dpm_range[0] <= score.deals_per_month <= expected_dpm_range[1]


class TestAnalyzeInvestmentPotential:
    """Test cases for analyze_investment_potential function."""

    def test_investment_analysis_basic(self):
        """Test basic investment analysis."""
        # Create deals with increasing prices
        deals = [
            Deal(
                objectid=1, deal_amount=1000000, deal_date="2024-01-01", asset_area=100
            ),  # 10000/sqm
            Deal(
                objectid=2, deal_amount=1100000, deal_date="2024-02-01", asset_area=100
            ),  # 11000/sqm
            Deal(
                objectid=3, deal_amount=1200000, deal_date="2024-03-01", asset_area=100
            ),  # 12000/sqm
        ]
        analysis = analyze_investment_potential(deals)

        assert isinstance(analysis, InvestmentAnalysis)
        assert analysis.total_deals == 3
        assert analysis.price_trend == "increasing"
        assert analysis.price_appreciation_rate > 0
        assert 0 <= analysis.investment_score <= 100

    def test_investment_analysis_declining_prices(self):
        """Test investment analysis with declining prices."""
        deals = [
            Deal(objectid=1, deal_amount=1200000, deal_date="2024-01-01", asset_area=100),
            Deal(objectid=2, deal_amount=1100000, deal_date="2024-02-01", asset_area=100),
            Deal(objectid=3, deal_amount=1000000, deal_date="2024-03-01", asset_area=100),
        ]
        analysis = analyze_investment_potential(deals)

        assert analysis.price_trend == "decreasing"
        assert analysis.price_appreciation_rate < 0
        assert analysis.price_change_pct < 0

    def test_investment_analysis_stable_prices(self):
        """Test investment analysis with stable prices."""
        deals = [
            Deal(objectid=1, deal_amount=1000000, deal_date="2024-01-01", asset_area=100),
            Deal(objectid=2, deal_amount=1005000, deal_date="2024-02-01", asset_area=100),
            Deal(objectid=3, deal_amount=1000000, deal_date="2024-03-01", asset_area=100),
        ]
        analysis = analyze_investment_potential(deals)

        assert analysis.price_trend == "stable"
        assert -2 <= analysis.price_appreciation_rate <= 2

    def test_investment_analysis_volatility_low(self):
        """Test volatility calculation with low volatility."""
        # Prices very similar
        deals = [
            Deal(
                objectid=i,
                deal_amount=1000000 + i * 1000,
                deal_date=f"2024-{i + 1:02d}-01",
                asset_area=100,
            )
            for i in range(5)
        ]
        analysis = analyze_investment_potential(deals)

        assert analysis.market_stability in ["very_stable", "stable"]
        assert analysis.price_volatility < 50

    def test_investment_analysis_volatility_high(self):
        """Test volatility calculation with high volatility."""
        # Prices vary wildly
        deals = [
            Deal(objectid=1, deal_amount=800000, deal_date="2024-01-01", asset_area=100),
            Deal(objectid=2, deal_amount=1500000, deal_date="2024-02-01", asset_area=100),
            Deal(objectid=3, deal_amount=900000, deal_date="2024-03-01", asset_area=100),
            Deal(objectid=4, deal_amount=1400000, deal_date="2024-04-01", asset_area=100),
        ]
        analysis = analyze_investment_potential(deals)

        assert analysis.market_stability in ["volatile", "very_volatile", "moderate"]
        assert analysis.price_volatility > 20

    def test_investment_analysis_data_quality_excellent(self):
        """Test data quality assessment with excellent data."""
        deals = [
            Deal(
                objectid=i,
                deal_amount=1000000,
                deal_date=f"2024-{(i % 12) + 1:02d}-01",
                asset_area=100,
            )
            for i in range(25)
        ]
        analysis = analyze_investment_potential(deals)

        assert analysis.data_quality == "excellent"
        assert analysis.total_deals >= 20

    def test_investment_analysis_data_quality_limited(self):
        """Test data quality assessment with limited data."""
        deals = [
            Deal(objectid=1, deal_amount=1000000, deal_date="2024-01-01", asset_area=100),
            Deal(objectid=2, deal_amount=1100000, deal_date="2024-02-01", asset_area=100),
            Deal(objectid=3, deal_amount=1200000, deal_date="2024-03-01", asset_area=100),
        ]
        analysis = analyze_investment_potential(deals)

        assert analysis.data_quality == "limited"
        assert analysis.total_deals < 5

    def test_investment_analysis_insufficient_data_raises_error(self):
        """Test that insufficient data raises error."""
        deals = [
            Deal(objectid=1, deal_amount=1000000, deal_date="2024-01-01", asset_area=100),
            Deal(objectid=2, deal_amount=1100000, deal_date="2024-02-01", asset_area=100),
        ]
        with pytest.raises(ValueError, match="Insufficient data"):
            analyze_investment_potential(deals)

    def test_investment_analysis_empty_raises_error(self):
        """Test that empty deals list raises error."""
        with pytest.raises(ValueError, match="Cannot analyze investment"):
            analyze_investment_potential([])

    def test_investment_analysis_no_price_per_sqm_raises_error(self):
        """Test that deals without price_per_sqm raise error."""
        # Deals without asset_area won't have price_per_sqm
        deals = [
            Deal(objectid=1, deal_amount=1000000, deal_date="2024-01-01"),
            Deal(objectid=2, deal_amount=1100000, deal_date="2024-02-01"),
            Deal(objectid=3, deal_amount=1200000, deal_date="2024-03-01"),
        ]
        with pytest.raises(ValueError, match="Insufficient data"):
            analyze_investment_potential(deals)

    @pytest.mark.parametrize(
        "price_changes,expected_trend",
        [
            ([1000000, 1100000, 1200000], "increasing"),  # +20%
            ([1200000, 1100000, 1000000], "decreasing"),  # -20%
            ([1000000, 1010000, 1000000], "stable"),  # <2% change
        ],
    )
    def test_investment_analysis_price_trends(self, price_changes, expected_trend):
        """Parametrized test for price trend detection."""
        deals = [
            Deal(objectid=i, deal_amount=price, deal_date=f"2024-{i + 1:02d}-01", asset_area=100)
            for i, price in enumerate(price_changes)
        ]
        analysis = analyze_investment_potential(deals)

        assert analysis.price_trend == expected_trend


class TestGetMarketLiquidity:
    """Test cases for get_market_liquidity function."""

    def test_market_liquidity_basic(self):
        """Test basic liquidity calculation."""
        deals = [
            Deal(
                objectid=i,
                deal_amount=1000000,
                deal_date=get_recent_date(months_ago=i),
                asset_area=80,
            )
            for i in range(12)
        ]
        liquidity = get_market_liquidity(deals, time_period_months=12)

        assert isinstance(liquidity, LiquidityMetrics)
        assert liquidity.total_deals == 12
        assert 0.9 <= liquidity.avg_deals_per_month <= 1.2  # Approximately 1
        assert liquidity.time_period_months == 12
        assert liquidity.liquidity_score >= 0

    def test_market_liquidity_very_high(self):
        """Test very high liquidity."""
        # 100 deals spread across last 10 months = ~10/month
        deals = []
        for i in range(100):
            month_ago = i % 10
            day = (i % 28) + 1
            deals.append(
                Deal(
                    objectid=i,
                    deal_amount=1000000,
                    deal_date=get_recent_date(months_ago=month_ago, days_ago=day),
                    asset_area=80,
                )
            )
        liquidity = get_market_liquidity(deals, time_period_months=12)

        assert liquidity.market_activity_level == "very_high"
        assert liquidity.liquidity_score == 100.0

    def test_market_liquidity_low(self):
        """Test low liquidity."""
        deals = [
            Deal(
                objectid=1,
                deal_amount=1000000,
                deal_date=get_recent_date(months_ago=1),
                asset_area=80,
            ),
            Deal(
                objectid=2,
                deal_amount=1100000,
                deal_date=get_recent_date(months_ago=6),
                asset_area=85,
            ),
        ]
        liquidity = get_market_liquidity(deals, time_period_months=12)

        assert liquidity.market_activity_level in ["very_low", "low"]
        assert liquidity.liquidity_score < 50

    def test_market_liquidity_deal_velocity(self):
        """Test deal velocity calculation."""
        # 12 deals spread evenly across 12 months
        deals = [
            Deal(
                objectid=i,
                deal_amount=1000000,
                deal_date=get_recent_date(months_ago=i),
                asset_area=80,
            )
            for i in range(12)
        ]
        liquidity = get_market_liquidity(deals, time_period_months=12)

        # deal_velocity should equal avg_deals_per_month
        assert liquidity.deal_velocity == liquidity.avg_deals_per_month
        assert 0.9 <= liquidity.deal_velocity <= 1.2

    def test_market_liquidity_empty_raises_error(self):
        """Test that empty deals list raises error."""
        with pytest.raises(ValueError, match="Cannot calculate market liquidity"):
            get_market_liquidity([])

    @pytest.mark.parametrize(
        "num_deals,months,expected_ratings",
        [
            (100, 10, ["very_high"]),  # 10 deals/month
            (60, 10, ["high"]),  # 6 deals/month
            (30, 10, ["moderate"]),  # 3 deals/month
            (5, 10, ["low"]),  # 0.5 deals/month
            (2, 10, ["low", "very_low"]),  # 0.2 deals/month - edge case
        ],
    )
    def test_market_liquidity_ratings(self, num_deals, months, expected_ratings):
        """Parametrized test for liquidity ratings."""
        deals = []
        for i in range(num_deals):
            month_ago = i % months
            day = (i // months) % 28
            deals.append(
                Deal(
                    objectid=i,
                    deal_amount=1000000,
                    deal_date=get_recent_date(months_ago=month_ago, days_ago=day),
                    asset_area=80,
                )
            )
        liquidity = get_market_liquidity(deals, time_period_months=12)

        assert liquidity.market_activity_level in expected_ratings
