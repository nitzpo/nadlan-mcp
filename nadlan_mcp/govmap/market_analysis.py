"""
Market analysis functions for real estate deal data.

This module provides functions for analyzing market trends, activity, and investment potential.
Focused on providing data metrics; the LLM interprets them for investment advice.
"""

import logging
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

from .models import Deal, MarketActivityScore, InvestmentAnalysis, LiquidityMetrics
from .statistics import calculate_std_dev

logger = logging.getLogger(__name__)

# Market Activity Thresholds (deals per month)
ACTIVITY_VERY_HIGH_THRESHOLD = 10
ACTIVITY_HIGH_THRESHOLD = 5
ACTIVITY_MODERATE_THRESHOLD = 3
ACTIVITY_LOW_THRESHOLD = 1

# Price Volatility Thresholds (coefficient of variation %)
VOLATILITY_VERY_VOLATILE_THRESHOLD = 50
VOLATILITY_VOLATILE_THRESHOLD = 30
VOLATILITY_MODERATE_THRESHOLD = 20
VOLATILITY_STABLE_THRESHOLD = 10

# Liquidity Thresholds (deals per month)
LIQUIDITY_VERY_HIGH_THRESHOLD = 8
LIQUIDITY_HIGH_THRESHOLD = 5
LIQUIDITY_MODERATE_THRESHOLD = 2
LIQUIDITY_LOW_THRESHOLD = 0.5


def parse_deal_dates(
    deals: List[Deal], time_period_months: Optional[int] = None
) -> Tuple[List[str], Dict[str, int], Dict[str, int]]:
    """
    Parse and filter deal dates from a list of deals.

    This helper method centralizes the date parsing logic used across
    multiple market analysis functions. It validates dates, filters by
    time period if specified, and groups deals by month and quarter.

    Args:
        deals: List of Deal model instances
        time_period_months: Optional time period to filter (from today backwards)

    Returns:
        Tuple containing:
            - List of valid deal date strings
            - Dictionary mapping year-month to deal counts
            - Dictionary mapping year-quarter to deal counts

    Raises:
        ValueError: If no valid deal dates are found
    """
    # Calculate cutoff date if time period is specified
    cutoff_date = None
    if time_period_months is not None:
        cutoff_date = datetime.now() - timedelta(days=time_period_months * 30)
        cutoff_date_str = cutoff_date.strftime("%Y-%m-%d")

    monthly_deals = defaultdict(int)
    quarterly_deals = defaultdict(int)
    deal_dates = []

    for deal in deals:
        if not deal.deal_date:
            continue

        try:
            # Convert date to string for comparison and parsing
            date_str = deal.deal_date.isoformat() if isinstance(deal.deal_date, date) else str(deal.deal_date)

            # Filter by time period if specified
            if cutoff_date is not None and date_str < cutoff_date_str:
                continue

            # Parse date components
            year = int(date_str[:4])
            month = int(date_str[5:7])
            quarter = (month - 1) // 3 + 1  # 1-4

            # Track by month and quarter
            year_month = f"{year}-{month:02d}"
            year_quarter = f"{year}-Q{quarter}"

            monthly_deals[year_month] += 1
            quarterly_deals[year_quarter] += 1
            deal_dates.append(date_str)
        except (ValueError, IndexError):
            logger.warning(f"Invalid date format: {date_str}")
            continue

    if not deal_dates:
        raise ValueError("No valid deal dates found in deals list")

    return deal_dates, dict(monthly_deals), dict(quarterly_deals)


