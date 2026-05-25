import pytest

from burst_oscillation_accretion_mapper.rxte_time import (
    RxteTimeError,
    utc_mjd_to_rxte_met,
)


def test_utc_mjd_to_rxte_met_converts_minbar_utc_to_rxte_tt_seconds() -> None:
    assert utc_mjd_to_rxte_met(50445.94401) == pytest.approx(94430364.464)


def test_utc_mjd_to_rxte_met_rejects_non_finite_input() -> None:
    with pytest.raises(RxteTimeError, match="mjd_utc"):
        utc_mjd_to_rxte_met(float("nan"))
