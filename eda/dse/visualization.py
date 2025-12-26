#!/usr/bin/env python3
"""
Visualization and Plotting Functions

Generates comprehensive visualizations for DSE results including:
- Area vs Performance Pareto frontier
- Parameter sweep plots
- Optimization history
- HTML interactive dashboards
"""

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import optuna
from matplotlib.backends.backend_pdf import PdfPages

from .dse_config import SEVERE_VIOLATION, WORST_AREA, WORST_PERFORMANCE, DSEConfig


def collect_trial_data(study: optuna.Study) -> tuple:
    """Collect and categorize trial data from completed study.

    Args:
        study: Completed Optuna study

    Returns:
        Tuple of (feasible_trials, infeasible_trials, failed_trials)
    """
    feasible_trials = []
    infeasible_trials = []
    failed_trials = []

    for trial in study.trials:
        if trial.state != optuna.trial.TrialState.COMPLETE:
            continue

        trial_data = {
            "number": trial.number,
            "params": trial.user_attrs.get("params", {}),
            "area": trial.user_attrs.get("area", WORST_AREA),
            "performance": trial.user_attrs.get("performance", WORST_PERFORMANCE),
            "failed": trial.user_attrs.get("failed", False),
            "constraint_violation": trial.user_attrs.get(
                "constraint_violation", SEVERE_VIOLATION
            ),
        }

        # Copy PPA metrics
        for key, value in trial.user_attrs.items():
            if key.startswith("ppa_"):
                trial_data[key] = value

        # Categorize trials based on constraint_violation
        if trial_data["failed"]:
            failed_trials.append(trial_data)
        elif trial_data["constraint_violation"] <= 0:
            feasible_trials.append(trial_data)
        else:
            infeasible_trials.append(trial_data)

    return feasible_trials, infeasible_trials, failed_trials


def setup_plot_style():
    """Configure matplotlib plot style for publication quality."""
    plt.rcParams.update(
        {
            "font.size": 11,
            "axes.labelsize": 13,
            "axes.titlesize": 14,
            "legend.fontsize": 11,
            "figure.dpi": 150,
            "savefig.dpi": 300,
            "axes.grid": True,
            "grid.alpha": 0.3,
            "grid.linestyle": "--",
        }
    )


def plot_area_vs_performance(
    pdf: PdfPages,
    study: optuna.Study,
    feasible: list[dict],
    infeasible: list[dict],
    failed: list[dict],
    config: DSEConfig,
):
    """Plot Area vs Performance Pareto frontier.

    This is the primary plot showing the trade-off between area and performance.

    Args:
        pdf: PDF pages object for output
        study: Optuna study
        feasible: List of feasible trial data
        infeasible: List of infeasible trial data
        failed: List of failed trial data
        config: DSE configuration
    """
    fig, ax = plt.subplots(figsize=(11, 8))

    # Plot all feasible points
    if feasible:
        areas = [t["area"] for t in feasible]
        perfs = [t["performance"] for t in feasible]

        ax.scatter(
            areas,
            perfs,
            c="lightblue",
            s=200,
            alpha=0.6,
            edgecolors="gray",
            linewidth=1,
            label=f"Feasible ({len(feasible)})",
            marker="o",
            zorder=2,
        )

        # Get and plot Pareto front
        pareto_trials = study.best_trials if hasattr(study, "best_trials") else []
        if pareto_trials:
            pareto_areas = [t.user_attrs.get("area", 0) for t in pareto_trials]
            pareto_perfs = [t.user_attrs.get("performance", 0) for t in pareto_trials]

            ax.scatter(
                pareto_areas,
                pareto_perfs,
                c="red",
                s=400,
                alpha=0.95,
                edgecolors="black",
                linewidth=2.5,
                label=f"Pareto Optimal ({len(pareto_trials)})",
                marker="*",
                zorder=10,
            )

            # Draw Pareto curve
            sorted_idx = np.argsort(pareto_areas)
            sorted_areas = [pareto_areas[i] for i in sorted_idx]
            sorted_perfs = [pareto_perfs[i] for i in sorted_idx]
            ax.plot(
                sorted_areas,
                sorted_perfs,
                "r--",
                linewidth=2.5,
                alpha=0.7,
                label="Pareto Front",
                zorder=8,
            )

            # Annotate Pareto points
            for i, (a, p) in enumerate(zip(pareto_areas, pareto_perfs)):
                ax.annotate(
                    f"{i + 1}",
                    xy=(a, p),
                    xytext=(5, 5),
                    textcoords="offset points",
                    fontsize=9,
                    fontweight="bold",
                    color="white",
                    bbox=dict(boxstyle="circle,pad=0.3", fc="red", ec="black", lw=1.5),
                )

    # Plot infeasible points
    if infeasible:
        ax.scatter(
            [t["area"] for t in infeasible],
            [t["performance"] for t in infeasible],
            c="red",
            s=150,
            alpha=0.5,
            linewidth=2,
            label=f"Constraint Violated ({len(infeasible)})",
            marker="x",
            zorder=1,
        )

    # Plot failed builds
    if failed:
        # Place failed builds at origin or corner
        ax.scatter(
            [0] * len(failed),
            [0] * len(failed),
            c="red",
            s=300,
            alpha=0.8,
            edgecolors="darkred",
            linewidth=2,
            label=f"Build Failed ({len(failed)})",
            marker="X",
            zorder=10,
        )

    ax.set_xlabel(config.area_label, fontweight="bold")
    ax.set_ylabel(config.performance_label, fontweight="bold")
    ax.set_title(
        f"{config.design_name}: Area-Performance Pareto Frontier\n(Upper-left is better)",
        fontweight="bold",
        pad=15,
    )
    ax.legend(loc="best", framealpha=0.9)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    pdf.savefig(fig, bbox_inches="tight")
    plt.close()


