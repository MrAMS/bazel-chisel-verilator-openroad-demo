#!/usr/bin/env python3
"""
DSE Configuration data structures

Defines the configuration interface for design-specific DSE parameters.
"""

from typing import Callable, Dict, Any, List
from dataclasses import dataclass


@dataclass
class DSEConfig:
    """Configuration for design-specific DSE parameters.

    This class defines the interface between the generic DSE framework
    and design-specific logic. Each design should provide implementations
    for all the callback functions.
    """

    # ========================================================================
    # Design Identification
    # ========================================================================

    design_name: str
    """Name of the design (e.g., 'SimdDotProduct')"""

    bazel_target: str
    """Bazel target for synthesis (e.g., '//eda/SimdDotProduct:SimdDotProduct')"""

    ppa_target: str
    """Bazel target for PPA extraction (e.g., '//eda/SimdDotProduct:SimdDotProduct_ppa')"""

    # ========================================================================
    # Parameter Space Definition
    # ========================================================================

    suggest_params: Callable[[Any], Dict[str, Any]]
    """Function that suggests trial parameters.

    Args:
        trial: Optuna Trial object

    Returns:
        Dictionary of parameter_name -> value
    """

    get_env_vars: Callable[[Dict[str, Any]], Dict[str, str]]
    """Function that converts trial params to environment variables.

    Args:
        params: Trial parameters

    Returns:
        Dictionary of environment_variable -> value
    """

    get_bazel_opts: Callable[[Dict[str, Any]], List[str]]
    """Function that converts trial params to Bazel build options.

    Args:
        params: Trial parameters

    Returns:
        List of Bazel command-line options
    """

    # ========================================================================
    # Metric Calculation
    # ========================================================================

    calc_performance: Callable[[Dict[str, float], Dict[str, Any]], float]
    """Function that calculates performance metric.

    This is the PRIMARY objective to maximize in the DSE.

    Args:
        ppa_metrics: PPA metrics from results.tcl
        params: Trial parameters

    Returns:
        Performance value (higher is better)
    """

    calc_area: Callable[[Dict[str, float]], float]
    """Function that extracts area metric.

    Args:
        ppa_metrics: PPA metrics from results.tcl

    Returns:
        Area value (lower is better)
    """

    check_constraints: Callable[[Dict[str, float]], bool]
    """Function that checks if design meets constraints.

    Args:
        ppa_metrics: PPA metrics from results.tcl

    Returns:
        True if constraints are met, False otherwise
    """

    # ========================================================================
    # Visualization Labels
    # ========================================================================

    performance_label: str
    """Label for performance axis in plots (e.g., 'Performance (TOPS)')"""

    area_label: str
    """Label for area axis in plots (e.g., 'Cell Area (μm²)')"""

    param_labels: Dict[str, str]
    """Display labels for parameters.

    Maps parameter names to human-readable labels for visualization.
    Example: {'n_lanes': 'Number of SIMD Lanes', 'target_clock_ns': 'Clock Period (ns)'}
    """
