# Instructions for nadlan-mcp Project: Normalize Response Structure

## Problem

Different MCP tools return data in **inconsistent structures**, causing the bot to fail when interpreting results.

### Current Inconsistent Structures

**`get_valuation_comparables`** returns:
```json
{
  "total_comparables": 3,
  "statistics": {
    "total_deals": 3,
    "price_statistics": { "mean": ..., "median": ... }
  },
  "comparables": [...]  // ← Array of deals
}
```

**`find_recent_deals_for_address`** returns:
```json
{
  "market_statistics": {
    "deal_breakdown": {
      "total_deals": 4
    },
    "price_stats": { "average_price": ..., "median_price": ... }
  },
  "deals": [...]  // ← Different field name!
}
```

### The Impact

The bot code looks for:
- Deal count in: `market_statistics.deal_breakdown.total_deals`
- Deal array in: `deals`

When `get_valuation_comparables` is called:
- Bot looks for `deals` array → finds nothing (field is called `comparables`)
- Bot looks for `market_statistics.deal_breakdown.total_deals` → finds nothing (field is `total_comparables` or `statistics.total_deals`)
- Bot thinks there are **0 deals** even when MCP returned **20 deals**
- User gets: "לא מצאתי עסקאות ספציפיות" (I didn't find specific deals)

---

## Solution: Normalize All MCP Tool Responses

All MCP tools should return data in a **consistent structure**. I recommend standardizing on this format:

### Recommended Standard Structure

```json
{
  "search_parameters": {
    // Tool-specific search parameters that were used
    "address": "...",
    "years_back": 2,
    // ... other params
  },
  "market_statistics": {
    "deal_breakdown": {
      "total_deals": N,              // ← Always here
      "same_building_deals": 0,      // Optional: only if relevant
      "street_deals": 0,             // Optional: only if relevant
      "neighborhood_deals": 0        // Optional: only if relevant
    },
    "price_statistics": {            // ← Standardize field name
      "mean": 1750000.0,             // Use "mean" not "average_price"
      "median": 1800000.0,           // Use "median" not "median_price"
      "min": 1443000.0,
      "max": 2100000.0,
      "p25": 1500000.0,
      "p75": 2000000.0,
      "std_dev": 250000.0,
      "total": 7000000.0
    },
    "area_statistics": {             // ← Standardize field name
      "mean": 68.8,                  // Use "mean" not "average_area"
      "median": 76.0,
      "min": 42.0,
      "max": 106.0,
      "p25": 50.0,
      "p75": 90.0
    },
    "price_per_sqm_statistics": {    // ← Standardize field name
      "mean": 27892.0,               // Use "mean" not "average_price_per_sqm"
      "median": 34357.0,
      "min": 19811.0,
      "max": 35294.0,
      "p25": 25000.0,
      "p75": 32000.0
    },
    "property_type_distribution": {  // Optional
      "דירה": 20,
      "בית": 5
    },
    "date_range": {                  // Optional
      "earliest": "2024-01-31",
      "latest": "2025-11-05"
    }
  },
  "deals": [                         // ← Always "deals", never "comparables"
    {
      "objectid": 1975198,
      "deal_amount": 1800000.0,
      "deal_date": "2025-08-21",
      "asset_area": 51.0,
      "settlement_name_heb": "חולון",
      "property_type_description": "דירה",
      "neighborhood": "קרית עבודה",
      "rooms": 3.0,
      "streetNameHeb": "חנקין",
      "streetNameEng": "Hankin",
      "houseNum": 62,
      "floorNo": "שניה",
      "price_per_sqm": 35294.12,
      "deal_source": "street",       // Optional: same_building, street, neighborhood
      "priority": 1,                 // Optional: relevance ranking
      // ... other fields
    }
  ]
}
```

---

## Specific Changes Needed

### 1. `get_valuation_comparables` Tool

**Current response**:
```json
{
  "total_comparables": 3,
  "statistics": { "total_deals": 3, "price_statistics": {...} },
  "comparables": [...]
}
```

**Should be changed to**:
```json
{
  "search_parameters": {
    "address": "חנקין 62 חולון",
    "years_back": 2,
    "filters_applied": {
      "property_type": null,
      "rooms": "2.5-3.5",
      "price": null,
      "area": null,
      "floor": null
    },
    "radius_meters": 100,
    "max_comparables": 50
  },
  "market_statistics": {
    "deal_breakdown": {
      "total_deals": 3              // ← Move from "total_comparables"
    },
    "price_statistics": {           // ← Keep, matches standard
      "mean": 1743333.33,
      "median": 1750000.0,
      "min": 1680000.0,
      "max": 1800000.0,
      "p25": 1680000.0,
      "p75": 1800000.0,
      "std_dev": 60277.14
    },
    "area_statistics": {...},       // ← Keep
    "price_per_sqm_statistics": {...} // ← Keep
  },
  "deals": [...]                    // ← Rename from "comparables"
}
```

**Changes**:
1. Remove `total_comparables` field
2. Add `market_statistics.deal_breakdown.total_deals` instead
3. Rename `comparables` → `deals`
4. Move `statistics` → `market_statistics`
5. Add `search_parameters` section with `filters_applied`

### 2. `find_recent_deals_for_address` Tool

**Current response**: ✅ Already follows the standard!

Keep as-is, except:
- Rename `price_stats.average_price` → `price_statistics.mean`
- Rename `price_stats.median_price` → `price_statistics.median`
- Rename `area_stats` → `area_statistics`
- Rename `price_per_sqm_stats` → `price_per_sqm_statistics`

### 3. `analyze_market_trends` Tool

**Should return**:
```json
{
  "analysis_parameters": {
    "address": "...",
    "years_back": 3
  },
  "market_statistics": {           // ← Add this
    "deal_breakdown": {
      "total_deals": 50             // ← Move from market_summary
    },
    "price_statistics": {...},      // ← From trend analysis
    "area_statistics": {...}
  },
  "yearly_trends": {...},           // Keep tool-specific data
  "trend_analysis": {...},          // Keep tool-specific data
  "deals": [...]                    // Optional: sample deals
}
```

### 4. `get_deal_statistics` Tool

**Should return**:
```json
{
  "search_parameters": {...},
  "market_statistics": {           // ← Rename from "statistics"
    "deal_breakdown": {
      "total_deals": 25
    },
    "price_statistics": {...},
    "area_statistics": {...},
    "price_per_sqm_statistics": {...}
  },
  "deals": []                      // Can be empty for statistics-only queries
}
```

### 5. `get_market_activity_metrics` Tool

**Should return**:
```json
{
  "analysis_parameters": {...},
  "market_statistics": {
    "deal_breakdown": {
      "total_deals": 20             // ← Move from total_deals_analyzed
    }
  },
  "market_activity": {              // Keep tool-specific metrics
    "activity_score": 75.0,
    "liquidity_score": 80.0,
    ...
  },
  "investment_potential": {...},    // Keep tool-specific metrics
  "deals": []                       // Optional
}
```

---

## Benefits of Normalization

1. **Bot compatibility**: Bot can use the same code path for all tools
2. **Consistency**: Developers always know where to find deal count and deal array
3. **Maintainability**: Adding new tools is easier with a standard structure
4. **Testing**: Can write generic tests that work for all tools
5. **Documentation**: Single structure to document instead of 5+ different formats

---

## Implementation Checklist

For each MCP tool that returns deals:

- [ ] Add `market_statistics.deal_breakdown.total_deals` field
- [ ] Ensure deals array is named `deals` (not `comparables`, etc.)
- [ ] Standardize statistics field names:
  - [ ] `price_statistics` with `mean`, `median`, `min`, `max`, `p25`, `p75`
  - [ ] `area_statistics` with same structure
  - [ ] `price_per_sqm_statistics` with same structure
- [ ] Add `search_parameters` or `analysis_parameters` section
- [ ] Keep tool-specific fields (like `yearly_trends`, `market_activity`, etc.) but always include the standard structure
- [ ] Test with bot to verify it correctly interprets results

---

## Migration Strategy

**Option 1: Breaking change (recommended)**
- Update all tools at once to use new structure
- Update bot to expect new structure
- Deploy both together

**Option 2: Backward compatible**
- Return BOTH old and new fields temporarily:
  ```json
  {
    "total_comparables": 3,           // Old (deprecated)
    "comparables": [...],             // Old (deprecated)
    "market_statistics": {            // New (standard)
      "deal_breakdown": {
        "total_deals": 3
      }
    },
    "deals": [...]                    // New (standard)
  }
  ```
- Update bot to prefer new fields, fall back to old
- Remove old fields after bot is updated

I recommend **Option 1** since this is an internal MCP server with a single client (the bot).

---

## Testing After Changes

Once normalized, test with the bot:

```
User: "כמה עולה דירת 3 חדרים בחנקין 62 חולון?"
Expected: Bot should return actual deals and prices, NOT "לא מצאתי עסקאות"
```

Verify in bot logs:
```
Total deals found: 20  // Should show actual count
Sample deals (most recent 10):
  1. חנקין 62 חולון - ₪1,800,000 - 3 rooms - 51 sqm - 2025-08-21
  ...
```
