"""Validation recovery status helpers for Phase 1 closeout.

These helpers do not change conservative catalog candidate classes. They add a
separate validation-facing status that says whether a known target was recovered
under the Phase 1 audit rules, or whether an expected non-detection needs
review.
"""

from __future__ import annotations

from dataclasses import dataclass

from .candidate_scoring import (
    MARGINAL_CANDIDATE,
    NON_DETECTION,
    PROBABLE_DETECTION,
    SECURE_DETECTION,
)
from .catalog_writer import CandidateCatalogRow, ControlCatalogRow
from .time_intervals import TimeInterval


RECOVERED = "recovered"
NOT_RECOVERED = "not_recovered"
REVIEW = "review"


@dataclass(frozen=True)
class ValidationRecoveryStatus:
    """Phase 1 validation status separate from catalog candidate class."""

    recovery_status: str
    reason_codes: tuple[str, ...]
    p_single: float | None
    p_trials: float | None
    empirical_control_fap: float | None
    control_exceedance_count: int | None
    control_count: int
    phase_window: str
    correction_status: str


def classify_phase1_recovery(
    *,
    candidate: CandidateCatalogRow,
    control_rows: tuple[ControlCatalogRow, ...],
    validation_goal: str,
    expected_signal: str,
    burst_window: TimeInterval,
    correction_status: str,
) -> ValidationRecoveryStatus:
    """Classify validation recovery without changing the candidate label."""

    reason_codes: list[str] = []
    phase_window = candidate_phase_window(candidate, burst_window=burst_window)
    empirical_fap, exceedance_count = empirical_control_fap(candidate, control_rows)
    has_probable_or_secure_control = any(
        row.classification in {SECURE_DETECTION, PROBABLE_DETECTION}
        for row in control_rows
    )
    trials_accounted = candidate.p_single is not None and candidate.p_trials is not None
    probable_or_secure = candidate.classification in {
        SECURE_DETECTION,
        PROBABLE_DETECTION,
    }
    marginal = candidate.classification == MARGINAL_CANDIDATE
    non_detection_expected = (
        validation_goal == "non_detection_control"
        or expected_signal == NON_DETECTION
    )

    if correction_status not in {"applied", "already_applied"}:
        reason_codes.append("timing_correction_not_applied")
    if has_probable_or_secure_control:
        reason_codes.append("probable_or_secure_control_present")
    if not trials_accounted:
        reason_codes.append("trials_not_accounted")
    if phase_window == "outside_burst_search":
        reason_codes.append("phase_window_not_plausible")

    if non_detection_expected:
        if candidate.classification == NON_DETECTION:
            status = NOT_RECOVERED
            reason_codes.append("expected_non_detection_no_candidate")
        elif marginal:
            status = REVIEW
            reason_codes.append("expected_non_detection_marginal_review")
        else:
            status = REVIEW
            reason_codes.append("expected_non_detection_detection_like_review")
    elif (
        probable_or_secure
        and not has_probable_or_secure_control
        and trials_accounted
        and phase_window != "outside_burst_search"
        and correction_status in {"applied", "already_applied"}
    ):
        status = RECOVERED
        reason_codes.append("known_signal_frequency_consistent_control_cleared")
    else:
        status = NOT_RECOVERED
        if not probable_or_secure:
            reason_codes.append("candidate_below_probable_threshold")

    return ValidationRecoveryStatus(
        recovery_status=status,
        reason_codes=tuple(dict.fromkeys(reason_codes)),
        p_single=candidate.p_single,
        p_trials=candidate.p_trials,
        empirical_control_fap=empirical_fap,
        control_exceedance_count=exceedance_count,
        control_count=len(control_rows),
        phase_window=phase_window,
        correction_status=correction_status,
    )


def candidate_phase_window(
    candidate: CandidateCatalogRow,
    *,
    burst_window: TimeInterval,
) -> str:
    """Return a coarse burst-phase label for a candidate search window."""

    if candidate.window_start is None or candidate.window_stop is None:
        return "none"
    center = 0.5 * (candidate.window_start + candidate.window_stop)
    if burst_window.start <= center <= burst_window.stop:
        return "burst_body"
    if burst_window.stop < center <= burst_window.stop + 20.0:
        return "early_tail"
    if burst_window.start - 10.0 <= center < burst_window.start:
        return "pre_rise_edge"
    return "outside_burst_search"


def empirical_control_fap(
    candidate: CandidateCatalogRow,
    control_rows: tuple[ControlCatalogRow, ...],
) -> tuple[float | None, int | None]:
    """Return the fraction of controls at least as strong as the candidate."""

    if candidate.z2_power is None:
        return None, None
    control_powers = tuple(
        row.z2_power for row in control_rows if row.z2_power is not None
    )
    if not control_powers:
        return None, 0
    exceedance_count = sum(power >= candidate.z2_power for power in control_powers)
    return exceedance_count / len(control_powers), exceedance_count
