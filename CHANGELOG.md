# Changelog

All notable changes to Nadlan-MCP will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2025-01-27

### 💥 BREAKING CHANGES
- **Pydantic Models Integration (Phase 4.1)**: All API methods now return Pydantic v2 models instead of dicts
  - `GovmapClient` methods return typed models: `Deal`, `AutocompleteResponse`, `DealStatistics`, etc.
  - Use model attributes (e.g., `deal.deal_amount`) instead of dict access (e.g., `deal["dealAmount"]`)
  - Field names are snake_case in Python (e.g., `deal_amount`, `asset_area`)
  - See MIGRATION.md for complete upgrade guide

### ✨ Added
- **Pydantic v2 Data Models** (nadlan_mcp/govmap/models.py):
  - `CoordinatePoint` - ITM coordinates (frozen/immutable)
  - `Address` - Israeli address with coordinates
  - `AutocompleteResult` & `AutocompleteResponse` - Autocomplete data
  - `Deal` - Real estate transaction with computed `price_per_sqm` field
  - `DealStatistics` - Statistical aggregations
  - `MarketActivityScore` - Market activity metrics
  - `InvestmentAnalysis` - Investment potential analysis
  - `LiquidityMetrics` - Market liquidity metrics
  - `DealFilters` - Filtering criteria with validation
  - `OutlierReport` - Outlier detection metadata (Nov 2025)
- **Outlier Detection System** (nadlan_mcp/govmap/outlier_detection.py):
  - IQR-based outlier detection (configurable k multiplier, default 1.0)
  - Percentage-based backup filtering (40% threshold for heterogeneous data)
  - Hard bounds filtering (price_per_sqm, min deal amount)
  - Robust volatility metrics using IQR instead of std_dev
  - Transparent reporting (filtered + unfiltered statistics)
- **HTTP Server Support**: Added `run_http_server.py` for cloud deployment
- **Distance-based Deal Prioritization**: Prioritize deals by proximity to search address
- **Comprehensive Test Suite** (Phase 5):
  - 314 total tests (195 unit/integration + 10 API health + model tests)
  - 84% code coverage
  - VCR.py infrastructure for API recording
  - Weekly API health checks
- **CI/CD Workflows** (.github/workflows/):
  - code-quality.yml - Ruff formatting & linting
  - test.yml - Pytest with coverage reporting
  - claude.yml & claude-code-review.yml - Claude Code integration
- **Configuration Variables** for outlier detection:
  - `ANALYSIS_OUTLIER_METHOD`, `ANALYSIS_IQR_MULTIPLIER`
  - `ANALYSIS_USE_PERCENTAGE_BACKUP`, `ANALYSIS_PERCENTAGE_THRESHOLD`
  - `ANALYSIS_PRICE_PER_SQM_MIN/MAX`, `ANALYSIS_MIN_DEAL_AMOUNT`
  - `ANALYSIS_USE_ROBUST_VOLATILITY`, `ANALYSIS_USE_ROBUST_TRENDS`

### 🔄 Changed
- **All statistics functions** now return Pydantic models instead of dicts
- **All filtering functions** accept and return Pydantic `Deal` models
- **All market analysis functions** return typed models
- **MCP tool responses** now serialize models using `.model_dump()`
- **Default IQR multiplier** changed from 1.5 to 1.0 (more aggressive outlier filtering)
- **Percentage threshold** changed from 50% to 40% (tighter outlier filtering)

### 🐛 Fixed
- Same-building detection using correct API field names
- Rooms filter not working due to missing alias
- Duplicate polygon queries causing redundant API calls
- Flaky temporal tests for market activity trend detection
- MCP response structure normalization across all tools

### 📚 Documentation
- Created MIGRATION.md with v1.x → v2.0.0 upgrade guide
- Updated ARCHITECTURE.md with Pydantic models layer
- Updated CLAUDE.md with model patterns and examples
- Created comprehensive test documentation (tests/api_health/README.md)
- Phase status docs: PHASE3-REFACTORING.md, PHASE4.1-STATUS.md, PHASE5-STATUS.md

## [1.0.0] - 2024-10-30

### ✨ Added - Phase 3: Package Refactoring
- **Modular Package Structure**: Refactored monolithic `govmap.py` (1,378 lines) into organized package:
  - `govmap/client.py` - Core API client (~700 lines)
  - `govmap/validators.py` - Input validation (~100 lines)
  - `govmap/filters.py` - Deal filtering (~140 lines)
  - `govmap/statistics.py` - Statistical calculations (~130 lines)
  - `govmap/market_analysis.py` - Market analysis (~450 lines)
  - `govmap/utils.py` - Helper utilities (~140 lines)
- **Backward Compatibility**: All existing imports still work

### ✨ Added - Phase 2: Core Functionality
- **10 MCP Tools** (all implemented):
  - `autocomplete_address` - Address search
  - `get_deals_by_radius` - Radius-based deal search
  - `get_street_deals` - Street-level deals
  - `get_neighborhood_deals` - Neighborhood deals
  - `find_recent_deals_for_address` - Comprehensive analysis
  - `analyze_market_trends` - Trend analysis
  - `compare_addresses` - Multi-address comparison
  - `get_valuation_comparables` - Comparable properties
  - `get_deal_statistics` - Statistical aggregations
  - `get_market_activity_metrics` - Market activity & liquidity
- **Enhanced Filtering**: Property type, rooms, price range, area, floor
- **Market Analysis Functions**:
  - `calculate_market_activity_score()` - Volume and velocity metrics
  - `analyze_investment_potential()` - ROI, appreciation, risk
  - `get_market_liquidity()` - Time-to-sell, supply/demand

### ✨ Added - Phase 1: Code Quality
- **Configuration Management** (config.py):
  - Environment variable support for all settings
  - Configurable timeouts, retries, rate limits
- **Reliability Features**:
  - Retry logic with exponential backoff
  - Rate limiting (5 requests/second default)
  - Comprehensive input validation
  - Standardized error handling (raise exceptions, not empty lists)
- **Development Infrastructure**:
  - requirements.txt with pinned versions
  - requirements-dev.txt for dev dependencies
  - Pre-commit hooks configuration
  - Ruff for formatting & linting

### 📚 Documentation
- Created ARCHITECTURE.md - System design documentation
- Created CLAUDE.md - AI coding agent guidance
- Created USECASES.md - Feature roadmap
- Created TASKS.md - Implementation tracking
- Created TESTING.md - Test documentation
- Created API_REFERENCE.md - API documentation
- Created CONTRIBUTING.md - Contribution guidelines
- Created DEPLOYMENT.md - Deployment guide

## [0.1.0] - Initial Release

### ✨ Added
- Basic MCP server with Govmap API integration
- FastMCP framework integration
- Address autocomplete functionality
- Basic deal search by address
- Initial test suite
- README with setup instructions

---

## Version History Summary

- **v2.0.0** (2025-01-27): Pydantic models + outlier detection (BREAKING)
- **v1.0.0** (2024-10-30): Package refactoring + 10 MCP tools + market analysis
- **v0.1.0** (2024): Initial MVP release
