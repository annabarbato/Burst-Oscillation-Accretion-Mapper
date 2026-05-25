from pathlib import Path

import pytest

from burst_oscillation_accretion_mapper.rxte_product_selection import (
    RxteProductSelectionError,
    rxte_filename_time_interval,
    select_rxte_phase1_product,
)
from burst_oscillation_accretion_mapper.time_intervals import TimeInterval


def test_select_rxte_phase1_product_prefers_barycentered_xte_se(tmp_path: Path) -> None:
    raw = tmp_path / "raw" / "obs"
    processed = tmp_path / "processed" / "obs"
    (raw / "pca").mkdir(parents=True)
    (processed / "barycorr").mkdir(parents=True)
    raw_se = raw / "pca" / "SE1_00100-00200.evt.gz"
    bary_se = processed / "barycorr" / "SE1_00100-00200_bary.evt"
    raw_se.touch()
    bary_se.touch()

    selection = select_rxte_phase1_product(
        raw_obs_path=raw,
        processed_obs_path=processed,
        target_time_met=0x150,
    )

    assert selection.selected_product_path == bary_se
    assert selection.reader_type == "fits"
    assert selection.data_mode == "XTE_SE"
    assert selection.fallback_status == "none"
    assert selection.is_barycentered


def test_select_rxte_phase1_product_uses_singlebit_fallback_with_reason(
    tmp_path: Path,
) -> None:
    raw = tmp_path / "raw" / "obs"
    processed = tmp_path / "processed" / "obs"
    (raw / "pca").mkdir(parents=True)
    singlebit = raw / "pca" / "FS4f_00100-00200.gz"
    wrong_se = raw / "pca" / "SE1_00300-00400.evt.gz"
    singlebit.touch()
    wrong_se.touch()

    selection = select_rxte_phase1_product(
        raw_obs_path=raw,
        processed_obs_path=processed,
        target_time_met=0x150,
    )

    assert selection.selected_product_path == singlebit
    assert selection.reader_type == "singlebit"
    assert selection.data_mode == "SingleBit"
    assert selection.fallback_status == "singlebit_binned_fallback"
    assert not selection.is_barycentered


def test_select_rxte_phase1_product_reports_no_burst_covering_product(
    tmp_path: Path,
) -> None:
    raw = tmp_path / "raw" / "obs"
    processed = tmp_path / "processed" / "obs"
    (raw / "pca").mkdir(parents=True)
    (raw / "pca" / "SE1_00300-00400.evt.gz").touch()

    with pytest.raises(RxteProductSelectionError, match="No burst-covering"):
        select_rxte_phase1_product(
            raw_obs_path=raw,
            processed_obs_path=processed,
            target_time_met=0x150,
        )


def test_rxte_filename_time_interval_parses_hex_product_bounds() -> None:
    assert rxte_filename_time_interval("SE1_5a0e110-5a0e6a1.evt.gz") == (
        TimeInterval(float(0x5A0E110), float(0x5A0E6A1))
    )
