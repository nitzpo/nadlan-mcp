# Migration Guide: v1.x → v2.0.0

## Overview

Version 2.0.0 introduces **Pydantic v2 models** throughout the codebase, replacing dict-based data structures with type-safe, validated models. This is a **breaking change** that improves type safety, validation, and developer experience.

## Breaking Changes Summary

### All API Methods Now Return Pydantic Models

| Method | v1.x Return Type | v2.0 Return Type |
|--------|------------------|------------------|
| `autocomplete_address()` | `Dict` | `AutocompleteResponse` |
| `get_deals_by_radius()` | `List[Dict]` | `List[Deal]` |
| `get_street_deals()` | `List[Dict]` | `List[Deal]` |
| `get_neighborhood_deals()` | `List[Dict]` | `List[Deal]` |
| `find_recent_deals_for_address()` | `List[Dict]` | `List[Deal]` |
| `calculate_deal_statistics()` | `Dict` | `DealStatistics` |
| `calculate_market_activity_score()` | `Dict` | `MarketActivityScore` |
| `analyze_investment_potential()` | `Dict` | `InvestmentAnalysis` |
| `get_market_liquidity()` | `Dict` | `LiquidityMetrics` |
| `filter_deals_by_criteria()` | `List[Dict]` | `List[Deal]` |

## Migration Examples

### 1. Autocomplete Address

**Before (v1.x):**
```python
from nadlan_mcp.govmap import GovmapClient

client = GovmapClient()
result = client.autocomplete_address("סוקולוב 38 חולון")

# Dict access
count = result["resultsCount"]
first_result = result["results"][0]
address_text = first_result["text"]
coords = first_result.get("coordinates")  # May not exist
```

**After (v2.0):**
```python
from nadlan_mcp.govmap import GovmapClient

client = GovmapClient()
result = client.autocomplete_address("סוקולוב 38 חולון")

# Model attributes with type hints
count = result.results_count  # int
first_result = result.results[0]  # AutocompleteResult
address_text = first_result.text  # str
coords = first_result.coordinates  # Optional[CoordinatePoint]

# Access coordinates if available
if coords:
    lon = coords.longitude  # float
    lat = coords.latitude  # float
```

### 2. Getting Deals

**Before (v1.x):**
```python
deals = client.get_street_deals("polygon123")

for deal in deals:
    price = deal.get("dealAmount")
    area = deal.get("assetArea")

    # Manual price per sqm calculation
    if price and area and area > 0:
        price_per_sqm = price / area
    else:
        price_per_sqm = None
```

**After (v2.0):**
```python
deals = client.get_street_deals("polygon123")

for deal in deals:  # deal is a Deal model
    price = deal.deal_amount  # float (camelCase → snake_case)
    area = deal.asset_area  # Optional[float]

    # Computed field - automatically calculated!
    price_per_sqm = deal.price_per_sqm  # Optional[float]
```

### 3. Market Analysis

**Before (v1.x):**
```python
stats = client.calculate_deal_statistics(deals)

# Dict access
total = stats["total_deals"]
avg_price = stats["price_statistics"]["mean"]
property_dist = stats["property_type_distribution"]
```

**After (v2.0):**
```python
stats = client.calculate_deal_statistics(deals)

# Model attributes
total = stats.total_deals  # int
avg_price = stats.price_statistics["mean"]  # Dict[str, float]
property_dist = stats.property_type_distribution  # Dict[str, int]

# Serialize to dict if needed
stats_dict = stats.model_dump()
stats_json = stats.model_dump_json()
```

### 4. Filtering Deals

**Before (v1.x):**
```python
filtered = client.filter_deals_by_criteria(
    deals,
    property_type="דירה",
    min_rooms=3.0,
    max_rooms=4.0,
    min_price=1000000.0,
    max_price=2000000.0
)

# Returns List[Dict]
for deal in filtered:
    rooms = deal.get("rooms")
```

**After (v2.0):**
```python
# Option 1: Individual parameters (same as before)
filtered = client.filter_deals_by_criteria(
    deals,
    property_type="דירה",
    min_rooms=3.0,
    max_rooms=4.0,
    min_price=1000000.0,
    max_price=2000000.0
)

# Option 2: Use DealFilters model (NEW!)
from nadlan_mcp.govmap.models import DealFilters

filters = DealFilters(
    property_type="דירה",
    min_rooms=3.0,
    max_rooms=4.0,
    min_price=1000000.0,
    max_price=2000000.0
)
filtered = client.filter_deals_by_criteria(deals, filters=filters)

# Returns List[Deal]
for deal in filtered:
    rooms = deal.rooms  # Optional[float]
```

### 5. Serialization for MCP/JSON

**Before (v1.x):**
```python
import json

deals = client.get_street_deals("polygon123")
# Already dicts, can serialize directly
json_str = json.dumps(deals)
```

**After (v2.0):**
```python
import json

deals = client.get_street_deals("polygon123")

# Option 1: Serialize individual models
deals_dicts = [deal.model_dump() for deal in deals]
json_str = json.dumps(deals_dicts)

# Option 2: Exclude None values for cleaner output
deals_dicts = [deal.model_dump(exclude_none=True) for deal in deals]
json_str = json.dumps(deals_dicts, ensure_ascii=False)

# Option 3: Direct JSON serialization
json_str = json.dumps([deal.model_dump() for deal in deals])
```

