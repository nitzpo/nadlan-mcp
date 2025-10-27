# Testing Strategy

## Overview

Nadlan-MCP uses a three-tier testing approach:
1. **Fast unit tests** - Cached fixtures, run in <1s (default)
2. **E2E smoke tests** - Minimal API calls, run in ~5s (verify API works)
3. **Comprehensive E2E tests** - Full API coverage, run in ~5min (optional)

## Running Tests

### Default: Fast Unit Tests Only
```bash
pytest tests/ --ignore=tests/e2e/
# Result: 180 passed, 1 skipped in 0.39s
```

### E2E Smoke Tests (Fast)
```bash
pytest tests/e2e/test_mcp_tools.py -m integration
# Result: 4 passed in 4.77s
```

### Comprehensive E2E Tests (Slow - Optional)
```bash
pytest tests/e2e/test_mcp_tools_comprehensive.py -m integration
# Result: 11 passed in 5m36s
```

### All Tests
```bash
pytest tests/
```

## Test Structure

### Fast Unit Tests (`tests/`)
- **174 tests** covering all core functionality
- Use cached API responses from `tests/fixtures/`
- Mock `GovmapClient` to avoid real API calls
- Run in **0.39 seconds**

Key test files:
- `tests/govmap/test_models.py` - Pydantic model validation (36 tests)
- `tests/govmap/test_utils.py` - Helper functions (45 tests)
- `tests/govmap/test_validators.py` - Input validation (24 tests)
- `tests/test_govmap_client.py` - Client and business logic (41 tests)
- `tests/test_fastmcp_tools.py` - MCP tool integration (22 tests)
- `tests/test_mcp_tools_fast.py` - Fast MCP tool tests with fixtures (6 tests)

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

## Fixtures

Cached API responses in `tests/fixtures/`:
- `autocomplete_response.json` - Address search results
- `street_deals.json` - Street-level deal data
- `neighborhood_deals.json` - Neighborhood-level deal data
- `polygon_metadata.json` - Polygon metadata from radius search

These fixtures are generated from real API calls and updated as needed.

## Test Markers

Configured in `pytest.ini`:
- `@pytest.mark.integration` - Slow tests requiring real API calls
- `@pytest.mark.unit` - Fast unit tests (default)

## Performance Comparison

| Test Suite | Count | Duration | Speed |
|------------|-------|----------|-------|
| Fast unit tests | 180 | 0.39s | 462 tests/sec |
| E2E smoke tests | 4 | 4.77s | 0.84 tests/sec |
| Comprehensive E2E | 11 | 5m36s | 0.033 tests/sec |

**Unit tests are 12x faster than smoke tests, 860x faster than comprehensive E2E!**

## CI/CD Recommendations

### PR Checks (~5s)
```bash
# Run unit tests + smoke tests
pytest tests/ --ignore=tests/e2e/test_mcp_tools_comprehensive.py
```

### Nightly Build (~6min)
```bash
# Run all tests including comprehensive E2E
pytest tests/
```

### Quick Verification (<5s)
```bash
# Just smoke tests to verify API works
pytest tests/e2e/test_mcp_tools.py -m integration
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
