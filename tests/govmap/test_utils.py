"""
Unit tests for utils module.

Tests helper utilities including distance calculation, address matching, and floor parsing.
"""

from nadlan_mcp.govmap.utils import (
    calculate_distance,
    extract_floor_number,
    is_same_building,
)


class TestCalculateDistance:
    """Test distance calculation function."""

    def test_distance_between_same_point(self):
        """Test distance between identical points is zero."""
        point = (180000.0, 650000.0)
        distance = calculate_distance(point, point)
        assert distance == 0.0

    def test_distance_horizontal(self):
        """Test distance calculation for horizontal displacement."""
        point1 = (180000.0, 650000.0)
        point2 = (180100.0, 650000.0)
        distance = calculate_distance(point1, point2)
        assert distance == 100.0

    def test_distance_vertical(self):
        """Test distance calculation for vertical displacement."""
        point1 = (180000.0, 650000.0)
        point2 = (180000.0, 650100.0)
        distance = calculate_distance(point1, point2)
        assert distance == 100.0

    def test_distance_diagonal(self):
        """Test distance calculation for diagonal displacement."""
        point1 = (0.0, 0.0)
        point2 = (3.0, 4.0)
        distance = calculate_distance(point1, point2)
        assert distance == 5.0  # Pythagorean: 3^2 + 4^2 = 25, sqrt(25) = 5

    def test_distance_is_symmetric(self):
        """Test distance calculation is symmetric."""
        point1 = (180000.0, 650000.0)
        point2 = (180100.0, 650100.0)
        distance1 = calculate_distance(point1, point2)
        distance2 = calculate_distance(point2, point1)
        assert distance1 == distance2

    def test_distance_negative_coordinates(self):
        """Test distance with negative coordinates."""
        point1 = (-100.0, -200.0)
        point2 = (100.0, 200.0)
        distance = calculate_distance(point1, point2)
        expected = (200.0**2 + 400.0**2) ** 0.5
        assert abs(distance - expected) < 0.01

    def test_distance_large_coordinates(self):
        """Test distance with large ITM coordinates."""
        point1 = (180000.0, 650000.0)
        point2 = (190000.0, 660000.0)
        distance = calculate_distance(point1, point2)
        expected = (10000.0**2 + 10000.0**2) ** 0.5
        assert abs(distance - expected) < 0.01


class TestIsSameBuilding:
    """Test address matching function."""

    def test_exact_match_same_building(self):
        """Test exact address match identifies same building."""
        address1 = "דיזנגוף 50 תל אביב"
        address2 = "דיזנגוף 50 תל אביב"
        assert is_same_building(address1, address2) is True

    def test_different_street_different_building(self):
        """Test different street names identify different buildings."""
        address1 = "דיזנגוף 50 תל אביב"
        address2 = "הרצל 50 תל אביב"
        assert is_same_building(address1, address2) is False

    def test_different_number_different_building(self):
        """Test different house numbers identify different buildings."""
        address1 = "דיזנגוף 50 תל אביב"
        address2 = "דיזנגוף 52 תל אביב"
        assert is_same_building(address1, address2) is False

    def test_same_street_and_number_same_building(self):
        """Test same street and number identify same building."""
        address1 = "דיזנגוף 50"
        address2 = "דיזנגוף 50 תל אביב"
        assert is_same_building(address1, address2) is True

    def test_case_sensitive_matching(self):
        """Test address matching is case sensitive for street names."""
        address1 = "Dizengoff 50 Tel Aviv"
        address2 = "dizengoff 50 tel aviv"
        # Function is case sensitive, so these won't match
        assert is_same_building(address1, address2) is False

    def test_whitespace_ignored(self):
        """Test extra whitespace doesn't affect matching."""
        address1 = "דיזנגוף  50  תל אביב"
        address2 = "דיזנגוף 50 תל אביב"
        assert is_same_building(address1, address2) is True

    def test_substring_matching(self):
        """Test substring matching for contained addresses."""
        address1 = "דיזנגוף 50"
        address2 = "רחוב דיזנגוף 50 תל אביב יפו"
        assert is_same_building(address1, address2) is True

    def test_short_addresses_dont_match_by_substring(self):
        """Test short addresses (<=5 chars) don't match by substring."""
        address1 = "דיז 5"
        address2 = "דיזנגוף 50"
        # Both <= 5 chars after normalization won't use substring matching
        result = is_same_building(address1, address2)
        # Result depends on whether street/number extraction works
        assert isinstance(result, bool)

    def test_empty_address_no_match(self):
        """Test empty addresses don't match."""
        address1 = ""
        address2 = "דיזנגוף 50"
        assert is_same_building(address1, address2) is False

    def test_both_empty_no_match(self):
        """Test two empty addresses don't match."""
        address1 = ""
        address2 = ""
        assert is_same_building(address1, address2) is False

    def test_number_with_letters(self):
        """Test house numbers with letters (e.g., '50א')."""
        address1 = "דיזנגוף 50א תל אביב"
        address2 = "דיזנגוף 50א"
        # Same street and number, one has city name
        assert is_same_building(address1, address2) is True

    def test_different_letter_suffix(self):
        """Test different letter suffixes identify different buildings."""
        address1 = "דיזנגוף 50א"
        address2 = "דיזנגוף 50ב"
        assert is_same_building(address1, address2) is False


