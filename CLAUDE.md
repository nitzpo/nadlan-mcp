# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Nadlan-MCP is a Model Context Protocol (MCP) server that provides Israeli real estate data to AI agents. It interfaces with the Israeli government's Govmap API to retrieve property deals, market trends, and real estate information.

**Key Technology:** FastMCP server exposing 7 main tools for querying Israeli real estate data

## Product Vision & Use Cases

**See USECASES.md for the complete feature roadmap and user-facing capabilities.**

### Current Capabilities (✅ Implemented - All 10 MCP Tools)
- **Address & Location Services** - Address autocomplete, location-based deal search
- **Real Estate Deal Analysis** - Recent deals, street/neighborhood analysis, enhanced filtering
- **Market Intelligence** - Trend analysis, price per sqm tracking, market activity metrics
- **Comparative Analysis** - Multi-address comparison, investment insights
- **Valuation Data** - Comparable properties, deal statistics, filtered deal sets
- **Enhanced Filtering** - Property type, rooms, price range, area, floor (all deal functions)

### In Development (🚧 In Progress)
- Phase 6-7: Documentation improvements, code quality with Ruff/mypy, pre-commit hooks

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

- Don't forget the virtualenv in venv/

### Code Quality Workflow

**IMPORTANT: Before making any commits, ensure code quality:**

```bash
# Quick check - runs all PR checks locally
./check-quality.sh

# Or manually:
ruff format .        # Format code
ruff check . --fix   # Fix lint issues
pytest tests/ -m "not api_health" -q  # Run tests
ruff check .         # Verify no issues remain
```

**For human developers using VSCode/Cursor:**
- Install Ruff extension (charliermarsh.ruff)
- Code is auto-formatted on save
- Lint errors shown inline
- `.vscode/settings.json` configures this automatically

**For Claude Code:**
- Always run `ruff format .` before committing
- Always run `ruff check . --fix` to auto-fix issues
- Always run tests to verify no breakage
- Or use `./check-quality.sh` to run all checks at once

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
# Format code with Ruff (replaces black + isort)
ruff format .

# Lint code with Ruff (replaces flake8 + many more)
ruff check .

# Lint with auto-fix
ruff check . --fix

# Type checking with mypy (currently has type annotation issues - WIP)
mypy nadlan_mcp/

# Run all pre-commit hooks manually (for CI, not installed locally)
pre-commit run --all-files

