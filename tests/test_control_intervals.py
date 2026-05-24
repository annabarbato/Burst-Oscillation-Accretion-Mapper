import pytest

from burst_oscillation_accretion_mapper.candidate_scoring import (
    MARGINAL_CANDIDATE,
    NON_DETECTION,
    PROBABLE_DETECTION,
    SECURE_DETECTION,
    OscillationCandidateReview,
)
from burst_oscillation_accretion_mapper.control_intervals import (
    NEIGHBORING_POST_BURST_CONTROL,
    NEIGHBORING_PRE_BURST_CONTROL,
    POST_BURST_CONTROL,
    PRE_BURST_CONTROL,
    ControlIntervalError,
    ControlReview,
    NeighboringControlWindowConfig,
    ControlWindowConfig,
    build_neighboring_non_burst_control_windows,
    build_pre_post_control_windows,
    summarize_control_reviews,
)
from burst_oscillation_accretion_mapper.time_intervals import TimeInterval


def test_build_pre_post_control_windows_clips_to_gtis() -> None:
    controls = build_pre_post_control_windows(
        burst_window=TimeInterval(100.0, 110.0),
        good_time_intervals=(TimeInterval(0.0, 200.0),),
        config=ControlWindowConfig(
            pre_duration_s=20.0,
            post_duration_s=20.0,
            pre_gap_s=5.0,
            post_gap_s=5.0,
        ),
        burst_id="burst-001",
    )

    assert [control.control_id for control in controls] == [
        "burst-001_pre_burst_001",
        "burst-001_post_burst_001",
    ]
    assert [control.kind for control in controls] == [
        PRE_BURST_CONTROL,
        POST_BURST_CONTROL,
    ]
    assert [control.interval for control in controls] == [
        TimeInterval(75.0, 95.0),
        TimeInterval(115.0, 135.0),
    ]
    assert [control.requested_interval for control in controls] == [
        TimeInterval(75.0, 95.0),
        TimeInterval(115.0, 135.0),
    ]
    assert [control.duration for control in controls] == [20.0, 20.0]


def test_build_pre_post_control_windows_splits_around_gti_gaps() -> None:
    controls = build_pre_post_control_windows(
        burst_window=TimeInterval(100.0, 110.0),
        good_time_intervals=(
            TimeInterval(70.0, 80.0),
            TimeInterval(90.0, 120.0),
        ),
        config=ControlWindowConfig(pre_duration_s=30.0, post_duration_s=0.0),
        burst_id="burst-002",
    )

    assert [control.control_id for control in controls] == [
        "burst-002_pre_burst_001",
        "burst-002_pre_burst_002",
    ]
    assert [control.interval for control in controls] == [
        TimeInterval(70.0, 80.0),
        TimeInterval(90.0, 100.0),
    ]
    assert all(
        control.requested_interval == TimeInterval(70.0, 100.0)
        for control in controls
    )


def test_build_pre_post_control_windows_omits_uncovered_requests() -> None:
    controls = build_pre_post_control_windows(
        burst_window=TimeInterval(100.0, 110.0),
        good_time_intervals=(TimeInterval(100.0, 200.0),),
        config=ControlWindowConfig(pre_duration_s=20.0, post_duration_s=10.0),
    )

    assert [control.kind for control in controls] == [POST_BURST_CONTROL]
    assert controls[0].control_id == "control_post_burst_001"
    assert controls[0].interval == TimeInterval(110.0, 120.0)


def test_build_neighboring_non_burst_control_windows_excludes_known_bursts() -> None:
    controls = build_neighboring_non_burst_control_windows(
        burst_window=TimeInterval(100.0, 110.0),
        good_time_intervals=(TimeInterval(0.0, 200.0),),
        excluded_intervals=(
            TimeInterval(80.0, 90.0),
            TimeInterval(120.0, 125.0),
        ),
        config=NeighboringControlWindowConfig(
            window_duration_s=30.0,
            max_windows_before=1,
            max_windows_after=1,
        ),
        burst_id="burst-003",
    )

    assert [control.control_id for control in controls] == [
        "burst-003_neighboring_non_burst_before_001",
        "burst-003_neighboring_non_burst_before_002",
        "burst-003_neighboring_non_burst_after_001",
        "burst-003_neighboring_non_burst_after_002",
    ]
    assert [control.kind for control in controls] == [
        NEIGHBORING_PRE_BURST_CONTROL,
        NEIGHBORING_PRE_BURST_CONTROL,
        NEIGHBORING_POST_BURST_CONTROL,
        NEIGHBORING_POST_BURST_CONTROL,
    ]
    assert [control.interval for control in controls] == [
        TimeInterval(70.0, 80.0),
        TimeInterval(90.0, 100.0),
        TimeInterval(110.0, 120.0),
        TimeInterval(125.0, 140.0),
    ]
    assert [control.requested_interval for control in controls] == [
        TimeInterval(70.0, 100.0),
        TimeInterval(70.0, 100.0),
        TimeInterval(110.0, 140.0),
        TimeInterval(110.0, 140.0),
    ]


