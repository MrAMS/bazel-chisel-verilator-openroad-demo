#!/usr/bin/env python3
"""
DSE Configuration data structures

Defines the configuration interface for design-specific DSE parameters.
"""

from typing import Callable, Dict, Any, List
from dataclasses import dataclass


# ============================================================================
# Global Constants for Constraint Violations and Default Values
# ============================================================================

# Severe constraint violation penalty (used when hard constraints fail)
# This is a large positive value indicating the design is infeasible
SEVERE_VIOLATION = 1e9

# Failed build penalty for constraint function
# Use a different value to distinguish failed builds from constraint violations
FAILED_BUILD_PENALTY = 1e6

# Default worst-case values for failed/invalid designs
WORST_AREA = 1e9          # Maximum area value (um^2)
WORST_PERFORMANCE = 0.0   # Minimum performance value
WORST_SLACK = -1e9        # Minimum slack value (ps) - severe timing violation


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

    target: str
    """Bazel target for building and extracting PPA metrics.

    This should be a target that produces PPA metrics (typically *_ppa target).
    Bazel will automatically build all dependencies (e.g., synthesis, CTS stages).

    Example: '//eda/SimdDotProduct:SimdDotProduct_ppa'
    """

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

    get_slack: Callable[[Dict[str, float]], float]
    """Function that extracts timing slack metric.

    This is used for constraint checking in Optuna optimization.

    Args:
        ppa_metrics: PPA metrics from results.tcl

    Returns:
        Slack value in picoseconds:
        - Positive: timing met (has setup margin)
        - Zero: timing exactly met
        - Negative: timing violated
    """

    calc_constraint_violation: Callable[[Dict[str, float]], float]
    """Function that calculates constraint violation for optimization.

    This is the UNIFIED constraint interface for Optuna optimization.
    It combines all design constraints (timing, area, power, etc.) into
    a single continuous metric that provides gradient information.

    Args:
        ppa_metrics: PPA metrics from results.tcl

    Returns:
        Constraint violation value:
        - Negative: constraints satisfied (more negative = more margin)
        - Zero: constraints exactly met (boundary)
        - Positive: constraints violated (more positive = worse violation)

    Convention for Optuna (constraint <= 0 is satisfied):
        - If all constraints pass, return -slack to provide timing margin info
        - If any constraint fails, return positive value indicating severity

    Note: To get a boolean constraint check, simply use:
        meets_constraints = (calc_constraint_violation(ppa_metrics) <= 0)
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
