import math

import pytest

from burst_oscillation_accretion_mapper.burst_detection import (
    BurstDetectionError,
    group_excess_bins,
    score_light_curve_excess,
    signed_poisson_sqrt_deviance,
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
