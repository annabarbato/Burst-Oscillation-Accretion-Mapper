import math

import pytest

from burst_oscillation_accretion_mapper.burst_detection import (
    BurstDetectionConfig,
    BurstDetectionError,
    BurstIntervalCandidate,
    MorphologyReviewConfig,
    find_burst_interval_reviews,
    group_excess_bins,
    review_candidate_morphology,
    score_light_curve_excess,
    signed_poisson_sqrt_deviance,
    summarize_candidate_morphology,
)
from burst_oscillation_accretion_mapper.event_products import EventProduct
from burst_oscillation_accretion_mapper.lightcurves import (
    estimate_rolling_baseline,
    make_light_curve,
)
from burst_oscillation_accretion_mapper.time_intervals import TimeInterval


def test_signed_poisson_sqrt_deviance_is_positive_for_excess() -> None:
    score = signed_poisson_sqrt_deviance(20, 10.0)

    expected = math.sqrt(2.0 * (20.0 * math.log(2.0) - 10.0))
    assert score == pytest.approx(expected)


def test_signed_poisson_sqrt_deviance_is_negative_for_deficit() -> None:
    score = signed_poisson_sqrt_deviance(5, 10.0)

    expected = -math.sqrt(2.0 * (5.0 * math.log(0.5) + 5.0))
    assert score == pytest.approx(expected)


def test_signed_poisson_sqrt_deviance_rejects_invalid_expected_counts() -> None:
    with pytest.raises(BurstDetectionError, match="expected_counts"):
        signed_poisson_sqrt_deviance(1, 0.0)


def test_score_light_curve_excess_keeps_unscored_zero_exposure_bins() -> None:
    product = EventProduct(
        source_id="source",
        obs_id="obs",
        instrument="RXTE/PCA",
        times=(0.25, 2.25),
        gtis=(TimeInterval(0.0, 1.0), TimeInterval(2.0, 3.0)),
    )
    light_curve = make_light_curve(
        product, interval=TimeInterval(0.0, 3.0), bin_size=1.0
    )
    baseline = estimate_rolling_baseline(light_curve, window_bins=1)

    scores = score_light_curve_excess(light_curve, baseline)

    assert scores[0].expected_counts == 1.0
    assert scores[1].expected_counts is None
    assert scores[1].signed_sqrt_deviance is None
    assert scores[2].expected_counts == 1.0


def test_group_excess_bins_returns_adjacent_interval_candidates() -> None:
    product = EventProduct(
        source_id="source",
        obs_id="obs",
        instrument="RXTE/PCA",
        times=(
            0.1,
            1.1,
            2.1,
            2.2,
            2.3,
            2.4,
            2.5,
            2.6,
            2.7,
            2.8,
            2.9,
            3.1,
            4.1,
        ),
        gtis=(TimeInterval(0.0, 5.0),),
    )
    light_curve = make_light_curve(
        product, interval=TimeInterval(0.0, 5.0), bin_size=1.0
    )
    baseline = estimate_rolling_baseline(
        light_curve, window_bins=2, excluded_bins=frozenset({2})
    )
    scores = score_light_curve_excess(light_curve, baseline)

    candidates = group_excess_bins(scores, threshold=3.0)

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.start == 2.0
    assert candidate.stop == 3.0
    assert candidate.peak_bin_index == 2
    assert candidate.total_counts == 9
    assert candidate.total_expected_counts == 1.0
    assert candidate.excess_counts == 8.0


def test_group_excess_bins_respects_min_consecutive_bins() -> None:
    product = EventProduct(
        source_id="source",
        obs_id="obs",
        instrument="RXTE/PCA",
        times=(0.1, 1.1, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9),
        gtis=(TimeInterval(0.0, 3.0),),
    )
    light_curve = make_light_curve(
        product, interval=TimeInterval(0.0, 3.0), bin_size=1.0
    )
    baseline = estimate_rolling_baseline(
        light_curve, window_bins=1, excluded_bins=frozenset({2})
    )
    scores = score_light_curve_excess(light_curve, baseline)

    assert group_excess_bins(scores, threshold=3.0, min_consecutive_bins=2) == ()


def test_group_excess_bins_rejects_invalid_threshold() -> None:
    with pytest.raises(BurstDetectionError, match="threshold"):
        group_excess_bins((), threshold=0.0)


def test_burst_detection_config_validates_thresholds() -> None:
    with pytest.raises(BurstDetectionError, match="baseline_window_bins"):
        BurstDetectionConfig(baseline_window_bins=0, excess_threshold=3.0)

    with pytest.raises(BurstDetectionError, match="excess_threshold"):
        BurstDetectionConfig(baseline_window_bins=1, excess_threshold=0.0)


