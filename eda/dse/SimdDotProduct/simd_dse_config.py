#!/usr/bin/env python3
"""
SimdDotProduct-specific DSE configuration

Defines the design space exploration parameters and metrics for the
SIMD Dot Product design, including:
- Architectural parameters: n_lanes (parallelism)
- Physical constraints: target_clock
- Performance metric: TOPS (Tera Operations Per Second)
- Effective frequency calculation based on WNS
"""

import optuna

from ..dse_config import SEVERE_VIOLATION, WORST_AREA, WORST_SLACK

# ============================================================================
# DSE Parameter Ranges
# ============================================================================

# Architectural parameter: number of SIMD lanes
# Determines "how wide the road is"
# Expected behavior:
#   - Low values (4-16): Linear scaling region
#   - Medium values (32-64): Knee point / sweet spot
#   - High values (128+): Saturation region (logic depth wall)
N_LANES_MIN = 4
N_LANES_MAX = 128
N_LANES_CHOICES = [
    4,
    8,
    12,
    16,
    20,
    24,
    28,
    32,
]  # Explicit choices for faster exploration

# Physical constraint: ABC clock period in picoseconds
# Determines "how hard we push the accelerator"
# Tighter constraints -> larger gates -> more area
# Looser constraints -> smaller gates -> less area
ABC_CLOCK_MIN_PS = 350  # 350 ps = ~2.86 GHz (aggressive)
ABC_CLOCK_MAX_PS = 1250  # 1250 ps = 800 MHz (conservative)

# Fixed design parameters
INPUT_WIDTH = 8  # 8-bit inputs
OUTPUT_WIDTH = 32  # 32-bit output (accumulator width)


# ============================================================================
# DSE Configuration Functions
# ============================================================================


def suggest_params(trial: optuna.Trial) -> dict[str, str | int | float | bool]:
    """Suggest trial parameters for SimdDotProduct DSE.

    Args:
        trial: Optuna trial object

    Returns:
        Dictionary of parameter_name -> value
    """
    # Suggest n_lanes from predefined choices
    n_lanes = trial.suggest_categorical("n_lanes", N_LANES_CHOICES)

    # Suggest ABC clock period in picoseconds
    abc_clock_ps = trial.suggest_int(
        "abc_clock_ps",
        ABC_CLOCK_MIN_PS,
        ABC_CLOCK_MAX_PS,
        log=True,  # Use log scale for clock period
    )

    return {
        "n_lanes": n_lanes,
        "abc_clock_ps": abc_clock_ps,
        "input_width": INPUT_WIDTH,
        "output_width": OUTPUT_WIDTH,
    }


def get_env_vars(params: dict[str, str | int | float | bool]) -> dict[str, str]:
    """Generate environment variables for Bazel build.

    Note: For OpenROAD flow, we use --define instead of environment variables
    to override parameters. This function is kept for compatibility but returns
    empty dict.

    Args:
        params: Trial parameters

    Returns:
        Dictionary of environment_variable -> value (empty for now)
    """
    return {}


def get_bazel_opts(params: dict[str, str | int | float | bool]) -> list[str]:
    """Generate Bazel build options.

    Args:
        params: Trial parameters

    Returns:
        List of Bazel command-line options
    """
    # Construct chisel_app_opts for RTL generation
    chisel_opts = (
        f"--nLanes={params['n_lanes']} "
        f"--inputWidth={params['input_width']} "
        f"--outputWidth={params['output_width']}"
    )

    return [
        f"--//rules:chisel_app_opts={chisel_opts}",
        f"--define=ABC_CLOCK_PERIOD_IN_PS={params['abc_clock_ps']}",
    ]


def get_parallel_bazel_opts(
    params: dict[str, str | int | float | bool],
    variant_index: int,
    package: str,
    batch_id: int = 0,
) -> list[str]:
    """Generate Bazel build options for parallel builds.

    This function converts global options to per-variant options for parallel builds.
    Each variant gets its own set of string_flag values.

    The parallel build targets and string_flags are located in //eda/dse/SimdDotProduct,
    so we always use that package regardless of the base target location.

    Args:
        params: Trial parameters
        variant_index: Index of the variant (0, 1, 2, ...)
        package: Bazel package name (ignored - always uses //eda/dse/SimdDotProduct)
        batch_id: Batch identifier for cache invalidation (default: 0)

    Returns:
        List of Bazel command-line options for this specific variant
    """
    # Construct chisel_app_opts for RTL generation
    chisel_opts = (
        f"--nLanes={params['n_lanes']} "
        f"--inputWidth={params['input_width']} "
        f"--outputWidth={params['output_width']}"
    )

    # Always use DSE package location for parallel builds
    dse_package = "//eda/dse/SimdDotProduct"

    return [
        f"--{dse_package}:chisel_opts_{variant_index}={chisel_opts}",
        f"--{dse_package}:abc_clock_ps_{variant_index}={params['abc_clock_ps']}",
        f"--{dse_package}:batch_id_{variant_index}={batch_id}",
    ]


