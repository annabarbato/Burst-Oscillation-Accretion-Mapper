from pathlib import Path

from burst_oscillation_accretion_mapper.archive_plan import (
    build_rxte_raw_archive_plan,
    missing_raw_observations,
)
from burst_oscillation_accretion_mapper.manifests import (
    ManifestIndex,
    ObservationRow,
    SourceRow,
    ValidationTargetRow,
    load_phase1_manifests,
)


MANIFEST_DIR = Path(__file__).resolve().parents[1] / "data" / "manifests"


def test_builds_rxte_archive_plan_from_curated_validation_manifest(
    tmp_path: Path,
) -> None:
    index = load_phase1_manifests(MANIFEST_DIR)

    plans = build_rxte_raw_archive_plan(index, raw_root=tmp_path)

    assert len(plans) == 5
    assert {plan.instrument for plan in plans} == {"RXTE/PCA"}
    assert plans[0].raw_path == tmp_path / "rxte" / "10088-01-07-02"
    assert not any(plan.raw_exists for plan in plans)
    assert not any(plan.is_ready_for_ingestion for plan in plans)


def test_missing_raw_observations_reports_absent_or_unverified_products(
    tmp_path: Path,
) -> None:
    raw_dir = tmp_path / "rxte" / "10088-01-07-02"
    raw_dir.mkdir(parents=True)
    index = _single_context_index(raw_status="downloaded")
    plans = build_rxte_raw_archive_plan(index, raw_root=tmp_path)

    missing = missing_raw_observations(plans)

    assert plans[0].raw_exists
    assert plans[0].is_ready_for_ingestion
    assert missing == ()


def test_selected_manifest_rows_are_not_ready_until_raw_products_exist(
    tmp_path: Path,
) -> None:
    raw_dir = tmp_path / "rxte" / "10088-01-07-02"
    raw_dir.mkdir(parents=True)
    index = _single_context_index(raw_status="selected")

    plans = build_rxte_raw_archive_plan(index, raw_root=tmp_path)

    assert plans[0].raw_exists
    assert not plans[0].is_ready_for_ingestion
    assert missing_raw_observations(plans) == plans


def test_local_raw_path_overrides_default_layout(tmp_path: Path) -> None:
    local_path = Path("data/raw/custom/obs")
    index = _single_context_index(raw_status="downloaded", local_raw_path=str(local_path))

    plans = build_rxte_raw_archive_plan(index, raw_root=tmp_path, repo_root=tmp_path)

    assert plans[0].raw_path == tmp_path / local_path


def _single_context_index(
    *, raw_status: str, local_raw_path: str = ""
) -> ManifestIndex:
    source = SourceRow(
        source_id="4u_1636_536",
        canonical_name="4U 1636-536",
        aliases=(),
        ra_deg=250.0,
        dec_deg=-53.0,
        coordinate_ref="simbad",
        source_class="atoll",
        known_spin_hz=581.0,
        spin_ref="bo_4u_1636_536_581hz",
        binary_ephemeris_ref="",
        minbar_name="4U 1636-536",
        rxte_priority="high",
        notes="test",
    )
    observation = ObservationRow(
        observation_id="rxte_4u_1636_536_10088_01_07_02",
        source_id=source.source_id,
        instrument="RXTE/PCA",
        obs_id="10088-01-07-02",
        archive_uri="",
        archive_ref="minbar_entry_2257",
        start_time="MJD 50445.93334",
        stop_time="MJD 50446.09376",
        exposure_s=7196.0,
        data_mode="MINBAR XPa",
        raw_status=raw_status,
        local_raw_path=local_raw_path,
        checksum="",
        event_product_uri="",
        software_version="",
        caldb_version="",
        screening_hash="",
        barycorr_ref="",
        quality_flags=(),
        notes="test",
    )
    target = ValidationTargetRow(
        target_id="rxte_4u_1636_536_known_osc_2257",
        source_id=source.source_id,
        instrument="RXTE/PCA",
        obs_id=observation.obs_id,
        minbar_burst_id="MINBAR.2257",
        validation_goal="known_oscillation_recovery",
        expected_signal="secure_detection",
        expected_frequency_hz=581.0,
        frequency_ref="bo_4u_1636_536_581hz",
        burst_time_ref=("minbar_entry_2257",),
        priority="high",
        notes="test",
    )
    return ManifestIndex(
        sources={source.source_id: source},
        observations_by_obs_id={observation.obs_id: observation},
        validation_targets=(target,),
    )
