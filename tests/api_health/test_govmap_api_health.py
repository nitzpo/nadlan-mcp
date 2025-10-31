"""
Govmap API health check tests.

These tests verify the Govmap API is working and hasn't changed significantly.
Run periodically (e.g., weekly) with: pytest -m api_health

IMPORTANT: These make real API calls and take longer to run.
"""

import pytest

from nadlan_mcp.govmap import GovmapClient
from nadlan_mcp.govmap.models import AutocompleteResponse, Deal


@pytest.fixture
def client():
    """Create a real Govmap client (no mocking)."""
    return GovmapClient()


class TestAutocompleteAPIHealth:
    """Test autocomplete API endpoint health."""

    @pytest.mark.api_health
    def test_autocomplete_returns_results(self, client):
        """Verify autocomplete returns results for known address."""
        response = client.autocomplete_address("סוקולוב 38 חולון")

        assert isinstance(response, AutocompleteResponse)
        assert response.results_count > 0
        assert len(response.results) > 0
        assert response.results[0].text is not None

    @pytest.mark.api_health
    def test_autocomplete_response_structure(self, client):
        """Verify autocomplete response has expected structure."""
        response = client.autocomplete_address("דיזנגוף תל אביב")

        # Check response model fields exist
        assert hasattr(response, "results_count")
        assert hasattr(response, "results")

        # Check result fields
        if len(response.results) > 0:
            result = response.results[0]
            assert hasattr(result, "id")
            assert hasattr(result, "text")
            assert hasattr(result, "type")
            assert hasattr(result, "coordinates")

    @pytest.mark.api_health
    def test_autocomplete_coordinates_present(self, client):
        """Verify autocomplete returns coordinates for addresses."""
        response = client.autocomplete_address("רוטשילד 1 תל אביב")

        assert len(response.results) > 0
        # At least one result should have coordinates
        has_coordinates = any(r.coordinates is not None for r in response.results)
        assert has_coordinates, "No results have coordinates"


class TestDealsAPIHealth:
    """Test deals API endpoints health."""

    @pytest.mark.api_health
    def test_get_deals_by_radius_works(self, client):
        """Verify get_deals_by_radius returns data."""
        # Use known working coordinates from E2E tests (Holon area)
        # client.get_deals_by_radius expects (lon, lat) tuple in ITM format
        lon, lat = 3870928.84, 3766290.19

        polygons = client.get_deals_by_radius((lon, lat), radius=100)

        # Should return some polygon data
        assert isinstance(polygons, list)
        assert len(polygons) > 0

    @pytest.mark.api_health
    def test_get_street_deals_works(self, client):
        """Verify get_street_deals returns deals."""
        # First get a polygon ID from autocomplete
        response = client.autocomplete_address("סוקולוב 38 חולון")
        assert len(response.results) > 0

        coords = response.results[0].coordinates
        assert coords is not None, "Address has no coordinates"

        # Get polygons near this address
        polygons = client.get_deals_by_radius((coords.longitude, coords.latitude), radius=50)
        assert len(polygons) > 0, "No polygons found"

        # Get street deals for first polygon
        polygon_id = polygons[0].get("polygon_id")
        assert polygon_id is not None, "Polygon has no ID"

        deals = client.get_street_deals(polygon_id, limit=10)

        # Verify deals structure
        assert isinstance(deals, list)
        if len(deals) > 0:
            deal = deals[0]
            assert isinstance(deal, Deal)
            assert deal.objectid is not None
            assert deal.deal_amount is not None

    @pytest.mark.api_health
    def test_deal_model_fields_present(self, client):
        """Verify Deal model has expected fields."""
        # Get some real deals
        response = client.autocomplete_address("דיזנגוף 50 תל אביב")
        if len(response.results) == 0:
            pytest.skip("No autocomplete results")

        coords = response.results[0].coordinates
        if coords is None:
            pytest.skip("No coordinates")

        polygons = client.get_deals_by_radius((coords.longitude, coords.latitude), radius=50)
        if len(polygons) == 0:
            pytest.skip("No polygons")

        polygon_id = polygons[0].get("polygon_id")
        deals = client.get_street_deals(polygon_id, limit=5)

        if len(deals) == 0:
            pytest.skip("No deals found")

        deal = deals[0]

        # Check required fields
        assert hasattr(deal, "objectid")
        assert hasattr(deal, "deal_amount")
        assert hasattr(deal, "deal_date")

        # Check common optional fields
        assert hasattr(deal, "asset_area")
        assert hasattr(deal, "property_type_description")
        assert hasattr(deal, "rooms")
        assert hasattr(deal, "floor")

        # Check computed field
        assert hasattr(deal, "price_per_sqm")