## Field Name Changes (API → Python)

Many field names changed from camelCase (API) to snake_case (Python convention). Pydantic handles both via aliases:

| API Field (camelCase) | Python Attribute (snake_case) |
|----------------------|------------------------------|
| `dealAmount` | `deal_amount` |
| `dealDate` | `deal_date` |
| `assetArea` | `asset_area` |
| `settlementNameHeb` | `settlement_name_heb` |
| `propertyTypeDescription` | `property_type_description` |
| `streetName` | `street_name` |
| `houseNumber` | `house_number` |
| `floorNumber` | `floor_number` |
| `sourcePolygonId` | `source_polygon_id` |
| `resultsCount` | `results_count` |

**Note:** When creating models from API responses, use either name:
```python
# Both work due to Pydantic aliases
deal = Deal(dealAmount=1500000, dealDate="2024-01-15", objectid=123)
deal = Deal(deal_amount=1500000, deal_date="2024-01-15", objectid=123)
```

## New Features

### 1. Computed Fields

Models automatically calculate derived values:

```python
deal = Deal(
    objectid=123,
    deal_amount=1500000.0,
    deal_date="2024-01-15",
    asset_area=85.0
)

# Automatically computed!
assert deal.price_per_sqm == 17647.06
```

### 2. Validation

Models validate data automatically:

```python
from pydantic import ValidationError

try:
    filters = DealFilters(
        min_rooms=4.0,
        max_rooms=2.0  # Error: max < min
    )
except ValidationError as e:
    print(e)  # Clear validation error message
```

### 3. Type Hints

Full IDE autocomplete and type checking:

```python
from nadlan_mcp.govmap.models import Deal

deal: Deal = client.get_street_deals("polygon123")[0]

# IDE knows all fields and their types!
amount: float = deal.deal_amount
area: Optional[float] = deal.asset_area
```

## Updating Tests

### Mock Data

**Before (v1.x):**
```python
mock_response = Mock()
mock_response.json.return_value = {
    "resultsCount": 1,
    "results": [{"text": "חולון", "id": "123", "type": "city"}]
}
```

**After (v2.0):**
```python
mock_response = Mock()
mock_response.json.return_value = {
    "resultsCount": 1,
    "results": [{"text": "חולון", "id": "123", "type": "city"}]
}
# Client will parse this into AutocompleteResponse model
```

### Assertions

**Before (v1.x):**
```python
result = client.autocomplete_address("test")
assert result["resultsCount"] == 1
assert result["results"][0]["text"] == "חולון"
```

**After (v2.0):**
```python
from nadlan_mcp.govmap.models import AutocompleteResponse

result = client.autocomplete_address("test")
assert isinstance(result, AutocompleteResponse)
assert result.results_count == 1
assert result.results[0].text == "חולון"
```

### Deal Mocks

**Before (v1.x):**
```python
mock_deals = [
    {"dealAmount": 1500000, "assetArea": 85, "dealDate": "2024-01-15"}
]
```

**After (v2.0):**
```python
# Mock API response (will be parsed into Deal models)
mock_response.json.return_value = {
    "data": [
        {
            "objectid": 123,  # Required!
            "dealAmount": 1500000,
            "dealDate": "2024-01-15",
            "assetArea": 85
        }
    ]
}

# Or create Deal models directly in tests
from nadlan_mcp.govmap.models import Deal

mock_deals = [
    Deal(objectid=123, deal_amount=1500000, deal_date="2024-01-15", asset_area=85)
]
```

## Gradual Migration Strategy

If you can't migrate everything at once:

### 1. Use `.model_dump()` for Compatibility

```python
# Get models from v2.0 API
deals = client.get_street_deals("polygon123")

# Convert to dicts for legacy code
deals_dicts = [deal.model_dump() for deal in deals]

# Now legacy code can use dict access
for deal_dict in deals_dicts:
    price = deal_dict["deal_amount"]  # Works!
```

### 2. Wrap in Compatibility Layer

```python
class LegacyClientWrapper:
    def __init__(self):
        self.client = GovmapClient()

    def get_street_deals(self, polygon_id, **kwargs):
        """Returns dicts for backward compatibility."""
        deals = self.client.get_street_deals(polygon_id, **kwargs)
        return [deal.model_dump() for deal in deals]
```

## Benefits of Migration

✅ **Type Safety** - Full IDE autocomplete and mypy support
✅ **Validation** - Automatic data validation with clear errors
✅ **Computed Fields** - Price per sqm auto-calculated
✅ **Better DX** - Models serve as living documentation
✅ **API Compatibility** - Field aliases handle camelCase ↔ snake_case
✅ **Clear Errors** - Pydantic validation errors are very descriptive
✅ **Performance** - Pydantic v2 is extremely fast (Rust core)

## Need Help?

- **Examples:** See `tests/govmap/test_models.py` for comprehensive model usage examples
- **Documentation:** Check `ARCHITECTURE.md` for system design
- **API Reference:** All models have detailed docstrings
- **Issues:** Report migration issues at https://github.com/anthropics/nadlan-mcp/issues

---

**Version:** 2.0.0
**Date:** 2025-01-26
**Breaking Changes:** Yes - all API methods now return Pydantic models
