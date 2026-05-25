import pytest

from burst_oscillation_accretion_mapper.burst_detection import (
    MultiCadenceBurstCandidateSummary,
)
from burst_oscillation_accretion_mapper.candidate_scoring import (
    MARGINAL_CANDIDATE,
    NON_DETECTION,
    PROBABLE_DETECTION,
    SECURE_DETECTION,
    OscillationCandidateReview,
)
from burst_oscillation_accretion_mapper.catalog_writer import (
    BurstCatalogWriteContext,
    CandidateCatalogWriteContext,
    ControlCatalogWriteContext,
    burst_catalog_row_from_summary,
    candidate_catalog_row_from_review,
    control_catalog_row_from_review,
)
from burst_oscillation_accretion_mapper.control_intervals import (
    PRE_BURST_CONTROL,
    ControlReview,
    ControlWindow,
)
from burst_oscillation_accretion_mapper.minbar_matching import (
    BurstTimingValidationMetrics,
)
from burst_oscillation_accretion_mapper.phase1_validation import (
    Phase1ValidationError,
    Phase1ValidationGatePolicy,
    review_phase1_validation_gate,
    summarize_phase1_validation_catalog,
)
from burst_oscillation_accretion_mapper.time_intervals import TimeInterval


def test_summarize_phase1_validation_catalog_counts_review_products() -> None:
    summary = summarize_phase1_validation_catalog(
        burst_rows=(_burst_row(),),
        candidate_rows=(
            _candidate_row("candidate-001", PROBABLE_DETECTION),
            _candidate_row("candidate-002", MARGINAL_CANDIDATE),
            _candidate_row("candidate-003", NON_DETECTION),
        ),
        control_rows=(
            _control_row("control-001", NON_DETECTION),
            _control_row("control-002", MARGINAL_CANDIDATE),
        ),
        timing_metrics=_timing_metrics(),
    )

    assert summary.burst_count == 1
    assert summary.minbar_linked_burst_count == 1
    assert summary.candidate_count == 3
    assert summary.probable_count == 1
    assert summary.marginal_count == 1
    assert summary.non_detection_count == 1
    assert summary.detection_like_count == 2
    assert summary.control_count == 2
    assert summary.control_marginal_count == 1
    assert summary.control_non_detection_count == 1
    assert summary.control_detection_like_count == 1
    assert summary.control_false_alarm_fraction == pytest.approx(0.5)
    assert summary.has_minbar_timing_metrics
    assert summary.minbar_recall_fraction == pytest.approx(1.0)


def test_review_phase1_validation_gate_passes_complete_artifacts() -> None:
    summary = summarize_phase1_validation_catalog(
        burst_rows=(_burst_row(),),
        candidate_rows=(
            _candidate_row("candidate-001", PROBABLE_DETECTION),
            _candidate_row("candidate-002", NON_DETECTION),
        ),
        control_rows=(_control_row("control-001", NON_DETECTION),),
        timing_metrics=_timing_metrics(),
    )

    review = review_phase1_validation_gate(
        summary,
        policy=Phase1ValidationGatePolicy(
            max_control_false_alarm_fraction=0.0,
            min_minbar_recall_fraction=0.9,
        ),
    )

    assert review.passed
    assert review.reasons == ()


def test_review_phase1_validation_gate_reports_missing_artifacts() -> None:
    summary = summarize_phase1_validation_catalog(
        burst_rows=(),
        candidate_rows=(),
        control_rows=(),
    )

    review = review_phase1_validation_gate(summary)

    assert not review.passed
    assert review.reasons == (
        "no_burst_rows",
        "no_candidate_rows",
        "no_non_detection_rows",
        "no_control_rows",
        "no_minbar_timing_metrics",
    )


def test_review_phase1_validation_gate_flags_control_and_recall_failures() -> None:
    summary = summarize_phase1_validation_catalog(
        burst_rows=(_burst_row(),),
        candidate_rows=(_candidate_row("candidate-001", NON_DETECTION),),
        control_rows=(_control_row("control-001", SECURE_DETECTION),),
        timing_metrics=BurstTimingValidationMetrics(
            expected_count=2,
            matched_count=1,
            missing_count=1,
            unmatched_detection_count=0,
            detected_window_count=1,
            recall_fraction=0.5,
            unmatched_detection_fraction=0.0,
            max_abs_delta_s=0.1,
            mean_abs_peak_delta_s=0.1,
        ),
    )

    review = review_phase1_validation_gate(
        summary,
        policy=Phase1ValidationGatePolicy(
            max_secure_control_count=0,
            max_control_false_alarm_fraction=0.0,
            min_minbar_recall_fraction=0.9,
        ),
    )

    assert not review.passed
    assert review.reasons == (
        "secure_control_count_exceeds_policy",
        "control_false_alarm_fraction_exceeds_policy",
        "minbar_recall_below_policy",
    )


