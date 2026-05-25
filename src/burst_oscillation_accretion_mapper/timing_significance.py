"""Timing-significance helpers for Phase 1 `Z_n^2` search products.

The functions here provide nominal single-trial and independent-trial corrected
p-values for event-based `Z_n^2` powers. They do not change candidate classes,
estimate empirical false-alarm rates, or account for correlated sliding windows.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import exp, expm1, factorial, isfinite, log1p

from .oscillation_search import (
    SlidingTargetedZ2SearchResult,
    TargetedZ2SearchResult,
)


class TimingSignificanceError(ValueError):
    """Raised when timing-significance inputs are invalid."""


@dataclass(frozen=True)
class Z2TrialSignificance:
    """Single-trial and trials-corrected significance for one `Z_n^2` power."""

    z2_power: float
    n_harmonics: int
    trial_count: int
    p_single: float
    p_trials: float


def z2_single_trial_p_value(z2_power: float, *, n_harmonics: int) -> float:
    """Return the chi-square survival probability for one `Z_n^2` trial.

    Under the noise-only null, `Z_n^2` is distributed as chi-square with
    ``2 * n_harmonics`` degrees of freedom.
    """

    _require_non_negative(z2_power, "z2_power")
    _require_positive_int(n_harmonics, "n_harmonics")

    half_power = 0.5 * z2_power
    series = sum(
        (half_power**term_index) / factorial(term_index)
        for term_index in range(n_harmonics)
    )
    return min(1.0, max(0.0, exp(-half_power) * series))


def independent_trials_p_value(p_single: float, *, trial_count: int) -> float:
    """Return a nominal corrected p-value for independent trial attempts."""

    _require_probability(p_single, "p_single")
    _require_positive_int(trial_count, "trial_count")
    if p_single == 0.0:
        return 0.0
    if p_single == 1.0:
        return 1.0
    return -expm1(trial_count * log1p(-p_single))


def z2_trial_significance(
    z2_power: float,
    *,
    n_harmonics: int,
    trial_count: int,
) -> Z2TrialSignificance:
    """Summarize single-trial and nominal corrected significance for `Z_n^2`."""

    p_single = z2_single_trial_p_value(z2_power, n_harmonics=n_harmonics)
    p_trials = independent_trials_p_value(p_single, trial_count=trial_count)
    return Z2TrialSignificance(
        z2_power=z2_power,
        n_harmonics=n_harmonics,
        trial_count=trial_count,
        p_single=p_single,
        p_trials=p_trials,
    )


def targeted_result_significance(
    result: TargetedZ2SearchResult,
) -> Z2TrialSignificance:
    """Return significance for the best frequency in one targeted search window."""

    return z2_trial_significance(
        result.best_z2_power,
        n_harmonics=result.n_harmonics,
        trial_count=len(result.powers),
    )


def sliding_result_significance(
    result: SlidingTargetedZ2SearchResult,
) -> Z2TrialSignificance:
    """Return significance for the best window/frequency in a sliding search."""

    return z2_trial_significance(
        result.best_z2_power,
        n_harmonics=result.best_result.n_harmonics,
        trial_count=result.trial_count,
    )


def _require_non_negative(value: float, field: str) -> None:
    if not isfinite(value) or value < 0:
        raise TimingSignificanceError(f"{field} must be finite and non-negative")


def _require_probability(value: float, field: str) -> None:
    if not isfinite(value) or value < 0 or value > 1:
        raise TimingSignificanceError(f"{field} must be a probability in [0, 1]")


def _require_positive_int(value: int, field: str) -> None:
    if not isinstance(value, int) or value < 1:
        raise TimingSignificanceError(f"{field} must be a positive integer")
