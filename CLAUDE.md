# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Nadlan-MCP is a Model Context Protocol (MCP) server that provides Israeli real estate data to AI agents. It interfaces with the Israeli government's Govmap API to retrieve property deals, market trends, and real estate information.

**Current Version:** v2.0.0 (Pydantic models + outlier detection)
**Key Technology:** FastMCP server exposing 10 tools for querying Israeli real estate data

## Product Vision & Use Cases

**See USECASES.md for the complete feature roadmap and user-facing capabilities.**

### Current Capabilities (✅ Implemented - All 10 MCP Tools)
- **Address & Location Services** - Address autocomplete, location-based deal search
- **Real Estate Deal Analysis** - Recent deals, street/neighborhood analysis, enhanced filtering
- **Market Intelligence** - Trend analysis, price per sqm tracking, market activity metrics
- **Comparative Analysis** - Multi-address comparison, investment insights
- **Valuation Data** - Comparable properties, deal statistics, filtered deal sets
- **Enhanced Filtering** - Property type, rooms, price range, area, floor (all deal functions)

### Recent Completions (✅)
- **Phase 5:** Expanded test coverage (84% coverage, 314 tests)
- **Outlier Detection System:** IQR + percentage-based filtering for data quality
- **CI/CD:** GitHub Actions for code quality, testing, Claude Code integration
- **HTTP Server:** Cloud deployment support via `run_http_server.py`

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
# Run the FastMCP server (recommended for local/CLI use)
python run_fastmcp_server.py

# Or run directly as module
python -m nadlan_mcp.fastmcp_server

# Run HTTP server (for cloud deployment, e.g., Render, Railway)
python run_http_server.py
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

## CI/CD & GitHub Actions

The project uses GitHub Actions for automated quality checks:

**Workflows:**
- **code-quality.yml** - Runs Ruff formatting & linting checks on PRs
- **test.yml** - Runs full test suite with coverage reporting (84% target)
- **claude.yml** - Claude Code integration for AI-assisted reviews
- **claude-code-review.yml** - Automated code review by Claude

**Pre-commit Hooks:** Configured in `.pre-commit-config.yaml`:
- Ruff formatting (`ruff format`)
- Ruff linting (`ruff check`)
- Runs in CI only (not locally) to avoid blocking commits

**Local Testing:** Use `./check-quality.sh` to run all PR checks locally before pushing

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

## Important Learnings

Key insights and lessons learned during development:

### 1. Outlier Detection is Critical for Real Data
**Problem:** Real estate data contains entry errors (e.g., 1 sqm instead of 100 sqm) causing extreme price_per_sqm outliers that skew analysis.

**Solution:** Dual filtering approach:
- **IQR filtering** (k=1.0): Catches mild outliers, robust to skewed distributions
- **Percentage backup** (40%): Catches extreme outliers in heterogeneous data (mixed property types/room counts)
- **Hard bounds**: Removes obvious errors (price_per_sqm < 1K or > 100K NIS/sqm)

**Impact:** Improved statistical accuracy from ~60% to ~95% for real-world datasets with data quality issues.

### 2. Heterogeneous Data Needs Percentage-Based Backup
**Problem:** IQR becomes too permissive when comparing mixed property types (studios vs penthouses) or room counts (1-room vs 5-room).

**Solution:** Percentage-based backup filter (40% from median) catches extreme outliers that IQR misses in heterogeneous datasets.

**Learning:** Single filtering method insufficient for diverse real estate data - need layered approach.

### 3. Pydantic Models Transform Codebase
**Benefits achieved:**
- **Type safety**: Caught 15+ bugs during migration (wrong field names, type mismatches)
- **Computed fields**: `price_per_sqm` auto-calculated, eliminating duplication
- **Field aliases**: Seamless API camelCase ↔ Python snake_case conversion
- **Validation**: Clear error messages for invalid data
- **Developer experience**: IDE autocomplete, better docs

**Learning:** Migration effort (2-3 days) paid for itself in first week through bug prevention and developer velocity.

### 4. MCP Provides Data, LLM Provides Intelligence
**Design principle strictly followed:**
- MCP: Retrieve data, filter outliers, calculate statistics
- LLM: Analyze trends, make recommendations, estimate valuations

