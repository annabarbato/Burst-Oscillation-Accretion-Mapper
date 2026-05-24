"""Early burst-detection primitives for Phase 1.

This module scores excess counts relative to a supplied baseline and groups
adjacent excess bins into interval candidates. It does not claim candidates are
thermonuclear bursts; later morphology filters and MINBAR validation must do
that work.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, log, sqrt

from .lightcurves import BaselineEstimate, LightCurve, LightCurveError


class BurstDetectionError(ValueError):
    """Raised when burst-detection scoring inputs are invalid."""


@dataclass(frozen=True)
class BinExcessScore:
    """Poisson excess score for one light-curve bin."""

    bin_index: int
    start: float
    stop: float
    observed_counts: int
    expected_counts: float | None
    exposure: float
    baseline_rate: float | None
    signed_sqrt_deviance: float | None

    def is_excess(self, threshold: float) -> bool:
        return (
            self.signed_sqrt_deviance is not None
            and self.signed_sqrt_deviance >= threshold
        )


@dataclass(frozen=True)
class BurstIntervalCandidate:
    """A contiguous interval of excess bins needing later morphology review."""

    start: float
    stop: float
    first_bin_index: int
    last_bin_index: int
    peak_bin_index: int
    peak_score: float
    total_counts: int
    total_expected_counts: float
    n_bins: int

    @property
    def duration(self) -> float:
        return self.stop - self.start

    @property
    def excess_counts(self) -> float:
        return self.total_counts - self.total_expected_counts


def signed_poisson_sqrt_deviance(observed_counts: int, expected_counts: float) -> float:
    """Return signed square root of the Poisson likelihood-ratio deviance.

    Positive values indicate excess counts, negative values indicate deficits.
    The statistic is useful for ranking bins, not as a final trials-corrected
    burst significance.
    """

    if observed_counts < 0:
        raise BurstDetectionError("observed_counts cannot be negative")
    if not isfinite(expected_counts) or expected_counts <= 0:
        raise BurstDetectionError(f"expected_counts must be positive: {expected_counts}")

    if observed_counts == expected_counts:
        return 0.0

    if observed_counts == 0:
        deviance = 2.0 * expected_counts
    else:
        deviance = 2.0 * (
            observed_counts * log(observed_counts / expected_counts)
            - (observed_counts - expected_counts)
        )

    sign = 1.0 if observed_counts > expected_counts else -1.0
    return sign * sqrt(max(deviance, 0.0))


def score_light_curve_excess(
    light_curve: LightCurve, baseline: BaselineEstimate
) -> tuple[BinExcessScore, ...]:
    """Score each light-curve bin against a baseline rate estimate."""

    if light_curve.n_bins != len(baseline.rates):
        raise LightCurveError("Light curve and baseline lengths must match")

    scores: list[BinExcessScore] = []
    for index, (count, exposure, baseline_rate) in enumerate(
        zip(light_curve.counts, light_curve.exposures, baseline.rates)
    ):
        expected_counts: float | None = None
        signed_score: float | None = None
        if exposure > 0 and baseline_rate is not None:
            if baseline_rate < 0 or not isfinite(baseline_rate):
                raise BurstDetectionError(f"Invalid baseline rate: {baseline_rate}")
            expected_counts = baseline_rate * exposure
            if expected_counts > 0:
                signed_score = signed_poisson_sqrt_deviance(count, expected_counts)

        scores.append(
            BinExcessScore(
                bin_index=index,
                start=light_curve.bin_starts[index],
                stop=light_curve.bin_stops[index],
                observed_counts=count,
                expected_counts=expected_counts,
                exposure=exposure,
                baseline_rate=baseline_rate,
                signed_sqrt_deviance=signed_score,
            )
        )

    return tuple(scores)


def group_excess_bins(
    scores: tuple[BinExcessScore, ...],
    *,
    threshold: float,
    min_consecutive_bins: int = 1,
) -> tuple[BurstIntervalCandidate, ...]:
    """Group adjacent scored bins above threshold into interval candidates."""

    if not isfinite(threshold) or threshold <= 0:
        raise BurstDetectionError(f"threshold must be positive: {threshold}")
    if min_consecutive_bins < 1:
        raise BurstDetectionError("min_consecutive_bins must be at least 1")

    candidates: list[BurstIntervalCandidate] = []
    current: list[BinExcessScore] = []
    for score in scores:
        if score.is_excess(threshold):
            current.append(score)
        else:
            _append_candidate_if_valid(candidates, current, min_consecutive_bins)
            current = []
    _append_candidate_if_valid(candidates, current, min_consecutive_bins)
    return tuple(candidates)


def _append_candidate_if_valid(
    candidates: list[BurstIntervalCandidate],
    scores: list[BinExcessScore],
    min_consecutive_bins: int,
) -> None:
    if len(scores) < min_consecutive_bins:
        return

    peak = max(scores, key=lambda score: score.signed_sqrt_deviance or float("-inf"))
    total_expected = sum(score.expected_counts or 0.0 for score in scores)
    candidates.append(
        BurstIntervalCandidate(
            start=scores[0].start,
            stop=scores[-1].stop,
            first_bin_index=scores[0].bin_index,
            last_bin_index=scores[-1].bin_index,
            peak_bin_index=peak.bin_index,
            peak_score=peak.signed_sqrt_deviance or 0.0,
            total_counts=sum(score.observed_counts for score in scores),
            total_expected_counts=total_expected,
            n_bins=len(scores),
        )
    )
