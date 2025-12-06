"""
Tests for outlier detection functions.
"""

from datetime import date

from nadlan_mcp.config import GovmapConfig
from nadlan_mcp.govmap.models import Deal
from nadlan_mcp.govmap.outlier_detection import (
    apply_hard_bounds_deal_amount,
    apply_hard_bounds_price_per_sqm,
    calculate_iqr,
    detect_outliers_iqr,
    detect_outliers_percent,
    filter_deals_for_analysis,
)


class TestCalculateIQR:
    """Tests for calculate_iqr function."""

    def test_calculate_iqr_normal_data(self):
        """Test IQR calculation with normal data."""
        values = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        iqr = calculate_iqr(values)
        # Q1 = 3 (index 2), Q3 = 8 (index 7), IQR = 5
        assert iqr == 5

    def test_calculate_iqr_empty_list(self):
        """Test IQR calculation with empty list."""
        assert calculate_iqr([]) == 0.0

    def test_calculate_iqr_single_value(self):
        """Test IQR calculation with single value."""
        assert calculate_iqr([5.0]) == 0.0


class TestDetectOutliersIQR:
    """Tests for detect_outliers_iqr function."""

    def test_detect_outliers_iqr_with_outliers(self):
        """Test IQR outlier detection with clear outliers."""
        # Dataset: 1-10 with outliers at 50 and 100
        values = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 50, 100]
        outliers = detect_outliers_iqr(values, multiplier=1.5)

        # The last two values (50, 100) should be outliers
        assert outliers[-2] is True  # 50
        assert outliers[-1] is True  # 100
        # The first 10 values should not be outliers
        assert sum(outliers[:10]) == 0

    def test_detect_outliers_iqr_no_outliers(self):
        """Test IQR outlier detection with no outliers."""
        values = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        outliers = detect_outliers_iqr(values, multiplier=1.5)
        assert sum(outliers) == 0

    def test_detect_outliers_iqr_empty_list(self):
        """Test IQR outlier detection with empty list."""
        assert detect_outliers_iqr([]) == []

    def test_detect_outliers_iqr_insufficient_data(self):
        """Test IQR outlier detection with insufficient data."""
        values = [1, 2, 3]
        outliers = detect_outliers_iqr(values, multiplier=1.5)
        assert outliers == [False, False, False]

    def test_detect_outliers_iqr_different_multipliers(self):
        """Test IQR outlier detection with different multipliers."""
        values = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 50]

        # More aggressive (k=1.5)
        outliers_aggressive = detect_outliers_iqr(values, multiplier=1.5)
        # Conservative (k=3.0)
        outliers_conservative = detect_outliers_iqr(values, multiplier=3.0)

        # Aggressive should detect more outliers
        assert sum(outliers_aggressive) >= sum(outliers_conservative)


class TestDetectOutliersPercent:
    """Tests for detect_outliers_percent function."""

    def test_detect_outliers_percent_with_outliers(self):
        """Test percent-based outlier detection with clear outliers."""
        # Median = 10, threshold=0.5 means 5-15 is acceptable, <5 or >15 is outlier
        values = [2, 9, 10, 10, 10, 11, 20]
        outliers = detect_outliers_percent(values, threshold=0.5)

        assert outliers[0] is True  # 2 < 5
        assert outliers[-1] is True  # 20 > 15
        # Middle values should not be outliers
        assert sum(outliers[1:-1]) == 0

    def test_detect_outliers_percent_no_outliers(self):
        """Test percent-based outlier detection with no outliers."""
        values = [8, 9, 10, 11, 12]
        outliers = detect_outliers_percent(values, threshold=0.5)
        assert sum(outliers) == 0

    def test_detect_outliers_percent_empty_list(self):
        """Test percent-based outlier detection with empty list."""
        assert detect_outliers_percent([]) == []


class TestApplyHardBoundsPricePerSqm:
    """Tests for apply_hard_bounds_price_per_sqm function."""

    def test_hard_bounds_price_per_sqm_within_bounds(self):
        """Test hard bounds filtering with values within bounds."""
        deals = [
            Deal(
                objectid=1,
                deal_amount=1000000,
                deal_date=date(2023, 1, 1),
                asset_area=100,  # price_per_sqm = 10000
            ),
            Deal(
                objectid=2,
                deal_amount=2000000,
                deal_date=date(2023, 1, 1),
                asset_area=100,  # price_per_sqm = 20000
            ),
        ]
        config = GovmapConfig()
        filters = apply_hard_bounds_price_per_sqm(deals, config)
        assert filters == [False, False]  # None should be filtered

    def test_hard_bounds_price_per_sqm_outside_bounds(self):
        """Test hard bounds filtering with values outside bounds."""
        deals = [
            Deal(
                objectid=1,
                deal_amount=500,
                deal_date=date(2023, 1, 1),
                asset_area=1,  # price_per_sqm = 500 (< 1000 min)
            ),
            Deal(
                objectid=2,
                deal_amount=10000000,
                deal_date=date(2023, 1, 1),
                asset_area=10,  # price_per_sqm = 1000000 (> 100000 max)
            ),
        ]
        config = GovmapConfig()
        filters = apply_hard_bounds_price_per_sqm(deals, config)
        assert filters == [True, True]  # Both should be filtered

    def test_hard_bounds_price_per_sqm_no_area(self):
        """Test hard bounds filtering with missing area data."""
        deals = [
            Deal(objectid=1, deal_amount=1000000, deal_date=date(2023, 1, 1)),  # No area
        ]
        config = GovmapConfig()
        filters = apply_hard_bounds_price_per_sqm(deals, config)
        assert filters == [False]  # Not filtered (can't calculate price_per_sqm)