class TestAPIDataQuality:
    """Test data quality from API."""

    @pytest.mark.api_health
    def test_deal_amounts_reasonable(self, client):
        """Verify deal amounts are in reasonable range."""
        response = client.autocomplete_address("חולון")
        if len(response.results) == 0:
            pytest.skip("No results")

        coords = response.results[0].coordinates
        if coords is None:
            pytest.skip("No coordinates")

        polygons = client.get_deals_by_radius((coords.longitude, coords.latitude), radius=100)
        if len(polygons) == 0:
            pytest.skip("No polygons")

        polygon_id = polygons[0].get("polygon_id")
        deals = client.get_street_deals(polygon_id, limit=20)

        if len(deals) == 0:
            pytest.skip("No deals")

        # Check deal amounts are reasonable (10K to 100M NIS)
        for deal in deals:
            if deal.deal_amount > 0:
                assert 10000 <= deal.deal_amount <= 100000000, (
                    f"Deal amount {deal.deal_amount} outside reasonable range"
                )

    @pytest.mark.api_health
    def test_dates_are_recent(self, client):
        """Verify deals have recent dates."""
        from datetime import date, timedelta

        response = client.autocomplete_address("תל אביב")
        if len(response.results) == 0:
            pytest.skip("No results")

        coords = response.results[0].coordinates
        if coords is None:
            pytest.skip("No coordinates")

        polygons = client.get_deals_by_radius((coords.longitude, coords.latitude), radius=100)
        if len(polygons) == 0:
            pytest.skip("No polygons")

        polygon_id = polygons[0].get("polygon_id")
        deals = client.get_street_deals(polygon_id, limit=50)

        if len(deals) == 0:
            pytest.skip("No deals")

        # At least some deals should be from last 5 years
        cutoff = date.today() - timedelta(days=5 * 365)
        recent_deals = [d for d in deals if isinstance(d.deal_date, date) and d.deal_date >= cutoff]

        assert len(recent_deals) > 0, "No recent deals found (within last 5 years)"


class TestAPIIntegration:
    """Test full integration workflows."""

    @pytest.mark.api_health
    def test_full_address_to_deals_workflow(self, client):
        """Test complete workflow: address -> coordinates -> polygons -> deals."""
        # Step 1: Autocomplete
        response = client.autocomplete_address("רוטשילד 1 תל אביב")
        assert len(response.results) > 0, "Autocomplete failed"

        # Step 2: Get coordinates
        coords = response.results[0].coordinates
        assert coords is not None, "No coordinates returned"

        # Step 3: Get polygons
        polygons = client.get_deals_by_radius((coords.longitude, coords.latitude), radius=50)
        assert len(polygons) > 0, "No polygons found"

        # Step 4: Get deals
        polygon_id = polygons[0].get("polygon_id")
        deals = client.get_street_deals(polygon_id, limit=10)

        # Should complete without errors
        assert isinstance(deals, list), "Deals should be a list"

    @pytest.mark.api_health
    def test_api_response_times_reasonable(self, client):
        """Verify API responds within reasonable time."""
        import time

        # Test autocomplete response time
        start = time.time()
        client.autocomplete_address("תל אביב")
        autocomplete_time = time.time() - start

        assert autocomplete_time < 5.0, f"Autocomplete took {autocomplete_time:.2f}s (too slow)"

        # Test deals query response time
        response = client.autocomplete_address("חולון")
        if len(response.results) > 0 and response.results[0].coordinates:
            coords = response.results[0].coordinates

            start = time.time()
            client.get_deals_by_radius((coords.longitude, coords.latitude), radius=50)
            deals_time = time.time() - start

            assert deals_time < 10.0, f"Deals query took {deals_time:.2f}s (too slow)"