def test_morphology_review_config_validates_rise_fraction() -> None:
    with pytest.raises(BurstDetectionError, match="max_rise_fraction"):
        MorphologyReviewConfig(max_rise_fraction=2.0)


def test_summarize_candidate_morphology_reports_binned_features() -> None:
    product = EventProduct(
        source_id="source",
        obs_id="obs",
        instrument="RXTE/PCA",
        times=(0.1, 1.1, 2.1, 2.2, 2.3, 2.4, 3.1),
        gtis=(TimeInterval(0.0, 4.0),),
    )
    light_curve = make_light_curve(
        product, interval=TimeInterval(0.0, 4.0), bin_size=1.0
    )
    baseline = estimate_rolling_baseline(
        light_curve, window_bins=2, excluded_bins=frozenset({2})
    )
    scores = score_light_curve_excess(light_curve, baseline)
    candidate = group_excess_bins(scores, threshold=1.5)[0]

    summary = summarize_candidate_morphology(light_curve, candidate)

    assert summary.start == 2.0
    assert summary.peak_time == 2.5
    assert summary.stop == 3.0
    assert summary.duration == 1.0
    assert summary.approximate_rise_time == 1.0
    assert summary.approximate_decay_time == 1.0
    assert summary.peak_rate == 4.0
    assert summary.total_counts == 4
    assert summary.total_expected_counts == 1.0
    assert summary.excess_counts == 3.0
    assert summary.rise_fraction == 1.0
    assert summary.has_fast_rise_slow_decay_shape


def test_summarize_candidate_morphology_rejects_out_of_range_candidate() -> None:
    product = EventProduct(
        source_id="source",
        obs_id="obs",
        instrument="RXTE/PCA",
        times=(0.1,),
        gtis=(TimeInterval(0.0, 1.0),),
    )
    light_curve = make_light_curve(
        product, interval=TimeInterval(0.0, 1.0), bin_size=1.0
    )
    candidate = BurstIntervalCandidate(
        start=0.0,
        stop=2.0,
        first_bin_index=0,
        last_bin_index=1,
        peak_bin_index=1,
        peak_score=1.0,
        total_counts=1,
        total_expected_counts=0.5,
        n_bins=2,
    )

    with pytest.raises(BurstDetectionError, match="outside the light curve"):
        summarize_candidate_morphology(light_curve, candidate)


def test_review_candidate_morphology_reports_rejection_reasons() -> None:
    product = EventProduct(
        source_id="source",
        obs_id="obs",
        instrument="RXTE/PCA",
        times=(0.1, 1.1, 2.1, 2.2, 2.3, 2.4, 3.1),
        gtis=(TimeInterval(0.0, 4.0),),
    )
    light_curve = make_light_curve(
        product, interval=TimeInterval(0.0, 4.0), bin_size=1.0
    )
    baseline = estimate_rolling_baseline(
        light_curve, window_bins=2, excluded_bins=frozenset({2})
    )
    scores = score_light_curve_excess(light_curve, baseline)
    candidate = group_excess_bins(scores, threshold=1.5)[0]
    morphology = summarize_candidate_morphology(light_curve, candidate)

    review = review_candidate_morphology(
        candidate,
        morphology,
        config=MorphologyReviewConfig(
            min_excess_counts=5.0,
            min_peak_score=10.0,
            max_rise_fraction=0.5,
        ),
    )

    assert not review.passes_review
    assert review.rejection_reasons == (
        "excess_counts_below_threshold",
        "peak_score_below_threshold",
        "rise_fraction_above_threshold",
    )


def test_find_burst_interval_reviews_returns_intermediate_products() -> None:
    product = EventProduct(
        source_id="source",
        obs_id="obs",
        instrument="RXTE/PCA",
        times=(
            0.1,
            1.1,
            2.1,
            2.2,
            2.3,
            2.4,
            2.5,
            2.6,
            2.7,
            2.8,
            2.9,
            3.1,
            4.1,
        ),
        gtis=(TimeInterval(0.0, 5.0),),
    )
    light_curve = make_light_curve(
        product, interval=TimeInterval(0.0, 5.0), bin_size=1.0
    )

    result = find_burst_interval_reviews(
        light_curve,
        detection_config=BurstDetectionConfig(
            baseline_window_bins=2,
            excess_threshold=3.0,
            excluded_bins=frozenset({2}),
        ),
        morphology_config=MorphologyReviewConfig(
            min_excess_counts=5.0,
            min_peak_score=3.0,
        ),
    )

    assert len(result.scores) == light_curve.n_bins
    assert len(result.candidates) == 1
    assert len(result.passed_reviews) == 1
    assert result.passed_reviews[0].candidate.start == 2.0
    assert result.passed_reviews[0].morphology.excess_counts == 8.0
