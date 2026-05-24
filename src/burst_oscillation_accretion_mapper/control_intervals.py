"""Control-window helpers for Phase 1 false-alarm checks.

This module creates deterministic pre-burst and post-burst control windows and
summarizes scored control reviews. It does not generate synthetic Poisson
envelopes, perform trials correction, or make population-level claims.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from .candidate_scoring import (
    MARGINAL_CANDIDATE,
    NON_DETECTION,
    PROBABLE_DETECTION,
    SECURE_DETECTION,
    OscillationCandidateReview,
)
from .time_intervals import TimeInterval, clip_to_gti


PRE_BURST_CONTROL = "pre_burst"
POST_BURST_CONTROL = "post_burst"


class ControlIntervalError(ValueError):
    """Raised when control-window inputs are invalid."""


@dataclass(frozen=True)
class ControlWindowConfig:
    """Configuration for pre-burst and post-burst control windows."""

    pre_duration_s: float
    post_duration_s: float
    pre_gap_s: float = 0.0
    post_gap_s: float = 0.0

    def __post_init__(self) -> None:
        _require_non_negative(self.pre_duration_s, "pre_duration_s")
        _require_non_negative(self.post_duration_s, "post_duration_s")
        _require_non_negative(self.pre_gap_s, "pre_gap_s")
        _require_non_negative(self.post_gap_s, "post_gap_s")
        if self.pre_duration_s == 0 and self.post_duration_s == 0:
            raise ControlIntervalError(
                "At least one control duration must be greater than zero"
            )


@dataclass(frozen=True)
class ControlWindow:
    """One clipped control interval associated with a burst search."""

    control_id: str
    kind: str
    interval: TimeInterval
    requested_interval: TimeInterval
    burst_id: str = ""

    @property
    def duration(self) -> float:
        return self.interval.duration


@dataclass(frozen=True)
class ControlReview:
    """A scored oscillation review associated with one control window."""

    control: ControlWindow
    review: OscillationCandidateReview


@dataclass(frozen=True)
class ControlFalseAlarmSummary:
    """Small empirical false-alarm summary over scored control windows."""

    control_count: int
    detection_like_count: int
    secure_count: int
    probable_count: int
    marginal_count: int
    non_detection_count: int

    @property
    def false_alarm_fraction(self) -> float | None:
        if self.control_count == 0:
            return None
        return self.detection_like_count / self.control_count


def build_pre_post_control_windows(
    *,
    burst_window: TimeInterval,
    good_time_intervals: tuple[TimeInterval, ...],
    config: ControlWindowConfig,
    burst_id: str = "",
) -> tuple[ControlWindow, ...]:
    """Build pre-burst and post-burst control windows clipped to GTIs."""

    requests = []
    if config.pre_duration_s > 0:
        requests.append(
            (
                PRE_BURST_CONTROL,
                TimeInterval(
                    burst_window.start - config.pre_gap_s - config.pre_duration_s,
                    burst_window.start - config.pre_gap_s,
                ),
            )
        )
    if config.post_duration_s > 0:
        requests.append(
            (
                POST_BURST_CONTROL,
                TimeInterval(
                    burst_window.stop + config.post_gap_s,
                    burst_window.stop + config.post_gap_s + config.post_duration_s,
                ),
            )
        )

    controls: list[ControlWindow] = []
    for kind, requested in requests:
        clipped_intervals = clip_to_gti(requested, good_time_intervals)
        for index, clipped in enumerate(clipped_intervals, start=1):
            controls.append(
                ControlWindow(
                    control_id=_control_id(kind, burst_id, index),
                    kind=kind,
                    interval=clipped,
                    requested_interval=requested,
                    burst_id=burst_id,
                )
            )
    return tuple(controls)


def summarize_control_reviews(
    control_reviews: tuple[ControlReview, ...],
) -> ControlFalseAlarmSummary:
    """Summarize detection-like classifications found in control windows."""

    secure_count = sum(
        review.review.classification == SECURE_DETECTION for review in control_reviews
    )
    probable_count = sum(
        review.review.classification == PROBABLE_DETECTION for review in control_reviews
    )
    marginal_count = sum(
        review.review.classification == MARGINAL_CANDIDATE for review in control_reviews
    )
    non_detection_count = sum(
        review.review.classification == NON_DETECTION for review in control_reviews
    )
    detection_like_count = secure_count + probable_count + marginal_count
    return ControlFalseAlarmSummary(
        control_count=len(control_reviews),
        detection_like_count=detection_like_count,
        secure_count=secure_count,
        probable_count=probable_count,
        marginal_count=marginal_count,
        non_detection_count=non_detection_count,
    )


def _control_id(kind: str, burst_id: str, index: int) -> str:
    prefix = burst_id.strip() if burst_id.strip() else "control"
    return f"{prefix}_{kind}_{index:03d}"


def _require_non_negative(value: float, field: str) -> None:
    if not isfinite(value) or value < 0:
        raise ControlIntervalError(f"{field} must be finite and non-negative")
