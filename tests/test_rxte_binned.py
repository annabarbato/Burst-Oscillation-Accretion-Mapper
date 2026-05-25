from pathlib import Path

import pytest
from astropy.io import fits

from burst_oscillation_accretion_mapper.event_products import EventProductProvenance
from burst_oscillation_accretion_mapper.rxte_binned import (
    RxteBinnedError,
    read_rxte_singlebit_event_product,
)
from burst_oscillation_accretion_mapper.time_intervals import TimeInterval


def test_read_rxte_singlebit_event_product_expands_counts_to_bin_centers(
    tmp_path: Path,
) -> None:
    path = tmp_path / "singlebit.fits"
    count_rows = [[0, 2, 1, 0], [1, 0, 0, 1]]
    fits.HDUList(
        [
            fits.PrimaryHDU(),
            fits.BinTableHDU.from_columns(
                [
                    fits.Column(name="Time", format="D", array=[10.0, 11.0]),
                    fits.Column(
                        name="XeCnt",
                        format="4I",
                        array=count_rows,
                    ),
                ],
                name="XTE_SA",
                header=fits.Header({"DATAMODE": "SB_125us_0_249_1s", "TIMEDEL": 1.0}),
            ),
            fits.BinTableHDU.from_columns(
                [
                    fits.Column(name="Start", format="D", array=[10.0]),
                    fits.Column(name="Stop", format="D", array=[12.0]),
                ],
                name="GTI",
            ),
        ]
    ).writeto(path)

    product = read_rxte_singlebit_event_product(
        path,
        source_id="source",
        obs_id="obs",
        provenance=EventProductProvenance(raw_uri=str(path)),
    )

    assert product.times == (10.375, 10.375, 10.625, 11.125, 11.875)
    assert product.gtis == (TimeInterval(10.0, 12.0),)
    assert product.provenance.raw_uri == str(path)


def test_read_rxte_singlebit_event_product_rejects_unsupported_datamode(
    tmp_path: Path,
) -> None:
    path = tmp_path / "standard2.fits"
    fits.HDUList(
        [
            fits.PrimaryHDU(),
            fits.BinTableHDU.from_columns(
                [
                    fits.Column(name="Time", format="D", array=[10.0]),
                    fits.Column(name="XeCnt", format="4I", array=[[0, 1, 0, 0]]),
                ],
                name="XTE_SA",
                header=fits.Header({"DATAMODE": "Standard2a", "TIMEDEL": 1.0}),
            ),
        ]
    ).writeto(path)

    with pytest.raises(RxteBinnedError, match="Unsupported"):
        read_rxte_singlebit_event_product(
            path,
            source_id="source",
            obs_id="obs",
            provenance=EventProductProvenance(raw_uri=str(path)),
        )
