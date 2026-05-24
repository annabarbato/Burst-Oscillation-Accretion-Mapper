"""MINBAR timing-window matching helpers for Phase 1 validation.

These helpers compare detector review summaries against expected burst timing
windows supplied by curated MINBAR validation data. They do not classify a
candidate as a thermonuclear burst; they only report timing matches, missing
expected bursts, and unmatched detector summaries.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from .burst_detection import MultiCadenceBurstCandidateSummary


MATCHED = "matched"
MISSING_DETECTION = "missing_detection"


class MinbarMatchingError(ValueError):
    """Raised when MINBAR matching inputs are invalid."""


@dataclass(frozen=True)
class MinbarBurstWindow:
    """Expected MINBAR burst timing window in observation-relative seconds."""

    source_id: str
    obs_id: str
    minbar_burst_id: str
    start: float
    peak: float
    stop: float
    expected_signal: str = ""

    def __post_init__(self) -> None:
        _require_identity(self.source_id, "source_id")
        _require_identity(self.obs_id, "obs_id")
        _require_identity(self.minbar_burst_id, "minbar_burst_id")
        _require_ordered_window(self.start, self.peak, self.stop, "MINBAR")


@dataclass(frozen=True)
class DetectedBurstWindow:
    """Detector review-summary timing window in observation-relative seconds."""

    source_id: str
    obs_id: str
    candidate_id: str
    start: float
    peak: float
    stop: float
    passes_review: bool

    def __post_init__(self) -> None:
        _require_identity(self.source_id, "source_id")
        _require_identity(self.obs_id, "obs_id")
        _require_identity(self.candidate_id, "candidate_id")
        _require_ordered_window(self.start, self.peak, self.stop, "detected")

    @classmethod
    def from_summary(
        cls,
        *,
        source_id: str,
        obs_id: str,
        candidate_id: str,
        summary: MultiCadenceBurstCandidateSummary,
    ) -> DetectedBurstWindow:
        """Create a detected window from a multi-cadence detector summary."""

        return cls(
            source_id=source_id,
            obs_id=obs_id,
            candidate_id=candidate_id,
            start=summary.start,
            peak=summary.peak_time,
            stop=summary.stop,
            passes_review=summary.passes_any_review,
        )


@dataclass(frozen=True)
class BurstTimingMatch:
    """One expected MINBAR window matched to zero or one detector window."""

    expected: MinbarBurstWindow
    detected: DetectedBurstWindow | None
    status: str
    start_delta_s: float | None
    peak_delta_s: float | None
    stop_delta_s: float | None
    max_abs_delta_s: float | None
    overlap_fraction: float

    @property
    def is_match(self) -> bool:
        return self.status == MATCHED


@dataclass(frozen=True)
class BurstTimingMatchReport:
    """Greedy timing-match report for one validation comparison run."""

    matches: tuple[BurstTimingMatch, ...]
    unmatched_detections: tuple[DetectedBurstWindow, ...]

    @property
    def matched_count(self) -> int:
        return sum(match.is_match for match in self.matches)

    @property
    def missing_count(self) -> int:
        return sum(match.status == MISSING_DETECTION for match in self.matches)

    @property
    def unmatched_detection_count(self) -> int:
        return len(self.unmatched_detections)


def match_detected_bursts_to_minbar(
    expected_windows: tuple[MinbarBurstWindow, ...],
    detected_windows: tuple[DetectedBurstWindow, ...],
    *,
    tolerance_s: float,
    require_passed_review: bool = True,
) -> BurstTimingMatchReport:
    """Match detector windows to MINBAR windows using source, ObsID, and timing.

    Matching is greedy and one-to-one. For each expected MINBAR window, the
    closest still-unused detector window within `tolerance_s` of start, peak,
    and stop is selected. Unmatched expected windows remain in the report as
    `missing_detection` entries.
    """

    if not isfinite(tolerance_s) or tolerance_s < 0:
        raise MinbarMatchingError(f"Invalid tolerance_s: {tolerance_s}")

    candidate_pool = tuple(
        detected
        for detected in detected_windows
        if detected.passes_review or not require_passed_review
    )
    used_detection_indexes: set[int] = set()
    matches: list[BurstTimingMatch] = []

    for expected in expected_windows:
        scored_candidates = [
            _score_candidate(expected, detected, detection_index)
            for detection_index, detected in enumerate(candidate_pool)
            if detection_index not in used_detection_indexes
            and _same_validation_context(expected, detected)
        ]
        viable_candidates = [
            candidate
            for candidate in scored_candidates
            if candidate.match.max_abs_delta_s is not None
            and candidate.match.max_abs_delta_s <= tolerance_s
        ]
        if not viable_candidates:
            matches.append(_missing_detection_match(expected))
            continue

        best = min(
            viable_candidates,
            key=lambda candidate: (
                candidate.match.max_abs_delta_s or float("inf"),
                abs(candidate.match.peak_delta_s or 0.0),
                -candidate.match.overlap_fraction,
                candidate.detection_index,
            ),
        )
        used_detection_indexes.add(best.detection_index)
        matches.append(best.match)

    unmatched = tuple(
        detected
        for detection_index, detected in enumerate(candidate_pool)
        if detection_index not in used_detection_indexes
    )
    return BurstTimingMatchReport(matches=tuple(matches), unmatched_detections=unmatched)


@dataclass(frozen=True)
class _ScoredCandidate:
    detection_index: int
    match: BurstTimingMatch


def _score_candidate(
    expected: MinbarBurstWindow,
    detected: DetectedBurstWindow,
    detection_index: int,
) -> _ScoredCandidate:
    start_delta = detected.start - expected.start
    peak_delta = detected.peak - expected.peak
    stop_delta = detected.stop - expected.stop
    max_abs_delta = max(abs(start_delta), abs(peak_delta), abs(stop_delta))
    match = BurstTimingMatch(
        expected=expected,
        detected=detected,
        status=MATCHED,
        start_delta_s=start_delta,
        peak_delta_s=peak_delta,
        stop_delta_s=stop_delta,
        max_abs_delta_s=max_abs_delta,
        overlap_fraction=_overlap_fraction(
            expected.start,
            expected.stop,
            detected.start,
            detected.stop,
        ),
    )
    return _ScoredCandidate(detection_index=detection_index, match=match)


def _missing_detection_match(expected: MinbarBurstWindow) -> BurstTimingMatch:
    return BurstTimingMatch(
        expected=expected,
        detected=None,
        status=MISSING_DETECTION,
        start_delta_s=None,
        peak_delta_s=None,
        stop_delta_s=None,
        max_abs_delta_s=None,
        overlap_fraction=0.0,
    )


def _same_validation_context(
    expected: MinbarBurstWindow, detected: DetectedBurstWindow
) -> bool:
    return (
        expected.source_id == detected.source_id
        and expected.obs_id == detected.obs_id
    )


def _overlap_fraction(
    expected_start: float,
    expected_stop: float,
    detected_start: float,
    detected_stop: float,
) -> float:
    overlap = max(
        0.0,
        min(expected_stop, detected_stop) - max(expected_start, detected_start),
    )
    expected_duration = expected_stop - expected_start
    return overlap / expected_duration if expected_duration > 0 else 0.0


def _require_identity(value: str, field: str) -> None:
    if not value.strip():
        raise MinbarMatchingError(f"Missing required field: {field}")


def _require_ordered_window(start: float, peak: float, stop: float, label: str) -> None:
    if not all(isfinite(value) for value in (start, peak, stop)):
        raise MinbarMatchingError(f"{label} window times must be finite")
    if not start <= peak <= stop or stop <= start:
        raise MinbarMatchingError(
            f"{label} window must satisfy start <= peak <= stop and stop > start"
        )
