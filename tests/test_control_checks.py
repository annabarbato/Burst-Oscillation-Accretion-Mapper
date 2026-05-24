import pytest

from burst_oscillation_accretion_mapper.candidate_scoring import (
    NON_DETECTION,
    PROBABLE_DETECTION,
    CandidateEvidenceFlags,
    CandidateScoringConfig,
)
from burst_oscillation_accretion_mapper.control_checks import (
    ControlCheckError,
    ControlClearancePolicy,
    build_search_and_score_pre_post_controls,
    evaluate_control_clearance,
    evidence_with_control_clearance,
    search_and_score_control_windows,
)
from burst_oscillation_accretion_mapper.control_intervals import (
    POST_BURST_CONTROL,
    PRE_BURST_CONTROL,
    ControlWindowConfig,
    build_pre_post_control_windows,
)
from burst_oscillation_accretion_mapper.event_products import EventProduct
from burst_oscillation_accretion_mapper.oscillation_search import (
    SlidingWindowConfig,
    TargetedFrequencyGrid,
    TargetedZ2SearchConfig,
)
from burst_oscillation_accretion_mapper.time_intervals import TimeInterval


def test_build_search_and_score_pre_post_controls_summarizes_false_alarm() -> None:
    run = build_search_and_score_pre_post_controls(
        _pre_control_phase_aligned_product(),
        burst_window=TimeInterval(10.0, 11.0),
        control_config=ControlWindowConfig(pre_duration_s=1.0, post_duration_s=1.0),
        window_config=SlidingWindowConfig(window_size_s=1.0, step_s=1.0),
        search_config=_search_config(),
        scoring_config=_scoring_config(),
        expected_frequency_hz=10.0,
        burst_id="burst-001",
    )

    assert [control.kind for control in run.controls] == [
        PRE_BURST_CONTROL,
        POST_BURST_CONTROL,
    ]
    assert [control.control_id for control in run.controls] == [
        "burst-001_pre_burst_001",
        "burst-001_post_burst_001",
    ]
    assert [review.classification for review in run.reviews] == [
        PROBABLE_DETECTION,
        NON_DETECTION,
    ]
    assert run.reviews[0].window == TimeInterval(9.0, 10.0)
    assert run.reviews[0].frequency_hz == pytest.approx(10.0)
    assert run.reviews[0].z2_power == pytest.approx(20.0)
    assert run.reviews[1].window is None
    assert run.reviews[1].reasons == ("no_searched_windows",)
    assert run.summary.control_count == 2
    assert run.summary.detection_like_count == 1
    assert run.summary.probable_count == 1
    assert run.summary.non_detection_count == 1
    assert run.summary.false_alarm_fraction == pytest.approx(0.5)
    assert run.has_detection_like_controls


def test_evaluate_control_clearance_fails_default_policy_on_detection_like_controls() -> None:
    run = build_search_and_score_pre_post_controls(
        _pre_control_phase_aligned_product(),
        burst_window=TimeInterval(10.0, 11.0),
        control_config=ControlWindowConfig(pre_duration_s=1.0, post_duration_s=1.0),
        window_config=SlidingWindowConfig(window_size_s=1.0, step_s=1.0),
        search_config=_search_config(),
        scoring_config=_scoring_config(),
        expected_frequency_hz=10.0,
    )

    clearance = evaluate_control_clearance(run)

    assert not clearance.passed
    assert clearance.summary.probable_count == 1
    assert clearance.reasons == ("probable_control_count_exceeds_policy",)


def test_evaluate_control_clearance_accepts_explicit_relaxed_policy() -> None:
    run = build_search_and_score_pre_post_controls(
        _pre_control_phase_aligned_product(),
        burst_window=TimeInterval(10.0, 11.0),
        control_config=ControlWindowConfig(pre_duration_s=1.0, post_duration_s=1.0),
        window_config=SlidingWindowConfig(window_size_s=1.0, step_s=1.0),
        search_config=_search_config(),
        scoring_config=_scoring_config(),
        expected_frequency_hz=10.0,
    )

    clearance = evaluate_control_clearance(
        run,
        policy=ControlClearancePolicy(
            max_probable_count=1,
            max_false_alarm_fraction=0.5,
        ),
    )

    assert clearance.passed
    assert clearance.reasons == ()
    assert clearance.policy.max_probable_count == 1


