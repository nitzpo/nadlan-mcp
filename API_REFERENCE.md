# API Reference

Complete reference for Nadlan-MCP's MCP tools and Python library.

## Table of Contents

- [MCP Tools](#mcp-tools) - For AI agents (Claude, etc.)
- [Python Client](#python-client) - For direct library usage
- [Data Models](#data-models) - Pydantic models reference
- [Configuration](#configuration) - Environment variables and settings

---

## MCP Tools

These tools are available when running Nadlan-MCP as an MCP server.

### Core Tools

#### `autocomplete_address`

Search and validate Israeli addresses.

**Parameters:**
- `search_text` (string, required): Address to search (Hebrew or English)

**Returns:** JSON with matching addresses and coordinates

**Example:**
```json
{
  "search_text": "רוטשילד תל אביב"
}
```

---

#### `find_recent_deals_for_address`

Find all recent real estate deals for a specific address.

**Parameters:**
- `address` (string, required): Address to search
- `years_back` (int, default: 2): Number of years to look back
- `radius_meters` (int, default: 30): Search radius in meters
- `max_deals` (int, default: 100): Maximum deals to return
- `deal_type` (int, default: 2): Deal type (1=new construction, 2=resale)

**Returns:** JSON with deals, sorted by priority and date

**Example:**
```json
{
  "address": "רוטשילד 1 תל אביב",
  "years_back": 2,
  "radius_meters": 50
}
```

---

#### `get_deals_by_radius`

Get polygon metadata within a radius of coordinates.

**Parameters:**
- `latitude` (float, required): Latitude coordinate
- `longitude` (float, required): Longitude coordinate
- `radius_meters` (int, default: 500): Search radius in meters

**Returns:** JSON with polygon metadata (NOT individual deals)

**Note:** This returns **polygon metadata**, not deals. Use `get_street_deals` or `find_recent_deals_for_address` for actual deals.

---

#### `get_street_deals`

Get deals for a specific street polygon.

**Parameters:**
- `polygon_id` (string, required): Street polygon ID
- `limit` (int, default: 100): Maximum deals to return
- `deal_type` (int, default: 2): Deal type filter

**Returns:** JSON with street-level deals

---

#### `get_neighborhood_deals`

Get deals for a neighborhood polygon.

**Parameters:**
- `polygon_id` (string, required): Neighborhood polygon ID
- `limit` (int, default: 100): Maximum deals to return
- `deal_type` (int, default: 2): Deal type filter

**Returns:** JSON with neighborhood-level deals

---

### Analysis Tools

#### `analyze_market_trends`

Analyze market trends and price patterns for an area.

**Parameters:**
- `address` (string, required): Address to analyze
- `years_back` (int, default: 3): Years of data to analyze
- `radius_meters` (int, default: 100): Search radius
- `max_deals` (int, default: 100): Maximum deals to analyze
- `deal_type` (int, default: 2): Deal type filter

**Returns:** JSON with:
- Deal statistics (prices, price/m², trends)
- Time-series analysis
- Market summary

**Example:**
```json
{
  "address": "דיזנגוף 50 תל אביב",
  "years_back": 3
}
```

---

#### `compare_addresses`

Compare real estate markets between multiple addresses.

**Parameters:**
- `addresses` (array of strings, required): List of addresses to compare

**Returns:** JSON with comparative analysis

**Example:**
```json
{
  "addresses": [
    "רוטשילד 1 תל אביב",
    "דיזנגוף 50 תל אביב",
    "ז'בוטינסקי 1 רמת גן"
  ]
}
```

---

### Valuation Tools

#### `get_valuation_comparables`

Get comparable properties for valuation analysis.

**Parameters:**
- `address` (string, required): Address to find comparables for
- `years_back` (int, default: 2): Years to look back
- `property_type` (string, optional): Filter by property type (e.g., "דירה")
- `min_rooms` (float, optional): Minimum rooms
- `max_rooms` (float, optional): Maximum rooms
- `min_price` (float, optional): Minimum price (NIS)
- `max_price` (float, optional): Maximum price (NIS)
- `min_area` (float, optional): Minimum area (m²)
- `max_area` (float, optional): Maximum area (m²)
- `min_floor` (int, optional): Minimum floor
- `max_floor` (int, optional): Maximum floor
- `radius_meters` (int, default: 100): Search radius
- `max_comparables` (int, default: 50): Max comparables to return

**Returns:** JSON with filtered comparable deals and statistics

**Example:**
```json
{
  "address": "רוטשילד 10 תל אביב",
  "min_rooms": 3,
  "max_rooms": 4,
  "min_area": 70,
  "max_area": 100
}
```

---

#### `get_deal_statistics`

Calculate statistical aggregations on deal data.

**Parameters:**
- `address` (string, required): Address to analyze
- `years_back` (int, default: 2): Years to analyze
- `property_type` (string, optional): Filter by property type
- `min_rooms` (float, optional): Minimum rooms
- `max_rooms` (float, optional): Maximum rooms

**Returns:** JSON with statistics (mean, median, percentiles, std dev)

---

#### `get_market_activity_metrics`

Get comprehensive market activity and investment analysis.

**Parameters:**
- `address` (string, required): Address to analyze
- `years_back` (int, default: 2): Years to analyze
- `radius_meters` (int, default: 100): Search radius

**Returns:** JSON with:
- Market activity score and trends
- Market liquidity metrics
- Investment potential analysis
- Price appreciation and volatility

---

## Python Client

For direct Python usage without MCP.

### Installation

```python
from nadlan_mcp.govmap import GovmapClient
client = GovmapClient()
```

### Main Methods

#### `autocomplete_address()`

```python
def autocomplete_address(search_text: str) -> AutocompleteResponse:
    """
    Search for addresses using autocomplete.

    Args:
        search_text: Address to search (Hebrew or English)

    Returns:
        AutocompleteResponse with matching addresses

    Raises:
        ValueError: If search text is invalid
        requests.RequestException: On API errors
    """
```

**Example:**
```python
result = client.autocomplete_address("רוטשילד תל אביב")
for address in result.results:
    print(f"{address.text} - {address.coordinates}")
```

---

#### `find_recent_deals_for_address()`

```python
def find_recent_deals_for_address(
    address: str,
    years_back: int = 2,
    radius: int = 50,
    max_deals: int = 100,
    deal_type: int = 2
) -> List[Deal]:
    """
    Find all relevant deals for an address.

    Args:
        address: Address to search
        years_back: Years to look back (default: 2)
        radius: Search radius in meters (default: 50)
        max_deals: Maximum deals to return (default: 100)
        deal_type: 1=new construction, 2=resale (default: 2)

    Returns:
        List of Deal models, sorted by priority and date

    Raises:
        ValueError: If address invalid or no results found
    """
```

**Example:**
```python
deals = client.find_recent_deals_for_address(
    "רוטשילד 1 תל אביב",
    years_back=3,
    radius=100
)

for deal in deals[:5]:
    print(f"{deal.address_description}: ₪{deal.deal_amount:,.0f}")
```

---

#### `filter_deals_by_criteria()`

```python
def filter_deals_by_criteria(
    deals: List[Deal],
    property_type: Optional[str] = None,
    min_rooms: Optional[float] = None,
    max_rooms: Optional[float] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    min_area: Optional[float] = None,
    max_area: Optional[float] = None,
    min_floor: Optional[int] = None,
    max_floor: Optional[int] = None,
) -> List[Deal]:
    """
    Filter deals by various criteria.

    Args:
        deals: List of Deal models to filter
        property_type: Property type (Hebrew, e.g., "דירה")
        min_rooms/max_rooms: Room count range
        min_price/max_price: Price range (NIS)
        min_area/max_area: Area range (m²)
        min_floor/max_floor: Floor range

    Returns:
        Filtered list of Deal models

    Raises:
        ValueError: If filter ranges are invalid
    """
```

**Example:**
```python
filtered = client.filter_deals_by_criteria(
    deals,
    property_type="דירה",
    min_rooms=3,
    max_rooms=4,
    min_price=1000000,
    max_price=2000000
)
```

---

#### `calculate_deal_statistics()`

```python
def calculate_deal_statistics(deals: List[Deal]) -> DealStatistics:
    """
    Calculate statistical aggregations.

    Args:
        deals: List of Deal models

    Returns:
        DealStatistics model with mean, median, percentiles, etc.

    Raises:
        ValueError: If deals list is empty
    """
```

---

#### `calculate_market_activity_score()`

```python
def calculate_market_activity_score(
    deals: List[Deal],
    time_period_months: Optional[int] = None
) -> MarketActivityScore:
    """
    Calculate market activity metrics.

    Args:
        deals: List of Deal models
        time_period_months: Time period to analyze (None = all data)

    Returns:
        MarketActivityScore model

    Raises:
        ValueError: If deals list is empty
    """
```

---

#### `get_market_liquidity()`

```python
def get_market_liquidity(
    deals: List[Deal],
    time_period_months: Optional[int] = None
) -> LiquidityMetrics:
    """
    Calculate market liquidity metrics.

    Args:
        deals: List of Deal models
        time_period_months: Time period to analyze

    Returns:
        LiquidityMetrics model

    Raises:
        ValueError: If deals list is empty
    """
```

---

#### `analyze_investment_potential()`

```python
def analyze_investment_potential(deals: List[Deal]) -> InvestmentAnalysis:
    """
    Analyze investment potential of an area.

    Args:
        deals: List of Deal models

    Returns:
        InvestmentAnalysis model

    Raises:
        ValueError: If deals list is empty or insufficient data
    """
```

---

## Data Models

All models are Pydantic v2 models with validation.

### Deal

Primary model for real estate transaction data.

```python
class Deal(BaseModel):
    objectid: int
    deal_amount: Optional[float]
    deal_date: date | str
    property_type_description: Optional[str]
    rooms: Optional[float]
    asset_area: Optional[float]
    floor_number: Optional[int]
    floor: Optional[str]
    address_description: Optional[str]

    # Computed field
    @computed_field
    @property
    def price_per_sqm(self) -> Optional[float]:
        """Calculate price per square meter."""
        if self.deal_amount and self.asset_area and self.asset_area > 0:
            return self.deal_amount / self.asset_area
        return None
```

### DealStatistics

Statistical aggregations on deal data.

```python
class DealStatistics(BaseModel):
    count: int
    mean_price: float
    median_price: float
    min_price: float
    max_price: float
    std_dev_price: float
    percentile_25_price: float
    percentile_75_price: float
    mean_price_per_sqm: Optional[float]
    median_price_per_sqm: Optional[float]
    # ... more fields
```

### MarketActivityScore

Market activity metrics.

```python
class MarketActivityScore(BaseModel):
    activity_score: float  # 0-100
    activity_level: str  # very_high, high, moderate, low, very_low
    trend: str  # improving, stable, declining
    deals_per_month: float
    unique_months: int
    total_deals: int
```

### InvestmentAnalysis

Investment potential analysis.

```python
class InvestmentAnalysis(BaseModel):
    investment_score: float  # 0-100
    price_trend: str
    price_appreciation_rate: float  # % per year
    market_stability: str
    volatility_score: float
    recommendation: str
```

### LiquidityMetrics

Market liquidity analysis.

```python
class LiquidityMetrics(BaseModel):
    liquidity_score: float  # 0-100
    total_deals: int
    avg_deals_per_month: float
    deal_velocity: float
    market_activity_level: str
    trend_direction: str
```

---

## Configuration

### Environment Variables

```bash
# API Settings
GOVMAP_BASE_URL=https://www.govmap.gov.il/api/
GOVMAP_USER_AGENT=NadlanMCP/2.0.0

# Timeouts (seconds)
GOVMAP_CONNECT_TIMEOUT=10
GOVMAP_READ_TIMEOUT=30

# Retry Settings
GOVMAP_MAX_RETRIES=3
GOVMAP_RETRY_MIN_WAIT=1
GOVMAP_RETRY_MAX_WAIT=10

# Rate Limiting
GOVMAP_REQUESTS_PER_SECOND=5.0

# Defaults
GOVMAP_DEFAULT_RADIUS=50
GOVMAP_DEFAULT_YEARS_BACK=2
GOVMAP_DEFAULT_DEAL_LIMIT=100

# Performance
GOVMAP_MAX_POLYGONS=10
```

### Programmatic Configuration

```python
from nadlan_mcp.config import GovmapConfig, set_config

config = GovmapConfig(
    connect_timeout=15,
    read_timeout=45,
    max_retries=5,
    requests_per_second=3.0,
    max_polygons=5
)
set_config(config)
```

---

## Error Handling

### Common Errors

**ValueError**
- Invalid input parameters
- Empty results
- Invalid filter ranges

**requests.RequestException**
- Network errors
- API timeouts
- HTTP errors

**pydantic.ValidationError**
- Invalid model data (handled internally, logged as warnings)

### Example

```python
from nadlan_mcp.govmap import GovmapClient

client = GovmapClient()

try:
    deals = client.find_recent_deals_for_address("invalid")
except ValueError as e:
    print(f"Invalid input: {e}")
except requests.RequestException as e:
    print(f"API error: {e}")
```

---

## Rate Limiting

Built-in rate limiting respects API limits:
- Default: 5 requests/second
- Configurable via `GOVMAP_REQUESTS_PER_SECOND`
- Automatic retry with exponential backoff

---

## Examples

See `examples/` directory for complete usage examples:
- `basic_search.py` - Simple address lookup
- `market_analysis.py` - Trend analysis
- `investment_analysis.py` - Multi-location comparison
- `valuation.py` - Property valuation

---

For more information, see:
- [README.md](README.md) - Overview and quickstart
- [DEPLOYMENT.md](DEPLOYMENT.md) - Deployment guide
- [CONTRIBUTING.md](CONTRIBUTING.md) - Development guide
