# Nadlan-MCP Architecture

## Overview

Nadlan-MCP is a Model Context Protocol (MCP) server that provides Israeli real estate data to AI agents (LLMs). The architecture follows a clean separation of concerns with three main layers:

1. **MCP Tools Layer** - Exposes functions to LLM clients
2. **Business Logic Layer** - Data analysis and processing
3. **API Client Layer** - Communicates with Govmap API

## Design Principles

### 1. MCP Provides Data, LLM Provides Intelligence

The server's role is to retrieve, structure, and optionally summarize data. Complex analysis, decision-making, and predictions are left to the LLM client.

**Example:**
- ✅ MCP: Provides comparable property deals with filters
- ✅ LLM: Analyzes comparables and estimates property value
- ❌ MCP: Calculates ML-based property valuation

### 2. Structured by Default

All tools return detailed, structured data by default. Optional `summarized_response` parameter provides condensed summaries when needed.

### 3. Reliability First

- Automatic retry with exponential backoff
- Rate limiting to respect API limits
- Comprehensive input validation
- Detailed error messages

### 4. Configuration Over Hard-coding

All settings (timeouts, retries, rate limits) are configurable via environment variables or code.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       LLM Client (AI Agent)                  │
│                    (Claude, GPT, etc.)                       │
└────────────────────────────┬────────────────────────────────┘
                             │ MCP Protocol
                             ↓
┌─────────────────────────────────────────────────────────────┐
│                    MCP Tools Layer                          │
│  ┌───────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │autocomplete   │  │find_recent_deals│  │analyze_market│ │
│  │_address       │  │_for_address     │  │_trends       │ │
│  └───────┬───────┘  └────────┬────────┘  └──────┬───────┘ │
│          │                   │                    │         │
│  ┌───────┴───────────────────┴────────────────────┴──────┐ │
│  │            fastmcp_server.py (Tool Definitions)       │ │
│  └───────────────────────────┬───────────────────────────┘ │
└────────────────────────────┬─┴────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────┐
│                 Business Logic Layer                         │
│  ┌────────────────────┐  ┌──────────────────────────────┐  │
│  │ Market Analysis    │  │ Deal Processing & Filtering  │  │
│  │ (analyze_market    │  │ (_is_same_building, etc.)    │  │
│  │  _trends logic)    │  │                              │  │
│  └────────────────────┘  └──────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────┐ │
│  │            govmap.py (GovmapClient)                    │ │
│  │  • Validation  • Retry Logic  • Rate Limiting         │ │
│  └─────────────────────────┬──────────────────────────────┘ │
└───────────────────────────┬┴──────────────────────────────┘
                            │ HTTP/JSON
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    Govmap API Layer                         │
│        (Israeli Government Real Estate API)                 │
│  ┌───────────────┐  ┌────────────┐  ┌──────────────────┐  │
│  │ Autocomplete  │  │ Deals by   │  │ Street/          │  │
│  │ Endpoint      │  │ Radius     │  │ Neighborhood     │  │
│  │               │  │ Endpoint   │  │ Deals Endpoints  │  │
│  └───────────────┘  └────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Component Details

### Configuration Layer (`config.py`)

**Purpose:** Centralized configuration management

**Key Components:**
- `GovmapConfig` - Dataclass with all configuration settings
- Environment variable support for all settings
- Validation on initialization

**Configuration Options:**
- API settings (base URL, user agent)
- Timeout settings (connect, read)
- Retry settings (max retries, backoff)
- Rate limiting (requests per second)
- Default search parameters

**Usage:**
```python
from nadlan_mcp.config import get_config, set_config, GovmapConfig

# Use global config
config = get_config()

# Override config
custom_config = GovmapConfig(max_retries=5, requests_per_second=10.0)
set_config(custom_config)
```

### API Client Layer (`govmap.py`)

**Purpose:** Communicate with Govmap API with reliability features

**Key Components:**

#### GovmapClient Class

**Responsibilities:**
- Make HTTP requests to Govmap API
- Implement retry logic with exponential backoff
- Enforce rate limiting
- Validate inputs
- Parse and validate responses