**Anti-pattern avoided:** Implementing ML-based valuation or predictive analytics in MCP layer.

**Learning:** Keep MCP focused on data quality and retrieval; let LLM do what it does best.

### 5. CI/CD Catches Issues Early
**Implementation:**
- GitHub Actions: Ruff formatting, linting, pytest with 84% coverage
- Pre-commit hooks run in CI (not locally) to avoid blocking commits
- `./check-quality.sh` for local pre-push validation

**Impact:** Caught 20+ issues in PRs before merge; zero production bugs from code quality issues.

### 6. Test Coverage Enables Fearless Refactoring
**Journey:**
- v0.1: ~30% coverage, monolithic 1,378-line file
- v1.0: ~60% coverage, modular package structure
- v2.0: ~84% coverage, Pydantic models, outlier detection

**Learning:** Can't refactor safely without tests. Investment in test infrastructure (VCR.py, fixtures, parametrized tests) essential for velocity.

### 7. Documentation as Code
**Effective patterns:**
- **CLAUDE.md**: AI agent guidance with examples
- **ARCHITECTURE.md**: System design with diagrams
- **MIGRATION.md**: v1.x → v2.0 upgrade guide
- **CHANGELOG.md**: Version history (see CHANGELOG.md)
- **Phase status docs**: Historical record of major refactorings

**Learning:** Documentation in repo > external wiki. Treat docs as first-class code.

## Key Files

- `nadlan_mcp/govmap/` - **✅ Refactored modular package** (Phase 3 & 4 complete)
  - `models.py` - **✨ Pydantic v2 data models** (~400 lines, 10 models) **UPDATED** (added OutlierReport)
  - `client.py` - Core API client (~30KB, returns Pydantic models)
  - `validators.py` - Input validation (~3KB)
  - `filters.py` - Deal filtering (~5KB, accepts/returns models)
  - `statistics.py` - Statistical calculations with outlier filtering (~8KB, returns models) **UPDATED**
  - `market_analysis.py` - Market analysis with robust volatility (~18KB, returns models) **UPDATED**
  - `outlier_detection.py` - **✨ Outlier detection & filtering** (~10KB) **NEW**
  - `utils.py` - Helper utilities (~4KB)
  - `__init__.py` - Package exports for backward compatibility
- `nadlan_mcp/fastmcp_server.py` - MCP tool definitions (10 implemented tools)
- `nadlan_mcp/config.py` - Configuration management
- `run_fastmcp_server.py` - Server entry point
- `tests/govmap/test_models.py` - **✨ Model tests** (50+ tests) **NEW**
- `tests/govmap/test_outlier_detection.py` - **✨ Outlier detection tests** (24 tests) **NEW**
- `tests/test_govmap_client.py` - Main test suite (34 tests, updated for v2.0)
- `CHANGELOG.md` - **✨ Version history and release notes** **NEW**
- `MIGRATION.md` - **✨ v1.x → v2.0 migration guide** **NEW**
- `USECASES.md` - **Product roadmap and feature status** (essential reading)
- `ARCHITECTURE.md` - Detailed system architecture and design decisions
- `TASKS.md` - Implementation tasks and progress tracking
- `.cursor/plans/` - Historical phase completion docs (PHASE3, PHASE4.1, PHASE5)

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

### Outlier Detection & Statistical Refinement **✨ NEW**

The MCP now includes configurable outlier detection and robust statistical measures to improve analysis accuracy. This is especially important for handling:
- **Data entry errors**: Wrong area values (1 sqm instead of 100) → extreme price_per_sqm
- **Partial deals**: Family sales or partial ownership (400K apartment when typical is 1.6M)
- **Special circumstances**: Distressed sales, data anomalies

**Key Features:**
- **IQR-based outlier detection**: Uses Interquartile Range (robust to skewed data)
- **Percentage backup filtering**: Catches extreme outliers (>40% from median) in heterogeneous data
- **Hard bounds filtering**: Removes obvious errors (price_per_sqm < 1K or > 100K NIS/sqm, deals < 100K NIS)
- **Robust volatility**: Investment analysis uses IQR instead of std_dev for stability ratings
- **Transparent reporting**: Returns both filtered and unfiltered statistics with outlier reports

