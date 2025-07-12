"""
Pytest configuration for nadlan_mcp tests.
"""

import pytest
from unittest.mock import Mock


@pytest.fixture
def mock_api_response():
    """Fixture providing a mock API response."""
    mock_response = Mock()
    mock_response.raise_for_status.return_value = None
    return mock_response


@pytest.fixture
def sample_autocomplete_response():
    """Fixture providing a sample autocomplete response."""
    return {
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


@pytest.fixture
def sample_deals_response():
    """Fixture providing a sample deals response."""
    return {
        "totalCount": "2",
        "data": [
            {
                "objectid": 123,
                "dealAmount": 1000000,
                "dealDate": "2025-01-01T00:00:00.000Z",
                "assetArea": 100,
                "settlementNameHeb": "תל אביב-יפו",
                "propertyTypeDescription": "דירה",
                "neighborhood": "test neighborhood"
            },
            {
                "objectid": 456,
                "dealAmount": 2000000,
                "dealDate": "2025-01-15T00:00:00.000Z",
                "assetArea": 120,
                "settlementNameHeb": "תל אביב-יפو",
                "propertyTypeDescription": "דירה",
                "neighborhood": "test neighborhood"
            }
        ]
    } 