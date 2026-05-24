import pytest

from burst_oscillation_accretion_mapper.event_products import EventProduct
from burst_oscillation_accretion_mapper.lightcurves import (
    LightCurveError,
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
