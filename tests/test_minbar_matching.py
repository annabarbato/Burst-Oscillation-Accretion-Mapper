import pytest

from burst_oscillation_accretion_mapper.burst_detection import (
    MultiCadenceBurstCandidateSummary,
)
from burst_oscillation_accretion_mapper.minbar_matching import (
    MATCHED,
    MISSING_DETECTION,
    DetectedBurstWindow,
    MinbarBurstWindow,
    MinbarMatchingError,
    detected_windows_from_summaries,
    match_detected_bursts_to_minbar,
    summarize_timing_match_report,
)


def test_detected_window_from_summary_preserves_identity_and_review_state() -> None:
    summary = _summary(start=10.0, peak=12.0, stop=20.0, passed=True)

    detected = DetectedBurstWindow.from_summary(
        source_id="4u_1636_536",
        obs_id="10088-01-07-02",
        candidate_id="candidate-001",
        summary=summary,
    )

    assert detected.source_id == "4u_1636_536"
    assert detected.obs_id == "10088-01-07-02"
    assert detected.candidate_id == "candidate-001"
    assert detected.start == 10.0
    assert detected.peak == 12.0
    assert detected.stop == 20.0
    assert detected.passes_review


def test_detected_windows_from_summaries_assigns_stable_ids() -> None:
    summaries = (
        _summary(start=10.0, peak=12.0, stop=20.0, passed=True),
        _summary(start=30.0, peak=31.0, stop=40.0, passed=False),
    )

    windows = detected_windows_from_summaries(
        source_id="4u_1636_536",
        obs_id="10088-01-07-02",
        summaries=summaries,
        candidate_id_prefix="rxte-10088-review",
        start_index=3,
    )

    assert [window.candidate_id for window in windows] == [
        "rxte-10088-review-0003",
        "rxte-10088-review-0004",
    ]
    assert [window.passes_review for window in windows] == [True, False]


def test_match_detected_bursts_to_minbar_matches_nearest_within_tolerance() -> None:
    expected = (
        MinbarBurstWindow(
            source_id="4u_1636_536",
            obs_id="10088-01-07-02",
            minbar_burst_id="MINBAR.2257",
            start=10.0,
            peak=12.0,
            stop=20.0,
            expected_signal="secure_detection",
        ),
    )
    detections = (
        _detected(candidate_id="far", start=9.0, peak=12.8, stop=20.8),
        _detected(candidate_id="near", start=9.8, peak=12.1, stop=20.2),
    )

    report = match_detected_bursts_to_minbar(
        expected,
        detections,
        tolerance_s=0.5,
    )

    assert report.matched_count == 1
    assert report.missing_count == 0
    assert report.unmatched_detection_count == 1
    match = report.matches[0]
    assert match.status == MATCHED
    assert match.detected is not None
    assert match.detected.candidate_id == "near"
    assert match.start_delta_s == pytest.approx(-0.2)
    assert match.peak_delta_s == pytest.approx(0.1)
    assert match.stop_delta_s == pytest.approx(0.2)
    assert match.max_abs_delta_s == pytest.approx(0.2)
    assert match.overlap_fraction == pytest.approx(1.0)


def test_summarize_timing_match_report_reports_recall_and_review_burden() -> None:
    expected = (
        MinbarBurstWindow(
            source_id="4u_1636_536",
            obs_id="10088-01-07-02",
            minbar_burst_id="MINBAR.2257",
            start=10.0,
            peak=12.0,
            stop=20.0,
        ),
        MinbarBurstWindow(
            source_id="4u_1636_536",
            obs_id="10088-01-07-02",
            minbar_burst_id="MINBAR.2258",
            start=30.0,
            peak=32.0,
            stop=40.0,
        ),
    )
    detections = (
        _detected(candidate_id="matched", start=9.8, peak=12.1, stop=20.2),
        _detected(candidate_id="extra", start=50.0, peak=51.0, stop=60.0),
    )
    report = match_detected_bursts_to_minbar(
        expected,
        detections,
        tolerance_s=0.5,
    )

    metrics = summarize_timing_match_report(report)

    assert metrics == report.metrics
    assert metrics.expected_count == 2
    assert metrics.matched_count == 1
    assert metrics.missing_count == 1
    assert metrics.unmatched_detection_count == 1
    assert metrics.detected_window_count == 2
    assert metrics.recall_fraction == pytest.approx(0.5)
    assert metrics.unmatched_detection_fraction == pytest.approx(0.5)
    assert metrics.max_abs_delta_s == pytest.approx(0.2)
    assert metrics.mean_abs_peak_delta_s == pytest.approx(0.1)


def test_match_detected_bursts_to_minbar_reports_missing_outside_tolerance() -> None:
    expected = (
        MinbarBurstWindow(
            source_id="4u_1728_34",
            obs_id="10073-01-01-00",
            minbar_burst_id="MINBAR.2204",
            start=30.0,
            peak=32.0,
            stop=42.0,
        ),
    )
    detections = (
        DetectedBurstWindow(
            source_id="4u_1728_34",
            obs_id="10073-01-01-00",
            candidate_id="late-candidate",
            start=31.5,
            peak=33.5,
            stop=43.5,
            passes_review=True,
        ),
    )

    report = match_detected_bursts_to_minbar(
        expected,
        detections,
        tolerance_s=0.5,
    )

    assert report.matched_count == 0
    assert report.missing_count == 1
    assert report.unmatched_detection_count == 1
    assert report.matches[0].status == MISSING_DETECTION
    assert report.matches[0].detected is None


