# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Nadlan-MCP is a Model Context Protocol (MCP) server that provides Israeli real estate data to AI agents. It interfaces with the Israeli government's Govmap API to retrieve property deals, market trends, and real estate information.

**Key Technology:** FastMCP server exposing 7 main tools for querying Israeli real estate data

## Product Vision & Use Cases

**See USECASES.md for the complete feature roadmap and user-facing capabilities.**

### Current Capabilities (✅ Implemented)
- **Address & Location Services** - Address autocomplete, location-based deal search
- **Real Estate Deal Analysis** - Recent deals, street/neighborhood analysis, filtering
- **Market Intelligence** - Trend analysis, price per sqm tracking
- **Comparative Analysis** - Multi-address comparison, investment insights

### In Development (🚧 In Progress)
- Enhanced deal filtering (property type, rooms, price range, area, floor)
- Valuation data provision tools (`get_valuation_comparables`, `get_deal_statistics`)
- Market activity metrics (detailed activity and velocity metrics)

### Future Features (📋 Planned)
- **Amenity Scoring** - Comprehensive quality-of-life analysis using:
  - Google Places API / OpenStreetMap for amenity locations
  - Ministry of Education data for school rankings
  - Ministry of Health data for healthcare facility ratings
  - CBS demographic data
  - Public transport APIs
- Caching system (in-memory → Redis)
- Async/parallel processing
- Multi-language support

**Important Design Principle:** The MCP provides data; the LLM provides intelligence. Avoid implementing complex analysis or predictions in the MCP layer - that's the LLM's job.

## Development Commands

### Running the Server

```bash
# Run the FastMCP server (recommended)
python run_fastmcp_server.py

# Or run directly as module
python -m nadlan_mcp.fastmcp_server
```

### Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_govmap_client.py

# Run with coverage
pytest --cov=nadlan_mcp

# Run only unit tests (skip integration)
pytest -m unit

# Run integration tests (makes real API calls)
pytest -m integration
```

### Code Quality

```bash
# Format code with black
black nadlan_mcp/ tests/

# Sort imports
isort nadlan_mcp/ tests/

# Type checking
mypy nadlan_mcp/

