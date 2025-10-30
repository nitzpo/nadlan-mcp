"""
Tests for nadlan_mcp.govmap.filters module.

Comprehensive tests for filter_deals_by_criteria function.
"""

import pytest
from nadlan_mcp.govmap.filters import filter_deals_by_criteria
from nadlan_mcp.govmap.models import Deal, DealFilters


class TestFilterDealsByCriteria:
    """Test cases for filter_deals_by_criteria function."""

    @pytest.fixture
    def sample_deals(self):
        """Create sample deals for testing."""
        return [
            Deal(
                objectid=1,
                deal_amount=1000000.0,
                deal_date="2024-01-15",
                property_type_description="דירה",
                rooms=3.0,
                asset_area=80.0,
                floor_number=2,
            ),
            Deal(
                objectid=2,
                deal_amount=1500000.0,
                deal_date="2024-02-01",
                property_type_description="דירת גג",
                rooms=4.0,
                asset_area=100.0,
                floor_number=5,
            ),
            Deal(
                objectid=3,
                deal_amount=2000000.0,
                deal_date="2024-02-15",
                property_type_description="בית פרטי",
                rooms=5.0,
                asset_area=150.0,
                floor_number=0,  # Ground floor
            ),
            Deal(
                objectid=4,
                deal_amount=800000.0,
                deal_date="2024-03-01",
                property_type_description="דירה",
                rooms=2.0,
                asset_area=60.0,
                floor_number=1,
            ),
            Deal(
                objectid=5,
                deal_amount=1200000.0,
                deal_date="2024-03-15",
                property_type_description="פנטהאוז",
                rooms=4.5,
                asset_area=120.0,
                floor_number=10,
            ),
        ]

    def test_no_filters_returns_all_deals(self, sample_deals):
        """Test that with no filters, all deals are returned."""
        result = filter_deals_by_criteria(sample_deals)
        assert len(result) == 5
        assert result == sample_deals

    def test_filter_by_property_type_exact_match(self, sample_deals):
        """Test filtering by exact property type."""
        result = filter_deals_by_criteria(sample_deals, property_type="בית פרטי")
        assert len(result) == 1
        assert result[0].objectid == 3

    def test_filter_by_property_type_partial_match(self, sample_deals):
        """Test filtering by partial property type (substring)."""
        result = filter_deals_by_criteria(sample_deals, property_type="דירה")
        # Should match only "דירה" exactly (not "דירת גג" because "דירה" != "דירת")
        assert len(result) == 2
        assert set(d.objectid for d in result) == {1, 4}

    def test_filter_by_property_type_case_insensitive(self, sample_deals):
        """Test that property type filtering is case-insensitive."""
        result = filter_deals_by_criteria(sample_deals, property_type="דירה")
        result_upper = filter_deals_by_criteria(sample_deals, property_type="דירה")
        assert len(result) == len(result_upper)

    def test_filter_by_min_rooms(self, sample_deals):
        """Test filtering by minimum rooms."""
        result = filter_deals_by_criteria(sample_deals, min_rooms=4.0)
        assert len(result) == 3
        assert set(d.objectid for d in result) == {2, 3, 5}

    def test_filter_by_max_rooms(self, sample_deals):
        """Test filtering by maximum rooms."""
        result = filter_deals_by_criteria(sample_deals, max_rooms=3.0)
        assert len(result) == 2
        assert set(d.objectid for d in result) == {1, 4}

    def test_filter_by_room_range(self, sample_deals):
        """Test filtering by room range."""
        result = filter_deals_by_criteria(sample_deals, min_rooms=3.0, max_rooms=4.0)
        assert len(result) == 2
        assert set(d.objectid for d in result) == {1, 2}

    def test_filter_by_min_price(self, sample_deals):
        """Test filtering by minimum price."""
        result = filter_deals_by_criteria(sample_deals, min_price=1200000.0)
        assert len(result) == 3
        assert set(d.objectid for d in result) == {2, 3, 5}

    def test_filter_by_max_price(self, sample_deals):
        """Test filtering by maximum price."""
        result = filter_deals_by_criteria(sample_deals, max_price=1000000.0)
        assert len(result) == 2
        assert set(d.objectid for d in result) == {1, 4}

    def test_filter_by_price_range(self, sample_deals):
        """Test filtering by price range."""
        result = filter_deals_by_criteria(
            sample_deals, min_price=1000000.0, max_price=1500000.0
        )
        assert len(result) == 3
        assert set(d.objectid for d in result) == {1, 2, 5}

    def test_filter_by_min_area(self, sample_deals):
        """Test filtering by minimum area."""
        result = filter_deals_by_criteria(sample_deals, min_area=100.0)
        assert len(result) == 3
        assert set(d.objectid for d in result) == {2, 3, 5}

    def test_filter_by_max_area(self, sample_deals):
        """Test filtering by maximum area."""
        result = filter_deals_by_criteria(sample_deals, max_area=80.0)
        assert len(result) == 2
        assert set(d.objectid for d in result) == {1, 4}

    def test_filter_by_area_range(self, sample_deals):
        """Test filtering by area range."""
        result = filter_deals_by_criteria(
            sample_deals, min_area=80.0, max_area=120.0
        )
        assert len(result) == 3
        assert set(d.objectid for d in result) == {1, 2, 5}

    def test_filter_by_min_floor(self, sample_deals):
        """Test filtering by minimum floor."""
        result = filter_deals_by_criteria(sample_deals, min_floor=2)
        assert len(result) == 3
        assert set(d.objectid for d in result) == {1, 2, 5}

    def test_filter_by_max_floor(self, sample_deals):
        """Test filtering by maximum floor."""
        result = filter_deals_by_criteria(sample_deals, max_floor=2)
        assert len(result) == 3
        assert set(d.objectid for d in result) == {1, 3, 4}

    def test_filter_by_floor_range(self, sample_deals):
        """Test filtering by floor range."""
        result = filter_deals_by_criteria(sample_deals, min_floor=1, max_floor=5)
        assert len(result) == 3
        assert set(d.objectid for d in result) == {1, 2, 4}

    def test_combined_filters(self, sample_deals):
        """Test combining multiple filters."""
        result = filter_deals_by_criteria(
            sample_deals,
            property_type="דירה",
            min_rooms=3.0,
            min_price=1000000.0,
            max_price=1500000.0,
        )
        # Should match only objectid=1 (דירה with 3 rooms, price 1M)
        # objectid=2 is "דירת גג" not "דירה", so filtered out
        assert len(result) == 1
        assert set(d.objectid for d in result) == {1}

    def test_filter_using_dealfilters_model(self, sample_deals):
        """Test filtering using DealFilters model."""
        filters = DealFilters(
            property_type="דירה", min_rooms=3.0, max_rooms=4.0
        )
        result = filter_deals_by_criteria(sample_deals, filters=filters)
        # Should match only objectid=1 (דירה with 3 rooms)
        # objectid=2 is "דירת גג" not exact match
        assert len(result) == 1
        assert set(d.objectid for d in result) == {1}

    def test_filter_using_dict(self, sample_deals):
        """Test filtering using dict (converted to DealFilters)."""
        filters_dict = {
            "property_type": "דירה",
            "min_rooms": 3.0,
            "max_rooms": 4.0,
        }
        result = filter_deals_by_criteria(sample_deals, filters=filters_dict)
        # Should match only objectid=1
        assert len(result) == 1
        assert set(d.objectid for d in result) == {1}

    def test_individual_params_override_filters_model(self, sample_deals):
        """Test that individual parameters override filters model."""
        filters = DealFilters(min_rooms=5.0)  # Would match only objectid=3
        result = filter_deals_by_criteria(
            sample_deals, filters=filters, min_rooms=3.0  # Override to 3.0
        )
        # Should use min_rooms=3.0, not 5.0
        assert len(result) == 4
        assert set(d.objectid for d in result) == {1, 2, 3, 5}

    def test_filters_exclude_deals_with_missing_property_type(self):
        """Test that deals with missing property_type are excluded when filter active."""
        deals = [
            Deal(objectid=1, deal_amount=1000000, deal_date="2024-01-01", property_type_description="דירה"),
            Deal(objectid=2, deal_amount=1000000, deal_date="2024-01-01", property_type_description=None),
            Deal(objectid=3, deal_amount=1000000, deal_date="2024-01-01"),  # No property_type
        ]
        result = filter_deals_by_criteria(deals, property_type="דירה")
        assert len(result) == 1
        assert result[0].objectid == 1

    def test_filters_exclude_deals_with_missing_rooms(self):
        """Test that deals with missing rooms are excluded when filter active."""
        deals = [
            Deal(objectid=1, deal_amount=1000000, deal_date="2024-01-01", rooms=3.0),
            Deal(objectid=2, deal_amount=1000000, deal_date="2024-01-01", rooms=None),
            Deal(objectid=3, deal_amount=1000000, deal_date="2024-01-01"),  # No rooms
        ]
        result = filter_deals_by_criteria(deals, min_rooms=2.0)
        assert len(result) == 1
        assert result[0].objectid == 1

    def test_filters_exclude_deals_with_missing_area(self):
        """Test that deals with missing area are excluded when filter active."""
        deals = [
            Deal(objectid=1, deal_amount=1000000, deal_date="2024-01-01", asset_area=80.0),
            Deal(objectid=2, deal_amount=1000000, deal_date="2024-01-01", asset_area=None),
            Deal(objectid=3, deal_amount=1000000, deal_date="2024-01-01"),  # No area
        ]
        result = filter_deals_by_criteria(deals, min_area=50.0)
        assert len(result) == 1
        assert result[0].objectid == 1

    def test_empty_deals_list_returns_empty(self):
        """Test filtering empty list returns empty list."""
        result = filter_deals_by_criteria([], property_type="דירה")
        assert result == []

    def test_no_matches_returns_empty(self, sample_deals):
        """Test filtering with no matches returns empty list."""
        result = filter_deals_by_criteria(sample_deals, min_rooms=10.0)
        assert len(result) == 0

    def test_invalid_input_raises_error(self):
        """Test that invalid input raises ValueError."""
        with pytest.raises(ValueError, match="deals must be a list"):
            filter_deals_by_criteria("not a list")

    def test_invalid_room_range_raises_error(self, sample_deals):
        """Test that min_rooms > max_rooms raises error."""
        with pytest.raises(ValueError, match="min_rooms cannot be greater than max_rooms"):
            filter_deals_by_criteria(sample_deals, min_rooms=5.0, max_rooms=3.0)

    def test_invalid_price_range_raises_error(self, sample_deals):
        """Test that min_price > max_price raises error."""
        with pytest.raises(ValueError, match="min_price cannot be greater than max_price"):
            filter_deals_by_criteria(sample_deals, min_price=2000000, max_price=1000000)

    def test_invalid_area_range_raises_error(self, sample_deals):
        """Test that min_area > max_area raises error."""
        with pytest.raises(ValueError, match="min_area cannot be greater than max_area"):
            filter_deals_by_criteria(sample_deals, min_area=150.0, max_area=80.0)

    def test_invalid_floor_range_raises_error(self, sample_deals):
        """Test that min_floor > max_floor raises error."""
        with pytest.raises(ValueError, match="min_floor cannot be greater than max_floor"):
            filter_deals_by_criteria(sample_deals, min_floor=5, max_floor=2)

    def test_floor_extraction_from_floor_description(self):
        """Test floor filtering with Hebrew floor descriptions."""
        deals = [
            Deal(objectid=1, deal_amount=1000000, deal_date="2024-01-01", floor="קרקע"),  # Ground=0
            Deal(objectid=2, deal_amount=1000000, deal_date="2024-01-01", floor="קומה 3"),  # Floor 3
            Deal(objectid=3, deal_amount=1000000, deal_date="2024-01-01", floor="מרתף"),  # Basement=-1
        ]
        result = filter_deals_by_criteria(deals, min_floor=0)
        # Should match ground (0) and floor 3, but not basement (-1)
        assert len(result) == 2
        assert set(d.objectid for d in result) == {1, 2}

    @pytest.mark.parametrize(
        "min_val,max_val,expected_count",
        [
            (None, None, 5),  # No filter
            (3.0, 4.0, 2),  # Range
            (3.0, None, 4),  # Min only
            (None, 4.0, 3),  # Max only
            (10.0, 20.0, 0),  # No matches
        ],
    )
    def test_room_filtering_parametrized(self, sample_deals, min_val, max_val, expected_count):
        """Parametrized test for room filtering."""
        result = filter_deals_by_criteria(sample_deals, min_rooms=min_val, max_rooms=max_val)
        assert len(result) == expected_count
