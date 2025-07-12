"""
Tests for the GovmapClient class.
"""

import pytest
import requests
from unittest.mock import Mock, patch
from nadlan_mcp.main import GovmapClient


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
        client = GovmapClient(custom_url)
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
        
        assert result["resultsCount"] == 1
        assert len(result["results"]) == 1
        assert result["results"][0]["text"] == "תל אביב"
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
        
        assert result["resultsCount"] == 0
        assert len(result["results"]) == 0
    
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
                "dealscount": "2",
                "settlementNameHeb": "תל אביב-יפו",
                "polygon_id": "123-456",
                "objectid": 12345
            }
        ]
        mock_response.raise_for_status.return_value = None
        
        mock_session = Mock()
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session
        
        client = GovmapClient()
        result = client.get_deals_by_radius((3870000.123, 3770000.456), radius=50)
        
        assert len(result) == 1
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
        
        assert len(result) == 1
        assert result[0]["dealAmount"] == 1000000
        assert result[0]["assetArea"] == 100
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
        
        assert len(result) == 1
        assert result[0]["dealAmount"] == 2000000
        assert result[0]["assetArea"] == 120
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
                "address": "Test Street 1"
            }
        ]
        
        # Mock neighborhood deals response
        mock_neighborhood.return_value = [
            {
                "dealId": "deal2",
                "dealAmount": 2000000,
                "dealDate": "2025-01-15T00:00:00.000Z",
                "address": "Test Street 2"
            }
        ]
        
        client = GovmapClient()
        result = client.find_recent_deals_for_address("test address", years_back=1)
        
        assert len(result) == 2
        assert result[0]["dealDate"] == "2025-01-15T00:00:00.000Z"  # Should be sorted by date
        assert result[1]["dealDate"] == "2025-01-01T00:00:00.000Z"
    
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