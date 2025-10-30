# Testing Strategy

## Overview

Nadlan-MCP uses a multi-tier testing approach:
1. **Fast unit tests** - Mocked/fixture-based, run in ~12s (default)
2. **E2E smoke tests** - Minimal API calls, run in ~5s (verify API works)
3. **Comprehensive E2E tests** - Full API coverage, run in ~5min (optional)
4. **API health checks** - Weekly API monitoring, run on-demand

## Running Tests

### Default: Fast Tests (Excludes API Health Checks)
```bash
pytest tests/ -m "not api_health"
# Result: 303 passed, 1 skipped in ~12s
```

### All Tests Including API Health
```bash
pytest tests/
# Result: 313 passed, 1 skipped in ~15s (if API health checks pass)
```

### API Health Checks Only (Weekly)
```bash
pytest -m api_health -v
# Result: 10 passed (verifies Govmap API is working)
```

### E2E Smoke Tests (Fast)
```bash
pytest tests/e2e/test_mcp_tools.py
# Result: 4 passed in 4.77s
```

### Comprehensive E2E Tests (Slow - Optional)
```bash
pytest tests/e2e/test_mcp_tools_comprehensive.py
# Result: 11 passed in 5m36s
```

### With Coverage Report
```bash
pytest tests/ -m "not api_health" --cov=nadlan_mcp --cov-report=term-missing
# Result: 84% coverage
```

## Test Structure

### Fast Unit Tests (`tests/`)
- **304 tests** covering all core functionality
- Use mocked responses and fixtures
- Run in **~12 seconds**

Key test files:
- `tests/govmap/test_filters.py` - Deal filtering (36 tests)
- `tests/govmap/test_statistics.py` - Statistical calculations (32 tests)
- `tests/govmap/test_market_analysis.py` - Market analysis (40 tests)
- `tests/govmap/test_models.py` - Pydantic model validation (36 tests)
- `tests/govmap/test_utils.py` - Helper functions (42 tests)
- `tests/govmap/test_validators.py` - Input validation (32 tests)
- `tests/test_govmap_client.py` - Client and business logic (34 tests)
- `tests/test_fastmcp_tools.py` - MCP tool integration (22 tests)
- `tests/test_mcp_tools_fast.py` - Fast MCP tool tests (7 tests)
- `tests/e2e/test_mcp_tools.py` - Smoke tests (4 tests)
- `tests/e2e/test_mcp_tools_comprehensive.py` - Comprehensive E2E (11 tests)

### E2E Smoke Tests (`tests/e2e/test_mcp_tools.py`)
- **4 minimal smoke tests** with real API calls
- Verify API connectivity and basic functionality
- Use minimal data (small limits, small radius)
- Run in **4.77 seconds**

### Comprehensive E2E Tests (`tests/e2e/test_mcp_tools_comprehensive.py`)
- **11 thorough integration tests** with real API calls
- Test all 10 MCP tools with full data
- Verify complete workflow from MCP tool → API → response
- Catch API contract changes
- Run in **5min 36sec** (optional, use for releases)

### API Health Checks (`tests/api_health/`)
- **10 health check tests** for weekly API monitoring
- Verify Govmap API is functioning correctly
- Check response structure, data quality, and performance
- Marked with `@pytest.mark.api_health`
- **Does not run by default** - must be explicitly requested
- See `tests/api_health/README.md` for details

## Fixtures & Mocking

### Fixtures (`tests/fixtures/`)
Cached API responses for fast tests:
- `autocomplete_response.json` - Address search results
- `street_deals.json` - Street-level deal data
- `neighborhood_deals.json` - Neighborhood-level deal data
- `polygon_metadata.json` - Polygon metadata from radius search

### VCR.py Integration
VCR.py is configured for recording/replaying HTTP interactions:
- Configuration: `tests/vcr_config.py`
- Cassettes stored in: `tests/cassettes/`
- Fixture: `vcr_cassette` available in `tests/conftest.py`
- Record mode: `once` (record first run, replay after)

Example usage:
```python
def test_something(vcr_cassette):
    with vcr_cassette:
        # HTTP calls recorded/replayed here
        response = client.autocomplete_address("תל אביב")
```

## Test Markers

Configured in `pytest.ini`:
- `@pytest.mark.integration` - Slow tests requiring real API calls
- `@pytest.mark.unit` - Fast unit tests (default)
- `@pytest.mark.api_health` - Weekly API health checks (run separately)

## Performance Comparison

| Test Suite | Count | Duration | Speed |
|------------|-------|----------|-------|
| Fast unit tests | 304 | 12s | 25 tests/sec |
| E2E smoke tests | 4 | 4.77s | 0.84 tests/sec |
| Comprehensive E2E | 11 | 5m36s | 0.033 tests/sec |
| API health checks | 10 | ~5-10s | 1-2 tests/sec |

**Unit tests are 30x faster than smoke tests, 750x faster than comprehensive E2E!**

## CI/CD Recommendations

### PR Checks (~12s)
```bash
# Run fast tests only (excludes API health and comprehensive E2E)
pytest tests/ -m "not api_health" --ignore=tests/e2e/test_mcp_tools_comprehensive.py
```

### Nightly Build (~6min)
```bash
# Run all tests except API health
pytest tests/ -m "not api_health"
```

### Weekly API Health (~10s)
```bash
# Run API health checks to verify Govmap API
pytest -m api_health -v
```

### Full Test Suite (~6min)
```bash
# Run everything including comprehensive E2E and API health
pytest tests/
```

## Updating Fixtures

When API responses change, regenerate fixtures:

```bash
source venv/bin/activate
python << 'EOF'
import json
from nadlan_mcp.govmap import GovmapClient

client = GovmapClient()

# Update autocomplete fixture
autocomplete_response = client.autocomplete_address("חולון סוקולוב")
with open("tests/fixtures/autocomplete_response.json", "w", encoding="utf-8") as f:
    json.dump([r.model_dump() for r in autocomplete_response.results], f, ensure_ascii=False, indent=2)

# Update street deals
street_deals = client.get_street_deals("52385050", limit=10)
with open("tests/fixtures/street_deals.json", "w", encoding="utf-8") as f:
    json.dump([d.model_dump(mode='json') for d in street_deals], f, ensure_ascii=False, indent=2)

# Update neighborhood deals
neighborhood_deals = client.get_neighborhood_deals("52385050", limit=10)
with open("tests/fixtures/neighborhood_deals.json", "w", encoding="utf-8") as f:
    json.dump([d.model_dump(mode='json') for d in neighborhood_deals], f, ensure_ascii=False, indent=2)

# Update polygon metadata
polygons = client.get_deals_by_radius((3870928.84, 3766290.19), radius=500)
with open("tests/fixtures/polygon_metadata.json", "w", encoding="utf-8") as f:
    json.dump(polygons[:10], f, ensure_ascii=False, indent=2)

print("✓ Fixtures updated")
EOF
```

## Test Coverage

Run with coverage reporting:
```bash
pytest --cov=nadlan_mcp --cov-report=html
open htmlcov/index.html
```
