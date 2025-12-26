#!/usr/bin/env python3
"""
Bazel Builder and PPA Parser

Handles building designs with Bazel and parsing PPA metrics.
"""

import os
import subprocess

from .dse_config import (
    SEVERE_VIOLATION,
    WORST_AREA,
    WORST_PERFORMANCE,
    WORST_SLACK,
    DSEConfig,
)


def find_workspace_root() -> str:
    """Find the Bazel workspace root directory.

    Returns BUILD_WORKSPACE_DIRECTORY env var (set by bazelisk run),
    otherwise falls back to current directory.

    Returns:
        Path to workspace root
    """
    return os.environ.get("BUILD_WORKSPACE_DIRECTORY", os.getcwd())


def parse_ppa_metrics(ppa_file: str) -> dict[str, float]:
    """Parse PPA metrics from results.tcl output file.

    The PPA file should contain lines in format:
        metric_name: value

    Args:
        ppa_file: Path to PPA metrics file

    Returns:
        Dictionary of metric_name -> value

    Raises:
        FileNotFoundError: If PPA file doesn't exist
        ValueError: If PPA file format is invalid
    """
    metrics = {}

    try:
        with open(ppa_file) as f:
            for line in f:
                line = line.strip()
                if ":" in line and not line.startswith("#"):
                    key, value = line.split(":", 1)
                    try:
                        metrics[key.strip()] = float(value.strip())
                    except ValueError:
                        # Store non-numeric values as strings (metadata)
                        metrics[key.strip()] = value.strip()

    except FileNotFoundError:
        raise FileNotFoundError(f"PPA file not found: {ppa_file}")
    except Exception as e:
        raise ValueError(f"Failed to parse PPA metrics from {ppa_file}: {e}")

    if not metrics:
        raise ValueError(f"No metrics found in PPA file: {ppa_file}")

    return metrics


def build_design(
    config: DSEConfig,
    params: dict[str, str | int | float | bool],
    workspace_root: str,
    timeout: int = 600,
) -> dict[str, str | int | float | bool | dict]:
    """Build design with given parameters and extract PPA metrics.

    This function:
    1. Constructs Bazel build command with design-specific options
    2. Sets environment variables for parameterized constraints
    3. Runs the build
    4. Parses PPA metrics from output
    5. Calculates area and performance metrics
    6. Checks constraints

    Args:
        config: DSE configuration
        params: Trial parameters (from suggest_params)
        workspace_root: Bazel workspace root directory
        timeout: Build timeout in seconds (default: 600)

    Returns:
        Dictionary containing:
            - failed: bool - Whether build failed
            - error: str - Error type if failed
            - area: float - Area metric
            - performance: float - Performance metric
            - slack: float - Timing slack in picoseconds
            - constraint_violation: float - Unified constraint violation metric (<=0 OK, >0 violated)
            - ppa_metrics: Dict[str, float] - Raw PPA metrics
    """
    # Print trial parameters
    param_str = ", ".join([f"{k}={v}" for k, v in params.items()])
    print(f"\n{'=' * 70}")
    print(f"Trial Parameters: {param_str}")
    print(f"{'=' * 70}")

    # Build environment with custom variables
    env = os.environ.copy()
    env_vars = config.get_env_vars(params)
    env.update(env_vars)

    # Build Bazel command-line options
    bazel_opts = config.get_bazel_opts(params)

    # Construct full Bazel command
    # Build the PPA target - Bazel will automatically build all dependencies
    # (e.g., synthesis, CTS stages) as defined in the BUILD file
    cmd = [
        "bazel",
        "build",
        *bazel_opts,
        config.target,
    ]

    print(f"Command: {' '.join(cmd)}")
    if env_vars:
        print(f"Environment: {env_vars}")

    # Run build with timeout
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=workspace_root,
            env=env,
        )
    except subprocess.TimeoutExpired:
        print(f"❌ Build timed out after {timeout}s")
        return {
            "failed": True,
            "error": "timeout",
            "area": WORST_AREA,
            "performance": WORST_PERFORMANCE,
            "slack": WORST_SLACK,
            "constraint_violation": SEVERE_VIOLATION,
            "ppa_metrics": {},
        }

    # Check build status
    if result.returncode != 0:
        print(f"❌ Build failed (return code {result.returncode})")
        # Print last 1000 chars of stderr for debugging
        print(f"Error output:\n{result.stderr[-1000:]}")
        return {
            "failed": True,
            "error": "build_failed",
            "area": WORST_AREA,
            "performance": WORST_PERFORMANCE,
            "slack": WORST_SLACK,
            "constraint_violation": SEVERE_VIOLATION,
            "ppa_metrics": {},
        }

    # Parse PPA metrics
    ppa_file = os.path.join(
        workspace_root,
        f"bazel-bin/eda/{config.design_name}/{config.design_name}_ppa.txt",
    )

    try:
        ppa_metrics = parse_ppa_metrics(ppa_file)
    except Exception as e:
        print(f"❌ Failed to parse PPA metrics: {e}")
        return {
            "failed": True,
            "error": "ppa_parse_failed",
            "area": WORST_AREA,
            "performance": WORST_PERFORMANCE,
            "slack": WORST_SLACK,
            "constraint_violation": SEVERE_VIOLATION,
            "ppa_metrics": {},
        }

    # Calculate derived metrics
    try:
        area = config.calc_area(ppa_metrics)
        performance = config.calc_performance(ppa_metrics, params)
        slack = config.get_slack(ppa_metrics)
        constraint_violation = config.calc_constraint_violation(ppa_metrics)
    except Exception as e:
        print(f"❌ Failed to calculate metrics: {e}")
        return {
            "failed": True,
            "error": "metric_calc_failed",
            "area": WORST_AREA,
            "performance": WORST_PERFORMANCE,
            "slack": WORST_SLACK,
            "constraint_violation": SEVERE_VIOLATION,
            "ppa_metrics": ppa_metrics,
        }

    # Print results summary
    # Derive boolean constraint check from constraint_violation for display
    meets_constraints = constraint_violation <= 0
    constraint_str = "✓" if meets_constraints else "✗"
    print(f"{constraint_str} Constraints: {'MET' if meets_constraints else 'VIOLATED'}")
    print(f"  Area: {area:.3f}")
    print(f"  Performance: {performance:.3f}")
    print(f"  Slack: {slack:.3f} ps")
    print(
        f"  Constraint Violation: {constraint_violation:.3f} ({'OK' if constraint_violation <= 0 else 'VIOLATED'})"
    )

    # Print raw PPA metrics
    print("  Raw PPA metrics:")
    for key, value in ppa_metrics.items():
        if isinstance(value, float):
            print(f"    {key}: {value:.3f}")
        else:
            print(f"    {key}: {value}")

    return {
        "failed": False,
        "area": area,
        "performance": performance,
        "slack": slack,
        "constraint_violation": constraint_violation,
        "ppa_metrics": ppa_metrics,
    }
