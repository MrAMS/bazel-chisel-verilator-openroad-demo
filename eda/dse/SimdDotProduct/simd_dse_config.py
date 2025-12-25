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

from typing import Any, Dict, List

import optuna

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
N_LANES_CHOICES = [4, 8, 16, 32, 64, 128]  # Explicit choices for faster exploration

# Physical constraint: ABC clock period in picoseconds
# Determines "how hard we push the accelerator"
# Tighter constraints -> larger gates -> more area
# Looser constraints -> smaller gates -> less area
ABC_CLOCK_MIN_PS = 700   # 700 ps = ~1.43 GHz (aggressive)
ABC_CLOCK_MAX_PS = 10000  # 10000 ps = 100 MHz (conservative)

# Fixed design parameters
INPUT_WIDTH = 8  # 8-bit inputs
OUTPUT_WIDTH = 16  # Fixed 16-bit output (may overflow for large n_lanes)


# ============================================================================
# DSE Configuration Functions
# ============================================================================


def suggest_params(trial: optuna.Trial) -> Dict[str, Any]:
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


def get_env_vars(params: Dict[str, Any]) -> Dict[str, str]:
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


def get_bazel_opts(params: Dict[str, Any]) -> List[str]:
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


def calc_performance(ppa_metrics: Dict[str, float], params: Dict[str, Any]) -> float:
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
    n_lanes = params["n_lanes"]

    # GOPS = 2 ops/lane * n_lanes * frequency(GHz)
    gops = 2.0 * n_lanes * f_real_ghz

    return gops


def calc_area(ppa_metrics: Dict[str, float]) -> float:
    """Extract cell area from PPA metrics.

    Args:
        ppa_metrics: PPA metrics from results.tcl

    Returns:
        Cell area in um^2
    """
    return ppa_metrics.get("cell_area", 1e9)


def check_constraints(ppa_metrics: Dict[str, float]) -> bool:
    """Check if design meets constraints.

    All designs must meet timing (slack >= 0). We also reject builds
    with obviously bad synthesis results.

    Args:
        ppa_metrics: PPA metrics from results.tcl

    Returns:
        True if design is valid
    """
    # Reject if area is unreasonably large (likely synthesis error)
    area = ppa_metrics.get("cell_area", 1e9)
    if area >= 1e8:  # 100 mm^2 is unreasonably large for this design
        return False

    # Reject if effective frequency is unreasonably low
    # This indicates severe synthesis problems
    effective_freq = ppa_metrics.get("effective_frequency_ghz", 0.0)
    if effective_freq <= 0.001:  # < 1 MHz is unreasonably low
        return False

    # Reject if power is unreasonably high (likely error)
    power = ppa_metrics.get("estimated_power_uw", 0.0)
    if power >= 1e9:  # > 1W is unreasonable for this design
        return False

    # All designs must meet timing (slack >= 0)
    slack = ppa_metrics.get("slack", -1e9)
    if slack < 0:
        return False

    return True


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
