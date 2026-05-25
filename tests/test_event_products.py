import pytest

from burst_oscillation_accretion_mapper.event_products import (
    EventProduct,
    EventProductError,
    EventProductProvenance,
)
from burst_oscillation_accretion_mapper.time_intervals import TimeInterval


def make_event_product() -> EventProduct:
    return EventProduct(
        source_id="4u_1728_34",
        obs_id="10073-01-01-00",
        instrument="RXTE/PCA",
        times=(10.0, 11.5, 12.0, 15.0, 19.999, 35.0),
        gtis=(TimeInterval(10.0, 20.0), TimeInterval(30.0, 40.0)),
        energies=(2.0, 3.5, 6.0, 8.0, 12.0, 4.0),
        detector_ids=("pcu2", "pcu2", "pcu2", "pcu0", "pcu0", "pcu2"),
        provenance=EventProductProvenance(
            raw_uri="rxte/10073-01-01-00",
            software_version="test",
            screening_hash="screening-test",
            barycorr_applied=True,
        ),
    )


def test_event_product_exposes_count_and_exposure() -> None:
    product = make_event_product()

    assert product.n_events == 6
    assert product.exposure_s == 20.0
    assert product.provenance.barycorr_applied


def test_event_product_rejects_misaligned_event_columns() -> None:
    with pytest.raises(EventProductError, match="energies length"):
        EventProduct(
            source_id="source",
            obs_id="obs",
            instrument="RXTE/PCA",
            times=(1.0, 2.0),
            gtis=(TimeInterval(0.0, 3.0),),
            energies=(5.0,),
        )


def test_event_product_rejects_unsorted_times() -> None:
    with pytest.raises(EventProductError, match="sorted"):
        EventProduct(
            source_id="source",
            obs_id="obs",
            instrument="RXTE/PCA",
            times=(2.0, 1.0),
            gtis=(TimeInterval(0.0, 3.0),),
        )


def test_event_product_rejects_events_outside_gtis() -> None:
    with pytest.raises(EventProductError, match="outside GTIs"):
        EventProduct(
            source_id="source",
            obs_id="obs",
            instrument="RXTE/PCA",
            times=(1.0, 3.0),
            gtis=(TimeInterval(0.0, 3.0),),
        )


def test_select_time_interval_clips_to_gti_and_preserves_columns() -> None:
    product = make_event_product()

    selected = product.select_time_interval(TimeInterval(11.0, 36.0))

    assert selected.times == (11.5, 12.0, 15.0, 19.999, 35.0)
    assert selected.gtis == (TimeInterval(11.0, 20.0), TimeInterval(30.0, 36.0))
    assert selected.energies == (3.5, 6.0, 8.0, 12.0, 4.0)
    assert selected.detector_ids == ("pcu2", "pcu2", "pcu0", "pcu0", "pcu2")
    assert selected.provenance == product.provenance


def test_select_energy_range_is_half_open() -> None:
    product = make_event_product()

    selected = product.select_energy_range(3.0, 8.0)

    assert selected.times == (11.5, 12.0, 35.0)
    assert selected.energies == (3.5, 6.0, 4.0)
    assert selected.gtis == product.gtis


def test_select_energy_range_requires_energy_column() -> None:
    product = EventProduct(
        source_id="source",
        obs_id="obs",
        instrument="RXTE/PCA",
        times=(1.0,),
        gtis=(TimeInterval(0.0, 2.0),),
    )

    with pytest.raises(EventProductError, match="without energies"):
        product.select_energy_range(2.0, 10.0)
