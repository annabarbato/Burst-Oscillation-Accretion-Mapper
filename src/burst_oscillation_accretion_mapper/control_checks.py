"""Empirical control-window false-alarm checks for Phase 1.

This module composes existing control-window, targeted-search, and candidate
scoring primitives. It can also score synthetic Poisson null realizations for
Phase 1 empirical false-alarm review. It does not inject coherent oscillations,
estimate sensitivity curves, perform trials correction, or change candidate
thresholds.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from .candidate_scoring import (
    CandidateEvidenceFlags,
    CandidateScoringConfig,
    OscillationCandidateReview,
    score_sliding_targeted_z2_result,
)
from .control_intervals import (
    ControlFalseAlarmSummary,
    ControlReview,
    ControlWindow,
    ControlWindowConfig,
    SYNTHETIC_POISSON_CONTROL,
    build_pre_post_control_windows,
    summarize_control_reviews,
)
from .event_products import EventProduct
from .oscillation_search import (
    SlidingWindowConfig,
    TargetedZ2SearchConfig,
    search_event_product_sliding_targeted_z2,
)
from .synthetic_controls import (
    PoissonEnvelopeConfig,
    SyntheticPoissonControlConfig,
    estimate_poisson_count_rate_envelope,
    generate_synthetic_poisson_event_product,
)
from .time_intervals import TimeInterval


class ControlCheckError(ValueError):
    """Raised when control false-alarm policy inputs are invalid."""


@dataclass(frozen=True)
class ControlSearchRun:
    """Scored control-window products for one burst or review context."""

    control_reviews: tuple[ControlReview, ...]
    summary: ControlFalseAlarmSummary

    @property
    def controls(self) -> tuple[ControlWindow, ...]:
        return tuple(control_review.control for control_review in self.control_reviews)

    @property
    def reviews(self) -> tuple[OscillationCandidateReview, ...]:
        return tuple(control_review.review for control_review in self.control_reviews)

    @property
    def has_detection_like_controls(self) -> bool:
        return self.summary.detection_like_count > 0


@dataclass(frozen=True)
class ControlClearancePolicy:
    """Policy for deciding whether controls clear a candidate review."""

    require_controls: bool = True
    max_secure_count: int = 0
    max_probable_count: int = 0
    max_marginal_count: int = 0
    max_false_alarm_fraction: float | None = None

    def __post_init__(self) -> None:
        _require_non_negative_int(self.max_secure_count, "max_secure_count")
        _require_non_negative_int(self.max_probable_count, "max_probable_count")
        _require_non_negative_int(self.max_marginal_count, "max_marginal_count")
        if self.max_false_alarm_fraction is not None and (
            not isfinite(self.max_false_alarm_fraction)
            or self.max_false_alarm_fraction < 0
            or self.max_false_alarm_fraction > 1
        ):
            raise ControlCheckError(
                "max_false_alarm_fraction must be a probability in [0, 1]"
            )


@dataclass(frozen=True)
class ControlClearanceReview:
    """Result of applying a control-clearance policy to scored controls."""

    summary: ControlFalseAlarmSummary
    policy: ControlClearancePolicy
    passed: bool
    reasons: tuple[str, ...]


def search_and_score_control_windows(
    event_product: EventProduct,
    *,
    controls: tuple[ControlWindow, ...],
    window_config: SlidingWindowConfig,
    search_config: TargetedZ2SearchConfig,
    scoring_config: CandidateScoringConfig,
    expected_frequency_hz: float | None,
    evidence: CandidateEvidenceFlags = CandidateEvidenceFlags(),
) -> ControlSearchRun:
    """Run the targeted sliding search and scorer on prepared controls."""

    control_reviews = tuple(
        ControlReview(
            control=control,
            review=_score_control_window(
                event_product,
                control=control,
                window_config=window_config,
                search_config=search_config,
                scoring_config=scoring_config,
                expected_frequency_hz=expected_frequency_hz,
                evidence=evidence,
            ),
        )
        for control in controls
    )
    return ControlSearchRun(
        control_reviews=control_reviews,
        summary=summarize_control_reviews(control_reviews),
    )


def build_search_and_score_pre_post_controls(
    event_product: EventProduct,
    *,
    burst_window: TimeInterval,
    control_config: ControlWindowConfig,
    window_config: SlidingWindowConfig,
    search_config: TargetedZ2SearchConfig,
    scoring_config: CandidateScoringConfig,
    expected_frequency_hz: float | None,
    burst_id: str = "",
    evidence: CandidateEvidenceFlags = CandidateEvidenceFlags(),
) -> ControlSearchRun:
    """Build deterministic pre/post-burst controls and score them."""

    controls = build_pre_post_control_windows(
        burst_window=burst_window,
        good_time_intervals=event_product.gtis,
        config=control_config,
        burst_id=burst_id,
    )
    return search_and_score_control_windows(
        event_product,
        controls=controls,
        window_config=window_config,
        search_config=search_config,
        scoring_config=scoring_config,
        expected_frequency_hz=expected_frequency_hz,
        evidence=evidence,
    )


def build_search_and_score_synthetic_poisson_controls(
    event_product: EventProduct,
    *,
    reference_interval: TimeInterval,
    synthetic_config: SyntheticPoissonControlConfig,
    window_config: SlidingWindowConfig,
    search_config: TargetedZ2SearchConfig,
    scoring_config: CandidateScoringConfig,
    expected_frequency_hz: float | None,
    burst_id: str = "",
    evidence: CandidateEvidenceFlags = CandidateEvidenceFlags(),
) -> ControlSearchRun:
    """Generate and score synthetic Poisson null controls for one interval."""

    envelope = estimate_poisson_count_rate_envelope(
        event_product,
        interval=reference_interval,
        config=PoissonEnvelopeConfig(bin_size_s=synthetic_config.envelope_bin_size_s),
    )
    control_reviews: list[ControlReview] = []
    for realization_number in range(1, synthetic_config.realization_count + 1):
        synthetic_product = generate_synthetic_poisson_event_product(
            event_product,
            envelope=envelope,
            seed=synthetic_config.seed_for_realization(realization_number),
            realization_number=realization_number,
        )
        control = ControlWindow(
            control_id=_synthetic_control_id(burst_id, realization_number),
            kind=SYNTHETIC_POISSON_CONTROL,
            interval=reference_interval,
            requested_interval=reference_interval,
            burst_id=burst_id,
        )
        control_reviews.append(
            ControlReview(
                control=control,
                review=_score_control_window(
                    synthetic_product,
                    control=control,
                    window_config=window_config,
                    search_config=search_config,
                    scoring_config=scoring_config,
                    expected_frequency_hz=expected_frequency_hz,
                    evidence=evidence,
                ),
            )
        )

    return ControlSearchRun(
        control_reviews=tuple(control_reviews),
        summary=summarize_control_reviews(tuple(control_reviews)),
    )


def evaluate_control_clearance(
    control_run: ControlSearchRun,
    *,
    policy: ControlClearancePolicy | None = None,
) -> ControlClearanceReview:
    """Evaluate whether scored controls clear candidate-promotion evidence."""

    if policy is None:
        policy = ControlClearancePolicy()
    summary = control_run.summary
    reasons: list[str] = []

    if policy.require_controls and summary.control_count == 0:
        reasons.append("no_controls_available")
    if summary.secure_count > policy.max_secure_count:
        reasons.append("secure_control_count_exceeds_policy")
    if summary.probable_count > policy.max_probable_count:
        reasons.append("probable_control_count_exceeds_policy")
    if summary.marginal_count > policy.max_marginal_count:
        reasons.append("marginal_control_count_exceeds_policy")
    if (
        policy.max_false_alarm_fraction is not None
        and summary.false_alarm_fraction is not None
        and summary.false_alarm_fraction > policy.max_false_alarm_fraction
    ):
        reasons.append("control_false_alarm_fraction_exceeds_policy")

    return ControlClearanceReview(
        summary=summary,
        policy=policy,
        passed=not reasons,
        reasons=tuple(reasons),
    )


def evidence_with_control_clearance(
    evidence: CandidateEvidenceFlags,
    clearance: ControlClearanceReview,
) -> CandidateEvidenceFlags:
    """Return candidate evidence with control clearance set from controls."""

    return CandidateEvidenceFlags(
        physically_plausible_phase=evidence.physically_plausible_phase,
        control_clearance=clearance.passed,
        sensitivity_confirmed=evidence.sensitivity_confirmed,
        coherent_structure=evidence.coherent_structure,
        phase_evolution_ok=evidence.phase_evolution_ok,
    )


def _score_control_window(
    event_product: EventProduct,
    *,
    control: ControlWindow,
    window_config: SlidingWindowConfig,
    search_config: TargetedZ2SearchConfig,
    scoring_config: CandidateScoringConfig,
    expected_frequency_hz: float | None,
    evidence: CandidateEvidenceFlags,
) -> OscillationCandidateReview:
    search_result = search_event_product_sliding_targeted_z2(
        event_product,
        interval=control.interval,
        window_config=window_config,
        search_config=search_config,
    )
    return score_sliding_targeted_z2_result(
        search_result,
        config=scoring_config,
        expected_frequency_hz=expected_frequency_hz,
        evidence=evidence,
    )


def _synthetic_control_id(burst_id: str, realization_number: int) -> str:
    prefix = burst_id.strip() if burst_id.strip() else "control"
    return f"{prefix}_{SYNTHETIC_POISSON_CONTROL}_{realization_number:03d}"


def _require_non_negative_int(value: int, field: str) -> None:
    if not isinstance(value, int) or value < 0:
        raise ControlCheckError(f"{field} must be a non-negative integer")