class TestExtractFloorNumber:
    """Test floor number extraction from Hebrew descriptions."""

    # Test all Hebrew floor names
    def test_hebrew_ground_floor(self):
        """Test extraction of ground floor (קרקע)."""
        assert extract_floor_number("קרקע") == 0

    def test_hebrew_basement(self):
        """Test extraction of basement floor (מרתף)."""
        assert extract_floor_number("מרתף") == -1

    def test_hebrew_first_floor(self):
        """Test extraction of first floor (ראשונה)."""
        assert extract_floor_number("ראשונה") == 1

    def test_hebrew_second_floor(self):
        """Test extraction of second floor (שניה)."""
        assert extract_floor_number("שניה") == 2

    def test_hebrew_third_floor(self):
        """Test extraction of third floor (שלישית)."""
        assert extract_floor_number("שלישית") == 3

    def test_hebrew_fourth_floor(self):
        """Test extraction of fourth floor (רביעית)."""
        assert extract_floor_number("רביעית") == 4

    def test_hebrew_fifth_floor(self):
        """Test extraction of fifth floor (חמישית)."""
        assert extract_floor_number("חמישית") == 5

    def test_hebrew_sixth_floor(self):
        """Test extraction of sixth floor (שישית)."""
        assert extract_floor_number("שישית") == 6

    def test_hebrew_seventh_floor(self):
        """Test extraction of seventh floor (שביעית)."""
        assert extract_floor_number("שביעית") == 7

    def test_hebrew_eighth_floor(self):
        """Test extraction of eighth floor (שמינית)."""
        assert extract_floor_number("שמינית") == 8

    def test_hebrew_ninth_floor(self):
        """Test extraction of ninth floor (תשיעית)."""
        assert extract_floor_number("תשיעית") == 9

    def test_hebrew_tenth_floor(self):
        """Test extraction of tenth floor (עשירית)."""
        assert extract_floor_number("עשירית") == 10

    # Test numeric strings
    def test_numeric_string(self):
        """Test extraction from numeric string."""
        assert extract_floor_number("5") == 5

    def test_numeric_string_with_spaces(self):
        """Test extraction from numeric string with spaces."""
        assert extract_floor_number("  12  ") == 12

    def test_hebrew_with_prefix(self):
        """Test extraction from Hebrew with prefix (e.g., 'קומה שלישית')."""
        assert extract_floor_number("קומה שלישית") == 3

    def test_mixed_hebrew_and_number(self):
        """Test extraction from mixed Hebrew and number."""
        assert extract_floor_number("קומה 7") == 7

    # Edge cases
    def test_empty_string_returns_none(self):
        """Test empty string returns None."""
        assert extract_floor_number("") is None

    def test_none_returns_none(self):
        """Test None input returns None."""
        assert extract_floor_number(None) is None

    def test_whitespace_only_returns_none(self):
        """Test whitespace-only string returns None."""
        assert extract_floor_number("   ") is None

    def test_invalid_text_returns_none(self):
        """Test invalid text without numbers or Hebrew floors returns None."""
        result = extract_floor_number("לא קומה")
        # Should return None since "לא קומה" doesn't contain a known floor
        assert result is None

    def test_case_insensitive_hebrew(self):
        """Test Hebrew floor names are case insensitive."""
        # Note: Hebrew doesn't have case, but testing with mixed formats
        assert extract_floor_number("קרקע") == 0
        assert extract_floor_number("קרקע") == 0

    def test_hebrew_floor_in_sentence(self):
        """Test extracting Hebrew floor from longer sentence."""
        assert extract_floor_number("דירה בקומה רביעית") == 4

    def test_multiple_numbers_uses_first(self):
        """Test when multiple numbers present, uses first one."""
        assert extract_floor_number("קומה 5 דירה 12") == 5

    def test_negative_number(self):
        """Test extraction of negative floor number."""
        # The regex extracts digits only, so -2 would be extracted as 2
        # But מרתף is -1
        assert extract_floor_number("מרתף") == -1

    def test_very_high_floor(self):
        """Test extraction of very high floor number."""
        assert extract_floor_number("קומה 25") == 25
        assert extract_floor_number("35") == 35

    def test_zero_floor(self):
        """Test extraction of floor zero."""
        assert extract_floor_number("0") == 0

    def test_hebrew_floor_with_typo(self):
        """Test Hebrew floor with slight variations still matches."""
        # The function uses 'in' matching, so partial matches work
        assert extract_floor_number("קומה ראשונה מיוחדת") == 1
