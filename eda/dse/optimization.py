#!/usr/bin/env python3
"""
Optuna Optimization Functions

Defines objective functions and constraint functions for Optuna-based DSE.
Supports both sequential and parallel execution modes.
"""

from typing import List
import optuna

from .bazel_builder import build_designs
from .dse_config import (
    FAILED_BUILD_PENALTY,
    SEVERE_VIOLATION,
    WORST_AREA,
    WORST_PERFORMANCE,
    WORST_SLACK,
    DSEConfig,
)


def _store_trial_results(
    trial: optuna.Trial, params: dict, result: dict
) -> tuple[float, float]:
    """Store build results in trial user attributes and return objectives.

    Args:
        trial: Optuna Trial object
        params: Trial parameters
        result: Build result dictionary from build_design(s)

    Returns:
        Tuple of (area, -performance) objectives for minimization
    """
    trial.set_user_attr("failed", result["failed"])
    trial.set_user_attr("params", params)

    if result["failed"]:
        trial.set_user_attr("area", WORST_AREA)
        trial.set_user_attr("performance", WORST_PERFORMANCE)
        trial.set_user_attr("slack", WORST_SLACK)
        trial.set_user_attr("constraint_violation", SEVERE_VIOLATION)
        return (WORST_AREA, -WORST_PERFORMANCE)

    # Store successful build results
    trial.set_user_attr("area", result["area"])
    trial.set_user_attr("performance", result["performance"])
    trial.set_user_attr("slack", result["slack"])
    trial.set_user_attr("constraint_violation", result["constraint_violation"])

    # Store raw PPA metrics with 'ppa_' prefix
    assert isinstance(result["ppa_metrics"], dict)  # make pyright happy
    for key, value in result["ppa_metrics"].items():
        trial.set_user_attr(f"ppa_{key}", value)

    # Return objectives: minimize area, minimize -performance (i.e., maximize performance)
    assert not isinstance(result["area"], dict)  # make pyright happy
    assert not isinstance(result["performance"], dict)  # make pyright happy
    return (float(result["area"]), -float(result["performance"]))


def objective_function_parallel(
    study: optuna.Study,
    trials: List[optuna.Trial],
    config: DSEConfig,
    workspace_root: str,
    batch_id: int = 0,
) -> None:
    """Optuna objective function for multi-objective optimization.

    Builds and evaluates one or more trials. When len(trials) == 1, this is
    sequential execution; when len(trials) > 1, trials are built in parallel
    using a single Bazel invocation.

    The function:
    1. Suggests parameters for all trials using design-specific suggest_params
    2. Builds all designs (in parallel if multiple) and extracts PPA metrics
    3. Stores results in trial user_attrs for later analysis
    4. Reports results back to Optuna using study.tell()

    Args:
        study: Optuna Study object
        trials: List of Optuna Trial objects to evaluate (can be single trial)
        config: DSE configuration
        workspace_root: Bazel workspace root directory
        batch_id: Batch identifier for cache busting (default: 0)
    """
    # Suggest parameters for all trials
    # IMPORTANT: Each trial must suggest its own parameters independently
    # to avoid parameter collision in parallel execution
    params_list = []
    for trial in trials:
        params = config.suggest_params(trial)
        params_list.append(params)

    # Build all designs in parallel
    results = build_designs(config, params_list, workspace_root, batch_id=batch_id)

    # Process results and report back to Optuna
    for trial, params, result in zip(trials, params_list, results):
        objectives = _store_trial_results(trial, params, result)
        study.tell(trial, objectives)


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