# Note: Pre-commit hooks run as PR checks in GitHub Actions, not locally
# This allows commits without blocking, with checks shown in PRs
```

## Architecture

The codebase follows a four-layer architecture:

### 1. MCP Tools Layer (`nadlan_mcp/fastmcp_server.py`)
- Exposes 10 tools to LLM clients via FastMCP
- Handles tool parameter validation and JSON response formatting
- Serializes Pydantic models to JSON using `.model_dump()`
- Main tools: `find_recent_deals_for_address`, `analyze_market_trends`, `compare_addresses`

### 2. Data Models Layer (`nadlan_mcp/govmap/models.py`) **✨ NEW in v2.0**
- **Pydantic v2 models** for type safety and validation
- 9 comprehensive models covering all data structures
- Key models: `Deal`, `AutocompleteResponse`, `DealStatistics`, `MarketActivityScore`
- Features:
  - Computed fields (e.g., `price_per_sqm` auto-calculated)
  - Field aliases (API camelCase ↔ Python snake_case)
  - Validation with clear error messages
  - Immutable coordinates for data integrity
- **Breaking Change:** All API methods return models, not dicts (v2.0.0)

### 3. Business Logic Layer (`nadlan_mcp/govmap/` package)
- Modular package with specialized modules (see ARCHITECTURE.md for details)
- `client.py` - GovmapClient class (returns Pydantic models)
- `models.py` - Pydantic data models **✨ NEW**
- `validators.py` - Input validation functions
- `filters.py` - Deal filtering logic (accepts/returns models)
- `statistics.py` - Statistical calculations (returns models)
- `market_analysis.py` - Market analysis functions (returns models)
- `utils.py` - Helper utilities
- Reliability features: retry logic with exponential backoff, rate limiting, input validation
- **Key Design Principle:** MCP provides data, LLM provides intelligence - avoid complex analysis in the MCP layer

### 4. Configuration Layer (`nadlan_mcp/config.py`)
- `GovmapConfig` dataclass with environment variable support
- Global config accessed via `get_config()` and `set_config()`
- All timeouts, retries, rate limits are configurable

## Key Files

- `nadlan_mcp/govmap/` - **✅ Refactored modular package** (Phase 3 & 4 complete)
  - `models.py` - **✨ Pydantic v2 data models** (~338 lines, 9 models) **NEW in v2.0**
  - `client.py` - Core API client (~30KB, returns Pydantic models)
  - `validators.py` - Input validation (~3KB)
  - `filters.py` - Deal filtering (~5KB, accepts/returns models)
  - `statistics.py` - Statistical calculations (~4KB, returns models)
  - `market_analysis.py` - Market analysis (~17KB, returns models)
  - `utils.py` - Helper utilities (~4KB)
  - `__init__.py` - Package exports for backward compatibility
- `nadlan_mcp/fastmcp_server.py` - MCP tool definitions (10 implemented tools)
- `nadlan_mcp/config.py` - Configuration management
- `run_fastmcp_server.py` - Server entry point
- `tests/govmap/test_models.py` - **✨ Model tests** (50+ tests) **NEW**
- `tests/test_govmap_client.py` - Main test suite (34 tests, partially updated for v2.0)
- `MIGRATION.md` - **✨ v1.x → v2.0 migration guide** **NEW**
- `USECASES.md` - **Product roadmap and feature status** (essential reading)
- `ARCHITECTURE.md` - Detailed system architecture and design decisions
- `TASKS.md` - Implementation tasks and progress tracking
- `.cursor/plans/PHASE4.1-STATUS.md` - Phase 4.1 completion status **NEW**

## Available MCP Tools

**Implemented (✅ All 10 Tools):**
- `autocomplete_address` - Search and autocomplete Israeli addresses
- `get_deals_by_radius` - Get deals within a radius of coordinates
- `get_street_deals` - Get deals for a specific street polygon
- `get_neighborhood_deals` - Get deals for a neighborhood polygon
- `find_recent_deals_for_address` - Main comprehensive analysis tool
- `analyze_market_trends` - Analyze market trends and price patterns
- `compare_addresses` - Compare real estate markets between multiple addresses
- `get_valuation_comparables` - Get comparable properties for valuation analysis
- `get_deal_statistics` - Calculate statistical aggregations on deal data
- `get_market_activity_metrics` - Detailed market activity and velocity metrics

**Planned (📋):**
- `get_address_amenity_rating` - Comprehensive amenity analysis with quality metrics
- `compare_addresses_by_amenities` - Side-by-side amenity comparison
- `find_amenities_near_address` - Raw amenity list with quality data

## Important Patterns

### Using Pydantic Models (v2.0+) **✨ NEW**

All API methods now return Pydantic models instead of dicts:

```python
from nadlan_mcp.govmap import GovmapClient
from nadlan_mcp.govmap.models import Deal, AutocompleteResponse

client = GovmapClient()

# Returns AutocompleteResponse model
result = client.autocomplete_address("חולון")
address_text = result.results[0].text  # Model attribute
coords = result.results[0].coordinates  # Optional[CoordinatePoint]

# Returns List[Deal]
deals = client.get_street_deals("polygon123")
for deal in deals:
    price = deal.deal_amount  # float (snake_case)
    area = deal.asset_area  # Optional[float]
    price_per_sqm = deal.price_per_sqm  # Computed field!

