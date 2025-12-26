#!/usr/bin/env python3
"""
DSE Runner - Main Entry Point

Provides the main run_dse() function that orchestrates the entire
design space exploration process.
"""

import os

import optuna

from .bazel_builder import find_workspace_root
from .dse_config import SEVERE_VIOLATION, DSEConfig
from .optimization import create_study, objective_function
from .visualization import generate_html_dashboard, generate_visualizations


def print_results_summary(study: optuna.Study, config: DSEConfig):
    """Print summary of DSE results.

    Args:
        study: Completed Optuna study
        config: DSE configuration
    """
    print(f"\n{'=' * 70}\nResults Summary\n{'=' * 70}")

    if hasattr(study, "best_trials") and study.best_trials:
        print(f"\n✓ Found {len(study.best_trials)} Pareto optimal solutions")

        # Show top 5 solutions
        for i, trial in enumerate(study.best_trials[:5]):
            print(f"\nSolution {i + 1}:")
            params = trial.user_attrs.get("params", {})
            for key, value in params.items():
                if isinstance(value, float):
                    print(f"  {key}: {value:.3f}")
                else:
                    print(f"  {key}: {value}")
            print(f"  Area: {trial.user_attrs['area']:.3f}")
            print(f"  Performance: {trial.user_attrs['performance']:.3f}")

            # Show key PPA metrics
            for key, value in trial.user_attrs.items():
                if key.startswith("ppa_") and isinstance(value, (int, float)):
                    metric_name = key.replace("ppa_", "")
                    print(f"  {metric_name}: {value:.3f}")

    else:
        print("\n⚠️  No feasible solutions found!")
        print("\nPossible reasons:")
        print("  - All trials failed to build")
        print("  - All trials violated constraints")
        print("  - Parameter ranges may be too restrictive")
        print("\nSuggestions:")
        print("  - Check build logs for errors")
        print("  - Relax constraints")
        print("  - Adjust parameter ranges")


def save_text_results(study: optuna.Study, config: DSEConfig, output_dir: str):
    """Save results to text file.

    Args:
        study: Completed Optuna study
        config: DSE configuration
        output_dir: Output directory
    """
    results_file = os.path.join(output_dir, f"{config.design_name}_results.txt")

    with open(results_file, "w") as f:
        f.write("=" * 70 + "\n")
        f.write(f"{config.design_name} DSE Results\n")
        f.write("=" * 70 + "\n\n")

        if hasattr(study, "best_trials") and study.best_trials:
            f.write(f"Pareto optimal solutions: {len(study.best_trials)}\n\n")

            for i, trial in enumerate(study.best_trials):
                f.write(f"Solution {i + 1}:\n")
                params = trial.user_attrs.get("params", {})
                for key, value in params.items():
                    f.write(f"  {key} = {value}\n")
                f.write(f"  Area = {trial.user_attrs['area']:.3f}\n")
                f.write(f"  Performance = {trial.user_attrs['performance']:.3f}\n")
                f.write("\n")

        f.write("\n" + "=" * 70 + "\n")
        f.write("All Completed Trials:\n")
        f.write("=" * 70 + "\n")

        for trial in study.trials:
            if trial.state == optuna.trial.TrialState.COMPLETE:
                failed = trial.user_attrs.get("failed", False)
                constraint_violation = trial.user_attrs.get(
                    "constraint_violation", SEVERE_VIOLATION
                )
                meets_constraints = constraint_violation <= 0

                if not failed and meets_constraints:
                    params = trial.user_attrs.get("params", {})
                    param_str = ", ".join([f"{k}={v}" for k, v in params.items()])

                    f.write(
                        f"Trial {trial.number}: "
                        f"{param_str}, "
                        f"Area={trial.user_attrs['area']:.3f}, "
                        f"Perf={trial.user_attrs['performance']:.3f}\n"
                    )

    print(f"✓ Text results saved to {os.path.abspath(results_file)}")


def run_dse(
    config: DSEConfig,
    n_trials: int,
    seed: int,
    output_dir: str,
    study_name: str,
    storage: str | None,
) -> optuna.Study:
    """Run complete design space exploration.

    This is the main entry point for running DSE. It:
    1. Creates output directory
    2. Sets up Optuna study
    3. Runs optimization trials
    4. Generates visualizations
    5. Saves results

    Args:
        config: DSE configuration (design-specific)
        n_trials: Number of trials to run
        seed: Random seed for reproducibility
        output_dir: Output directory for results
        study_name: Optuna study name (for resuming)
        storage: Optuna storage URL for persistence (e.g., 'sqlite:///study.db')

    Returns:
        Completed Optuna Study object

    Example:
        >>> config = create_my_dse_config()
        >>> study = run_dse(
        ...     config=config,
        ...     n_trials=50,
        ...     output_dir="results/my_design"
        ... )
    """
    # Get workspace root
    workspace_root = find_workspace_root()

    # Create output directory
    if not os.path.isabs(output_dir):
        output_dir = os.path.join(workspace_root, output_dir)
    os.makedirs(output_dir, exist_ok=True)

    # Print configuration
    print("=" * 70)
    print(f"Design Space Exploration: {config.design_name}")
    print("=" * 70)
    print(f"Workspace root: {workspace_root}")
    print(f"Trials: {n_trials}")
    print(f"Seed: {seed}")
    print(f"Output directory: {output_dir}")
    if storage:
        print(f"Storage: {storage}")
        print(f"Study name: {study_name}")
    print("=" * 70)

    # Create Optuna study
    study = create_study(
        study_name=study_name,
        storage=storage,
        seed=seed,
    )

    # Run optimization
    print("\nStarting optimization...")
    study.optimize(
        lambda trial: objective_function(trial, config, workspace_root),
        n_trials=n_trials,
        show_progress_bar=True,
    )

    # Print results summary
    print_results_summary(study, config)

    # Generate visualizations
    print("\nGenerating visualizations...")

    plot_file = os.path.join(output_dir, f"{config.design_name}_dse_results.pdf")
    generate_visualizations(study, config, plot_file)

    generate_html_dashboard(study, config, output_dir)

    # Save text results
    save_text_results(study, config, output_dir)

    print(f"\n{'=' * 70}")
    print("DSE Complete!")
    print(f"{'=' * 70}")
    print(f"Results directory: {output_dir}")

    return study
