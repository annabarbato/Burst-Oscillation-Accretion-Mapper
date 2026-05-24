"""Empirical control-window false-alarm checks for Phase 1.

This module composes existing control-window, targeted-search, and candidate
scoring primitives. It does not generate synthetic Poisson envelopes, estimate
p-values, perform trials correction, or change candidate thresholds.
"""

from __future__ import annotations

from dataclasses import dataclass

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
    build_pre_post_control_windows,
    summarize_control_reviews,
)
from .event_products import EventProduct
from .oscillation_search import (
    SlidingWindowConfig,
    TargetedZ2SearchConfig,
    search_event_product_sliding_targeted_z2,
)
from .time_intervals import TimeInterval


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