def calc_performance(
    ppa_metrics: dict[str, float], params: dict[str, str | int | float | bool]
) -> float:
    """Calculate GOPS (Giga Operations Per Second) performance.

    Performance calculation:
        GOPS = 2 * n_lanes * F_real

    Where:
        - 2: Each dot product lane performs 1 multiply + 1 add = 2 ops
        - n_lanes: Number of parallel lanes
        - F_real: Effective frequency in GHz (accounting for WNS)

    F_real calculation:
        - If WNS >= 0: F_real = target_frequency
        - If WNS < 0: F_real = 1 / (T_target + |WNS|)

    This accounts for the "logic depth wall" - as n_lanes increases,
    combinational logic depth increases, WNS becomes negative, and
    F_real drops, limiting GOPS growth.

    Args:
        ppa_metrics: PPA metrics from results.tcl
        params: Trial parameters including n_lanes

    Returns:
        Performance in GOPS
    """
    f_real_ghz = ppa_metrics.get("effective_frequency_ghz", 0.0)
    n_lanes = float(params["n_lanes"])

    # GOPS = 2 ops/lane * n_lanes * frequency(GHz)
    gops = 2.0 * n_lanes * f_real_ghz

    return gops


def calc_area(ppa_metrics: dict[str, float]) -> float:
    """Extract cell area from PPA metrics.

    Args:
        ppa_metrics: PPA metrics from results.tcl

    Returns:
        Cell area in um^2
    """
    return ppa_metrics.get("cell_area", WORST_AREA)


def get_slack(ppa_metrics: dict[str, float]) -> float:
    """Extract timing slack from PPA metrics.

    Args:
        ppa_metrics: PPA metrics from results.tcl

    Returns:
        Slack value in picoseconds:
        - Positive: timing met (has setup margin)
        - Zero: timing exactly met
        - Negative: timing violated
    """
    return ppa_metrics.get("slack", WORST_SLACK)


def calc_constraint_violation(ppa_metrics: dict[str, float]) -> float:
    """Calculate unified constraint violation for Optuna optimization.

    This function combines all design constraints into a single continuous
    metric. It checks hard constraints (area, frequency, power) first, then
    returns timing slack for gradient information.

    Constraint checks:
        1. Area < 100 mm² (hard constraint)
        2. Effective frequency > 1 MHz (hard constraint)
        3. Power < 1W (hard constraint)
        4. Timing slack >= 0 (soft constraint with gradient)

    Args:
        ppa_metrics: PPA metrics from results.tcl

    Returns:
        Constraint violation value:
        - Negative: all constraints satisfied (value = -slack, more negative = more margin)
        - Zero: timing exactly met, other constraints satisfied
        - Positive: one or more constraints violated
            - Large positive (SEVERE_VIOLATION): hard constraint (area/freq/power) violated
            - Small positive: only timing violated (value = -slack)
    """
    # Check hard constraints first
    # If any hard constraint fails, return large positive value

    # 1. Area constraint
    area = calc_area(ppa_metrics)
    if area >= 1e8:  # 100 mm^2 is unreasonably large
        return SEVERE_VIOLATION  # Severe violation

    # 2. Frequency constraint
    effective_freq = ppa_metrics.get("effective_frequency_ghz", 0.0)
    if effective_freq <= 0.001:  # < 1 MHz is unreasonably low
        return SEVERE_VIOLATION  # Severe violation

    # 3. Power constraint
    power = ppa_metrics.get("estimated_power_uw", 0.0)
    if power >= 1e9:  # > 1W is unreasonable
        return SEVERE_VIOLATION  # Severe violation

    # All hard constraints passed
    # Return -slack for continuous gradient information:
    # - If slack > 0 (timing met): returns negative value (satisfied)
    # - If slack = 0 (timing boundary): returns 0
    # - If slack < 0 (timing violated): returns positive value (violated)
    slack = get_slack(ppa_metrics)
    return -slack


# ============================================================================
# Display Labels for Visualization
# ============================================================================

PARAM_LABELS = {
    "n_lanes": "Number of SIMD Lanes",
    "abc_clock_ps": "ABC Clock Period (ps)",
    "input_width": "Input Width (bits)",
    "output_width": "Output Width (bits)",
}

PERFORMANCE_LABEL = "Performance (GOPS)"
AREA_LABEL = "Cell Area (μm²)"
