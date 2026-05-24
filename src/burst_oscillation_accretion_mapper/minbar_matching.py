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

    @property
    def metrics(self) -> BurstTimingValidationMetrics:
        return summarize_timing_match_report(self)


@dataclass(frozen=True)
class ObservationTimingMatchReport:
    """Timing-match report scoped to one source and ObsID."""

    source_id: str
    obs_id: str
    report: BurstTimingMatchReport

    def __post_init__(self) -> None:
        _require_identity(self.source_id, "source_id")
        _require_identity(self.obs_id, "obs_id")

    @property
    def metrics(self) -> BurstTimingValidationMetrics:
        return self.report.metrics


@dataclass(frozen=True)
class BurstTimingValidationRunReport:
    """Timing-match reports for a multi-observation validation run."""

    observation_reports: tuple[ObservationTimingMatchReport, ...]

    @property
    def metrics(self) -> BurstTimingValidationMetrics:
        return summarize_timing_match_reports(
            tuple(report.report for report in self.observation_reports)
        )


@dataclass(frozen=True)
class BurstTimingValidationMetrics:
    """Compact validation metrics for MINBAR timing matching."""

    expected_count: int
    matched_count: int
    missing_count: int
    unmatched_detection_count: int
    detected_window_count: int
    recall_fraction: float | None
    unmatched_detection_fraction: float | None
    max_abs_delta_s: float | None
    mean_abs_peak_delta_s: float | None


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


def match_detected_bursts_by_observation(
    expected_windows: tuple[MinbarBurstWindow, ...],
    detected_windows: tuple[DetectedBurstWindow, ...],
    *,
    tolerance_s: float,
    require_passed_review: bool = True,
) -> BurstTimingValidationRunReport:
    """Run MINBAR timing matching independently for each source/ObsID."""

    if not isfinite(tolerance_s) or tolerance_s < 0:
        raise MinbarMatchingError(f"Invalid tolerance_s: {tolerance_s}")

    candidate_pool = tuple(
        detected
        for detected in detected_windows
        if detected.passes_review or not require_passed_review
    )
    expected_by_key = _group_expected_by_observation(expected_windows)
    detected_by_key = _group_detected_by_observation(candidate_pool)
    keys = tuple(sorted(set(expected_by_key) | set(detected_by_key)))

    observation_reports = tuple(
        ObservationTimingMatchReport(
            source_id=source_id,
            obs_id=obs_id,
            report=match_detected_bursts_to_minbar(
                expected_by_key.get((source_id, obs_id), ()),
                detected_by_key.get((source_id, obs_id), ()),
                tolerance_s=tolerance_s,
                require_passed_review=False,
            ),
        )
        for source_id, obs_id in keys
    )
    return BurstTimingValidationRunReport(observation_reports=observation_reports)


def detected_windows_from_summaries(
    *,
    source_id: str,
    obs_id: str,
    summaries: tuple[MultiCadenceBurstCandidateSummary, ...],
    candidate_id_prefix: str,
    start_index: int = 1,
) -> tuple[DetectedBurstWindow, ...]:
    """Create deterministic detected windows from ordered detector summaries."""

    _require_identity(candidate_id_prefix, "candidate_id_prefix")
    if start_index < 0:
        raise MinbarMatchingError("start_index cannot be negative")

    return tuple(
        DetectedBurstWindow.from_summary(
            source_id=source_id,
            obs_id=obs_id,
            candidate_id=f"{candidate_id_prefix}-{index:04d}",
            summary=summary,
        )
        for index, summary in enumerate(summaries, start=start_index)
    )


def summarize_timing_match_report(
    report: BurstTimingMatchReport,
) -> BurstTimingValidationMetrics:
    """Summarize recall and review burden for one timing-match report."""

    return summarize_timing_match_reports((report,))


def summarize_timing_match_reports(
    reports: tuple[BurstTimingMatchReport, ...],
) -> BurstTimingValidationMetrics:
    """Summarize recall and review burden across timing-match reports."""

    matches = tuple(match for report in reports for match in report.matches)
    matched_count = sum(match.is_match for match in matches)
    missing_count = sum(match.status == MISSING_DETECTION for match in matches)
    unmatched_detection_count = sum(
        report.unmatched_detection_count for report in reports
    )
    expected_count = len(matches)
    detected_window_count = matched_count + unmatched_detection_count
    matched_peak_deltas = tuple(
        abs(match.peak_delta_s)
        for match in matches
        if match.is_match and match.peak_delta_s is not None
    )
    max_abs_delta_values = tuple(
        match.max_abs_delta_s
        for match in matches
        if match.is_match and match.max_abs_delta_s is not None
    )

    return BurstTimingValidationMetrics(
        expected_count=expected_count,
        matched_count=matched_count,
        missing_count=missing_count,
        unmatched_detection_count=unmatched_detection_count,
        detected_window_count=detected_window_count,
        recall_fraction=(
            matched_count / expected_count if expected_count > 0 else None
        ),
        unmatched_detection_fraction=(
            unmatched_detection_count / detected_window_count
            if detected_window_count > 0
            else None
        ),
        max_abs_delta_s=max(max_abs_delta_values) if max_abs_delta_values else None,
        mean_abs_peak_delta_s=(
            sum(matched_peak_deltas) / len(matched_peak_deltas)
            if matched_peak_deltas
            else None
        ),
    )


@dataclass(frozen=True)
class _ScoredCandidate:
    detection_index: int
    match: BurstTimingMatch


def _group_expected_by_observation(
    windows: tuple[MinbarBurstWindow, ...]
) -> dict[tuple[str, str], tuple[MinbarBurstWindow, ...]]:
    grouped: dict[tuple[str, str], list[MinbarBurstWindow]] = {}
    for window in windows:
        grouped.setdefault((window.source_id, window.obs_id), []).append(window)
    return {key: tuple(values) for key, values in grouped.items()}


def _group_detected_by_observation(
    windows: tuple[DetectedBurstWindow, ...]
) -> dict[tuple[str, str], tuple[DetectedBurstWindow, ...]]:
    grouped: dict[tuple[str, str], list[DetectedBurstWindow]] = {}
    for window in windows:
        grouped.setdefault((window.source_id, window.obs_id), []).append(window)
    return {key: tuple(values) for key, values in grouped.items()}


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