def test_build_neighboring_non_burst_control_windows_uses_multiple_neighbors_and_gtis() -> None:
    controls = build_neighboring_non_burst_control_windows(
        burst_window=TimeInterval(100.0, 110.0),
        good_time_intervals=(
            TimeInterval(45.0, 95.0),
            TimeInterval(115.0, 170.0),
        ),
        excluded_intervals=(),
        config=NeighboringControlWindowConfig(
            window_duration_s=20.0,
            max_windows_before=2,
            max_windows_after=2,
            gap_s=5.0,
        ),
        burst_id="burst-004",
    )

    assert [control.interval for control in controls] == [
        TimeInterval(75.0, 95.0),
        TimeInterval(55.0, 75.0),
        TimeInterval(115.0, 135.0),
        TimeInterval(135.0, 155.0),
    ]
    assert [control.kind for control in controls] == [
        NEIGHBORING_PRE_BURST_CONTROL,
        NEIGHBORING_PRE_BURST_CONTROL,
        NEIGHBORING_POST_BURST_CONTROL,
        NEIGHBORING_POST_BURST_CONTROL,
    ]


def test_build_neighboring_non_burst_control_windows_omits_fully_excluded_requests() -> None:
    controls = build_neighboring_non_burst_control_windows(
        burst_window=TimeInterval(100.0, 110.0),
        good_time_intervals=(TimeInterval(0.0, 200.0),),
        excluded_intervals=(TimeInterval(70.0, 100.0),),
        config=NeighboringControlWindowConfig(
            window_duration_s=30.0,
            max_windows_before=1,
            max_windows_after=0,
        ),
    )

    assert controls == ()


def test_control_window_config_validates_inputs() -> None:
    with pytest.raises(ControlIntervalError, match="pre_duration_s"):
        ControlWindowConfig(pre_duration_s=-1.0, post_duration_s=10.0)

    with pytest.raises(ControlIntervalError, match="post_gap_s"):
        ControlWindowConfig(
            pre_duration_s=10.0,
            post_duration_s=10.0,
            post_gap_s=-1.0,
        )

    with pytest.raises(ControlIntervalError, match="At least one"):
        ControlWindowConfig(pre_duration_s=0.0, post_duration_s=0.0)


def test_neighboring_control_window_config_validates_inputs() -> None:
    with pytest.raises(ControlIntervalError, match="window_duration_s"):
        NeighboringControlWindowConfig(window_duration_s=0.0)

    with pytest.raises(ControlIntervalError, match="max_windows_before"):
        NeighboringControlWindowConfig(
            window_duration_s=10.0,
            max_windows_before=-1,
        )

    with pytest.raises(ControlIntervalError, match="At least one"):
        NeighboringControlWindowConfig(
            window_duration_s=10.0,
            max_windows_before=0,
            max_windows_after=0,
        )


def test_summarize_control_reviews_counts_detection_like_reviews() -> None:
    control = build_pre_post_control_windows(
        burst_window=TimeInterval(100.0, 110.0),
        good_time_intervals=(TimeInterval(0.0, 200.0),),
        config=ControlWindowConfig(pre_duration_s=10.0, post_duration_s=10.0),
    )[0]
    reviews = tuple(
        ControlReview(control=control, review=_review(classification))
        for classification in (
            SECURE_DETECTION,
            PROBABLE_DETECTION,
            MARGINAL_CANDIDATE,
            NON_DETECTION,
        )
    )

    summary = summarize_control_reviews(reviews)

    assert summary.control_count == 4
    assert summary.secure_count == 1
    assert summary.probable_count == 1
    assert summary.marginal_count == 1
    assert summary.non_detection_count == 1
    assert summary.detection_like_count == 3
    assert summary.false_alarm_fraction == pytest.approx(0.75)


def test_summarize_control_reviews_handles_empty_inputs() -> None:
    summary = summarize_control_reviews(())

    assert summary.control_count == 0
    assert summary.detection_like_count == 0
    assert summary.false_alarm_fraction is None


def _review(classification: str) -> OscillationCandidateReview:
    return OscillationCandidateReview(
        source_id="source",
        obs_id="obs",
        instrument="RXTE/PCA",
        search_mode="targeted_known_frequency",
        classification=classification,
        trial_count=3,
        photon_count=10,
        window=TimeInterval(0.0, 1.0),
        frequency_hz=581.0,
        expected_frequency_hz=581.0,
        frequency_offset_hz=0.0,
        z2_power=20.0,
        n_harmonics=1,
        fractional_rms=0.1,
        phase_rad=0.0,
        reasons=(),
    )
