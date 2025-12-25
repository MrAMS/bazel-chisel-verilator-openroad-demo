#!/usr/bin/env python3
"""
Optuna Optimization Functions

Defines objective functions and constraint functions for Optuna-based DSE.
"""

from typing import Tuple
import optuna

from dse_config import DSEConfig
from bazel_builder import build_design


def objective_function(
    trial: optuna.Trial,
    config: DSEConfig,
    workspace_root: str
) -> Tuple[float, float]:
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
        trial.set_user_attr("area", 1e9)
        trial.set_user_attr("performance", 0.0)
        trial.set_user_attr("meets_constraints", False)
        return (1e9, 1e9)  # Both objectives are minimized

    # Store successful build results
    trial.set_user_attr("area", result["area"])
    trial.set_user_attr("performance", result["performance"])
    trial.set_user_attr("meets_constraints", result["meets_constraints"])

    # Store raw PPA metrics with 'ppa_' prefix
    for key, value in result["ppa_metrics"].items():
        trial.set_user_attr(f"ppa_{key}", value)

    # Return objectives for Optuna
    # Objective 1: Minimize area
    # Objective 2: Maximize performance -> Minimize -performance
    return (result["area"], -result["performance"])


def constraint_function(trial: optuna.Trial) -> Tuple[float]:
    """Constraint function for Optuna optimization.

    Optuna requires constraints to be formulated as: constraint_value <= 0
    A negative value means the constraint is satisfied.

    This function returns -slack to provide continuous gradient information:
    - slack > 0 (timing met with margin): constraint < 0 (satisfied, more negative is better)
    - slack = 0 (timing exactly met): constraint = 0 (boundary)
    - slack < 0 (timing violated): constraint > 0 (violated, more positive is worse)

    By using continuous slack values instead of binary 0/1, we give Optuna's
    sampler information about how far each design is from the constraint boundary,
    enabling better exploration and convergence.

    Args:
        trial: Optuna Trial object

    Returns:
        Tuple containing constraint value based on slack:
        - Negative value: constraint satisfied with margin
        - Zero: constraint exactly met
        - Positive value: constraint violated
    """
    # For failed builds, return large positive value (severe constraint violation)
    failed = trial.user_attrs.get("failed", False)
    if failed:
        return (1e6,)

    # Get slack from PPA metrics (in picoseconds)
    # slack > 0: timing met (has setup margin)
    # slack = 0: timing exactly met
    # slack < 0: timing violated
    slack = trial.user_attrs.get("ppa_slack", -1e9)

    # Return -slack to satisfy Optuna's constraint convention (value <= 0)
    # - slack > 0 -> constraint < 0 (satisfied)
    # - slack < 0 -> constraint > 0 (violated)
    return (-slack,)


def create_study(
    study_name: str = None,
    storage: str = None,
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
            seed=seed,
            constraints_func=constraint_function
        ),
        load_if_exists=True if storage else False,
    )

    return study
