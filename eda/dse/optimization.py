#!/usr/bin/env python3
"""
Optuna Optimization Functions

Defines objective functions and constraint functions for Optuna-based DSE.
"""

import optuna

from .bazel_builder import build_design
from .dse_config import (
    FAILED_BUILD_PENALTY,
    SEVERE_VIOLATION,
    WORST_AREA,
    WORST_PERFORMANCE,
    WORST_SLACK,
    DSEConfig,
)


def objective_function(
    trial: optuna.Trial, config: DSEConfig, workspace_root: str
) -> tuple[float, float]:
    """Optuna objective function for multi-objective optimization.

    This function is called by Optuna for each trial to evaluate the design.

    Optimization objectives:
        1. Minimize area
        2. Maximize performance (converted to minimize -performance)

    The function:
    1. Suggests parameters using design-specific suggest_params
    2. Builds the design and extracts PPA metrics
    3. Stores results in trial user_attrs for later analysis
    4. Returns objectives for Optuna to optimize

    Args:
        trial: Optuna Trial object
        config: DSE configuration
        workspace_root: Bazel workspace root directory

    Returns:
        Tuple of (area, -performance) for minimization
        Both values are to be minimized by Optuna
    """
    # Suggest parameters using design-specific function
    params = config.suggest_params(trial)

    # Build design and evaluate
    result = build_design(config, params, workspace_root)

    # Store all results in trial attributes for later analysis
    trial.set_user_attr("failed", result["failed"])
    trial.set_user_attr("params", params)

    # Handle build failures
    if result["failed"]:
        # Return worst-case values to discourage failed builds
        trial.set_user_attr("area", WORST_AREA)
        trial.set_user_attr("performance", WORST_PERFORMANCE)
        trial.set_user_attr("slack", WORST_SLACK)
        trial.set_user_attr("constraint_violation", SEVERE_VIOLATION)
        return (WORST_AREA, -WORST_PERFORMANCE)  # Both objectives are minimized

    # Store successful build results
    trial.set_user_attr("area", result["area"])
    trial.set_user_attr("performance", result["performance"])
    trial.set_user_attr("slack", result["slack"])
    trial.set_user_attr("constraint_violation", result["constraint_violation"])

    assert isinstance(result["ppa_metrics"], dict)  # make pyright happy

    # Store raw PPA metrics with 'ppa_' prefix
    for key, value in result["ppa_metrics"].items():
        trial.set_user_attr(f"ppa_{key}", value)

    assert not isinstance(result["area"], dict)  # make pyright happy
    assert not isinstance(result["performance"], dict)  # make pyright happy
    # Return objectives for Optuna
    # Objective 1: Minimize area
    # Objective 2: Maximize performance -> Minimize -performance
    return (float(result["area"]), -float(result["performance"]))


def constraint_function(trial: optuna.trial.FrozenTrial) -> tuple[float]:
    """Constraint function for Optuna optimization.

    Optuna requires constraints to be formulated as: constraint_value <= 0
    A negative value means the constraint is satisfied.

    This function returns the unified constraint violation calculated by
    config.calc_constraint_violation(), which combines all design constraints
    (timing, area, power, etc.) into a single continuous metric:

    - constraint_violation <= 0: all constraints satisfied
      - More negative = more timing margin (slack)
    - constraint_violation > 0: one or more constraints violated
      - Small positive: timing violated (= -slack where slack < 0)
      - Large positive (SEVERE_VIOLATION): hard constraint violated (area/freq/power)

    By using the continuous constraint_violation value instead of binary 0/1,
    we give Optuna's sampler gradient information about how far each design is
    from the constraint boundary, enabling better exploration and convergence.

    Args:
        trial: Optuna Trial object

    Returns:
        Tuple containing constraint violation value:
        - Negative: constraints satisfied with margin
        - Zero: constraints exactly met
        - Positive: constraints violated
    """
    # For failed builds, return large positive value (severe constraint violation)
    failed = trial.user_attrs.get("failed", False)
    if failed:
        return (FAILED_BUILD_PENALTY,)

    # Get the unified constraint violation from design-specific implementation
    # This is calculated by config.calc_constraint_violation(ppa_metrics)
    # and stored directly by the objective function
    constraint_violation = trial.user_attrs.get(
        "constraint_violation", SEVERE_VIOLATION
    )

    return (constraint_violation,)


def create_study(
    study_name: str,
    storage: str | None,
    seed: int = 42,
) -> optuna.Study:
    """Create Optuna study for multi-objective optimization.

    Args:
        study_name: Name for the study (for resuming)
        storage: Storage URL for persistence (e.g., 'sqlite:///study.db')
        seed: Random seed for reproducibility

    Returns:
        Configured Optuna Study object
    """
    study = optuna.create_study(
        study_name=study_name,
        storage=storage,
        directions=["minimize", "minimize"],  # Minimize area and -performance
        sampler=optuna.samplers.TPESampler(
            seed=seed, constraints_func=constraint_function
        ),
        load_if_exists=True if storage else False,
    )

    return study