def calculate_market_activity_score(
    deals: List[Deal], time_period_months: Optional[int] = 12
) -> MarketActivityScore:
    """
    Calculate market activity and liquidity metrics.

    This function analyzes deal frequency, velocity, and market activity levels
    to provide a comprehensive view of market liquidity.

    Args:
        deals: List of Deal model instances
        time_period_months: Time period to analyze in months (default: 12)

    Returns:
        MarketActivityScore model with:
            - total_deals: Total number of deals
            - deals_per_month: Average deals per month
            - activity_score: Market activity score (0-100)
            - trend: Activity trend ('increasing', 'stable', 'decreasing')
            - monthly_distribution: Deals per month breakdown

    Raises:
        ValueError: If deals list is empty or invalid
    """
    if not deals:
        raise ValueError("Cannot calculate market activity from empty deals list")

    # Parse deal dates and group by month (with time period filtering)
    deal_dates, monthly_deals, _ = parse_deal_dates(deals, time_period_months)

    # Calculate metrics
    total_deals = len(deal_dates)
    unique_months = len(monthly_deals)
    deals_per_month = total_deals / unique_months if unique_months > 0 else 0

    # Calculate activity score (0-100)
    # Based on deals per month using defined thresholds
    if deals_per_month >= ACTIVITY_VERY_HIGH_THRESHOLD:
        activity_score = 100
    elif deals_per_month >= ACTIVITY_HIGH_THRESHOLD:
        activity_score = 75 + ((deals_per_month - ACTIVITY_HIGH_THRESHOLD) / ACTIVITY_HIGH_THRESHOLD) * 25
    elif deals_per_month >= ACTIVITY_MODERATE_THRESHOLD:
        activity_score = 50 + ((deals_per_month - ACTIVITY_MODERATE_THRESHOLD) / (ACTIVITY_HIGH_THRESHOLD - ACTIVITY_MODERATE_THRESHOLD)) * 25
    elif deals_per_month >= ACTIVITY_LOW_THRESHOLD:
        activity_score = 25 + ((deals_per_month - ACTIVITY_LOW_THRESHOLD) / (ACTIVITY_MODERATE_THRESHOLD - ACTIVITY_LOW_THRESHOLD)) * 25
    else:
        activity_score = deals_per_month * 25

    # Calculate trend (compare first half vs second half)
    sorted_months = sorted(monthly_deals.keys())
    if len(sorted_months) >= 4:
        mid_point = len(sorted_months) // 2
        first_half_avg = sum(monthly_deals[m] for m in sorted_months[:mid_point]) / mid_point
        second_half_avg = sum(monthly_deals[m] for m in sorted_months[mid_point:]) / (
            len(sorted_months) - mid_point
        )

        change_ratio = (second_half_avg - first_half_avg) / first_half_avg if first_half_avg > 0 else 0

        if change_ratio > 0.15:
            trend = "increasing"
        elif change_ratio < -0.15:
            trend = "decreasing"
        else:
            trend = "stable"
    else:
        trend = "insufficient_data"

    return MarketActivityScore(
        activity_score=round(activity_score, 1),
        total_deals=total_deals,
        deals_per_month=round(deals_per_month, 2),
        trend=trend,
        time_period_months=time_period_months,
        monthly_distribution=dict(sorted(monthly_deals.items())),
    )


