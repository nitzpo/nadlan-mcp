# API Health Check Tests

These tests verify that the Govmap API is functioning correctly and hasn't changed in breaking ways.

## Purpose

- Verify API endpoints are accessible
- Check response structure matches expectations
- Validate data quality (reasonable values, recent dates)
- Monitor API performance

## Running Health Checks

### Run all health checks
```bash
pytest -m api_health
```

### Run specific health check file
```bash
pytest tests/api_health/test_govmap_api_health.py -m api_health
```

### Run with verbose output
```bash
pytest -m api_health -v
```

## When to Run

- **Weekly**: Automated CI/CD schedule
- **Before releases**: Manual verification
- **After API changes**: When Govmap API is updated
- **When debugging**: If production issues occur

## Notes

- These tests make **real API calls** (no mocking)
- Tests may be slow (network latency)
- Tests may fail due to:
  - Network issues
  - API rate limiting
  - API maintenance
  - API breaking changes

## What to Do If Tests Fail

1. **Check network connectivity** - Ensure you can access govmap.gov.il
2. **Check API status** - Visit the Govmap website to see if it's down
3. **Review error messages** - Determine if it's a data structure change
4. **Update models** - If API response format changed, update Pydantic models
5. **Update tests** - If test expectations were wrong, update test assertions

## Test Categories

### TestAutocompleteAPIHealth
- Autocomplete endpoint works
- Response structure is correct
- Coordinates are present

### TestDealsAPIHealth
- Deals by radius endpoint works
- Street deals endpoint works
- Deal model fields are present

### TestAPIDataQuality
- Deal amounts are reasonable
- Dates are recent

### TestAPIIntegration
- Full workflow works (address → deals)
- API response times are reasonable
