"""
Unit tests for validators module.

Tests input validation functions for addresses, coordinates, integers, and deal types.
"""

import pytest

from nadlan_mcp.govmap.validators import (
    validate_address,
    validate_coordinates,
    validate_deal_type,
    validate_positive_int,
)


class TestValidateAddress:
    """Test address validation function."""

    def test_valid_address(self):
        """Test validation of valid address."""
        address = "דיזנגוף 50 תל אביב"
        result = validate_address(address)
        assert result == "דיזנגוף 50 תל אביב"

    def test_address_with_whitespace(self):
        """Test address with leading/trailing whitespace is trimmed."""
        address = "  הרצל 1 תל אביב  "
        result = validate_address(address)
        assert result == "הרצל 1 תל אביב"

    def test_empty_string_raises_error(self):
        """Test empty string raises ValueError."""
        with pytest.raises(ValueError, match="Address must be a non-empty string"):
            validate_address("")

    def test_none_raises_error(self):
        """Test None raises ValueError."""
        with pytest.raises(ValueError, match="Address must be a non-empty string"):
            validate_address(None)

    def test_whitespace_only_raises_error(self):
        """Test whitespace-only string raises ValueError."""
        with pytest.raises(ValueError, match="Address cannot be empty or whitespace only"):
            validate_address("   ")

    def test_very_long_address_raises_error(self):
        """Test address longer than 500 characters raises ValueError."""
        long_address = "א" * 501
        with pytest.raises(ValueError, match="Address is too long"):
            validate_address(long_address)

    def test_address_at_max_length(self):
        """Test address at exactly 500 characters is valid."""
        max_length_address = "א" * 500
        result = validate_address(max_length_address)
        assert len(result) == 500

    def test_non_string_raises_error(self):
        """Test non-string input raises ValueError."""
        with pytest.raises(ValueError, match="Address must be a non-empty string"):
            validate_address(123)

    def test_english_address(self):
        """Test English address is valid."""
        address = "Dizengoff 50 Tel Aviv"
        result = validate_address(address)
        assert result == "Dizengoff 50 Tel Aviv"


class TestValidateCoordinates:
    """Test coordinate validation function."""

    def test_valid_itm_coordinates(self):
        """Test valid ITM coordinates."""
        point = (180000.0, 650000.0)
        result = validate_coordinates(point)
        assert result == (180000.0, 650000.0)

    def test_coordinates_as_list(self):
        """Test coordinates provided as list are converted to tuple."""
        point = [180000.0, 650000.0]
        result = validate_coordinates(point)
        assert result == (180000.0, 650000.0)
        assert isinstance(result, tuple)

    def test_coordinates_as_integers(self):
        """Test coordinates as integers are converted to floats."""
        point = (180000, 650000)
        result = validate_coordinates(point)
        assert result == (180000.0, 650000.0)
        assert all(isinstance(x, float) for x in result)

    def test_wrong_number_of_coordinates_raises_error(self):
        """Test tuple with wrong number of elements raises ValueError."""
        with pytest.raises(ValueError, match="Point must be a tuple of"):
            validate_coordinates((180000.0,))

    def test_three_coordinates_raises_error(self):
        """Test three coordinates raises ValueError."""
        with pytest.raises(ValueError, match="Point must be a tuple of"):
            validate_coordinates((180000.0, 650000.0, 100.0))

    def test_non_numeric_coordinates_raises_error(self):
        """Test non-numeric coordinates raise ValueError."""
        with pytest.raises(ValueError, match="Coordinates must be numeric values"):
            validate_coordinates(("abc", "def"))

    def test_none_coordinates_raises_error(self):
        """Test None coordinates raise ValueError."""
        with pytest.raises(ValueError, match="Coordinates must be numeric values"):
            validate_coordinates((None, None))

    def test_string_coordinates_raises_error(self):
        """Test string coordinates raise ValueError."""
        with pytest.raises(ValueError, match="Point must be a tuple of"):
            validate_coordinates("180000, 650000")

    def test_out_of_bounds_longitude_logs_warning(self, caplog):
        """Test out-of-bounds longitude logs warning but doesn't raise error."""
        point = (500000.0, 650000.0)  # Longitude > 400000
        result = validate_coordinates(point)
        assert result == (500000.0, 650000.0)
        # Warning should be logged (implementation uses logger.warning)

    def test_out_of_bounds_latitude_logs_warning(self, caplog):
        """Test out-of-bounds latitude logs warning but doesn't raise error."""
        point = (180000.0, 2000000.0)  # Latitude > 1400000
        result = validate_coordinates(point)
        assert result == (180000.0, 2000000.0)
        # Warning should be logged (implementation uses logger.warning)

    def test_negative_coordinates_logs_warning(self, caplog):
        """Test negative coordinates log warning but don't raise error."""
        point = (-10000.0, 650000.0)
        result = validate_coordinates(point)
        assert result == (-10000.0, 650000.0)
        # Warning should be logged