**Key Methods:**
- `autocomplete_address()` - Search for addresses
- `get_gush_helka()` - Get block/parcel data
- `get_deals_by_radius()` - Get nearby deals
- `get_street_deals()` - Get street-level deals
- `get_neighborhood_deals()` - Get neighborhood deals
- `find_recent_deals_for_address()` - Main comprehensive search

**Reliability Features:**
1. **Retry Logic** - Exponential backoff on failures
2. **Rate Limiting** - Tracks request times, enforces delays
3. **Input Validation** - Validates all inputs before API calls
4. **Timeouts** - Configurable connect and read timeouts

### MCP Tools Layer (`fastmcp_server.py`)

**Purpose:** Expose functionality to LLM clients via MCP protocol

**Key Components:**
- FastMCP server instance
- Tool definitions (decorated functions)
- JSON response formatting
- Error handling for user-friendly messages

**Tool Design Pattern:**
```python
@mcp.tool()
def tool_name(param: type, summarized_response: bool = False) -> str:
    """
    Tool description for LLM.
    
    Args:
        param: Parameter description
        summarized_response: 
            - False (default): Full structured data for LLM processing
            - True: Condensed summary with key insights
    
    Returns:
        JSON string with data or summary
    """
    # 1. Call business logic / API client
    # 2. Format response
    # 3. Return JSON string
```

## Data Flow

### Example: Find Recent Deals for Address

```
1. LLM Request
   └─> "Find deals for Sokolov 38 Holon in last 2 years"

2. MCP Tool: find_recent_deals_for_address()
   ├─> Validate inputs
   └─> Call GovmapClient

3. GovmapClient Workflow:
   ├─> autocomplete_address("סוקולוב 38 חולון")
   │   ├─> Rate limit check
   │   ├─> HTTP POST (with retry)
   │   └─> Parse coordinates
   │
   ├─> get_deals_by_radius(coordinates, 30m)
   │   ├─> Rate limit check
   │   ├─> HTTP GET (with retry)
   │   └─> Extract polygon_ids
   │
   ├─> For each polygon_id:
   │   ├─> get_street_deals(polygon_id)
   │   └─> get_neighborhood_deals(polygon_id)
   │
   ├─> Filter & Prioritize:
   │   ├─> Same building deals (priority 0)
   │   ├─> Street deals (priority 1)
   │   └─> Neighborhood deals (priority 2)
   │
   └─> Sort by priority then date

4. Format Response
   └─> JSON with deals + metadata

5. Return to LLM
   └─> LLM analyzes and responds to user
```

## Error Handling Strategy

### Validation Errors (ValueError)
- Invalid address format
- Negative/zero parameters
- Out-of-range values
- **Action:** Immediate failure with clear message

### Network Errors (requests.RequestException)
- Connection failures
- Timeouts
- HTTP errors
- **Action:** Retry with exponential backoff (up to configured max_retries)

### API Response Errors
- Invalid JSON
- Unexpected format
- Missing required fields
- **Action:** Raise ValueError with specific details

### Rate Limiting
- Track last request time
- Sleep if necessary before request
- **Action:** Transparent to caller, automatic

## Performance Considerations

### Current Implementation

**Optimizations:**
- Connection pooling (requests.Session)
- Rate limiting prevents API throttling
- Early validation reduces unnecessary API calls
- Polygon deduplication in find_recent_deals_for_address()

**Limitations:**
- Synchronous (blocking) API calls
- No caching (MVP decision)
- Sequential polygon queries

### Future Optimizations (Not in MVP)

**Phase 1: In-Memory Caching**
- Cache autocomplete results (1 hour TTL)
- Cache deal results (30 minute TTL)
- Reduce API load by 60-80%

**Phase 2: Async/Parallel**
- Convert to async/await
- Parallel polygon queries
- 3-5x faster for multi-polygon searches

**Phase 3: Production Caching**
- Redis for distributed caching
- Cache warming strategies
- Cross-instance consistency

## Security & Rate Limiting

### Rate Limiting

**Current:** 5 requests/second (configurable)

**Rationale:**
- Respects Govmap API (no published limits, being conservative)
- Prevents accidental DoS
- Balances responsiveness with safety