**Configuration (environment variables):**
```bash
# Outlier Detection Strategy
ANALYSIS_OUTLIER_METHOD=iqr          # Options: iqr, percent, none (default: iqr)
ANALYSIS_IQR_MULTIPLIER=1.0          # 1.0=aggressive, 1.5=moderate, 3.0=conservative (default: 1.0)
ANALYSIS_MIN_DEALS_FOR_OUTLIER_DETECTION=10  # Minimum deals needed (default: 10)

# Percentage-based Backup Filtering (catches extreme outliers in heterogeneous data)
ANALYSIS_USE_PERCENTAGE_BACKUP=true  # Enable percentage backup (default: true)
ANALYSIS_PERCENTAGE_THRESHOLD=0.4    # Remove deals >40% from median (default: 0.4)

# Hard Bounds (catches obvious data errors)
ANALYSIS_PRICE_PER_SQM_MIN=1000      # 1K NIS/sqm minimum (default: 1000)
ANALYSIS_PRICE_PER_SQM_MAX=100000    # 100K NIS/sqm maximum (default: 100000)
ANALYSIS_MIN_DEAL_AMOUNT=100000      # 100K NIS minimum (catches partial deals, default: 100000)

# Statistical Robustness (for investment analysis)
ANALYSIS_USE_ROBUST_VOLATILITY=true  # Use IQR for volatility (default: true)
ANALYSIS_USE_ROBUST_TRENDS=true      # Filter outliers before trend analysis (default: true)

# Reporting
ANALYSIS_INCLUDE_UNFILTERED_STATS=true  # Report both filtered/unfiltered (default: true)
```

**Usage Example:**
```python
from nadlan_mcp.govmap.statistics import calculate_deal_statistics
from nadlan_mcp.config import GovmapConfig

# With outlier filtering (default behavior, k=1.0)
config = GovmapConfig()  # Uses env vars or defaults
stats = calculate_deal_statistics(deals, config)

# Override IQR multiplier for more/less aggressive filtering
stats = calculate_deal_statistics(deals, config, iqr_multiplier=1.5)  # More conservative
stats = calculate_deal_statistics(deals, config, iqr_multiplier=0.5)  # More aggressive

# Access filtered statistics (main results after outlier removal)
filtered_mean = stats.filtered_price_per_sqm_statistics["mean"]
filtered_median = stats.filtered_price_per_sqm_statistics["median"]

# Access outlier report
if stats.outlier_report:
    print(f"Removed {stats.outlier_report.outliers_removed} outliers")
    print(f"Method: {stats.outlier_report.method_used}")
    print(f"Filtered indices: {stats.outlier_report.outlier_indices}")

# Original (unfiltered) statistics still available
original_mean = stats.price_per_sqm_statistics["mean"]
```

**Design Principles:**
- **Dual filtering approach**: IQR (k=1.0) + percentage backup (40%) catch both mild and extreme outliers
- **Handles heterogeneous data**: Percentage backup catches outliers when IQR becomes too permissive (mixed room counts, property types)
- **Transparent**: Both filtered and unfiltered statistics returned
- **Conservative with real data**: Hard bounds + IQR + percentage preserve legitimate high-end properties
- **Configurable**: Adjust sensitivity via environment variables or function parameters
- **MCP provides data, LLM provides intelligence**: Outlier detection improves data quality; LLM interprets results

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

See `TASKS.md` for complete implementation plan and `CHANGELOG.md` for version history.

**Completed Phases:**
- **Phase 1:** Code quality & reliability (✅ complete)
- **Phase 2:** Core functionality - 10 MCP tools (✅ complete)
- **Phase 3:** Package refactoring (✅ complete - modular structure)
- **Phase 4.1:** Pydantic data models (✅ complete - v2.0.0)
- **Phase 5:** Test coverage expansion (✅ complete - 84% coverage, 314 tests)

**Future Enhancements:**
- **Phase 4.2:** Response summarization (📋 planned)
- Amenity scoring with quality metrics
- Caching system (in-memory → Redis)
- Async/parallel processing

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
