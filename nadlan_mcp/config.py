"""
Configuration management for Nadlan MCP.

This module provides centralized configuration for API clients, timeouts,
rate limiting, and other settings. Configuration can be set via environment
variables or code.
"""

import os
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class GovmapConfig:
    """Configuration for Govmap API client."""
    
    # API settings
    base_url: str = field(
        default_factory=lambda: os.getenv(
            "GOVMAP_BASE_URL", 
            "https://www.govmap.gov.il/api/"
        )
    )
    
    # Timeout settings (in seconds)
    connect_timeout: int = field(
        default_factory=lambda: int(os.getenv("GOVMAP_CONNECT_TIMEOUT", "10"))
    )
    read_timeout: int = field(
        default_factory=lambda: int(os.getenv("GOVMAP_READ_TIMEOUT", "30"))
    )
    
    # Retry settings
    max_retries: int = field(
        default_factory=lambda: int(os.getenv("GOVMAP_MAX_RETRIES", "3"))
    )
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
    
    # User agent
    user_agent: str = field(
        default_factory=lambda: os.getenv(
            "GOVMAP_USER_AGENT",
            "NadlanMCP/1.0.0"
        )
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
        if not self.base_url:
            raise ValueError("base_url cannot be empty")
        if not self.user_agent:
            raise ValueError("user_agent cannot be empty")


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

