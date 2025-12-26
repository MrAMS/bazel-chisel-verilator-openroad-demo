#!/usr/bin/env python3
"""
Main DSE script for SimdDotProduct design

This script integrates the generic DSE framework with SimdDotProduct-specific
configuration to explore the architectural design space.

Usage:
    bazel run //eda/dse/SimdDotProduct:run_simd_dse -- [options]
"""

import argparse
import sys

from eda.dse.dse_config import WORST_AREA, DSEConfig
from eda.dse.dse_runner import run_dse
from eda.dse.SimdDotProduct import simd_dse_config


def create_simd_dse_config() -> DSEConfig:
    """Create DSE configuration for SimdDotProduct.

    Returns:
        Configured DSEConfig object
    """
    return DSEConfig(
        # Design identification
        design_name="SimdDotProduct",
        target="//eda/SimdDotProduct:SimdDotProduct_ppa",
        # Parameter space
        suggest_params=simd_dse_config.suggest_params,
        get_env_vars=simd_dse_config.get_env_vars,
        get_bazel_opts=simd_dse_config.get_bazel_opts,
        # Metrics calculation
        calc_performance=simd_dse_config.calc_performance,
        calc_area=simd_dse_config.calc_area,
        get_slack=simd_dse_config.get_slack,
        calc_constraint_violation=simd_dse_config.calc_constraint_violation,
        # Display labels
        performance_label=simd_dse_config.PERFORMANCE_LABEL,
        area_label=simd_dse_config.AREA_LABEL,
        param_labels=simd_dse_config.PARAM_LABELS,
    )


def main():
    """Main entry point for SimdDotProduct DSE."""
    parser = argparse.ArgumentParser(
        description="Design Space Exploration for SimdDotProduct",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Design Space Parameters:
  - n_lanes: {simd_dse_config.N_LANES_MIN} to {simd_dse_config.N_LANES_MAX}
    (choices: {simd_dse_config.N_LANES_CHOICES})
  - abc_clock_ps: {simd_dse_config.ABC_CLOCK_MIN_PS}ps to {simd_dse_config.ABC_CLOCK_MAX_PS}ps
    This controls the clock frequency throughout the entire ORFS flow
    (synthesis, CTS, timing repair)

Optimization Objectives:
  - Maximize: GOPS (Giga Operations Per Second)
  - Minimize: Cell Area (um^2)

Expected Behavior:
  1. Linear scaling region (low n_lanes): Area ∝ GOPS
  2. Knee point (medium n_lanes): Best performance/area ratio
  3. Saturation region (high n_lanes): "Logic depth wall"
     - Combinational logic too deep
     - Effective frequency drops due to WNS
     - GOPS plateaus despite area increase

Output:
  - PDF plots: Area-GOPS Pareto frontier, parameter sweeps
  - HTML dashboard: Interactive Optuna visualizations
  - Text report: Best configurations, all feasible solutions
        """,
    )

    # DSE parameters
    parser.add_argument(
        "--n-trials",
        type=int,
        default=20,
        help="Number of DSE trials to run (default: 20)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="eda/dse/SimdDotProduct/results",
        help="Output directory for results (default: eda/dse/SimdDotProduct/results)",
    )

    # Optuna study persistence
    parser.add_argument(
        "--study-name",
        type=str,
        default="simd_dotproduct_dse",
        help="Optuna study name for resuming (default: simd_dotproduct_dse)",
    )
    parser.add_argument(
        "--storage",
        type=str,
        default=None,
        help="Optuna storage URL (e.g., sqlite:///study.db) for persistence",
    )

    # Quick test mode
    parser.add_argument(
        "--quick-test",
        action="store_true",
        help="Quick test mode: 5 trials with limited parameter space",
    )

    args = parser.parse_args()

    # Quick test mode overrides
    if args.quick_test:
        print("⚡ Quick test mode enabled")
        args.n_trials = 5
        simd_dse_config.ABC_CLOCK_MAX_PS = 5000  # Limit to 5ns = 200 MHz

    # Create configuration
    config = create_simd_dse_config()

    # Print configuration summary
    print("\n" + "=" * 70)
    print("SimdDotProduct Design Space Exploration")
    print("=" * 70)
    print(f"Design: {config.design_name}")
    print(f"Trials: {args.n_trials}")
    print(f"Seed: {args.seed}")
    print(f"Output: {args.output_dir}")
    if args.storage:
        print(f"Storage: {args.storage}")
        print(f"Study: {args.study_name}")
    print("\nParameter Space:")
    print(f"  n_lanes: {simd_dse_config.N_LANES_CHOICES}")
    print(
        f"  abc_clock_ps: {simd_dse_config.ABC_CLOCK_MIN_PS}ps - "
        f"{simd_dse_config.ABC_CLOCK_MAX_PS}ps"
    )
    print("\nObjectives:")
    print(f"  Maximize: {config.performance_label}")
    print(f"  Minimize: {config.area_label}")
    print("=" * 70 + "\n")

    # Run DSE
    try:
        study = run_dse(
            config=config,
            n_trials=args.n_trials,
            seed=args.seed,
            output_dir=args.output_dir,
            study_name=args.study_name,
            storage=args.storage,
        )

        print("\n" + "=" * 70)
        print("DSE Complete!")
        print("=" * 70)

        # Print summary
        if hasattr(study, "best_trials") and study.best_trials:
            print(f"\n✓ Found {len(study.best_trials)} Pareto optimal solutions")
            print("\nBest area solution:")
            best_area_trial = min(
                study.best_trials, key=lambda t: t.user_attrs.get("area", WORST_AREA)
            )
            params = best_area_trial.user_attrs.get("params", {})
            print(f"  n_lanes = {params.get('n_lanes')}")
            print(f"  abc_clock_ps = {params.get('abc_clock_ps')} ps")
            print(f"  Area = {best_area_trial.user_attrs['area']:.3f} um^2")
            print(f"  GOPS = {best_area_trial.user_attrs['performance']:.3f}")

            print("\nBest performance solution:")
            best_perf_trial = max(
                study.best_trials, key=lambda t: t.user_attrs.get("performance", 0)
            )
            params = best_perf_trial.user_attrs.get("params", {})
            print(f"  n_lanes = {params.get('n_lanes')}")
            print(f"  abc_clock_ps = {params.get('abc_clock_ps')} ps")
            print(f"  Area = {best_perf_trial.user_attrs['area']:.3f} um^2")
            print(f"  GOPS = {best_perf_trial.user_attrs['performance']:.3f}")

        print(f"\n✓ Results saved to: {args.output_dir}")
        print(f"  - PDF plots: {config.design_name}_dse_results.pdf")
        print(f"  - HTML dashboard: {config.design_name}_pareto.html")

        return 0

    except Exception as e:
        print(f"\n❌ DSE failed: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