def plot_parameter_sweeps(
    pdf: PdfPages, feasible: list[dict], infeasible: list[dict], config: DSEConfig
):
    """Plot parameter sweep plots for each design parameter.

    For each parameter, creates two subplots:
    - Parameter vs Area (colored by Performance)
    - Parameter vs Performance (colored by Area)

    Args:
        pdf: PDF pages object for output
        feasible: List of feasible trial data
        infeasible: List of infeasible trial data
        config: DSE configuration
    """
    if not feasible:
        return

    # Get parameter names from first trial
    param_names = list(feasible[0]["params"].keys())

    for param_name in param_names:
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

        param_values = [t["params"][param_name] for t in feasible]
        areas = [t["area"] for t in feasible]
        perfs = [t["performance"] for t in feasible]

        # Param vs Area (colored by Performance)
        scatter1 = ax1.scatter(
            param_values,
            areas,
            c=perfs,
            cmap="plasma",
            s=200,
            alpha=0.7,
            edgecolors="black",
            linewidth=1.5,
        )
        ax1.set_xlabel(
            config.param_labels.get(param_name, param_name), fontweight="bold"
        )
        ax1.set_ylabel(config.area_label, fontweight="bold")
        ax1.set_title(f"{param_name} vs Area (Color = Performance)")
        ax1.grid(True, alpha=0.3)
        plt.colorbar(scatter1, ax=ax1, label=config.performance_label)

        # Param vs Performance (colored by Area)
        scatter2 = ax2.scatter(
            param_values,
            perfs,
            c=areas,
            cmap="viridis",
            s=200,
            alpha=0.7,
            edgecolors="black",
            linewidth=1.5,
        )
        ax2.set_xlabel(
            config.param_labels.get(param_name, param_name), fontweight="bold"
        )
        ax2.set_ylabel(config.performance_label, fontweight="bold")
        ax2.set_title(f"{param_name} vs Performance (Color = Area)")
        ax2.grid(True, alpha=0.3)
        plt.colorbar(scatter2, ax=ax2, label=config.area_label)

        plt.tight_layout()
        pdf.savefig(fig, bbox_inches="tight")
        plt.close()


