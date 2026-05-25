from pathlib import Path

import pytest

from burst_oscillation_accretion_mapper.manifests import (
    ManifestLoadError,
    load_phase1_manifests,
)


MANIFEST_DIR = Path(__file__).resolve().parents[1] / "data" / "manifests"


def test_loads_rxte_validation_contexts() -> None:
    index = load_phase1_manifests(MANIFEST_DIR)

    contexts = index.rxte_validation_contexts()

    assert len(contexts) == 5
    assert {context.observation.instrument for context in contexts} == {"RXTE/PCA"}
    assert {context.target.obs_id for context in contexts} == {
        "10088-01-07-02",
        "10073-01-01-000",
        "10073-01-02-000",
        "20084-02-01-000",
        "30061-01-02-01",
    }


def test_secure_detection_targets_keep_expected_frequencies() -> None:
    index = load_phase1_manifests(MANIFEST_DIR)

    secure = {
        context.target.target_id: context.target.expected_frequency_hz
        for context in index.rxte_validation_contexts()
        if context.target.expected_signal == "secure_detection"
    }

    assert secure == {
        "rxte_4u_1636_536_known_osc_2257": 581.0,
        "rxte_4u_1728_34_known_osc_2204": 363.0,
    }


def test_non_detection_control_is_available_without_frequency() -> None:
    index = load_phase1_manifests(MANIFEST_DIR)

    controls = index.non_detection_controls()

    assert len(controls) == 1
    control = controls[0]
    assert control.target.target_id == "rxte_4u_1728_34_non_detection_2206"
    assert control.target.expected_frequency_hz is None
    assert control.source.source_id == "4u_1728_34"
    assert control.observation.obs_id == "10073-01-02-000"


def test_missing_manifest_directory_raises_clear_error(tmp_path: Path) -> None:
    with pytest.raises(ManifestLoadError, match="Missing manifest"):
        load_phase1_manifests(tmp_path)