def test_match_detected_bursts_to_minbar_does_not_reuse_detection() -> None:
    expected = (
        MinbarBurstWindow(
            source_id="4u_1728_34",
            obs_id="10073-01-01-00",
            minbar_burst_id="MINBAR.2204",
            start=30.0,
            peak=32.0,
            stop=42.0,
        ),
        MinbarBurstWindow(
            source_id="4u_1728_34",
            obs_id="10073-01-01-00",
            minbar_burst_id="MINBAR.2205",
            start=30.2,
            peak=32.2,
            stop=42.2,
        ),
    )
    detections = (
        DetectedBurstWindow(
            source_id="4u_1728_34",
            obs_id="10073-01-01-00",
            candidate_id="single-candidate",
            start=30.1,
            peak=32.1,
            stop=42.1,
            passes_review=True,
        ),
    )

    report = match_detected_bursts_to_minbar(
        expected,
        detections,
        tolerance_s=0.5,
    )

    assert [match.status for match in report.matches] == [
        MATCHED,
        MISSING_DETECTION,
    ]
    assert report.unmatched_detection_count == 0


def test_match_detected_bursts_to_minbar_filters_rejected_reviews_by_default() -> None:
    expected = (
        MinbarBurstWindow(
            source_id="4u_1702_429",
            obs_id="20084-02-01-00",
            minbar_burst_id="MINBAR.2322",
            start=5.0,
            peak=6.0,
            stop=15.0,
        ),
    )
    detections = (
        DetectedBurstWindow(
            source_id="4u_1702_429",
            obs_id="20084-02-01-00",
            candidate_id="rejected-candidate",
            start=5.0,
            peak=6.0,
            stop=15.0,
            passes_review=False,
        ),
    )

    default_report = match_detected_bursts_to_minbar(
        expected,
        detections,
        tolerance_s=0.0,
    )
    inclusive_report = match_detected_bursts_to_minbar(
        expected,
        detections,
        tolerance_s=0.0,
        require_passed_review=False,
    )

    assert default_report.missing_count == 1
    assert default_report.unmatched_detection_count == 0
    assert inclusive_report.matched_count == 1
    assert inclusive_report.matches[0].detected is not None
    assert inclusive_report.matches[0].detected.candidate_id == "rejected-candidate"


def test_match_detected_bursts_to_minbar_ignores_other_obsids() -> None:
    expected = (
        MinbarBurstWindow(
            source_id="ks_1731_260",
            obs_id="30061-01-02-01",
            minbar_burst_id="MINBAR.2431",
            start=5.0,
            peak=6.0,
            stop=15.0,
        ),
    )
    detections = (
        DetectedBurstWindow(
            source_id="ks_1731_260",
            obs_id="different-obsid",
            candidate_id="other-observation",
            start=5.0,
            peak=6.0,
            stop=15.0,
            passes_review=True,
        ),
    )

    report = match_detected_bursts_to_minbar(
        expected,
        detections,
        tolerance_s=0.0,
    )

    assert report.missing_count == 1
    assert report.unmatched_detection_count == 1


def test_minbar_matching_validates_windows_and_tolerance() -> None:
    with pytest.raises(MinbarMatchingError, match="MINBAR window"):
        MinbarBurstWindow(
            source_id="source",
            obs_id="obs",
            minbar_burst_id="MINBAR.1",
            start=2.0,
            peak=1.0,
            stop=3.0,
        )

    with pytest.raises(MinbarMatchingError, match="Invalid tolerance"):
        match_detected_bursts_to_minbar((), (), tolerance_s=-1.0)

    with pytest.raises(MinbarMatchingError, match="start_index"):
        detected_windows_from_summaries(
            source_id="source",
            obs_id="obs",
            summaries=(),
            candidate_id_prefix="candidate",
            start_index=-1,
        )


def _detected(
    candidate_id: str, start: float, peak: float, stop: float
) -> DetectedBurstWindow:
    return DetectedBurstWindow(
        source_id="4u_1636_536",
        obs_id="10088-01-07-02",
        candidate_id=candidate_id,
        start=start,
        peak=peak,
        stop=stop,
        passes_review=True,
    )


def _summary(
    *,
    start: float,
    peak: float,
    stop: float,
    passed: bool,
) -> MultiCadenceBurstCandidateSummary:
    return MultiCadenceBurstCandidateSummary(
        start=start,
        peak_time=peak,
        stop=stop,
        duration=stop - start,
        bin_sizes=(0.5, 1.0),
        best_bin_size=1.0,
        review_count=2,
        passed_review_count=1 if passed else 0,
        best_peak_score=5.0,
        best_excess_counts=12.0,
        total_counts=20,
        total_expected_counts=8.0,
        rejection_reasons=() if passed else ("peak_score_below_threshold",),
    )