def analyze_investment_potential(deals: List[Deal]) -> InvestmentAnalysis:
    """
    Analyze investment potential based on price trends and market stability.

    This function calculates price appreciation rates, market volatility,
    and provides investment metrics for decision-making. The MCP provides
    data metrics; the LLM interprets them for investment advice.

    Args:
        deals: List of Deal model instances with price and date information

    Returns:
        InvestmentAnalysis model containing:
            - price_appreciation_rate: Annual price growth rate (%)
            - price_volatility: Price volatility score (0-100, lower is more stable)
            - market_stability: Stability rating ('very_stable', 'stable', 'moderate', 'volatile', 'very_volatile')
            - price_trend: Price direction ('increasing', 'stable', 'decreasing')
            - avg_price_per_sqm: Average price per square meter
            - price_change_pct: Total price change percentage
            - investment_score: Overall investment score (0-100)
            - data_quality: Quality of data ('excellent', 'good', 'fair', 'limited')

    Raises:
        ValueError: If deals list is empty or lacks required data
    """
    if not deals:
        raise ValueError("Cannot analyze investment potential from empty deals list")

    # Extract price per sqm and dates
    price_data = []
    for deal in deals:
        price_per_sqm = deal.price_per_sqm  # Use computed field from Deal model

        if price_per_sqm and price_per_sqm > 0 and deal.deal_date:
            try:
                # Convert date to string for parsing
                date_str = deal.deal_date.isoformat() if isinstance(deal.deal_date, date) else str(deal.deal_date)

                # Parse date for sorting
                year = int(date_str[:4])
                month = int(date_str[5:7])
                price_data.append((year + month / 12.0, price_per_sqm))
            except (ValueError, IndexError):
                continue

    if len(price_data) < 3:
        raise ValueError(
            "Insufficient data for investment analysis (need at least 3 valid deals with price and date)"
        )

    # Sort by time
    price_data.sort(key=lambda x: x[0])
    times = [p[0] for p in price_data]
    prices = [p[1] for p in price_data]

    # Calculate average price
    avg_price_per_sqm = sum(prices) / len(prices)

    # Calculate price appreciation rate (using linear regression approximation)
    n = len(price_data)
    sum_t = sum(times)
    sum_p = sum(prices)
    sum_tp = sum(t * p for t, p in price_data)
    sum_t2 = sum(t * t for t in times)

    # Linear regression slope
    if n * sum_t2 - sum_t * sum_t != 0:
        slope = (n * sum_tp - sum_t * sum_p) / (n * sum_t2 - sum_t * sum_t)
        # Convert to annual percentage change
        price_appreciation_rate = (slope / avg_price_per_sqm) * 100 if avg_price_per_sqm > 0 else 0
    else:
        price_appreciation_rate = 0

    # Calculate price change from first to last deal
    if prices[0] > 0:
        price_change_pct = ((prices[-1] - prices[0]) / prices[0]) * 100
    else:
        price_change_pct = 0

    # Determine price trend
    if price_appreciation_rate > 2:
        price_trend = "increasing"
    elif price_appreciation_rate < -2:
        price_trend = "decreasing"
    else:
        price_trend = "stable"

    # Calculate price volatility (coefficient of variation)
    std_dev = calculate_std_dev(prices)
    if avg_price_per_sqm > 0:
        coefficient_of_variation = (std_dev / avg_price_per_sqm) * 100
    else:
        coefficient_of_variation = 0

    # Convert CV to volatility score (0-100, lower is better)
    # Using defined volatility thresholds
    if coefficient_of_variation > VOLATILITY_VERY_VOLATILE_THRESHOLD:
        volatility_score = 100
        market_stability = "very_volatile"
    elif coefficient_of_variation > VOLATILITY_VOLATILE_THRESHOLD:
        volatility_score = 75 + ((coefficient_of_variation - VOLATILITY_VOLATILE_THRESHOLD) / (VOLATILITY_VERY_VOLATILE_THRESHOLD - VOLATILITY_VOLATILE_THRESHOLD)) * 25
        market_stability = "volatile"
    elif coefficient_of_variation > VOLATILITY_MODERATE_THRESHOLD:
        volatility_score = 50 + ((coefficient_of_variation - VOLATILITY_MODERATE_THRESHOLD) / (VOLATILITY_VOLATILE_THRESHOLD - VOLATILITY_MODERATE_THRESHOLD)) * 25
        market_stability = "moderate"
    elif coefficient_of_variation > VOLATILITY_STABLE_THRESHOLD:
        volatility_score = 25 + ((coefficient_of_variation - VOLATILITY_STABLE_THRESHOLD) / (VOLATILITY_MODERATE_THRESHOLD - VOLATILITY_STABLE_THRESHOLD)) * 25
        market_stability = "stable"
    else:
        volatility_score = (coefficient_of_variation / VOLATILITY_STABLE_THRESHOLD) * 25
        market_stability = "very_stable"

    # Calculate investment score (0-100)
    # Positive: price appreciation, market stability (low volatility)
    # Negative: price decline, high volatility
    appreciation_component = min(max(price_appreciation_rate * 5, -25), 50)  # -25 to +50
    stability_component = (100 - volatility_score) * 0.5  # 0 to 50

    investment_score = max(0, min(100, appreciation_component + stability_component))

    # Data quality assessment
    if n >= 20:
        data_quality = "excellent"
    elif n >= 10:
        data_quality = "good"
    elif n >= 5:
        data_quality = "fair"
    else:
        data_quality = "limited"

    return InvestmentAnalysis(
        investment_score=round(investment_score, 1),
        price_trend=price_trend,
        price_appreciation_rate=round(price_appreciation_rate, 2),
        price_volatility=round(volatility_score, 1),
        market_stability=market_stability,
        avg_price_per_sqm=round(avg_price_per_sqm, 0),
        price_change_pct=round(price_change_pct, 2),
        total_deals=n,
        data_quality=data_quality,
    )


