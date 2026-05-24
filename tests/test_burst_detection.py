import math

import pytest

from burst_oscillation_accretion_mapper.burst_detection import (
    BurstDetectionConfig,
    BurstDetectionError,
    BurstCandidateReview,
    BurstIntervalCandidate,
    BurstMorphologySummary,
    MultiCadenceBurstCandidateReview,
    MorphologyReviewConfig,
    cluster_overlapping_candidate_reviews,
    find_burst_interval_reviews,
    find_multi_cadence_burst_clusters,
    find_multi_cadence_burst_reviews,
    group_excess_bins,
    review_candidate_morphology,
    score_light_curve_excess,
    signed_poisson_sqrt_deviance,
    summarize_candidate_morphology,
    summarize_multi_cadence_candidate_cluster,
    summarize_multi_cadence_candidate_clusters,
)
from burst_oscillation_accretion_mapper.event_products import EventProduct
from burst_oscillation_accretion_mapper.lightcurves import (
    estimate_rolling_baseline,
    make_light_curve,
    make_multi_cadence_light_curves,
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


def test_find_multi_cadence_burst_reviews_runs_per_cadence_configs() -> None:
    product = _synthetic_multi_cadence_event_product()
    light_curves = make_multi_cadence_light_curves(
        product,
        interval=TimeInterval(0.0, 5.0),
        bin_sizes=(1.0, 0.5),
    )

    reviews = find_multi_cadence_burst_reviews(
        light_curves,
        detection_configs={
            1.0: BurstDetectionConfig(
                baseline_window_bins=2,
                excess_threshold=3.0,
                excluded_bins=frozenset({2}),
            ),
            0.5: BurstDetectionConfig(
                baseline_window_bins=2,
                excess_threshold=2.0,
                excluded_bins=frozenset({4, 5}),
            ),
        },
        morphology_config=MorphologyReviewConfig(
            min_excess_counts=1.0,
            min_peak_score=2.0,
        ),
    )

    assert tuple(review.bin_size for review in reviews) == (0.5, 1.0)
    assert all(review.review.passes_review for review in reviews)
    assert {review.review.candidate.start for review in reviews} == {2.0}


def test_find_multi_cadence_burst_reviews_requires_each_cadence_config() -> None:
    product = _synthetic_multi_cadence_event_product()
    light_curves = make_multi_cadence_light_curves(
        product,
        interval=TimeInterval(0.0, 5.0),
        bin_sizes=(1.0, 0.5),
    )

    with pytest.raises(BurstDetectionError, match="Missing detection config"):
        find_multi_cadence_burst_reviews(
            light_curves,
            detection_configs={
                1.0: BurstDetectionConfig(
                    baseline_window_bins=2,
                    excess_threshold=3.0,
                    excluded_bins=frozenset({2}),
                )
            },
        )


def test_find_multi_cadence_burst_reviews_can_return_passed_only() -> None:
    product = _synthetic_multi_cadence_event_product()
    light_curves = make_multi_cadence_light_curves(
        product,
        interval=TimeInterval(0.0, 5.0),
        bin_sizes=(1.0, 0.5),
    )

    reviews = find_multi_cadence_burst_reviews(
        light_curves,
        detection_configs={
            1.0: BurstDetectionConfig(
                baseline_window_bins=2,
                excess_threshold=3.0,
                excluded_bins=frozenset({2}),
            ),
            0.5: BurstDetectionConfig(
                baseline_window_bins=2,
                excess_threshold=2.0,
                excluded_bins=frozenset({4, 5}),
            ),
        },
        morphology_config=MorphologyReviewConfig(min_excess_counts=10.0),
        passed_only=True,
    )

    assert reviews == ()


def test_cluster_overlapping_candidate_reviews_groups_cadences() -> None:
    product = _synthetic_multi_cadence_event_product()
    light_curves = make_multi_cadence_light_curves(
        product,
        interval=TimeInterval(0.0, 5.0),
        bin_sizes=(1.0, 0.5),
    )
    reviews = find_multi_cadence_burst_reviews(
        light_curves,
        detection_configs={
            1.0: BurstDetectionConfig(
                baseline_window_bins=2,
                excess_threshold=3.0,
                excluded_bins=frozenset({2}),
            ),
            0.5: BurstDetectionConfig(
                baseline_window_bins=2,
                excess_threshold=2.0,
                excluded_bins=frozenset({4, 5}),
            ),
        },
        morphology_config=MorphologyReviewConfig(
            min_excess_counts=1.0,
            min_peak_score=2.0,
        ),
    )

    clusters = cluster_overlapping_candidate_reviews(reviews)

    assert len(clusters) == 1
    assert clusters[0].start == 2.0
    assert clusters[0].stop == 3.0
    assert clusters[0].bin_sizes == (0.5, 1.0)
    assert clusters[0].review_count == 2
    assert clusters[0].passed_review_count == 2
    assert clusters[0].passes_any_review
    assert clusters[0].best_peak_score == pytest.approx(
        max(review.review.candidate.peak_score for review in reviews)
    )


def test_cluster_overlapping_candidate_reviews_keeps_separate_intervals() -> None:
    reviews = tuple(
        MultiCadenceBurstCandidateReview(
            bin_size=1.0,
            review=_review_for_interval(start=start, stop=stop),
        )
        for start, stop in ((2.0, 3.0), (4.0, 5.0))
    )

    clusters = cluster_overlapping_candidate_reviews(reviews)

    assert [(cluster.start, cluster.stop) for cluster in clusters] == [
        (2.0, 3.0),
        (4.0, 5.0),
    ]


def test_find_multi_cadence_burst_clusters_wraps_review_and_clustering() -> None:
    product = _synthetic_multi_cadence_event_product()
    light_curves = make_multi_cadence_light_curves(
        product,
        interval=TimeInterval(0.0, 5.0),
        bin_sizes=(1.0, 0.5),
    )

    clusters = find_multi_cadence_burst_clusters(
        light_curves,
        detection_configs={
            1.0: BurstDetectionConfig(
                baseline_window_bins=2,
                excess_threshold=3.0,
                excluded_bins=frozenset({2}),
            ),
            0.5: BurstDetectionConfig(
                baseline_window_bins=2,
                excess_threshold=2.0,
                excluded_bins=frozenset({4, 5}),
            ),
        },
        morphology_config=MorphologyReviewConfig(
            min_excess_counts=1.0,
            min_peak_score=2.0,
        ),
    )

    assert len(clusters) == 1
    assert clusters[0].start == 2.0
    assert clusters[0].stop == 3.0
    assert clusters[0].bin_sizes == (0.5, 1.0)


def test_summarize_multi_cadence_candidate_cluster_uses_best_review() -> None:
    product = _synthetic_multi_cadence_event_product()
    light_curves = make_multi_cadence_light_curves(
        product,
        interval=TimeInterval(0.0, 5.0),
        bin_sizes=(1.0, 0.5),
    )
    clusters = find_multi_cadence_burst_clusters(
        light_curves,
        detection_configs={
            1.0: BurstDetectionConfig(
                baseline_window_bins=2,
                excess_threshold=3.0,
                excluded_bins=frozenset({2}),
            ),
            0.5: BurstDetectionConfig(
                baseline_window_bins=2,
                excess_threshold=2.0,
                excluded_bins=frozenset({4, 5}),
            ),
        },
        morphology_config=MorphologyReviewConfig(
            min_excess_counts=1.0,
            min_peak_score=2.0,
        ),
    )

    summary = summarize_multi_cadence_candidate_cluster(clusters[0])

    assert summary.start == 2.0
    assert summary.peak_time == 2.5
    assert summary.stop == 3.0
    assert summary.duration == 1.0
    assert summary.bin_sizes == (0.5, 1.0)
    assert summary.best_bin_size == 1.0
    assert summary.review_count == 2
    assert summary.passed_review_count == 2
    assert summary.passes_any_review
    assert summary.best_peak_score == clusters[0].best_peak_score
    assert summary.best_excess_counts == 8.0
    assert summary.total_counts == 9
    assert summary.total_expected_counts == 1.0
    assert summary.rejection_reasons == ()


def test_summarize_multi_cadence_candidate_clusters_preserves_order() -> None:
    clusters = cluster_overlapping_candidate_reviews(
        tuple(
            MultiCadenceBurstCandidateReview(
                bin_size=1.0,
                review=_review_for_interval(start=start, stop=stop),
            )
            for start, stop in ((2.0, 3.0), (4.0, 5.0))
        )
    )

    summaries = summarize_multi_cadence_candidate_clusters(clusters)

    assert [(summary.start, summary.stop) for summary in summaries] == [
        (2.0, 3.0),
        (4.0, 5.0),
    ]


def _synthetic_multi_cadence_event_product() -> EventProduct:
    return EventProduct(
        source_id="source",
        obs_id="obs",
        instrument="RXTE/PCA",
        times=(
            0.1,
            1.1,
            2.05,
            2.15,
            2.25,
            2.35,
            2.45,
            2.55,
            2.65,
            2.75,
            2.85,
            3.1,
            4.1,
        ),
        gtis=(TimeInterval(0.0, 5.0),),
    )


def _review_for_interval(start: float, stop: float) -> BurstCandidateReview:
    candidate = BurstIntervalCandidate(
        start=start,
        stop=stop,
        first_bin_index=int(start),
        last_bin_index=int(stop) - 1,
        peak_bin_index=int(start),
        peak_score=3.0,
        total_counts=5,
        total_expected_counts=1.0,
        n_bins=1,
    )
    return BurstCandidateReview(
        candidate=candidate,
        morphology=BurstMorphologySummary(
            start=start,
            peak_time=0.5 * (start + stop),
            stop=stop,
            duration=stop - start,
            approximate_rise_time=stop - start,
            approximate_decay_time=stop - start,
            peak_rate=5.0,
            total_counts=5,
            total_expected_counts=1.0,
            excess_counts=4.0,
            n_bins=1,
        ),
        rejection_reasons=(),
    )