def test_review_phase1_validation_gate_can_reject_probable_controls() -> None:
    summary = summarize_phase1_validation_catalog(
        burst_rows=(_burst_row(),),
        candidate_rows=(_candidate_row("candidate-001", NON_DETECTION),),
        control_rows=(_control_row("control-001", PROBABLE_DETECTION),),
        timing_metrics=_timing_metrics(),
    )

    review = review_phase1_validation_gate(
        summary,
        policy=Phase1ValidationGatePolicy(max_probable_control_count=0),
    )

    assert not review.passed
    assert review.reasons == ("probable_control_count_exceeds_policy",)


def test_phase1_validation_policy_validates_probability_thresholds() -> None:
    with pytest.raises(Phase1ValidationError, match="max_control_false_alarm_fraction"):
        Phase1ValidationGatePolicy(max_control_false_alarm_fraction=1.1)

    with pytest.raises(Phase1ValidationError, match="min_minbar_recall_fraction"):
        Phase1ValidationGatePolicy(min_minbar_recall_fraction=-0.1)


def _burst_row():
    return burst_catalog_row_from_summary(
        MultiCadenceBurstCandidateSummary(
            start=10.0,
            peak_time=12.0,
            stop=20.0,
            duration=10.0,
            bin_sizes=(0.25, 1.0),
            best_bin_size=0.25,
            review_count=2,
            passed_review_count=1,
            best_peak_score=7.5,
            best_excess_counts=42.0,
            total_counts=100,
            total_expected_counts=58.0,
            rejection_reasons=(),
        ),
        context=BurstCatalogWriteContext(
            burst_id="burst-001",
            source_id="source",
            obs_id="obs",
            instrument="RXTE/PCA",
            pipeline_version="phase1-test",
            detection_config_id="multi-cadence-default",
            minbar_burst_id="MINBAR.2257",
        ),
    )


def _candidate_row(candidate_id: str, classification: str):
    return candidate_catalog_row_from_review(
        _candidate_review(classification),
        context=CandidateCatalogWriteContext(
            candidate_id=candidate_id,
            burst_id="burst-001",
            pipeline_version="phase1-test",
            search_config_id="targeted",
        ),
    )


def _control_row(control_id: str, classification: str):
    return control_catalog_row_from_review(
        ControlReview(
            control=ControlWindow(
                control_id=control_id,
                kind=PRE_BURST_CONTROL,
                interval=TimeInterval(0.0, 1.0),
                requested_interval=TimeInterval(0.0, 1.0),
                burst_id="burst-001",
            ),
            review=_candidate_review(classification),
        ),
        context=ControlCatalogWriteContext(
            pipeline_version="phase1-test",
            search_config_id="targeted",
        ),
    )


def _candidate_review(classification: str) -> OscillationCandidateReview:
    is_detection = classification != NON_DETECTION
    return OscillationCandidateReview(
        source_id="source",
        obs_id="obs",
        instrument="RXTE/PCA",
        search_mode="targeted_known_frequency",
        classification=classification,
        trial_count=5 if is_detection else 0,
        photon_count=20 if is_detection else 0,
        window=TimeInterval(10.0, 12.0) if is_detection else None,
        frequency_hz=581.0 if is_detection else None,
        expected_frequency_hz=581.0,
        frequency_offset_hz=0.0 if is_detection else None,
        z2_power=42.0 if is_detection else None,
        leahy_power=40.0 if is_detection else None,
        n_harmonics=1 if is_detection else None,
        fractional_rms=0.12 if is_detection else None,
        phase_rad=1.25 if is_detection else None,
        reasons=() if is_detection else ("no_searched_windows",),
    )


def _timing_metrics() -> BurstTimingValidationMetrics:
    return BurstTimingValidationMetrics(
        expected_count=1,
        matched_count=1,
        missing_count=0,
        unmatched_detection_count=0,
        detected_window_count=1,
        recall_fraction=1.0,
        unmatched_detection_fraction=0.0,
        max_abs_delta_s=0.1,
        mean_abs_peak_delta_s=0.1,
    )
