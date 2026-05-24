from pathlib import Path

import pytest

from burst_oscillation_accretion_mapper.archive_plan import RawObservationPlan
from burst_oscillation_accretion_mapper.external_tools import ExternalToolEnvironment
from burst_oscillation_accretion_mapper.rxte_backend import (
    RxtePreflightError,
    build_rxte_event_provenance,
    prepare_rxte_observation,
    prepare_rxte_observations,
)
from burst_oscillation_accretion_mapper.rxte_config import (
    RxteDetectorSelection,
    RxteIngestionConfig,
)


def test_prepare_rxte_observation_inventories_ready_raw_directory(
    tmp_path: Path,
) -> None:
    raw_path = tmp_path / "rxte" / "10088-01-07-02"
    raw_path.mkdir(parents=True)
    (raw_path / "events.evt").write_bytes(b"synthetic event bytes")
    plan = _plan(raw_path=raw_path, raw_status="downloaded")

    prepared = prepare_rxte_observation(plan)

    assert prepared.obs_id == "10088-01-07-02"
    assert prepared.n_raw_files == 1
    assert prepared.inventory.files[0].relative_path == "events.evt"


def test_prepare_rxte_observation_rejects_unready_manifest_status(
    tmp_path: Path,
) -> None:
    raw_path = tmp_path / "rxte" / "10088-01-07-02"
    raw_path.mkdir(parents=True)
    (raw_path / "events.evt").write_bytes(b"synthetic event bytes")
    plan = _plan(raw_path=raw_path, raw_status="selected")

    with pytest.raises(RxtePreflightError, match="raw_status"):
        prepare_rxte_observation(plan)


def test_prepare_rxte_observation_rejects_missing_raw_directory(
    tmp_path: Path,
) -> None:
    plan = _plan(raw_path=tmp_path / "missing", raw_status="downloaded")

    with pytest.raises(RxtePreflightError, match="raw inventory failed"):
        prepare_rxte_observation(plan)


def test_prepare_rxte_observation_rejects_empty_raw_directory(
    tmp_path: Path,
) -> None:
    raw_path = tmp_path / "empty"
    raw_path.mkdir()
    plan = _plan(raw_path=raw_path, raw_status="verified")

    with pytest.raises(RxtePreflightError, match="contains no files"):
        prepare_rxte_observation(plan)


def test_prepare_rxte_observations_validates_multiple_plans(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    (first / "events.evt").write_bytes(b"first")
    (second / "events.evt").write_bytes(b"second")

    prepared = prepare_rxte_observations(
        (
            _plan(raw_path=first, raw_status="downloaded", obs_id="obs-1"),
            _plan(raw_path=second, raw_status="verified", obs_id="obs-2"),
        )
    )

    assert tuple(observation.obs_id for observation in prepared) == ("obs-1", "obs-2")


def test_build_rxte_event_provenance_records_config_and_environment(
    tmp_path: Path,
) -> None:
    raw_path = tmp_path / "rxte" / "10088-01-07-02"
    raw_path.mkdir(parents=True)
    (raw_path / "events.evt").write_bytes(b"synthetic event bytes")
    prepared = prepare_rxte_observation(
        _plan(raw_path=raw_path, raw_status="downloaded")
    )
    config = RxteIngestionConfig(
        detector_selection=RxteDetectorSelection(pcus=(2,), layers=(1,))
    )
    environment = ExternalToolEnvironment(
        variables={"HEADAS": "/opt/heasoft", "CALDB": "/caldb"},
        tool_paths={"barycorr": "/tools/barycorr", "xtefilt": None},
    )

    provenance = build_rxte_event_provenance(
        prepared, config=config, environment=environment
    )

    assert provenance.raw_uri == str(raw_path)
    assert provenance.caldb_version == "/caldb"
    assert provenance.screening_hash == config.screening_hash
    assert provenance.barycorr_ref == "DE405"
    assert not provenance.barycorr_applied
    assert "HEADAS=/opt/heasoft" in provenance.software_version
    assert "missing_tools=xtefilt" in provenance.software_version
    assert "detector=pcu2_layer1" in provenance.notes
    assert "raw_files=1" in provenance.notes


def _plan(
    *,
    raw_path: Path,
    raw_status: str,
    obs_id: str = "10088-01-07-02",
    instrument: str = "RXTE/PCA",
) -> RawObservationPlan:
    return RawObservationPlan(
        target_id="target",
        source_id="source",
        obs_id=obs_id,
        instrument=instrument,
        minbar_burst_id="MINBAR.2257",
        expected_signal="secure_detection",
        raw_path=raw_path,
        raw_exists=raw_path.exists(),
        raw_status=raw_status,
        archive_ref="minbar_entry_2257",
        archive_uri="",
    )
