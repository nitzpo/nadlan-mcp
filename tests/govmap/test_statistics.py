"""
Tests for nadlan_mcp.govmap.statistics module.

Comprehensive tests for statistical calculation functions.
"""

from datetime import date

import pytest

from nadlan_mcp.govmap.models import Deal, DealStatistics
from nadlan_mcp.govmap.statistics import calculate_deal_statistics, calculate_std_dev


class TestCalculateDealStatistics:
    """Test cases for calculate_deal_statistics function."""

    @pytest.fixture
    def sample_deals(self):
        """Create sample deals for testing."""
        return [
            Deal(
                objectid=1,
                deal_amount=1000000.0,
                deal_date="2024-01-15",
                asset_area=80.0,
                property_type_description="דירה",
            ),
            Deal(
                objectid=2,
                deal_amount=1500000.0,
                deal_date="2024-02-01",
                asset_area=100.0,
                property_type_description="דירת גג",
            ),
            Deal(
                objectid=3,
                deal_amount=2000000.0,
                deal_date="2024-03-01",
                asset_area=150.0,
                property_type_description="בית פרטי",
            ),
            Deal(
                objectid=4,
                deal_amount=800000.0,
                deal_date="2024-01-01",
                asset_area=60.0,
                property_type_description="דירה",
            ),
            Deal(
                objectid=5,
                deal_amount=1200000.0,
                deal_date="2024-04-01",
                asset_area=120.0,
                property_type_description="פנטהאוז",
            ),
        ]

    def test_basic_statistics_calculation(self, sample_deals):
        """Test basic statistics calculation."""
        stats = calculate_deal_statistics(sample_deals)

        assert isinstance(stats, DealStatistics)
        assert stats.total_deals == 5
        assert "mean" in stats.price_statistics
        assert "median" in stats.price_statistics
        assert len(stats.property_type_distribution) > 0

    def test_price_statistics(self, sample_deals):
        """Test price statistics calculation."""
        stats = calculate_deal_statistics(sample_deals)

        # Mean: (1000000 + 1500000 + 2000000 + 800000 + 1200000) / 5 = 1300000
        assert stats.price_statistics["mean"] == 1300000.0

        # Median of [800000, 1000000, 1200000, 1500000, 2000000] = 1200000
        assert stats.price_statistics["median"] == 1200000.0

        assert stats.price_statistics["min"] == 800000.0
        assert stats.price_statistics["max"] == 2000000.0
        assert "std_dev" in stats.price_statistics
        assert "total" in stats.price_statistics
        assert stats.price_statistics["total"] == 6500000.0

    def test_area_statistics(self, sample_deals):
        """Test area statistics calculation."""
        stats = calculate_deal_statistics(sample_deals)

        # Mean: (80 + 100 + 150 + 60 + 120) / 5 = 102
        assert stats.area_statistics["mean"] == 102.0

        # Median of [60, 80, 100, 120, 150] = 100
        assert stats.area_statistics["median"] == 100.0

        assert stats.area_statistics["min"] == 60.0
        assert stats.area_statistics["max"] == 150.0

    def test_price_per_sqm_statistics(self, sample_deals):
        """Test price per square meter statistics."""
        stats = calculate_deal_statistics(sample_deals)

        # All deals have both price and area, so should have price_per_sqm
        assert "mean" in stats.price_per_sqm_statistics
        assert "median" in stats.price_per_sqm_statistics
        assert stats.price_per_sqm_statistics["mean"] > 0

    def test_property_type_distribution(self, sample_deals):
        """Test property type distribution."""
        stats = calculate_deal_statistics(sample_deals)

        dist = stats.property_type_distribution
        assert dist["דירה"] == 2  # objectid 1 and 4
        assert dist["דירת גג"] == 1
        assert dist["בית פרטי"] == 1
        assert dist["פנטהאוז"] == 1

    def test_date_range(self, sample_deals):
        """Test date range calculation."""
        stats = calculate_deal_statistics(sample_deals)

        assert stats.date_range is not None
        assert stats.date_range["earliest"] == "2024-01-01"
        assert stats.date_range["latest"] == "2024-04-01"

    def test_empty_deals_list(self):
        """Test statistics with empty deals list."""
        stats = calculate_deal_statistics([])

        assert stats.total_deals == 0
        assert stats.price_statistics == {}
        assert stats.area_statistics == {}
        assert stats.price_per_sqm_statistics == {}
        assert stats.property_type_distribution == {}
        assert stats.date_range is None

    def test_deals_with_missing_prices(self):
        """Test statistics when some deals have zero prices."""
        deals = [
            Deal(objectid=1, deal_amount=1000000.0, deal_date="2024-01-01", asset_area=80.0),
            Deal(
                objectid=2, deal_amount=0.0, deal_date="2024-01-02", asset_area=100.0
            ),  # Zero price excluded
            Deal(
                objectid=3, deal_amount=-1.0, deal_date="2024-01-03", asset_area=120.0
            ),  # Negative excluded
        ]
        stats = calculate_deal_statistics(deals)

        assert stats.total_deals == 3
        # Only deals with positive prices are included
        assert stats.price_statistics["mean"] == 1000000.0
        assert len(stats.price_statistics) > 0  # Should still calculate stats for non-null values

    def test_deals_with_missing_areas(self):
        """Test statistics when some deals have missing areas."""
        deals = [
            Deal(objectid=1, deal_amount=1000000.0, deal_date="2024-01-01", asset_area=80.0),
            Deal(objectid=2, deal_amount=1500000.0, deal_date="2024-01-02", asset_area=None),
            Deal(objectid=3, deal_amount=2000000.0, deal_date="2024-01-03"),  # No asset_area
        ]
        stats = calculate_deal_statistics(deals)

        assert stats.total_deals == 3
        assert stats.area_statistics["mean"] == 80.0  # Only one deal with area
        assert len(stats.price_statistics) == 8  # All 3 deals have prices

    def test_deals_with_missing_property_types(self):
        """Test statistics when some deals have missing property types."""
        deals = [
            Deal(
                objectid=1,
                deal_amount=1000000.0,
                deal_date="2024-01-01",
                property_type_description="דירה",
            ),
            Deal(
                objectid=2,
                deal_amount=1500000.0,
                deal_date="2024-01-02",
                property_type_description=None,
            ),
            Deal(objectid=3, deal_amount=2000000.0, deal_date="2024-01-03"),  # No property_type
        ]
        stats = calculate_deal_statistics(deals)

        assert stats.total_deals == 3
        assert stats.property_type_distribution == {"דירה": 1}

    def test_deals_with_zero_prices(self):
        """Test that zero prices are excluded from statistics."""
        deals = [
            Deal(objectid=1, deal_amount=1000000.0, deal_date="2024-01-01"),
            Deal(objectid=2, deal_amount=0.0, deal_date="2024-01-02"),  # Zero price
            Deal(objectid=3, deal_amount=2000000.0, deal_date="2024-01-03"),
        ]
        stats = calculate_deal_statistics(deals)

        # Only 2 deals should be counted (excluding zero)
        assert stats.price_statistics["mean"] == 1500000.0

    def test_deals_with_zero_areas(self):
        """Test that zero areas are excluded from statistics."""
        deals = [
            Deal(objectid=1, deal_amount=1000000.0, deal_date="2024-01-01", asset_area=80.0),
            Deal(objectid=2, deal_amount=1500000.0, deal_date="2024-01-02", asset_area=0.0),
            Deal(objectid=3, deal_amount=2000000.0, deal_date="2024-01-03", asset_area=100.0),
        ]
        stats = calculate_deal_statistics(deals)

        assert stats.area_statistics["mean"] == 90.0  # (80 + 100) / 2

    def test_single_deal(self):
        """Test statistics with single deal."""
        deals = [
            Deal(
                objectid=1,
                deal_amount=1000000.0,
                deal_date="2024-01-01",
                asset_area=80.0,
                property_type_description="דירה",
            )
        ]
        stats = calculate_deal_statistics(deals)

        assert stats.total_deals == 1
        assert stats.price_statistics["mean"] == 1000000.0
        assert stats.price_statistics["median"] == 1000000.0
        assert stats.price_statistics["min"] == 1000000.0
        assert stats.price_statistics["max"] == 1000000.0
        assert stats.price_statistics["std_dev"] == 0  # Only one value

    def test_percentiles_calculation(self, sample_deals):
        """Test percentile calculations (p25, p75)."""
        stats = calculate_deal_statistics(sample_deals)

        # Sorted prices: [800000, 1000000, 1200000, 1500000, 2000000]
        assert "p25" in stats.price_statistics
        assert "p75" in stats.price_statistics
        # p25 should be around 1000000, p75 around 1500000
        assert stats.price_statistics["p25"] >= 800000
        assert stats.price_statistics["p75"] <= 2000000

    def test_invalid_input_raises_error(self):
        """Test that invalid input raises ValueError."""
        with pytest.raises(ValueError, match="deals must be a list"):
            calculate_deal_statistics("not a list")

    def test_date_handling_with_date_objects(self):
        """Test date range calculation with date objects."""
        deals = [
            Deal(objectid=1, deal_amount=1000000.0, deal_date=date(2024, 1, 15), asset_area=80.0),
            Deal(objectid=2, deal_amount=1500000.0, deal_date=date(2024, 2, 1), asset_area=100.0),
        ]
        stats = calculate_deal_statistics(deals)

        assert stats.date_range is not None
        assert stats.date_range["earliest"] == "2024-01-15"
        assert stats.date_range["latest"] == "2024-02-01"

    def test_date_handling_with_iso_strings(self):
        """Test date range calculation with ISO format strings."""
        deals = [
            Deal(
                objectid=1,
                deal_amount=1000000.0,
                deal_date="2024-01-15T00:00:00.000Z",
                asset_area=80.0,
            ),
            Deal(
                objectid=2,
                deal_amount=1500000.0,
                deal_date="2024-02-01T12:30:45.123Z",
                asset_area=100.0,
            ),
        ]
        stats = calculate_deal_statistics(deals)

        assert stats.date_range is not None
        assert stats.date_range["earliest"] == "2024-01-15"
        assert stats.date_range["latest"] == "2024-02-01"

    def test_multiple_same_property_types(self):
        """Test property type distribution with duplicates."""
        deals = [
            Deal(
                objectid=1,
                deal_amount=1000000.0,
                deal_date="2024-01-01",
                property_type_description="דירה",
            ),
            Deal(
                objectid=2,
                deal_amount=1500000.0,
                deal_date="2024-01-02",
                property_type_description="דירה",
            ),
            Deal(
                objectid=3,
                deal_amount=2000000.0,
                deal_date="2024-01-03",
                property_type_description="דירה",
            ),
        ]
        stats = calculate_deal_statistics(deals)

        assert stats.property_type_distribution["דירה"] == 3

    def test_std_dev_calculation(self):
        """Test standard deviation calculation."""
        deals = [
            Deal(objectid=1, deal_amount=1000.0, deal_date="2024-01-01"),
            Deal(objectid=2, deal_amount=2000.0, deal_date="2024-01-02"),
            Deal(objectid=3, deal_amount=3000.0, deal_date="2024-01-03"),
        ]
        stats = calculate_deal_statistics(deals)

        assert "std_dev" in stats.price_statistics
        assert stats.price_statistics["std_dev"] > 0

    @pytest.mark.parametrize(
        "deal_count,has_price,has_area,expected_price_stats,expected_area_stats",
        [
            (0, False, False, False, False),  # Empty
            (1, True, True, True, True),  # Single deal
            (3, True, False, True, False),  # Deals with price only
            (3, False, True, False, True),  # Deals with area only (use zero for no price)
        ],
    )
    def test_statistics_with_various_data_availability(
        self, deal_count, has_price, has_area, expected_price_stats, expected_area_stats
    ):
        """Parametrized test for statistics with varying data availability."""
        deals = []
        for i in range(deal_count):
            deals.append(
                Deal(
                    objectid=i,
                    deal_amount=1000000.0 if has_price else 0.0,  # Use 0.0 instead of None
                    deal_date=f"2024-01-{i + 1:02d}",
                    asset_area=80.0 if has_area else None,
                )
            )

        stats = calculate_deal_statistics(deals)

        assert stats.total_deals == deal_count
        assert (len(stats.price_statistics) > 0) == expected_price_stats
        assert (len(stats.area_statistics) > 0) == expected_area_stats