# Linting
flake8 nadlan_mcp/
```

## Architecture

The codebase follows a three-layer architecture:

### 1. MCP Tools Layer (`nadlan_mcp/fastmcp_server.py`)
- Exposes 7 tools to LLM clients via FastMCP
- Handles tool parameter validation and JSON response formatting
- Main tools: `find_recent_deals_for_address`, `analyze_market_trends`, `compare_addresses`
- **Important:** Tools return structured JSON by default; use `summarized_response=True` for condensed summaries

### 2. Business Logic Layer (`nadlan_mcp/govmap.py`)
- `GovmapClient` class implements all API interactions
- Reliability features: retry logic with exponential backoff, rate limiting, input validation
- Helper functions for data processing, filtering, and analysis
- **Key Design Principle:** MCP provides data, LLM provides intelligence - avoid complex analysis in the MCP layer

### 3. Configuration Layer (`nadlan_mcp/config.py`)
- `GovmapConfig` dataclass with environment variable support
- Global config accessed via `get_config()` and `set_config()`
- All timeouts, retries, rate limits are configurable

## Key Files

- `nadlan_mcp/govmap.py` - Core API client with ~1000 lines of business logic
- `nadlan_mcp/fastmcp_server.py` - MCP tool definitions (7 implemented tools)
- `nadlan_mcp/config.py` - Configuration management
- `run_fastmcp_server.py` - Server entry point
- `tests/test_govmap_client.py` - Main test suite
- `USECASES.md` - **Product roadmap and feature status** (essential reading)
- `ARCHITECTURE.md` - Detailed system architecture and design decisions
- `TASKS.md` - Implementation tasks and progress tracking

## Available MCP Tools

**Implemented (✅):**
- `autocomplete_address` - Search and autocomplete Israeli addresses
- `get_deals_by_radius` - Get deals within a radius of coordinates
- `get_street_deals` - Get deals for a specific street polygon
- `get_neighborhood_deals` - Get deals for a neighborhood polygon
- `find_recent_deals_for_address` - Main comprehensive analysis tool
- `analyze_market_trends` - Analyze market trends and price patterns
- `compare_addresses` - Compare real estate markets between multiple addresses

**In Progress (🚧):**
- `get_valuation_comparables` - Get comparable properties for valuation analysis
- `get_deal_statistics` - Calculate statistical aggregations on deal data
- `get_market_activity_metrics` - Detailed market activity and velocity metrics

**Planned (📋):**
- `get_address_amenity_rating` - Comprehensive amenity analysis with quality metrics
- `compare_addresses_by_amenities` - Side-by-side amenity comparison
- `find_amenities_near_address` - Raw amenity list with quality data

## Important Patterns

### Retry Logic
All API calls use automatic retry with exponential backoff (configurable via `GOVMAP_MAX_RETRIES`). The pattern is implemented in `GovmapClient._make_request()`.

### Rate Limiting
Client enforces rate limiting via `_rate_limit()` method, tracking last request time and sleeping if needed. Default: 5 requests/second.

### Error Handling
- Validation errors: Raise `ValueError` immediately with clear message
- Network errors: Retry with backoff, then raise `requests.RequestException`
- API response errors: Raise `ValueError` with specific details
- **Never return empty lists on error** - always raise exceptions

### Input Validation
All user inputs are validated before API calls:
- `_validate_address()` - address strings
- `_validate_coordinates()` - coordinate tuples
- `_validate_positive_int()` - numeric parameters

### Deal Prioritization
`find_recent_deals_for_address()` assigns priority levels:
- Priority 0: Same building deals
- Priority 1: Street deals
- Priority 2: Neighborhood deals

Helper `_is_same_building()` checks if deals are from the same property using address matching.

## Data Flow Example

1. LLM calls find_recent_deals_for_address("סוקולוב 38 חולון")
2. Tool validates inputs → calls GovmapClient
3. Client workflow:
   - autocomplete_address() → get coordinates
   - get_deals_by_radius() → extract polygon_ids
   - For each polygon: get_street_deals() + get_neighborhood_deals()
   - Filter & prioritize deals (same building > street > neighborhood)
   - Sort by priority then date
4. Return JSON with deals + metadata

## Testing Strategy

- **Unit tests:** Mock API responses, test validation and retry logic
- **Integration tests:** Mark with `@pytest.mark.integration`, use real API (use sparingly)
- Fixtures defined in `tests/conftest.py`
- Consider using VCR.py for recording/replaying API interactions (planned)

## Configuration via Environment Variables

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

## Development Roadmap

See `TASKS.md` for complete implementation plan. Current focus:
- **Phase 2.2:** Market analysis tools (in progress)
- **Phase 2.3:** Enhanced filtering (mostly complete)
- **Phase 3:** Architecture improvements with Pydantic models
- **Phase 4:** Expanded test coverage

## Common Tasks

### Adding a New MCP Tool

1. Add `@mcp.tool()` decorated function in `fastmcp_server.py`
2. Call appropriate `GovmapClient` methods
3. Format response as JSON string
4. Add error handling with try/except
5. Update README.md with tool documentation

### Adding New API Endpoint Support

1. Add method to `GovmapClient` class in `govmap.py`
2. Implement validation, retry logic, rate limiting
3. Add unit tests in `tests/test_govmap_client.py`
4. Optionally expose as MCP tool

### Modifying Configuration

1. Add field to `GovmapConfig` dataclass in `config.py`
2. Add environment variable default in `field(default_factory=...)`
3. Add validation in `_validate()` method
4. Update ARCHITECTURE.md with new config option

## Govmap API Endpoints

The client uses these Govmap API endpoints:
- `POST /search-service/autocomplete` - Address search
- `POST /layers-catalog/entitiesByPoint` - Get block/parcel data
- `GET /real-estate/deals/{point}/{radius}` - Deals within radius
- `GET /real-estate/street-deals/{polygon_id}` - Street-level deals
- `GET /real-estate/neighborhood-deals/{polygon_id}` - Neighborhood deals

**Note:** No API key required (public API). Be respectful of rate limits.

## Known Limitations

- No caching (planned for future)
- Synchronous API calls (async conversion planned)
- Hebrew addresses work best; English support is limited
- Rate limiting is per-instance, not distributed
- Deal data freshness depends on government updates (not real-time)

## Important Notes for AI Agents

- This project uses **FastMCP**, not the standard MCP library
- All coordinate tuples are `(longitude, latitude)` in ITM projection (Israeli Transverse Mercator)
- When reading `govmap.py`, note it's ~1000 lines with multiple helper functions - use search/grep to find specific methods
- Floor numbers in Hebrew (e.g., "קרקע", "מרתף") are parsed by `_extract_floor_number()`
- Deal types: 1 = first hand/new construction, 2 = second hand/resale