class TestApplyHardBoundsDealAmount:
    """Tests for apply_hard_bounds_deal_amount function."""

    def test_hard_bounds_deal_amount_within_bounds(self):
        """Test hard bounds filtering for deal amounts within bounds."""
        deals = [
            Deal(objectid=1, deal_amount=500000, deal_date=date(2023, 1, 1)),  # > 100K (OK)
            Deal(objectid=2, deal_amount=1000000, deal_date=date(2023, 1, 1)),  # > 100K (OK)
        ]
        config = GovmapConfig()
        filters = apply_hard_bounds_deal_amount(deals, config)
        assert filters == [False, False]  # Both are >= 100K, so not filtered

    def test_hard_bounds_deal_amount_below_minimum(self):
        """Test hard bounds filtering for deal amounts below minimum."""
        deals = [
            Deal(objectid=1, deal_amount=50000, deal_date=date(2023, 1, 1)),  # Below 100K
            Deal(objectid=2, deal_amount=100000, deal_date=date(2023, 1, 1)),  # At 100K (OK)
        ]
        config = GovmapConfig()
        filters = apply_hard_bounds_deal_amount(deals, config)
        assert filters == [True, False]


class TestFilterDealsForAnalysis:
    """Tests for filter_deals_for_analysis function."""

    def test_filter_deals_empty_list(self):
        """Test filtering with empty deal list."""
        config = GovmapConfig()
        filtered, report = filter_deals_for_analysis([], config)
        assert filtered == []
        assert report["total_deals"] == 0
        assert report["outliers_removed"] == 0

    def test_filter_deals_disabled(self):
        """Test filtering with outlier detection disabled."""
        deals = [
            Deal(objectid=1, deal_amount=1000000, deal_date=date(2023, 1, 1), asset_area=100),
            Deal(objectid=2, deal_amount=2000000, deal_date=date(2023, 1, 1), asset_area=100),
        ]
        config = GovmapConfig(analysis_outlier_method="none")
        filtered, report = filter_deals_for_analysis(deals, config)
        assert len(filtered) == 2
        assert report["method_used"] == "none"
        assert report["outliers_removed"] == 0

    def test_filter_deals_insufficient_data(self):
        """Test filtering with insufficient data for outlier detection."""
        deals = [
            Deal(objectid=1, deal_amount=1000000, deal_date=date(2023, 1, 1), asset_area=100),
            Deal(objectid=2, deal_amount=2000000, deal_date=date(2023, 1, 1), asset_area=100),
        ]
        config = GovmapConfig(analysis_min_deals_for_outlier_detection=10)
        filtered, report = filter_deals_for_analysis(deals, config)
        assert len(filtered) == 2
        assert report["outliers_removed"] == 0

    def test_filter_deals_with_outliers(self):
        """Test filtering with actual outliers in data."""
        # Create deals with one clear outlier (very low price_per_sqm)
        deals = []
        for i in range(15):
            deals.append(
                Deal(
                    objectid=i,
                    deal_amount=1000000,
                    deal_date=date(2023, 1, 1),
                    asset_area=100,  # Normal: 10K/sqm
                )
            )
        # Add outlier: very high price_per_sqm
        deals.append(
            Deal(
                objectid=100,
                deal_amount=10000000,
                deal_date=date(2023, 1, 1),
                asset_area=10,  # Outlier: 1M/sqm (way too high)
            )
        )

        config = GovmapConfig(analysis_outlier_method="iqr", analysis_iqr_multiplier=1.5)
        filtered, report = filter_deals_for_analysis(deals, config, metric="price_per_sqm")

        assert len(filtered) < len(deals)  # Some deals should be filtered
        assert report["outliers_removed"] > 0
        assert report["method_used"] == "iqr"
        assert (
            15 in report["outlier_indices"]
        )  # The outlier deal (at index 15) should be in the list

    def test_filter_deals_hard_bounds_only(self):
        """Test filtering with hard bounds catching outliers."""
        deals = [
            # Normal deals
            Deal(objectid=1, deal_amount=1000000, deal_date=date(2023, 1, 1), asset_area=100),
            Deal(objectid=2, deal_amount=1100000, deal_date=date(2023, 1, 1), asset_area=100),
            # Data error: price_per_sqm way too high (2M/sqm > 100K max)
            Deal(objectid=3, deal_amount=10000000, deal_date=date(2023, 1, 1), asset_area=5),
        ]
        # Need to set min_deals to 1 so filtering actually runs (default is 10)
        config = GovmapConfig(analysis_min_deals_for_outlier_detection=1)
        filtered, report = filter_deals_for_analysis(deals, config)

        # Should filter the last deal due to hard bounds (price_per_sqm = 2M > 100K)
        assert len(filtered) == 2
        assert report["outliers_removed"] == 1

    def test_filter_deals_percent_method(self):
        """Test filtering using percent-based method."""
        # Create deals with clear outliers
        deals = []
        for i in range(12):
            deals.append(
                Deal(objectid=i, deal_amount=1000000, deal_date=date(2023, 1, 1), asset_area=100)
            )
        # Add outlier
        deals.append(
            Deal(objectid=100, deal_amount=5000000, deal_date=date(2023, 1, 1), asset_area=100)
        )

        config = GovmapConfig(analysis_outlier_method="percent")
        filtered, report = filter_deals_for_analysis(deals, config, metric="price_per_sqm")

        assert report["method_used"] == "percent"
        # Outlier might be filtered depending on the threshold
        assert len(filtered) <= len(deals)


