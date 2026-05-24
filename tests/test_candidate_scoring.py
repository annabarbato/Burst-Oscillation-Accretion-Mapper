import math

import pytest

from burst_oscillation_accretion_mapper.candidate_scoring import (
    MARGINAL_CANDIDATE,
    NON_DETECTION,
    PROBABLE_DETECTION,
    SECURE_DETECTION,
    CandidateEvidenceFlags,
    CandidateScoringConfig,
    CandidateScoringError,
    score_sliding_targeted_z2_result,
    score_targeted_z2_result,
)
from burst_oscillation_accretion_mapper.event_products import EventProduct
from burst_oscillation_accretion_mapper.oscillation_search import (
    SlidingWindowConfig,
    TargetedFrequencyGrid,
    TargetedZ2SearchConfig,
    search_event_product_sliding_targeted_z2,
    search_event_product_targeted_z2,
)
from burst_oscillation_accretion_mapper.time_intervals import TimeInterval


def test_score_targeted_z2_result_keeps_strong_candidate_probable_without_later_evidence() -> None:
    review = score_targeted_z2_result(
        _single_window_search_result(),
        config=CandidateScoringConfig(
            marginal_z2_threshold=5.0,
            probable_z2_threshold=10.0,
            secure_z2_threshold=15.0,
            max_frequency_offset_hz=0.5,
        ),
        expected_frequency_hz=10.0,
    )

    assert review.classification == PROBABLE_DETECTION
    assert review.is_detection_like
    assert review.frequency_hz == 10.0
    assert review.frequency_offset_hz == 0.0
    assert review.z2_power == pytest.approx(20.0)
    assert review.fractional_rms == pytest.approx(math.sqrt(2.0))
    assert review.phase_rad == pytest.approx(0.0, abs=1e-12)
    assert review.trial_count == 3
    assert review.reasons == (
        "control_clearance_missing",
        "sensitivity_confirmation_missing",
        "coherent_structure_missing",
        "phase_evolution_check_missing",
    )


def test_score_targeted_z2_result_allows_secure_only_with_explicit_evidence() -> None:
    review = score_targeted_z2_result(
        _single_window_search_result(),
        config=CandidateScoringConfig(
            marginal_z2_threshold=5.0,
            probable_z2_threshold=10.0,
            secure_z2_threshold=15.0,
            max_frequency_offset_hz=0.5,
        ),
        expected_frequency_hz=10.0,
        evidence=CandidateEvidenceFlags(
            control_clearance=True,
            sensitivity_confirmed=True,
            coherent_structure=True,
            phase_evolution_ok=True,
        ),
    )

    assert review.classification == SECURE_DETECTION
    assert review.reasons == ()


def test_score_targeted_z2_result_marks_below_probable_as_marginal() -> None:
    review = score_targeted_z2_result(
        _single_window_search_result(),
        config=CandidateScoringConfig(
            marginal_z2_threshold=5.0,
            probable_z2_threshold=30.0,
            secure_z2_threshold=40.0,
            max_frequency_offset_hz=0.5,
        ),
        expected_frequency_hz=10.0,
    )

    assert review.classification == MARGINAL_CANDIDATE
    assert review.reasons == ("z2_below_probable_threshold",)


def test_score_targeted_z2_result_marks_below_marginal_as_non_detection() -> None:
    review = score_targeted_z2_result(
        _single_window_search_result(),
        config=CandidateScoringConfig(
            marginal_z2_threshold=25.0,
            probable_z2_threshold=30.0,
            secure_z2_threshold=40.0,
        ),
        expected_frequency_hz=10.0,
    )

    assert review.classification == NON_DETECTION
    assert not review.is_detection_like
    assert review.reasons == ("z2_below_marginal_threshold",)


