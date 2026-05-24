import pytest

from burst_oscillation_accretion_mapper.event_products import EventProduct
from burst_oscillation_accretion_mapper.lightcurves import (
    LightCurveError,
    estimate_rolling_baseline,
    make_light_curve,
)
from burst_oscillation_accretion_mapper.time_intervals import TimeInterval


def test_make_light_curve_counts_half_open_bins() -> None:
    product = EventProduct(
        source_id="source",
        obs_id="obs",
        instrument="RXTE/PCA",
        times=(0.0, 0.999, 1.0, 1.999, 2.0),
        gtis=(TimeInterval(0.0, 3.0),),
    )

    light_curve = make_light_curve(
        product, interval=TimeInterval(0.0, 3.0), bin_size=1.0
    )

    assert light_curve.counts == (2, 2, 1)
    assert light_curve.exposures == (1.0, 1.0, 1.0)
    assert light_curve.rates == (2.0, 2.0, 1.0)


def test_make_light_curve_truncates_final_partial_bin() -> None:
    product = EventProduct(
        source_id="source",
        obs_id="obs",
        instrument="RXTE/PCA",
        times=(0.25, 1.25, 2.25),
        gtis=(TimeInterval(0.0, 2.5),),
    )

    light_curve = make_light_curve(
        product, interval=TimeInterval(0.0, 2.5), bin_size=1.0
    )

    assert light_curve.bin_starts == (0.0, 1.0, 2.0)
    assert light_curve.bin_stops == (1.0, 2.0, 2.5)
    assert light_curve.counts == (1, 1, 1)
    assert light_curve.exposures == (1.0, 1.0, 0.5)
    assert light_curve.rates == (1.0, 1.0, 2.0)


def test_make_light_curve_tracks_zero_exposure_gaps() -> None:
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

    assert light_curve.counts == (1, 0, 1)
    assert light_curve.exposures == (1.0, 0.0, 1.0)
    assert light_curve.rates == (1.0, None, 1.0)


def test_make_light_curve_clips_exposure_to_gti_edges() -> None:
    product = EventProduct(
        source_id="source",
        obs_id="obs",
        instrument="RXTE/PCA",
        times=(0.25, 1.25, 2.25),
        gtis=(TimeInterval(0.0, 1.5), TimeInterval(2.0, 3.0)),
    )

    light_curve = make_light_curve(
        product, interval=TimeInterval(0.0, 3.0), bin_size=1.0
    )

    assert light_curve.counts == (1, 1, 1)
    assert light_curve.exposures == (1.0, 0.5, 1.0)
    assert light_curve.total_counts == 3
    assert light_curve.total_exposure == 2.5


def test_make_light_curve_rejects_invalid_bin_size() -> None:
    product = EventProduct(
        source_id="source",
        obs_id="obs",
        instrument="RXTE/PCA",
        times=(),
        gtis=(),
    )

    with pytest.raises(LightCurveError, match="Invalid bin_size"):
        make_light_curve(product, interval=TimeInterval(0.0, 1.0), bin_size=0.0)


def test_estimate_rolling_baseline_uses_median_rates() -> None:
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

    baseline = estimate_rolling_baseline(light_curve, window_bins=2)

    assert light_curve.counts == (1, 1, 9, 1, 1)
    assert baseline.rates == (1.0, 1.0, 1.0, 1.0, 1.0)
    assert baseline.reference_bin_counts == (3, 4, 5, 4, 3)


def test_estimate_rolling_baseline_ignores_zero_exposure_bins() -> None:
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

    assert light_curve.rates == (1.0, None, 1.0)
    assert baseline.rates == (1.0, 1.0, 1.0)
    assert baseline.reference_bin_counts == (1, 2, 1)


def test_estimate_rolling_baseline_supports_explicit_exclusions() -> None:
    product = EventProduct(
        source_id="source",
        obs_id="obs",
        instrument="RXTE/PCA",
        times=(0.1, 1.1, 1.2, 1.3, 2.1),
        gtis=(TimeInterval(0.0, 3.0),),
    )
    light_curve = make_light_curve(
        product, interval=TimeInterval(0.0, 3.0), bin_size=1.0
    )

    baseline = estimate_rolling_baseline(
        light_curve, window_bins=1, excluded_bins=frozenset({1})
    )

    assert light_curve.counts == (1, 3, 1)
    assert baseline.rates == (1.0, 1.0, 1.0)
    assert baseline.reference_bin_counts == (1, 2, 1)


def test_estimate_rolling_baseline_rejects_invalid_window() -> None:
    product = EventProduct(
        source_id="source",
        obs_id="obs",
        instrument="RXTE/PCA",
        times=(),
        gtis=(),
    )
    light_curve = make_light_curve(
        product, interval=TimeInterval(0.0, 1.0), bin_size=1.0
    )

    with pytest.raises(LightCurveError, match="window_bins"):
        estimate_rolling_baseline(light_curve, window_bins=0)
