"""
Outlier detection and robust statistical analysis for real estate data.

This module provides functions to detect and filter outliers from deal data,
improving the accuracy of statistical analyses and market assessments.
"""

from typing import Any, Dict, List, Optional, Tuple

from nadlan_mcp.config import GovmapConfig, get_config
from nadlan_mcp.govmap.models import Deal


def calculate_iqr(values: List[float]) -> float:
    """
    Calculate the Interquartile Range (IQR) of a dataset.

    Args:
        values: List of numeric values

    Returns:
        IQR (Q3 - Q1)
    """
    if not values:
        return 0.0

    sorted_values = sorted(values)
    n = len(sorted_values)

    # Calculate Q1 (25th percentile)
    q1_index = n // 4
    q1 = sorted_values[q1_index]

    # Calculate Q3 (75th percentile)
    q3_index = (3 * n) // 4
    q3 = sorted_values[q3_index]

    return q3 - q1


def detect_outliers_iqr(values: List[float], multiplier: float = 1.5) -> List[bool]:
    """
    Detect outliers using the IQR (Interquartile Range) method.

    This is the most robust method for real estate data, as it doesn't assume
    a normal distribution and handles skewed data well.

    Outliers are defined as values outside [Q1 - k*IQR, Q3 + k*IQR] where:
    - k=1.5 (mild outliers, more aggressive filtering)
    - k=3.0 (extreme outliers, conservative filtering)

    Args:
        values: List of numeric values to check
        multiplier: IQR multiplier (default 1.5)

    Returns:
        List of booleans, True if value is an outlier
    """
    if not values or len(values) < 4:
        return [False] * len(values)

    sorted_values = sorted(values)
    n = len(sorted_values)

    # Calculate Q1 and Q3
    q1_index = n // 4
    q1 = sorted_values[q1_index]

    q3_index = (3 * n) // 4
    q3 = sorted_values[q3_index]

    iqr = q3 - q1

    # Calculate bounds
    lower_bound = q1 - (multiplier * iqr)
    upper_bound = q3 + (multiplier * iqr)

    # Mark outliers
    return [value < lower_bound or value > upper_bound for value in values]


