"""
Pydantic models for Govmap API data structures.

This module defines type-safe models for all data structures used in the
Israeli real estate MCP system. Models provide validation, serialization,
and type safety throughout the codebase.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator, computed_field, ConfigDict


class CoordinatePoint(BaseModel):
    """
    ITM (Israeli Transverse Mercator) coordinate point.

    Attributes:
        longitude: X coordinate in ITM projection (meters)
        latitude: Y coordinate in ITM projection (meters)
    """
    longitude: float = Field(..., description="X coordinate in ITM projection (meters)")
    latitude: float = Field(..., description="Y coordinate in ITM projection (meters)")

    model_config = ConfigDict(frozen=True)  # Immutable coordinates


class Address(BaseModel):
    """
    Israeli address with coordinates and metadata.

    Attributes:
        text: Full address text (Hebrew or English)
        id: Unique identifier for the address
        type: Address type (e.g., 'address', 'street', 'city')
        score: Relevance score from autocomplete
        coordinates: ITM coordinate point
    """
    text: str = Field(..., description="Full address text")
    id: str = Field(..., description="Unique address identifier")
    type: str = Field(..., description="Address type")
    score: float = Field(default=0, description="Relevance score")
    coordinates: Optional[CoordinatePoint] = Field(default=None, description="ITM coordinates")


class AutocompleteResult(BaseModel):
    """
    Single result from address autocomplete API.

    Attributes:
        text: Display text for the address
        id: Unique identifier
        type: Result type (address, street, city, etc.)
        score: Relevance score
        coordinates: Optional coordinate point
        shape: Original WKT shape string from API
    """
    text: str
    id: str
    type: str
    score: float = 0
    coordinates: Optional[CoordinatePoint] = None
    shape: Optional[str] = None  # Original WKT POINT string from API


class AutocompleteResponse(BaseModel):
    """
    Response from address autocomplete API.

    Attributes:
        results_count: Number of results returned
        results: List of autocomplete results
    """
    results_count: int = Field(alias="resultsCount")
    results: List[AutocompleteResult] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)


class Deal(BaseModel):
    """
    Real estate deal from Govmap API.

    Represents a single property transaction with all available details.
    Most fields are optional as the API doesn't guarantee all data.

    Attributes:
        objectid: Unique deal identifier
        deal_amount: Transaction amount in NIS
        deal_date: Date of transaction
        asset_area: Property area in square meters
        settlement_name_heb: City/settlement name in Hebrew
        property_type_description: Type of property (דירה, בית, etc.)
        neighborhood: Neighborhood name
        street_name: Street name
        house_number: House number
        floor: Floor description (may be Hebrew text)
        floor_number: Parsed numeric floor number
        rooms: Number of rooms
        priority: Priority level for sorting (0=same building, 1=street, 2=neighborhood)
        shape: WKT geometry (usually MULTIPOLYGON)
        source_polygon_id: Source polygon ID
        sourceorder: Source ordering
    """
    # Required fields
    objectid: int = Field(..., description="Unique deal identifier")
    deal_amount: float = Field(..., alias="dealAmount", description="Transaction amount in NIS")
    deal_date: str = Field(..., alias="dealDate", description="Transaction date (ISO format)")

    # Common optional fields
    asset_area: Optional[float] = Field(None, alias="assetArea", description="Property area in sqm")
    settlement_name_heb: Optional[str] = Field(None, alias="settlementNameHeb", description="City name in Hebrew")
    property_type_description: Optional[str] = Field(None, alias="propertyTypeDescription", description="Property type")
    neighborhood: Optional[str] = Field(None, description="Neighborhood name")
    street_name: Optional[str] = Field(None, alias="streetName", description="Street name")
    house_number: Optional[str] = Field(None, alias="houseNumber", description="House number")

    # Floor information
    floor: Optional[str] = Field(None, description="Floor description (may be Hebrew)")
    floor_number: Optional[int] = Field(None, alias="floorNumber", description="Numeric floor number")

    # Additional details
    rooms: Optional[float] = Field(None, description="Number of rooms")

    # Priority and metadata (added by our system, not from API)
    priority: Optional[int] = Field(None, description="Priority for sorting (0=same building, 1=street, 2=neighborhood)")

    # Geometry and internal fields (often not useful for analysis)
    shape: Optional[str] = Field(None, description="WKT geometry")
    source_polygon_id: Optional[str] = Field(None, alias="sourcePolygonId", description="Source polygon ID")
    sourceorder: Optional[int] = Field(None, description="Source ordering")

    model_config = ConfigDict(
        populate_by_name=True,  # Allow both alias and field name
        extra='allow'  # Allow extra fields from API that we don't model
    )

    @computed_field
    @property
    def price_per_sqm(self) -> Optional[float]:
        """
        Calculated price per square meter.

        Returns:
            Price per sqm in NIS, or None if area is missing/zero
        """
        if self.asset_area and self.asset_area > 0:
            return round(self.deal_amount / self.asset_area, 2)
        return None

    @field_validator('deal_date', mode='before')
    @classmethod
    def parse_deal_date(cls, v: Any) -> str:
        """Parse deal date to ISO format string."""
        if isinstance(v, str):
            return v
        if isinstance(v, datetime):
            return v.isoformat()
        return str(v)


class DealStatistics(BaseModel):
    """
    Statistical analysis of real estate deals.

    Attributes:
        total_deals: Total number of deals analyzed
        price_statistics: Statistics for deal prices
        area_statistics: Statistics for property areas
        price_per_sqm_statistics: Statistics for price per sqm
        property_type_distribution: Count by property type
        date_range: Earliest and latest deal dates
    """
    total_deals: int = Field(..., description="Total number of deals analyzed")

    # Price statistics
    price_statistics: Dict[str, float] = Field(
        default_factory=dict,
        description="Price stats (mean, median, std_dev, min, max, percentiles)"
    )

    # Area statistics
    area_statistics: Dict[str, float] = Field(
        default_factory=dict,
        description="Area stats (mean, median, std_dev, min, max)"
    )

    # Price per sqm statistics
    price_per_sqm_statistics: Dict[str, float] = Field(
        default_factory=dict,
        description="Price/sqm stats (mean, median, std_dev, min, max)"
    )

    # Distribution by property type
    property_type_distribution: Dict[str, int] = Field(
        default_factory=dict,
        description="Count of deals by property type"
    )

    # Date range
    date_range: Optional[Dict[str, str]] = Field(
        None,
        description="Earliest and latest deal dates"
    )


class MarketActivityScore(BaseModel):
    """
    Market activity scoring metrics.

    Attributes:
        activity_score: Overall activity score (0-100)
        total_deals: Total number of deals in period
        deals_per_month: Average deals per month
        trend: Market trend (increasing, stable, decreasing)
        time_period_months: Analysis period in months
        monthly_distribution: Deals per month breakdown
    """
    activity_score: float = Field(..., description="Overall activity score (0-100)", ge=0, le=100)
    total_deals: int = Field(..., description="Total deals in period")
    deals_per_month: float = Field(..., description="Average deals per month")
    trend: str = Field(..., description="Market trend (increasing, stable, decreasing)")
    time_period_months: int = Field(..., description="Analysis period in months")
    monthly_distribution: Dict[str, int] = Field(
        default_factory=dict,
        description="Deals per month (YYYY-MM: count)"
    )


class InvestmentAnalysis(BaseModel):
    """
    Investment potential analysis metrics.

    Attributes:
        investment_score: Overall investment score (0-100)
        price_trend: Price trend direction
        price_appreciation_rate: Annualized price appreciation rate (%)
        price_volatility: Price volatility score (0-100, lower is more stable)
        market_stability: Stability rating description
        avg_price_per_sqm: Average price per square meter
        price_change_pct: Total price change percentage
        total_deals: Total deals analyzed (sample size)
        data_quality: Data quality assessment
    """
    investment_score: float = Field(..., description="Overall investment score (0-100)", ge=0, le=100)
    price_trend: str = Field(..., description="Price trend (increasing, stable, decreasing)")
    price_appreciation_rate: float = Field(..., description="Annual price growth rate (%)")
    price_volatility: float = Field(..., description="Price volatility score (0-100)", ge=0, le=100)
    market_stability: str = Field(..., description="Market stability rating")
    avg_price_per_sqm: float = Field(..., description="Average price per sqm")
    price_change_pct: float = Field(..., description="Total price change percentage")
    total_deals: int = Field(..., description="Total deals analyzed (sample size)")
    data_quality: str = Field(..., description="Data quality (excellent, good, fair, limited)")


class LiquidityMetrics(BaseModel):
    """
    Market liquidity metrics.

    Attributes:
        liquidity_score: Overall liquidity score (0-100, based on velocity)
        total_deals: Total deals in period
        time_period_months: Analysis period in months
        avg_deals_per_month: Average deals per month
        liquidity_rating: Market liquidity rating
        trend_direction: Liquidity trend direction
    """
    liquidity_score: float = Field(..., description="Overall liquidity score (0-100)", ge=0, le=100)
    total_deals: int = Field(..., description="Total deals in period")
    time_period_months: int = Field(..., description="Analysis period in months")
    avg_deals_per_month: float = Field(..., description="Average deals per month")
    deal_velocity: float = Field(..., description="Deal velocity (deals per month)")
    market_activity_level: str = Field(..., description="Activity level (very_high, high, moderate, low, very_low)")


class DealFilters(BaseModel):
    """
    Filtering criteria for real estate deals.

    All fields are optional - only specified filters are applied.

    Attributes:
        property_type: Filter by property type (דירה, בית, etc.)
        min_rooms: Minimum number of rooms
        max_rooms: Maximum number of rooms
        min_price: Minimum deal amount (NIS)
        max_price: Maximum deal amount (NIS)
        min_area: Minimum asset area (sqm)
        max_area: Maximum asset area (sqm)
        min_floor: Minimum floor number
        max_floor: Maximum floor number
    """
    property_type: Optional[str] = Field(None, description="Property type filter")
    min_rooms: Optional[float] = Field(None, description="Minimum rooms", ge=0)
    max_rooms: Optional[float] = Field(None, description="Maximum rooms", ge=0)
    min_price: Optional[float] = Field(None, description="Minimum price (NIS)", ge=0)
    max_price: Optional[float] = Field(None, description="Maximum price (NIS)", ge=0)
    min_area: Optional[float] = Field(None, description="Minimum area (sqm)", ge=0)
    max_area: Optional[float] = Field(None, description="Maximum area (sqm)", ge=0)
    min_floor: Optional[int] = Field(None, description="Minimum floor")
    max_floor: Optional[int] = Field(None, description="Maximum floor")

    @field_validator('max_rooms')
    @classmethod
    def validate_max_rooms(cls, v: Optional[float], info) -> Optional[float]:
        """Ensure max_rooms >= min_rooms if both specified."""
        if v is not None and info.data.get('min_rooms') is not None:
            if v < info.data['min_rooms']:
                raise ValueError("max_rooms must be >= min_rooms")
        return v

    @field_validator('max_price')
    @classmethod
    def validate_max_price(cls, v: Optional[float], info) -> Optional[float]:
        """Ensure max_price >= min_price if both specified."""
        if v is not None and info.data.get('min_price') is not None:
            if v < info.data['min_price']:
                raise ValueError("max_price must be >= min_price")
        return v

    @field_validator('max_area')
    @classmethod
    def validate_max_area(cls, v: Optional[float], info) -> Optional[float]:
        """Ensure max_area >= min_area if both specified."""
        if v is not None and info.data.get('min_area') is not None:
            if v < info.data['min_area']:
                raise ValueError("max_area must be >= min_area")
        return v

    @field_validator('max_floor')
    @classmethod
    def validate_max_floor(cls, v: Optional[int], info) -> Optional[int]:
        """Ensure max_floor >= min_floor if both specified."""
        if v is not None and info.data.get('min_floor') is not None:
            if v < info.data['min_floor']:
                raise ValueError("max_floor must be >= min_floor")
        return v