def test_score_targeted_z2_result_demotes_frequency_mismatch_to_marginal() -> None:
    review = score_targeted_z2_result(
        _single_window_search_result(),
        config=CandidateScoringConfig(
            marginal_z2_threshold=5.0,
            probable_z2_threshold=10.0,
            secure_z2_threshold=15.0,
            max_frequency_offset_hz=0.5,
        ),
        expected_frequency_hz=12.0,
    )

    assert review.classification == MARGINAL_CANDIDATE
    assert review.frequency_offset_hz == 2.0
    assert "frequency_offset_above_threshold" in review.reasons


def test_score_sliding_targeted_z2_result_uses_best_window_and_total_trials() -> None:
    result = search_event_product_sliding_targeted_z2(
        _phase_aligned_product(),
        interval=TimeInterval(0.0, 1.0),
        window_config=SlidingWindowConfig(window_size_s=0.5, step_s=0.5),
        search_config=_search_config(),
    )

    review = score_sliding_targeted_z2_result(
        result,
        config=CandidateScoringConfig(
            marginal_z2_threshold=5.0,
            probable_z2_threshold=8.0,
            secure_z2_threshold=15.0,
        ),
        expected_frequency_hz=10.0,
    )

    assert review.classification == PROBABLE_DETECTION
    assert review.window == TimeInterval(0.0, 0.5)
    assert review.trial_count == 6
    assert review.photon_count == 5


def test_score_sliding_targeted_z2_result_records_empty_non_detection() -> None:
    product = EventProduct(
        source_id="source",
        obs_id="obs",
        instrument="RXTE/PCA",
        times=(),
        gtis=(TimeInterval(0.0, 1.0),),
    )
    result = search_event_product_sliding_targeted_z2(
        product,
        interval=TimeInterval(0.0, 1.0),
        window_config=SlidingWindowConfig(window_size_s=1.0, step_s=1.0),
        search_config=TargetedZ2SearchConfig(
            frequency_grid=TargetedFrequencyGrid(
                center_hz=10.0,
                half_width_hz=0.0,
                step_hz=1.0,
            ),
            min_photons=1,
        ),
    )

    review = score_sliding_targeted_z2_result(
        result,
        config=CandidateScoringConfig(
            marginal_z2_threshold=5.0,
            probable_z2_threshold=10.0,
            secure_z2_threshold=15.0,
        ),
        expected_frequency_hz=10.0,
    )

    assert review.classification == NON_DETECTION
    assert review.window is None
    assert review.frequency_hz is None
    assert review.trial_count == 0
    assert review.reasons == ("no_searched_windows",)


def test_candidate_scoring_config_validates_thresholds() -> None:
    with pytest.raises(CandidateScoringError, match="positive"):
        CandidateScoringConfig(
            marginal_z2_threshold=0.0,
            probable_z2_threshold=10.0,
            secure_z2_threshold=15.0,
        )

    with pytest.raises(CandidateScoringError, match="marginal <= probable <= secure"):
        CandidateScoringConfig(
            marginal_z2_threshold=20.0,
            probable_z2_threshold=10.0,
            secure_z2_threshold=15.0,
        )

    with pytest.raises(CandidateScoringError, match="max_frequency_offset_hz"):
        CandidateScoringConfig(
            marginal_z2_threshold=5.0,
            probable_z2_threshold=10.0,
            secure_z2_threshold=15.0,
            max_frequency_offset_hz=-1.0,
        )


def _single_window_search_result():
    return search_event_product_targeted_z2(
        _phase_aligned_product(),
        window=TimeInterval(0.0, 1.0),
        config=_search_config(),
    )


def _search_config() -> TargetedZ2SearchConfig:
    return TargetedZ2SearchConfig(
        frequency_grid=TargetedFrequencyGrid(
            center_hz=10.0,
            half_width_hz=1.0,
            step_hz=1.0,
        ),
        min_photons=5,
    )


def _phase_aligned_product() -> EventProduct:
    return EventProduct(
        source_id="source",
        obs_id="obs",
        instrument="RXTE/PCA",
        times=tuple(index * 0.1 for index in range(10)),
        gtis=(TimeInterval(0.0, 1.0),),
    )