**Implementation:**
- Tracks last request timestamp
- Sleeps if interval too short
- Per-instance (not distributed)

### Input Validation

All user inputs are validated before use:
- Address strings: length, type, non-empty
- Coordinates: numeric, reasonable bounds
- Integers: positive, max values
- Deal types: enum validation (1 or 2)

**Prevents:**
- Injection attacks
- API errors from malformed requests
- Expensive/dangerous operations

### API Key Management

**Current:** No API keys required (public API)

**Future:** If API keys added:
- Store in environment variables only
- Never log or expose in responses
- Rotate regularly

## Testing Strategy

### Unit Tests
- Mock API responses
- Test validation logic
- Test error handling
- Test retry logic

### Integration Tests
- Real API calls (marked `@pytest.mark.integration`)
- VCR.py for recording/replaying
- Test complete workflows

### Validation Tests
- Invalid inputs
- Edge cases
- Boundary conditions

## Configuration Options

### Environment Variables

```bash
# API Settings
GOVMAP_BASE_URL=https://www.govmap.gov.il/api/
GOVMAP_USER_AGENT=NadlanMCP/1.0.0

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
```

### Tuning Guidelines

**High Reliability (Production):**
- `MAX_RETRIES=5`
- `RETRY_MAX_WAIT=30`
- `REQUESTS_PER_SECOND=3.0`

**High Performance (Development):**
- `MAX_RETRIES=2`
- `RETRY_MAX_WAIT=5`
- `REQUESTS_PER_SECOND=10.0`

**Conservative (Shared API):**
- `MAX_RETRIES=3`
- `RETRY_MAX_WAIT=10`
- `REQUESTS_PER_SECOND=2.0`

## Future Architecture Evolution

### Phase 2: Data Models (Pydantic)

Add structured models for type safety:
```python
class Deal(BaseModel):
    deal_id: str
    address: str
    deal_amount: float
    asset_area: float
    price_per_sqm: float
    deal_date: datetime
    property_type: str
    # ...
```

### Phase 3: Separation of Concerns

```
nadlan_mcp/
├── api_client.py       # Pure API communication
├── analyzers/
│   ├── market.py       # Market analysis logic
│   ├── valuation.py    # Valuation helpers
│   └── filtering.py    # Deal filtering
├── models.py           # Pydantic models
└── fastmcp_server.py   # Thin MCP tool definitions
```

### Phase 4: Database Layer (Optional)

For historical tracking and faster queries:
```
├── database/
│   ├── models.py       # SQLAlchemy models
│   ├── crud.py         # CRUD operations
│   └── migrations/     # Alembic migrations
```

## Deployment

### Development
```bash
python run_fastmcp_server.py
```

### Production (MCP Client)
```json
{
  "servers": {
    "nadlan-mcp": {
      "command": "python",
      "args": ["/path/to/nadlan-mcp/run_fastmcp_server.py"],
      "env": {
        "GOVMAP_REQUESTS_PER_SECOND": "3.0",
        "GOVMAP_MAX_RETRIES": "5"
      }
    }
  }
}
```

## API Limitations

### Govmap API Constraints

**Known Limitations:**
- No published rate limits (being conservative with 5 req/sec)
- No authentication required (public API)
- Data freshness: Updated periodically (not real-time)
- Coverage: Official Israeli government records only

**Best Practices:**
- Use appropriate time ranges (2-5 years recommended)
- Limit radius searches (under 1000m for performance)
- Cache results when possible (future feature)
- Respect rate limiting

### MCP Protocol Constraints

**Token Limits:**
- Large deal lists can exceed LLM context windows
- Use `summarized_response=True` for large datasets
- Default limits (50-100 deals) are token-optimized

## Monitoring & Debugging

### Logging Levels

**INFO:** Normal operations
- Requests being made
- Successful responses

**WARNING:** Recoverable issues
- Retrying after failures
- Rate limiting delays
- Validation warnings

**ERROR:** Failures
- Exhausted retries
- Invalid responses
- Configuration errors

### Debug Mode

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## References

- [Govmap API](https://www.govmap.gov.il/)
- [MCP Protocol](https://modelcontextprotocol.io/)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [Israeli Real Estate Data](https://data.gov.il/)

