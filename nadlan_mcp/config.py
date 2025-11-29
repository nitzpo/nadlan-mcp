"""
Configuration management for Nadlan MCP.

This module provides centralized configuration for API clients, timeouts,
rate limiting, and other settings. Configuration can be set via environment
variables or code.
"""

from dataclasses import dataclass, field
import os
from typing import Optional


@dataclass
class GovmapConfig:
    """Configuration for Govmap API client."""

    # API settings
    base_url: str = field(
        default_factory=lambda: os.getenv("GOVMAP_BASE_URL", "https://www.govmap.gov.il/api/")
    )

    # Timeout settings (in seconds)
    connect_timeout: int = field(
        default_factory=lambda: int(os.getenv("GOVMAP_CONNECT_TIMEOUT", "10"))
    )
    read_timeout: int = field(default_factory=lambda: int(os.getenv("GOVMAP_READ_TIMEOUT", "30")))

    # Retry settings
    max_retries: int = field(default_factory=lambda: int(os.getenv("GOVMAP_MAX_RETRIES", "3")))
    retry_min_wait: int = field(
        default_factory=lambda: int(os.getenv("GOVMAP_RETRY_MIN_WAIT", "1"))
    )
    retry_max_wait: int = field(
        default_factory=lambda: int(os.getenv("GOVMAP_RETRY_MAX_WAIT", "10"))
    )

    # Rate limiting
    requests_per_second: float = field(
        default_factory=lambda: float(os.getenv("GOVMAP_REQUESTS_PER_SECOND", "5.0"))
    )

    # Default search parameters
    default_radius_meters: int = field(
        default_factory=lambda: int(os.getenv("GOVMAP_DEFAULT_RADIUS", "50"))
    )
    default_years_back: int = field(
        default_factory=lambda: int(os.getenv("GOVMAP_DEFAULT_YEARS_BACK", "2"))
    )
    default_deal_limit: int = field(
        default_factory=lambda: int(os.getenv("GOVMAP_DEFAULT_DEAL_LIMIT", "100"))
    )

    # Performance optimization
    max_polygons_to_query: int = field(
        default_factory=lambda: int(os.getenv("GOVMAP_MAX_POLYGONS", "10"))
    )

    # Outlier Detection & Statistical Refinement
    analysis_outlier_method: str = field(
        default_factory=lambda: os.getenv("ANALYSIS_OUTLIER_METHOD", "iqr")
    )
    analysis_iqr_multiplier: float = field(
        default_factory=lambda: float(os.getenv("ANALYSIS_IQR_MULTIPLIER", "1.0"))
    )
    analysis_min_deals_for_outlier_detection: int = field(
        default_factory=lambda: int(os.getenv("ANALYSIS_MIN_DEALS_FOR_OUTLIER_DETECTION", "10"))
    )

    # Percentage-based backup filtering (catches extreme outliers in heterogeneous data)
    analysis_use_percentage_backup: bool = field(
        default_factory=lambda: os.getenv("ANALYSIS_USE_PERCENTAGE_BACKUP", "true").lower()
        == "true"
    )
    analysis_percentage_threshold: float = field(
        default_factory=lambda: float(os.getenv("ANALYSIS_PERCENTAGE_THRESHOLD", "0.4"))
    )

    # Hard Bounds for Price per Sqm (catches obvious data errors)
    analysis_price_per_sqm_min: float = field(
        default_factory=lambda: float(os.getenv("ANALYSIS_PRICE_PER_SQM_MIN", "1000"))
    )
    analysis_price_per_sqm_max: float = field(
        default_factory=lambda: float(os.getenv("ANALYSIS_PRICE_PER_SQM_MAX", "100000"))
    )

    # Hard Bounds for Deal Amount (catches partial deals)
    analysis_min_deal_amount: float = field(
        default_factory=lambda: float(os.getenv("ANALYSIS_MIN_DEAL_AMOUNT", "100000"))
    )

    # Statistical Robustness (for investment analysis)
    analysis_use_robust_volatility: bool = field(
        default_factory=lambda: os.getenv("ANALYSIS_USE_ROBUST_VOLATILITY", "true").lower()
        == "true"
    )
    analysis_use_robust_trends: bool = field(
        default_factory=lambda: os.getenv("ANALYSIS_USE_ROBUST_TRENDS", "true").lower() == "true"
    )

    # Reporting
    analysis_include_unfiltered_stats: bool = field(
        default_factory=lambda: os.getenv("ANALYSIS_INCLUDE_UNFILTERED_STATS", "true").lower()
        == "true"
    )

    # Distance Filtering for Deal Relevance
    max_street_deal_distance_meters: int = field(
        default_factory=lambda: int(os.getenv("MAX_STREET_DEAL_DISTANCE_METERS", "500"))
    )
    max_neighborhood_deal_distance_meters: int = field(
        default_factory=lambda: int(os.getenv("MAX_NEIGHBORHOOD_DEAL_DISTANCE_METERS", "1000"))
    )

    # User agent
    user_agent: str = field(
        default_factory=lambda: os.getenv("GOVMAP_USER_AGENT", "NadlanMCP/1.0.0")
    )

    def __post_init__(self):
        """Validate configuration after initialization."""
        self._validate()

    def _validate(self):
        """Validate configuration values."""
        if self.connect_timeout <= 0:
            raise ValueError("connect_timeout must be positive")
        if self.read_timeout <= 0:
            raise ValueError("read_timeout must be positive")
        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        if self.retry_min_wait <= 0:
            raise ValueError("retry_min_wait must be positive")
        if self.retry_max_wait < self.retry_min_wait:
            raise ValueError("retry_max_wait must be >= retry_min_wait")
        if self.requests_per_second <= 0:
            raise ValueError("requests_per_second must be positive")
        if self.default_radius_meters <= 0:
            raise ValueError("default_radius_meters must be positive")
        if self.default_years_back <= 0:
            raise ValueError("default_years_back must be positive")
        if self.default_deal_limit <= 0:
            raise ValueError("default_deal_limit must be positive")
        if self.max_polygons_to_query <= 0:
            raise ValueError("max_polygons_to_query must be positive")
        if not self.base_url:
            raise ValueError("base_url cannot be empty")
        if not self.user_agent:
            raise ValueError("user_agent cannot be empty")

        # Validate outlier detection settings
        if self.analysis_outlier_method not in ["iqr", "percent", "none"]:
            raise ValueError("analysis_outlier_method must be one of: iqr, percent, none")
        if self.analysis_iqr_multiplier <= 0:
            raise ValueError("analysis_iqr_multiplier must be positive")
        if self.analysis_min_deals_for_outlier_detection < 0:
            raise ValueError("analysis_min_deals_for_outlier_detection must be non-negative")
        if self.analysis_percentage_threshold <= 0 or self.analysis_percentage_threshold >= 1:
            raise ValueError("analysis_percentage_threshold must be between 0 and 1")
        if self.analysis_price_per_sqm_min <= 0:
            raise ValueError("analysis_price_per_sqm_min must be positive")
        if self.analysis_price_per_sqm_max <= self.analysis_price_per_sqm_min:
            raise ValueError("analysis_price_per_sqm_max must be > analysis_price_per_sqm_min")
        if self.analysis_min_deal_amount <= 0:
            raise ValueError("analysis_min_deal_amount must be positive")


# Global configuration instance
_config: Optional[GovmapConfig] = None


def get_config() -> GovmapConfig:
    """
    Get the global configuration instance.

    Returns:
        GovmapConfig: The global configuration object
    """
    global _config
    if _config is None:
        _config = GovmapConfig()
    return _config


def set_config(config: GovmapConfig):
    """
    Set the global configuration instance.

    Args:
        config: The new configuration object
    """
    global _config
    _config = config


def reset_config():
    """Reset the global configuration to default values."""
    global _config
    _config = None
