from pathlib import Path

import pytest
from astropy.io import fits

from burst_oscillation_accretion_mapper.event_products import EventProductProvenance
from burst_oscillation_accretion_mapper.rxte_fits import (
    RxteFitsError,
    read_rxte_fits_event_product,
)
from burst_oscillation_accretion_mapper.time_intervals import TimeInterval


def test_read_rxte_fits_event_product_reads_event_table_and_gti(tmp_path: Path) -> None:
    path = tmp_path / "events.evt"
    fits.HDUList(
        [
            fits.PrimaryHDU(),
            fits.BinTableHDU.from_columns(
                [
                    fits.Column(name="TIME", format="D", array=[1.0, 1.5, 2.0]),
                    fits.Column(name="PHA", format="E", array=[3.0, 4.0, 5.0]),
                    fits.Column(name="PCUID", format="I", array=[2, 2, 3]),
                ],
                name="EVENTS",
            ),
            fits.BinTableHDU.from_columns(
                [
                    fits.Column(name="START", format="D", array=[0.5]),
                    fits.Column(name="STOP", format="D", array=[2.5]),
                ],
                name="GTI",
            ),
        ]
    ).writeto(path)

    product = read_rxte_fits_event_product(
        path,
        source_id="source",
        obs_id="obs",
        provenance=EventProductProvenance(raw_uri=str(path)),
    )

    assert product.times == (1.0, 1.5, 2.0)
    assert product.energies == (3.0, 4.0, 5.0)
    assert product.detector_ids == ("2", "2", "3")
    assert product.gtis == (TimeInterval(0.5, 2.5),)
    assert product.provenance.raw_uri == str(path)


def test_read_rxte_fits_event_product_rejects_vector_time_columns(
    tmp_path: Path,
) -> None:
    path = tmp_path / "vector-events.evt"
    fits.HDUList(
        [
            fits.PrimaryHDU(),
            fits.BinTableHDU.from_columns(
                [fits.Column(name="TIME", format="2D", array=[[1.0, 1.5]])],
                name="EVENTS",
            ),
        ]
    ).writeto(path)

    with pytest.raises(RxteFitsError, match="HEASoft/FTOOLS"):
        read_rxte_fits_event_product(
            path,
            source_id="source",
            obs_id="obs",
            provenance=EventProductProvenance(raw_uri=str(path)),
        )


def test_read_rxte_fits_event_product_rejects_non_event_mode_tables(
    tmp_path: Path,
) -> None:
    path = tmp_path / "binned-mode.fits"
    fits.HDUList(
        [
            fits.PrimaryHDU(),
            fits.BinTableHDU.from_columns(
                [fits.Column(name="TIME", format="D", array=[1.0, 2.0])],
                name="XTE_SP",
            ),
        ]
    ).writeto(path)

    with pytest.raises(RxteFitsError, match="HEASoft/FTOOLS"):
        read_rxte_fits_event_product(
            path,
            source_id="source",
            obs_id="obs",
            provenance=EventProductProvenance(raw_uri=str(path)),
        )
