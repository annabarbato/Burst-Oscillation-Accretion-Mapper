"""Phase 1 RXTE validation-run summaries and gate checks.

This module summarizes the existing Phase 1 catalog/review products. It does
not run ingestion, search, controls, injection/recovery, inference, or dashboard
code.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from .candidate_scoring import (
    MARGINAL_CANDIDATE,
    NON_DETECTION,
    PROBABLE_DETECTION,
    SECURE_DETECTION,
)
from .catalog_writer import BurstCatalogRow, CandidateCatalogRow, ControlCatalogRow
from .minbar_matching import BurstTimingValidationMetrics


class Phase1ValidationError(ValueError):
    """Raised when Phase 1 validation summary inputs are invalid."""


@dataclass(frozen=True)
class Phase1ValidationSummary:
    """Compact status summary for one Phase 1 RXTE validation run."""

    burst_count: int
    minbar_linked_burst_count: int
    candidate_count: int
    secure_count: int
    probable_count: int
    marginal_count: int
    non_detection_count: int
    control_count: int
    control_secure_count: int
    control_probable_count: int
    control_marginal_count: int
    control_non_detection_count: int
    timing_metrics: BurstTimingValidationMetrics | None = None

    @property
    def detection_like_count(self) -> int:
        return self.secure_count + self.probable_count + self.marginal_count

    @property
    def control_detection_like_count(self) -> int:
        return (
            self.control_secure_count
            + self.control_probable_count
            + self.control_marginal_count
        )

    @property
    def control_false_alarm_fraction(self) -> float | None:
        if self.control_count == 0:
            return None
        return self.control_detection_like_count / self.control_count

    @property
    def has_minbar_timing_metrics(self) -> bool:
        return self.timing_metrics is not None

    @property
    def minbar_recall_fraction(self) -> float | None:
        if self.timing_metrics is None:
            return None
        return self.timing_metrics.recall_fraction


@dataclass(frozen=True)
class Phase1ValidationGatePolicy:
    """Policy for deciding whether Phase 1 validation artifacts are complete."""

    require_burst_rows: bool = True
    require_candidate_rows: bool = True
    require_non_detection_rows: bool = True
    require_control_rows: bool = True
    require_timing_metrics: bool = True
    max_secure_control_count: int = 0
    max_probable_control_count: int | None = None
    max_control_false_alarm_fraction: float | None = None
    min_minbar_recall_fraction: float | None = None

    def __post_init__(self) -> None:
        _require_non_negative_int(
            self.max_secure_control_count,
            "max_secure_control_count",
        )
        if self.max_probable_control_count is not None:
            _require_non_negative_int(
                self.max_probable_control_count,
                "max_probable_control_count",
            )
        if self.max_control_false_alarm_fraction is not None:
            _require_probability(
                self.max_control_false_alarm_fraction,
                "max_control_false_alarm_fraction",
            )
        if self.min_minbar_recall_fraction is not None:
            _require_probability(
                self.min_minbar_recall_fraction,
                "min_minbar_recall_fraction",
            )


@dataclass(frozen=True)
class Phase1ValidationGateReview:
    """Result of applying a Phase 1 validation gate policy."""

    summary: Phase1ValidationSummary
    policy: Phase1ValidationGatePolicy
    passed: bool
    reasons: tuple[str, ...]


def summarize_phase1_validation_catalog(
    *,
    burst_rows: tuple[BurstCatalogRow, ...],
    candidate_rows: tuple[CandidateCatalogRow, ...],
    control_rows: tuple[ControlCatalogRow, ...],
    timing_metrics: BurstTimingValidationMetrics | None = None,
) -> Phase1ValidationSummary:
    """Summarize Phase 1 catalog/review rows for validation closeout."""

    _validate_non_negative_counts(timing_metrics)
    return Phase1ValidationSummary(
        burst_count=len(burst_rows),
        minbar_linked_burst_count=sum(
            1 for row in burst_rows if row.minbar_burst_id.strip()
        ),
        candidate_count=len(candidate_rows),
        secure_count=_classification_count(candidate_rows, SECURE_DETECTION),
        probable_count=_classification_count(candidate_rows, PROBABLE_DETECTION),
        marginal_count=_classification_count(candidate_rows, MARGINAL_CANDIDATE),
        non_detection_count=_classification_count(candidate_rows, NON_DETECTION),
        control_count=len(control_rows),
        control_secure_count=_classification_count(control_rows, SECURE_DETECTION),
        control_probable_count=_classification_count(control_rows, PROBABLE_DETECTION),
        control_marginal_count=_classification_count(control_rows, MARGINAL_CANDIDATE),
        control_non_detection_count=_classification_count(control_rows, NON_DETECTION),
        timing_metrics=timing_metrics,
    )


def review_phase1_validation_gate(
    summary: Phase1ValidationSummary,
    *,
    policy: Phase1ValidationGatePolicy | None = None,
) -> Phase1ValidationGateReview:
    """Apply a conservative Phase 1 validation-artifact gate."""

    if policy is None:
        policy = Phase1ValidationGatePolicy()
    reasons: list[str] = []

    if policy.require_burst_rows and summary.burst_count == 0:
        reasons.append("no_burst_rows")
    if policy.require_candidate_rows and summary.candidate_count == 0:
        reasons.append("no_candidate_rows")
    if policy.require_non_detection_rows and summary.non_detection_count == 0:
        reasons.append("no_non_detection_rows")
    if policy.require_control_rows and summary.control_count == 0:
        reasons.append("no_control_rows")
    if policy.require_timing_metrics and summary.timing_metrics is None:
        reasons.append("no_minbar_timing_metrics")
    if summary.control_secure_count > policy.max_secure_control_count:
        reasons.append("secure_control_count_exceeds_policy")
    if (
        policy.max_probable_control_count is not None
        and summary.control_probable_count > policy.max_probable_control_count
    ):
        reasons.append("probable_control_count_exceeds_policy")
    if (
        policy.max_control_false_alarm_fraction is not None
        and summary.control_false_alarm_fraction is not None
        and summary.control_false_alarm_fraction
        > policy.max_control_false_alarm_fraction
    ):
        reasons.append("control_false_alarm_fraction_exceeds_policy")
    if (
        policy.min_minbar_recall_fraction is not None
        and (
            summary.minbar_recall_fraction is None
            or summary.minbar_recall_fraction < policy.min_minbar_recall_fraction
        )
    ):
        reasons.append("minbar_recall_below_policy")

    return Phase1ValidationGateReview(
        summary=summary,
        policy=policy,
        passed=not reasons,
        reasons=tuple(reasons),
    )


def _classification_count(rows: tuple[object, ...], classification: str) -> int:
    return sum(getattr(row, "classification") == classification for row in rows)


def _validate_non_negative_counts(
    metrics: BurstTimingValidationMetrics | None,
) -> None:
    if metrics is None:
        return
    for field_name in (
        "expected_count",
        "matched_count",
        "missing_count",
        "unmatched_detection_count",
        "detected_window_count",
    ):
        _require_non_negative_int(getattr(metrics, field_name), field_name)


def _require_non_negative_int(value: int, field: str) -> None:
    if not isinstance(value, int) or value < 0:
        raise Phase1ValidationError(f"{field} must be a non-negative integer")


def _require_probability(value: float, field: str) -> None:
    if not isfinite(value) or value < 0 or value > 1:
        raise Phase1ValidationError(f"{field} must be a probability in [0, 1]")