def detect_outliers_percent(values: List[float], threshold: float = 0.5) -> List[bool]:
    """
    Detect outliers using percentage-based thresholds from the median.

    Outliers are defined as values outside [median * (1-threshold), median * (1+threshold)]

    Example: threshold=0.5 means values >150% or <50% of median are outliers

    Args:
        values: List of numeric values to check
        threshold: Percentage threshold (0.5 = 50%)

    Returns:
        List of booleans, True if value is an outlier
    """
    if not values:
        return []

    sorted_values = sorted(values)
    n = len(sorted_values)
    median = sorted_values[n // 2]

    lower_bound = median * (1 - threshold)
    upper_bound = median * (1 + threshold)

    return [value < lower_bound or value > upper_bound for value in values]


def apply_hard_bounds_price_per_sqm(
    deals: List[Deal], config: Optional[GovmapConfig] = None
) -> List[bool]:
    """
    Apply hard bounds filtering to price per sqm values.

    This catches obvious data entry errors (e.g., wrong area leading to
    extreme price per sqm values).

    Args:
        deals: List of deals to check
        config: Configuration object (optional, uses global if not provided)

    Returns:
        List of booleans, True if deal should be filtered out
    """
    if config is None:
        config = get_config()

    filters = []
    for deal in deals:
        price_per_sqm = deal.price_per_sqm

        # Skip deals without valid price per sqm
        if price_per_sqm is None:
            filters.append(False)
            continue

        # Check bounds
        is_outlier = (
            price_per_sqm < config.analysis_price_per_sqm_min
            or price_per_sqm > config.analysis_price_per_sqm_max
        )
        filters.append(is_outlier)

    return filters


def apply_hard_bounds_deal_amount(
    deals: List[Deal], config: Optional[GovmapConfig] = None
) -> List[bool]:
    """
    Apply hard bounds filtering to deal amounts.

    This catches partial deals and obvious data errors (e.g., 400K apartment
    when typical apartments are 1.6M).

    Args:
        deals: List of deals to check
        config: Configuration object (optional, uses global if not provided)

    Returns:
        List of booleans, True if deal should be filtered out
    """
    if config is None:
        config = get_config()

    filters = []
    for deal in deals:
        is_outlier = deal.deal_amount < config.analysis_min_deal_amount
        filters.append(is_outlier)

    return filters


def filter_deals_for_analysis(
    deals: List[Deal],
    config: Optional[GovmapConfig] = None,
    metric: str = "price_per_sqm",
    iqr_multiplier: Optional[float] = None,
) -> Tuple[List[Deal], Dict[str, Any]]:
    """
    Filter deals to remove outliers based on configuration.

    This is the main entry point for outlier filtering. It applies a combination
    of hard bounds and statistical outlier detection.

    Process:
    1. Apply hard bounds to price per sqm (catches data errors)
    2. Apply hard bounds to deal amount (catches partial deals)
    3. Apply statistical outlier detection (IQR or percent method) to specified metric
    4. Combine all filters and remove outliers

    Args:
        deals: List of deals to filter
        config: Configuration object (optional, uses global if not provided)
        metric: Which metric to apply statistical outlier detection to
                Options: "price_per_sqm", "deal_amount"
        iqr_multiplier: Override IQR multiplier (optional, uses config value if not provided)

    Returns:
        Tuple of:
        - Filtered list of deals
        - Outlier report dict with details on what was filtered
    """
    if config is None:
        config = get_config()

    if not deals:
        return [], {
            "total_deals": 0,
            "outliers_removed": 0,
            "outlier_indices": [],
            "method_used": config.analysis_outlier_method,
            "parameters": {},
        }

    # Skip outlier detection if disabled or insufficient data
    if (
        config.analysis_outlier_method == "none"
        or len(deals) < config.analysis_min_deals_for_outlier_detection
    ):
        return deals, {
            "total_deals": len(deals),
            "outliers_removed": 0,
            "outlier_indices": [],
            "method_used": "none",
            "parameters": {"reason": "disabled or insufficient data"},
        }

    # Initialize filter masks (True = keep, False = remove)
    filters_to_remove = [False] * len(deals)

    # Step 1: Apply hard bounds to price per sqm
    price_per_sqm_outliers = apply_hard_bounds_price_per_sqm(deals, config)
    for i, is_outlier in enumerate(price_per_sqm_outliers):
        if is_outlier:
            filters_to_remove[i] = True

    # Step 2: Apply hard bounds to deal amount
    deal_amount_outliers = apply_hard_bounds_deal_amount(deals, config)
    for i, is_outlier in enumerate(deal_amount_outliers):
        if is_outlier:
            filters_to_remove[i] = True

    # Step 3: Apply statistical outlier detection to specified metric
    # Use override value if provided, otherwise use config
    effective_iqr_multiplier = (
        iqr_multiplier if iqr_multiplier is not None else config.analysis_iqr_multiplier
    )

    if config.analysis_outlier_method == "iqr":
        # Extract values for the specified metric
        if metric == "price_per_sqm":
            values = [
                deal.price_per_sqm
                for i, deal in enumerate(deals)
                if deal.price_per_sqm is not None and not filters_to_remove[i]
            ]
            value_indices = [
                i
                for i, deal in enumerate(deals)
                if deal.price_per_sqm is not None and not filters_to_remove[i]
            ]
        elif metric == "deal_amount":
            values = [deal.deal_amount for i, deal in enumerate(deals) if not filters_to_remove[i]]
            value_indices = [i for i in range(len(deals)) if not filters_to_remove[i]]
        else:
            values = []
            value_indices = []

        if values:
            statistical_outliers = detect_outliers_iqr(values, effective_iqr_multiplier)
            for i, is_outlier in enumerate(statistical_outliers):
                if is_outlier:
                    filters_to_remove[value_indices[i]] = True

    elif config.analysis_outlier_method == "percent":
        # Extract values for the specified metric
        if metric == "price_per_sqm":
            values = [
                deal.price_per_sqm
                for i, deal in enumerate(deals)
                if deal.price_per_sqm is not None and not filters_to_remove[i]
            ]
            value_indices = [
                i
                for i, deal in enumerate(deals)
                if deal.price_per_sqm is not None and not filters_to_remove[i]
            ]
        elif metric == "deal_amount":
            values = [deal.deal_amount for i, deal in enumerate(deals) if not filters_to_remove[i]]
            value_indices = [i for i in range(len(deals)) if not filters_to_remove[i]]
        else:
            values = []
            value_indices = []

        if values:
            statistical_outliers = detect_outliers_percent(values, 0.5)
            for i, is_outlier in enumerate(statistical_outliers):
                if is_outlier:
                    filters_to_remove[value_indices[i]] = True

    # Step 4: Apply percentage-based backup filtering (catches extreme outliers in heterogeneous data)
    # This runs in addition to IQR when enabled, providing a safety net for wide distributions
    if config.analysis_use_percentage_backup and config.analysis_outlier_method == "iqr":
        # Extract values for the specified metric (same logic as above)
        if metric == "price_per_sqm":
            values = [
                deal.price_per_sqm
                for i, deal in enumerate(deals)
                if deal.price_per_sqm is not None and not filters_to_remove[i]
            ]
            value_indices = [
                i
                for i, deal in enumerate(deals)
                if deal.price_per_sqm is not None and not filters_to_remove[i]
            ]
        elif metric == "deal_amount":
            values = [deal.deal_amount for i, deal in enumerate(deals) if not filters_to_remove[i]]
            value_indices = [i for i in range(len(deals)) if not filters_to_remove[i]]
        else:
            values = []
            value_indices = []

        if values:
            percentage_outliers = detect_outliers_percent(
                values, config.analysis_percentage_threshold
            )
            for i, is_outlier in enumerate(percentage_outliers):
                if is_outlier:
                    filters_to_remove[value_indices[i]] = True

    # Filter deals
    filtered_deals = [deal for i, deal in enumerate(deals) if not filters_to_remove[i]]
    outlier_indices = [i for i, should_remove in enumerate(filters_to_remove) if should_remove]

    # Create outlier report
    report = {
        "total_deals": len(deals),
        "outliers_removed": len(outlier_indices),
        "outlier_indices": outlier_indices,
        "method_used": config.analysis_outlier_method,
        "parameters": {
            "iqr_multiplier": effective_iqr_multiplier
            if config.analysis_outlier_method == "iqr"
            else None,
            "percentage_backup_enabled": config.analysis_use_percentage_backup
            if config.analysis_outlier_method == "iqr"
            else None,
            "percentage_threshold": config.analysis_percentage_threshold
            if config.analysis_use_percentage_backup and config.analysis_outlier_method == "iqr"
            else None,
            "metric": metric,
            "price_per_sqm_min": config.analysis_price_per_sqm_min,
            "price_per_sqm_max": config.analysis_price_per_sqm_max,
            "min_deal_amount": config.analysis_min_deal_amount,
        },
    }

    return filtered_deals, report