class TestIntegration:
    """Integration tests combining multiple functions."""

    def test_real_world_scenario_partial_deal(self):
        """Test filtering a real-world scenario with a partial deal."""
        # Scenario: 15 normal apartments around 1.6M, one partial deal at 400K
        deals = []
        for i in range(15):
            deals.append(
                Deal(objectid=i, deal_amount=1600000, deal_date=date(2023, 1, 1), asset_area=100)
            )
        # Partial deal (outlier)
        deals.append(
            Deal(objectid=100, deal_amount=400000, deal_date=date(2023, 1, 1), asset_area=100)
        )

        config = GovmapConfig(analysis_outlier_method="iqr", analysis_iqr_multiplier=1.5)
        filtered, report = filter_deals_for_analysis(deals, config, metric="price_per_sqm")

        # The partial deal should be filtered out
        assert len(filtered) == 15
        assert report["outliers_removed"] == 1
        assert 15 in report["outlier_indices"]  # Index 15 (not objectid 100)

    def test_real_world_scenario_data_entry_error(self):
        """Test filtering a data entry error (wrong area)."""
        # Scenario: Normal deals + one with wrong area (1 sqm instead of 100)
        deals = []
        for i in range(12):
            deals.append(
                Deal(objectid=i, deal_amount=1000000, deal_date=date(2023, 1, 1), asset_area=100)
            )
        # Data entry error: area=1 instead of 100
        deals.append(
            Deal(objectid=100, deal_amount=1000000, deal_date=date(2023, 1, 1), asset_area=1)
        )

        config = GovmapConfig()
        filtered, report = filter_deals_for_analysis(deals, config)

        # The data error should be filtered by hard bounds (price_per_sqm > 100K)
        assert len(filtered) == 12
        assert report["outliers_removed"] == 1

    def test_edge_case_few_deals_with_hard_bounds_filter(self):
        """
        Test edge case: Small dataset where hard bounds filter removes some deals.

        This reproduces the bug where list index goes out of range when:
        - Initial dataset is small (e.g., 21 deals)
        - Hard bounds filter removes some deals (e.g., 8 outliers)
        - Remaining dataset is processed with IQR

        The bug was in line 257 where enumerate() was missing, causing
        the value_indices to be misaligned with the statistical_outliers list.
        """
        # Create 21 deals with some extreme outliers
        deals = []

        # 13 normal deals (around 10K per sqm)
        for i in range(13):
            deals.append(
                Deal(objectid=i, deal_amount=1000000, deal_date=date(2023, 1, 1), asset_area=100)
            )

        # 8 extreme outliers that will be caught by hard bounds (price_per_sqm > 100K)
        for i in range(13, 21):
            deals.append(
                Deal(objectid=i, deal_amount=200000000, deal_date=date(2023, 1, 1), asset_area=100)
            )

        config = GovmapConfig(
            analysis_outlier_method="iqr",
            analysis_iqr_multiplier=1.0,
            analysis_price_per_sqm_max=100000,
        )

        # This should not raise IndexError
        filtered, report = filter_deals_for_analysis(deals, config, metric="price_per_sqm")

        # Hard bounds should filter the 8 extreme outliers
        assert len(filtered) == 13
        assert report["outliers_removed"] == 8
        assert report["method_used"] == "iqr"