def plot_optimization_history(pdf: PdfPages, feasible: list[dict], config: DSEConfig):
    """Plot optimization history showing convergence over trials.

    Creates two subplots:
    - Area optimization history with best-so-far curve
    - Performance optimization history with best-so-far curve

    Args:
        pdf: PDF pages object for output
        feasible: List of feasible trial data
        config: DSE configuration
    """
    if not feasible:
        return

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 10))

    trial_numbers = [t["number"] for t in feasible]
    areas = [t["area"] for t in feasible]
    perfs = [t["performance"] for t in feasible]

    # Area history
    ax1.scatter(trial_numbers, areas, c="blue", s=150, alpha=0.6, label="Trial")

    # Best area so far
    best_area = []
    current_best = float("inf")
    for area in areas:
        current_best = min(current_best, area)
        best_area.append(current_best)
    ax1.plot(trial_numbers, best_area, "r-", linewidth=2.5, label="Best So Far")

    ax1.set_xlabel("Trial Number", fontweight="bold")
    ax1.set_ylabel(config.area_label, fontweight="bold")
    ax1.set_title("Area Minimization History")
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # Performance history
    ax2.scatter(trial_numbers, perfs, c="green", s=150, alpha=0.6, label="Trial")

    # Best performance so far
    best_perf = []
    current_best = 0.0
    for perf in perfs:
        current_best = max(current_best, perf)
        best_perf.append(current_best)
    ax2.plot(trial_numbers, best_perf, "r-", linewidth=2.5, label="Best So Far")

    ax2.set_xlabel("Trial Number", fontweight="bold")
    ax2.set_ylabel(config.performance_label, fontweight="bold")
    ax2.set_title("Performance Maximization History")
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    pdf.savefig(fig, bbox_inches="tight")
    plt.close()


def generate_visualizations(study: optuna.Study, config: DSEConfig, output_file: str):
    """Generate comprehensive visualization plots for DSE results.

    Creates a PDF file containing:
    - Area vs Performance Pareto frontier
    - Parameter sweep plots for each parameter
    - Optimization history plots

    Args:
        study: Completed Optuna study
        config: DSE configuration
        output_file: Output PDF file path
    """
    # Collect trial data
    feasible, infeasible, failed = collect_trial_data(study)

    if not feasible:
        print("⚠ No feasible trials to plot")
        return

    # Setup plot style
    setup_plot_style()

    # Generate all plots
    with PdfPages(output_file) as pdf:
        # Plot 1: Area vs Performance Pareto Frontier (PRIMARY PLOT)
        plot_area_vs_performance(pdf, study, feasible, infeasible, failed, config)

        # Plot 2-N: Parameter sweep plots
        plot_parameter_sweeps(pdf, feasible, infeasible, config)

        # Plot: Optimization history
        plot_optimization_history(pdf, feasible, config)

    print(f"✓ Plots saved to {os.path.abspath(output_file)}")


def generate_html_dashboard(study: optuna.Study, config: DSEConfig, output_dir: str):
    """Generate interactive HTML dashboards using Optuna's visualization tools.

    Creates:
    - Pareto front plot (HTML) - for multi-objective optimization
    - Parameter importance plot (HTML, if applicable)

    Args:
        study: Completed Optuna study
        config: DSE configuration
        output_dir: Output directory for HTML files
    """
    try:
        # Pareto front (multi-objective)
        optuna.visualization.plot_pareto_front(
            study, target_names=["Area (μm²)", "Performance (GOPS)"]
        ).write_html(os.path.join(output_dir, f"{config.design_name}_pareto.html"))

        # Parameter importances (only if enough trials)
        if len(study.trials) >= 10:
            try:
                # For multi-objective, plot importance for each target
                optuna.visualization.plot_param_importances(
                    study,
                    target=lambda t: t.values[0],  # Area
                    target_name="Area (μm²)",
                ).write_html(
                    os.path.join(
                        output_dir, f"{config.design_name}_area_importance.html"
                    )
                )

                optuna.visualization.plot_param_importances(
                    study,
                    target=lambda t: t.values[1],  # Performance
                    target_name="Performance (GOPS)",
                ).write_html(
                    os.path.join(
                        output_dir, f"{config.design_name}_perf_importance.html"
                    )
                )
            except Exception as e:
                print(f"⚠ Failed to generate parameter importance plots: {e}")
        else:
            print(
                f"⚠ Skipping parameter importance plots (need >= 10 trials, got {len(study.trials)})"
            )

        print(f"✓ HTML dashboards saved to {output_dir}")

    except Exception as e:
        print(f"⚠ Failed to generate HTML visualizations: {e}")