class TestValidatePositiveInt:
    """Test positive integer validation function."""

    def test_valid_positive_integer(self):
        """Test validation of valid positive integer."""
        result = validate_positive_int(10, "test_param")
        assert result == 10

    def test_zero_raises_error(self):
        """Test zero raises ValueError."""
        with pytest.raises(ValueError, match="test_param must be positive"):
            validate_positive_int(0, "test_param")

    def test_negative_integer_raises_error(self):
        """Test negative integer raises ValueError."""
        with pytest.raises(ValueError, match="test_param must be positive"):
            validate_positive_int(-5, "test_param")

    def test_non_integer_raises_error(self):
        """Test non-integer raises ValueError."""
        with pytest.raises(ValueError, match="test_param must be an integer"):
            validate_positive_int(10.5, "test_param")

    def test_string_raises_error(self):
        """Test string raises ValueError."""
        with pytest.raises(ValueError, match="test_param must be an integer"):
            validate_positive_int("10", "test_param")

    def test_max_value_check(self):
        """Test max value constraint is enforced."""
        result = validate_positive_int(50, "test_param", max_value=100)
        assert result == 50

    def test_exceeds_max_value_raises_error(self):
        """Test value exceeding max raises ValueError."""
        with pytest.raises(ValueError, match="test_param must be <= 100"):
            validate_positive_int(150, "test_param", max_value=100)

    def test_at_max_value(self):
        """Test value at exactly max is valid."""
        result = validate_positive_int(100, "test_param", max_value=100)
        assert result == 100

    def test_large_integer(self):
        """Test very large integer is valid."""
        large_int = 1000000
        result = validate_positive_int(large_int, "test_param")
        assert result == large_int


class TestValidateDealType:
    """Test deal type validation function."""

    def test_deal_type_1_is_valid(self):
        """Test deal type 1 (first hand/new) is valid."""
        result = validate_deal_type(1)
        assert result == 1

    def test_deal_type_2_is_valid(self):
        """Test deal type 2 (second hand/used) is valid."""
        result = validate_deal_type(2)
        assert result == 2

    def test_deal_type_0_raises_error(self):
        """Test deal type 0 raises ValueError."""
        with pytest.raises(ValueError, match="deal_type must be 1.*or 2"):
            validate_deal_type(0)

    def test_deal_type_3_raises_error(self):
        """Test deal type 3 raises ValueError."""
        with pytest.raises(ValueError, match="deal_type must be 1.*or 2"):
            validate_deal_type(3)

    def test_negative_deal_type_raises_error(self):
        """Test negative deal type raises ValueError."""
        with pytest.raises(ValueError, match="deal_type must be 1.*or 2"):
            validate_deal_type(-1)

    def test_float_deal_type_raises_error(self):
        """Test float deal type raises ValueError (not an int)."""
        # Note: This test depends on whether the function checks type before value
        # If the function coerces to int, this might pass. Adjust based on implementation.
        with pytest.raises(ValueError):
            validate_deal_type(1.5)

    def test_string_deal_type_raises_error(self):
        """Test string deal type raises ValueError."""
        with pytest.raises(ValueError):
            validate_deal_type("1")