def test_search_and_score_control_windows_accepts_empty_control_set() -> None:
    run = search_and_score_control_windows(
        _pre_control_phase_aligned_product(),
        controls=(),
        window_config=SlidingWindowConfig(window_size_s=1.0, step_s=1.0),
        search_config=_search_config(),
        scoring_config=_scoring_config(),
        expected_frequency_hz=10.0,
    )

    assert run.controls == ()
    assert run.reviews == ()
    assert run.summary.control_count == 0
    assert run.summary.false_alarm_fraction is None
    assert not run.has_detection_like_controls


def test_evaluate_control_clearance_requires_controls_by_default() -> None:
    run = search_and_score_control_windows(
        _pre_control_phase_aligned_product(),
        controls=(),
        window_config=SlidingWindowConfig(window_size_s=1.0, step_s=1.0),
        search_config=_search_config(),
        scoring_config=_scoring_config(),
        expected_frequency_hz=10.0,
    )

    clearance = evaluate_control_clearance(run)

    assert not clearance.passed
    assert clearance.reasons == ("no_controls_available",)


def test_search_and_score_control_windows_preserves_supplied_controls() -> None:
    controls = build_pre_post_control_windows(
        burst_window=TimeInterval(10.0, 11.0),
        good_time_intervals=(TimeInterval(0.0, 20.0),),
        config=ControlWindowConfig(pre_duration_s=1.0, post_duration_s=0.0),
        burst_id="burst-002",
    )

    run = search_and_score_control_windows(
        _pre_control_phase_aligned_product(),
        controls=controls,
        window_config=SlidingWindowConfig(window_size_s=1.0, step_s=1.0),
        search_config=_search_config(),
        scoring_config=_scoring_config(),
        expected_frequency_hz=10.0,
    )

    assert run.controls == controls
    assert run.control_reviews[0].control.control_id == "burst-002_pre_burst_001"
    assert run.reviews[0].classification == PROBABLE_DETECTION
    assert run.summary.detection_like_count == 1


def test_evidence_with_control_clearance_preserves_other_evidence_flags() -> None:
    run = search_and_score_control_windows(
        _pre_control_phase_aligned_product(),
        controls=(),
        window_config=SlidingWindowConfig(window_size_s=1.0, step_s=1.0),
        search_config=_search_config(),
        scoring_config=_scoring_config(),
        expected_frequency_hz=10.0,
    )
    clearance = evaluate_control_clearance(
        run,
        policy=ControlClearancePolicy(require_controls=False),
    )

    evidence = evidence_with_control_clearance(
        CandidateEvidenceFlags(
            physically_plausible_phase=False,
            control_clearance=False,
            sensitivity_confirmed=True,
            coherent_structure=True,
            phase_evolution_ok=True,
        ),
        clearance,
    )

    assert evidence.physically_plausible_phase is False
    assert evidence.control_clearance is True
    assert evidence.sensitivity_confirmed is True
    assert evidence.coherent_structure is True
    assert evidence.phase_evolution_ok is True


def test_control_clearance_policy_validates_inputs() -> None:
    with pytest.raises(ControlCheckError, match="max_secure_count"):
        ControlClearancePolicy(max_secure_count=-1)

    with pytest.raises(ControlCheckError, match="max_false_alarm_fraction"):
        ControlClearancePolicy(max_false_alarm_fraction=1.1)


def _pre_control_phase_aligned_product() -> EventProduct:
    return EventProduct(
        source_id="source",
        obs_id="obs",
        instrument="RXTE/PCA",
        times=tuple(9.0 + index * 0.1 for index in range(10)),
        gtis=(TimeInterval(0.0, 20.0),),
    )


def _search_config() -> TargetedZ2SearchConfig:
    return TargetedZ2SearchConfig(
        frequency_grid=TargetedFrequencyGrid(
            center_hz=10.0,
            half_width_hz=0.0,
            step_hz=1.0,
        ),
        min_photons=5,
    )


def _scoring_config() -> CandidateScoringConfig:
    return CandidateScoringConfig(
        marginal_z2_threshold=5.0,
        probable_z2_threshold=10.0,
        secure_z2_threshold=30.0,
        max_frequency_offset_hz=0.5,
    )
