from burst_oscillation_accretion_mapper.rxte_archive import (
    RxteArchiveError,
    rxte_observation_archive_url,
)


def test_rxte_observation_archive_url_uses_ao_and_proposal_path() -> None:
    assert rxte_observation_archive_url("10088-01-07-02") == (
        "https://heasarc.gsfc.nasa.gov/FTP/xte/data/archive/"
        "AO1/P10088/10088-01-07-02/"
    )
    assert rxte_observation_archive_url("30061-01-02-01") == (
        "https://heasarc.gsfc.nasa.gov/FTP/xte/data/archive/"
        "AO3/P30061/30061-01-02-01/"
    )


def test_rxte_observation_archive_url_rejects_invalid_obsid() -> None:
    try:
        rxte_observation_archive_url("bad-obsid")
    except RxteArchiveError as exc:
        assert "Invalid RXTE ObsID" in str(exc)
    else:
        raise AssertionError("Expected invalid ObsID to raise")