class TestCalculateStdDev:
    """Test cases for calculate_std_dev function."""

    def test_std_dev_basic(self):
        """Test standard deviation calculation with basic values."""
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        std_dev = calculate_std_dev(values)

        # Std dev of [1,2,3,4,5] with n-1 denominator ≈ 1.58
        assert std_dev > 1.5
        assert std_dev < 1.6

    def test_std_dev_single_value(self):
        """Test std dev with single value returns 0."""
        assert calculate_std_dev([5.0]) == 0.0

    def test_std_dev_empty_list(self):
        """Test std dev with empty list returns 0."""
        assert calculate_std_dev([]) == 0.0

    def test_std_dev_identical_values(self):
        """Test std dev with identical values returns 0."""
        assert calculate_std_dev([5.0, 5.0, 5.0, 5.0]) == 0.0

    def test_std_dev_two_values(self):
        """Test std dev with two values."""
        values = [10.0, 20.0]
        std_dev = calculate_std_dev(values)

        # Std dev of [10, 20] with n-1 denominator = sqrt((10^2 + 10^2)/1) ≈ 7.07
        assert 7.0 < std_dev < 7.1

    def test_std_dev_large_spread(self):
        """Test std dev with large value spread."""
        values = [1.0, 100.0, 1000.0]
        std_dev = calculate_std_dev(values)

        # Large spread should have high std dev
        assert std_dev > 500

    @pytest.mark.parametrize(
        "values,expected_range",
        [
            ([1.0, 2.0, 3.0], (0.8, 1.2)),  # Small range
            ([10.0, 20.0, 30.0], (8.0, 12.0)),  # Medium range
            ([100.0, 200.0, 300.0], (80.0, 120.0)),  # Large range
        ],
    )
    def test_std_dev_parametrized(self, values, expected_range):
        """Parametrized test for std dev with various value ranges."""
        std_dev = calculate_std_dev(values)
        assert expected_range[0] <= std_dev <= expected_range[1]