# Serialize to dict/JSON when needed
deal_dict = deal.model_dump()  # Convert to dict
deal_json = deal.model_dump_json()  # Convert to JSON string
```

**Key points:**
- Use model attributes (e.g., `deal.deal_amount`), not dict access (e.g., `deal["dealAmount"]`)
- Field names are snake_case in Python (e.g., `deal_amount` not `dealAmount`)
- Computed fields like `price_per_sqm` are automatically calculated
- Use `.model_dump()` to serialize models to dicts for JSON/MCP responses
- See `MIGRATION.md` for complete migration guide

### Retry Logic
All API calls use automatic retry with exponential backoff (configurable via `GOVMAP_MAX_RETRIES`). The pattern is implemented in `GovmapClient._make_request()`.

### Rate Limiting
Client enforces rate limiting via `_rate_limit()` method, tracking last request time and sleeping if needed. Default: 5 requests/second.

### Error Handling
- Validation errors: Raise `ValueError` immediately with clear message
- Network errors: Retry with backoff, then raise `requests.RequestException`
- API response errors: Raise `ValueError` with specific details
- Pydantic validation errors: Logged as warnings, invalid deals are skipped
- **Never return empty lists on error** - always raise exceptions

### Input Validation
All user inputs are validated before API calls:
- `_validate_address()` - address strings
- `_validate_coordinates()` - coordinate tuples
- `_validate_positive_int()` - numeric parameters
- Pydantic models validate all field values automatically

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

# Performance
GOVMAP_MAX_POLYGONS=10  # Limit polygons per search (reduces API calls, improves speed)
```

## Development Roadmap

See `TASKS.md` for complete implementation plan. Current status:
- **Phase 2.2:** Market analysis tools (✅ complete)
- **Phase 2.3:** Enhanced filtering (✅ complete)
- **Phase 3:** Package refactoring (✅ complete - monolithic govmap.py refactored into modular package)
- **Phase 4.1:** Pydantic data models (✅ complete - **v2.0.0 released** with breaking changes)
- **Phase 4.2:** Response summarization (📋 planned)
- **Phase 5:** Expanded test coverage (⏳ in progress - core model tests complete)

## Common Tasks

### Adding a New MCP Tool

1. Add `@mcp.tool()` decorated function in `fastmcp_server.py`
2. Call appropriate `GovmapClient` methods
3. Format response as JSON string
4. Add error handling with try/except
5. Update README.md with tool documentation

### Adding New API Endpoint Support

1. Add method to `GovmapClient` class in `govmap/client.py`
2. Implement validation (use `validators.py` functions)
3. Implement retry logic and rate limiting (follow existing patterns)
4. Add unit tests in `tests/test_govmap_client.py`
5. Optionally expose as MCP tool in `fastmcp_server.py`

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
- **v2.0.0 Breaking Change:** All API methods now return **Pydantic models**, not dicts
  - Use model attributes (e.g., `deal.deal_amount`) not dict access (e.g., `deal["dealAmount"]`)
  - Field names are **snake_case** in Python (e.g., `deal_amount`, `asset_area`)
  - Serialize with `.model_dump()` for JSON/dicts
  - See `MIGRATION.md` for complete migration guide
- All coordinate tuples are `(longitude, latitude)` in ITM projection (Israeli Transverse Mercator)
- The `govmap` package is now modular - each module has a specific responsibility:
  - `models.py` - **Pydantic v2 data models** (9 models with validation)
  - `client.py` - API calls and HTTP logic (returns Pydantic models)
  - `validators.py` - Input validation
  - `filters.py` - Deal filtering (accepts/returns models)
  - `statistics.py` - Statistical calculations (returns models)
  - `market_analysis.py` - Market analysis metrics (returns models)
  - `utils.py` - Helper utilities
- Floor numbers in Hebrew (e.g., "קרקע", "מרתף") are parsed by `extract_floor_number()` in `utils.py`
- Deal types: 1 = first hand/new construction, 2 = second hand/resale
- Import compatibility maintained: `from nadlan_mcp.govmap import GovmapClient` still works
