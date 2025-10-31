# Nadlan-MCP Usage Examples

This directory contains practical examples demonstrating how to use the Nadlan-MCP library for Israeli real estate data analysis.

## Prerequisites

```bash
# Install nadlan-mcp
pip install -r requirements.txt

# Or if installed as package
pip install nadlan-mcp
```

## Running the Examples

All examples can be run directly:

```bash
python examples/basic_search.py
python examples/market_analysis.py
python examples/investment_analysis.py
python examples/valuation.py
```

## Examples

### 1. Basic Address Search (`basic_search.py`)

**What it does:**
- Searches for recent real estate deals near a specific address
- Displays deal details including price, rooms, area, and price per m²

**Use case:** Quick lookup of recent transactions in a specific location

**Run:**
```bash
python examples/basic_search.py
```

### 2. Market Analysis (`market_analysis.py`)

**What it does:**
- Analyzes market trends for a specific area over multiple years
- Calculates price statistics, market activity, liquidity, and investment potential
- Provides comprehensive metrics for understanding local market dynamics

**Use case:** Deep-dive analysis of a neighborhood's real estate market

**Run:**
```bash
python examples/market_analysis.py
```

### 3. Investment Comparison (`investment_analysis.py`)

**What it does:**
- Compares multiple neighborhoods side-by-side
- Evaluates investment potential based on activity, liquidity, trends, and appreciation
- Recommends the best investment opportunity

**Use case:** Comparing different areas to identify the best investment location

**Run:**
```bash
python examples/investment_analysis.py
```

### 4. Property Valuation (`valuation.py`)

**What it does:**
- Finds comparable properties based on size, rooms, and floor
- Calculates estimated property value using price per m² from comparables
- Provides valuation range (25th-75th percentile)

**Use case:** Estimating the fair market value of a specific property

**Run:**
```bash
python examples/valuation.py
```

## Modifying the Examples

All examples are designed to be easily customizable:

1. **Change the address:** Edit the `address` variable to analyze different locations
2. **Adjust time period:** Modify `years_back` parameter to look further back
3. **Change search radius:** Adjust `radius` parameter (in meters)
4. **Add filters:** Use `filter_deals_by_criteria()` to filter by property type, rooms, price, etc.

### Example Modifications

```python
# Analyze last 5 years instead of 2
deals = client.find_recent_deals_for_address(address, years_back=5)

# Use wider search radius (500m instead of default)
deals = client.find_recent_deals_for_address(address, radius=500)

# Filter for apartments only
filtered = client.filter_deals_by_criteria(
    deals,
    property_type="דירה",
    min_rooms=3,
    max_rooms=4,
    min_price=1000000,
    max_price=2000000
)
```

## Tips for Best Results

1. **Use Hebrew addresses:** The API works best with Hebrew street names and city names
   - Good: `"רוטשילד 1 תל אביב"`
   - OK: `"Rothschild 1 Tel Aviv"`

2. **Adjust radius based on density:**
   - High-density areas (Tel Aviv, Jerusalem): 50-100m
   - Medium-density (Ramat Gan, Herzliya): 100-200m
   - Low-density areas: 200-500m

3. **Time periods:**
   - Quick analysis: 1-2 years
   - Trend analysis: 3-5 years
   - Historical perspective: 5+ years (data availability varies)

4. **Use filters for precision:**
   - When valuing property: filter by similar size, rooms, and floor
   - When comparing markets: don't filter too much (need enough data)

## Common Use Cases

### 1. Pre-Purchase Research
```bash
# Run market analysis and valuation for target property
python examples/market_analysis.py  # Understand the market
python examples/valuation.py        # Estimate fair value
```

### 2. Investment Decision
```bash
# Compare multiple locations
python examples/investment_analysis.py
```

### 3. Market Monitoring
```bash
# Regular analysis to track market changes
python examples/basic_search.py
```

## Need More Help?

- See main [README.md](../README.md) for full API documentation
- Check [CLAUDE.md](../CLAUDE.md) for development guide
- Review [ARCHITECTURE.md](../ARCHITECTURE.md) for system design

## Contributing

Have an idea for a new example? Please submit a pull request! Good examples should:
- Solve a real use case
- Be well-commented
- Include error handling
- Be easy to modify
