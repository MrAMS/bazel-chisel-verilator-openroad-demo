#!/usr/bin/env python3
"""
Bazel Builder and PPA Parser

Unified builder that handles both single and parallel design builds.
Single-design build is just a special case of parallel build with N=1.
"""

import os
import subprocess
from typing import Any, Dict, List

from .dse_config import (
    SEVERE_VIOLATION,
    WORST_AREA,
    WORST_PERFORMANCE,
    WORST_SLACK,
    DSEConfig,
)

# Performance tracing
TRACE_ON = False


def _create_failure_result(error_type: str) -> Dict[str, Any]:
    """Create standardized failure result dictionary.

    Args:
        error_type: Type of failure (timeout, build_failed, ppa_parse_failed, etc.)

    Returns:
        Dictionary with failure status and worst-case metrics
    """
    return {
        "failed": True,
        "error": error_type,
        "area": WORST_AREA,
        "performance": WORST_PERFORMANCE,
        "slack": WORST_SLACK,
        "constraint_violation": SEVERE_VIOLATION,
        "ppa_metrics": {},
    }


def find_workspace_root() -> str:
    """Find the Bazel workspace root directory.

    Returns BUILD_WORKSPACE_DIRECTORY env var (set by bazelisk run),
    otherwise falls back to current directory.

    Returns:
        Path to workspace root
    """
    return os.environ.get("BUILD_WORKSPACE_DIRECTORY", os.getcwd())


def parse_ppa_metrics(ppa_file: str) -> Dict[str, float]:
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


def build_designs(
    config: DSEConfig,
    params_list: List[Dict[str, Any]],
    workspace_root: str,
    timeout: int = 1200,
    batch_id: int = 0,
) -> List[Dict[str, Any]]:
    """Build one or more design variants.

    This is the unified builder that handles both single and parallel builds.
    For single design: pass params_list with one element
    For parallel builds: pass params_list with multiple elements

    Args:
        config: DSE configuration
        params_list: List of parameter dictionaries (one per design variant)
        workspace_root: Bazel workspace root directory
        timeout: Build timeout in seconds (default: 1200)
        batch_id: Batch identifier for cache busting (default: 0)

    Returns:
        List of result dictionaries, one per design variant.
        Each dictionary contains:
            - failed: bool - Whether build failed
            - error: str - Error type if failed
            - area: float - Area metric
            - performance: float - Performance metric
            - slack: float - Timing slack in picoseconds
            - constraint_violation: float - Unified constraint violation metric
            - ppa_metrics: Dict[str, float] - Raw PPA metrics
    """
    n_designs = len(params_list)

    print(f"\n{'=' * 70}")
    print(f"Building {n_designs} design variant{'s' if n_designs > 1 else ''}")
    print(f"Batch ID: {batch_id}")
    print(f"{'=' * 70}")

    # Print all parameter sets
    for i, params in enumerate(params_list):
        param_str = ", ".join([f"{k}={v}" for k, v in params.items()])
        print(f"Variant {i}: {param_str}")

    # Build environment (common for all variants)
    env = os.environ.copy()

    # Set OpenROAD thread count to avoid thread contention in parallel builds
    # Each OpenROAD instance will use at most (total_cpus / n_designs) threads
    # This prevents the severe performance degradation observed when multiple
    # OpenROAD instances compete for CPU resources
    import os as os_module

    total_cpus = os_module.cpu_count() or 1
    threads_per_instance = max(1, total_cpus // n_designs)

    # IMPORTANT: ORFS openroad.bzl uses ctx.var.get() which reads --define variables
    # Use standard ORFS variable name NUM_CORES
    num_cores_define = f"--define=NUM_CORES={threads_per_instance}"

    print(
        f"Setting NUM_CORES={threads_per_instance} ({n_designs} parallel builds on {total_cpus} CPUs)"
    )
    print(f"Propagating OpenROAD thread cap via {num_cores_define}")

    # Construct Bazel command (unified for single and parallel builds)
    # Use --jobs=auto to maximize CPU utilization across all variants
    cmd = ["bazel", "build", "--keep_going", "--jobs=auto", num_cores_define]

    if TRACE_ON:
        cmd.append(f"--profile=trace-{batch_id}.json.gz")

    # Determine package for parallel targets
    package = config.parallel_target_package

    name_base = config.design_name

    # Check if design provides parallel build options
    if config.get_parallel_bazel_opts is None:
        raise ValueError(
            f"Design {config.design_name} does not support parallel builds. "
            "Please implement get_parallel_bazel_opts() in the DSE config."
        )

    # Build command with per-variant options
    for i, params in enumerate(params_list):
        # Get per-variant options from design-specific function
        # Pass batch_id for cache invalidation via string_flag
        variant_opts = config.get_parallel_bazel_opts(params, i, batch_id)
        cmd.extend(variant_opts)

    # Add all variant targets at the end
    for i in range(n_designs):
        variant_target = f"{package}:{name_base}_{i}_ppa"
        cmd.append(variant_target)

    print(f"\nCommand: {' '.join(cmd)}")

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
        return [_create_failure_result("timeout") for _ in range(n_designs)]

    # Check if any builds succeeded (--keep_going allows partial success)
    if result.returncode != 0:
        print(f"⚠️  Some builds failed (return code {result.returncode})")
        # Print last 1000 chars of stderr for debugging
        if result.stderr:
            print(f"Error output:\n{result.stderr[-1000:]}")

    # Parse results for each variant
    results = []
    for i, params in enumerate(params_list):
        # Construct PPA file path for this variant
        # Extract package path from parallel_target_package (e.g., "//eda/dse/SimdDotProduct" -> "eda/dse/SimdDotProduct")
        package_path = config.parallel_target_package.lstrip("//")
        ppa_file = os.path.join(
            workspace_root,
            f"bazel-bin/{package_path}/{config.design_name}_{i}_ppa.txt",
        )

        # Check if this variant succeeded
        if not os.path.exists(ppa_file):
            print(f"❌ Variant {i} failed (PPA file not found)")
            results.append(_create_failure_result("build_failed"))
            continue

        # Parse PPA metrics
        try:
            ppa_metrics = parse_ppa_metrics(ppa_file)
        except Exception as e:
            print(f"❌ Variant {i} failed to parse PPA metrics: {e}")
            results.append(_create_failure_result("ppa_parse_failed"))
            continue

        # Calculate derived metrics
        try:
            area = config.calc_area(ppa_metrics)
            performance = config.calc_performance(ppa_metrics, params)
            slack = config.get_slack(ppa_metrics)
            constraint_violation = config.calc_constraint_violation(ppa_metrics)
        except Exception as e:
            print(f"❌ Variant {i} failed to calculate metrics: {e}")
            results.append(_create_failure_result("metric_calc_failed"))
            continue

        # Success!
        meets_constraints = constraint_violation <= 0
        constraint_str = "✓" if meets_constraints else "✗"

        print(
            f"\n{constraint_str} Variant {i}: {'MET' if meets_constraints else 'VIOLATED'}"
        )
        print(f"  Area: {area:.3f}")
        print(f"  Performance: {performance:.3f}")
        print(f"  Slack: {slack:.3f} ps")

        results.append(
            {
                "failed": False,
                "area": area,
                "performance": performance,
                "slack": slack,
                "constraint_violation": constraint_violation,
                "ppa_metrics": ppa_metrics,
            }
        )

    return results