def get_market_liquidity(
    deals: List[Deal], time_period_months: Optional[int] = 12
) -> LiquidityMetrics:
    """
    Get detailed market liquidity and turnover metrics.

    This function provides granular liquidity metrics including deal velocity,
    quarterly trends, and market turnover indicators.

    Args:
        deals: List of deal dictionaries
        time_period_months: Time period to analyze in months (default: 12)

    Returns:
        Dictionary containing:
            - total_deals: Total number of deals in period
            - deals_per_month: Average deals per month
            - deals_per_quarter: Average deals per quarter
            - quarterly_breakdown: Deals grouped by quarter
            - velocity_score: Market velocity score (0-100)
            - liquidity_rating: Liquidity rating ('very_high', 'high', 'moderate', 'low', 'very_low')
            - trend_direction: Trend in liquidity ('improving', 'stable', 'declining')
            - most_active_period: Quarter/month with most activity

    Raises:
        ValueError: If deals list is empty or invalid
    """
    if not deals:
        raise ValueError("Cannot calculate market liquidity from empty deals list")

    # Parse deal dates and group by month and quarter (with time period filtering)
    deal_dates, monthly_deals, quarterly_deals = parse_deal_dates(deals, time_period_months)

    # Calculate metrics
    total_deals = len(deal_dates)
    unique_months = len(monthly_deals)
    unique_quarters = len(quarterly_deals)

    deals_per_month = total_deals / unique_months if unique_months > 0 else 0
    deals_per_quarter = total_deals / unique_quarters if unique_quarters > 0 else 0

    # Calculate velocity score (similar to activity score but focused on turnover)
    # Based on monthly deal velocity using defined thresholds
    if deals_per_month >= LIQUIDITY_VERY_HIGH_THRESHOLD:
        velocity_score = 100
        liquidity_rating = "very_high"
    elif deals_per_month >= LIQUIDITY_HIGH_THRESHOLD:
        velocity_score = 75 + ((deals_per_month - LIQUIDITY_HIGH_THRESHOLD) / (LIQUIDITY_VERY_HIGH_THRESHOLD - LIQUIDITY_HIGH_THRESHOLD)) * 25
        liquidity_rating = "high"
    elif deals_per_month >= LIQUIDITY_MODERATE_THRESHOLD:
        velocity_score = 50 + ((deals_per_month - LIQUIDITY_MODERATE_THRESHOLD) / (LIQUIDITY_HIGH_THRESHOLD - LIQUIDITY_MODERATE_THRESHOLD)) * 25
        liquidity_rating = "moderate"
    elif deals_per_month >= LIQUIDITY_LOW_THRESHOLD:
        velocity_score = 25 + ((deals_per_month - LIQUIDITY_LOW_THRESHOLD) / (LIQUIDITY_MODERATE_THRESHOLD - LIQUIDITY_LOW_THRESHOLD)) * 25
        liquidity_rating = "low"
    else:
        velocity_score = deals_per_month * 50
        liquidity_rating = "very_low"

    # Determine trend direction (compare recent quarter to earlier quarters)
    sorted_quarters = sorted(quarterly_deals.keys())
    if len(sorted_quarters) >= 3:
        recent_quarter_avg = quarterly_deals[sorted_quarters[-1]]
        earlier_quarters_avg = sum(quarterly_deals[q] for q in sorted_quarters[:-1]) / (
            len(sorted_quarters) - 1
        )

        if recent_quarter_avg > earlier_quarters_avg * 1.2:
            trend_direction = "improving"
        elif recent_quarter_avg < earlier_quarters_avg * 0.8:
            trend_direction = "declining"
        else:
            trend_direction = "stable"
    else:
        trend_direction = "insufficient_data"

    return LiquidityMetrics(
        liquidity_score=round(velocity_score, 1),
        total_deals=total_deals,
        time_period_months=time_period_months,
        avg_deals_per_month=round(deals_per_month, 2),
        deal_velocity=round(deals_per_month, 2),
        market_activity_level=liquidity_rating,
    )
