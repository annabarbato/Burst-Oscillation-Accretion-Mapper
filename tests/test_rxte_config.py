import pytest

from burst_oscillation_accretion_mapper.rxte_config import (
    RxteBarycenterConfig,
    RxteConfigError,
    RxteDetectorSelection,
    RxteIngestionConfig,
)


def test_rxte_ingestion_config_has_stable_screening_hash() -> None:
    config = RxteIngestionConfig(
        detector_selection=RxteDetectorSelection(pcus=(0, 2), layers=(1, 2)),
        barycenter=RxteBarycenterConfig(source_position_ref="simbad"),
        accepted_data_modes=("GoodXenon",),
    )

    same_config = RxteIngestionConfig(
        detector_selection=RxteDetectorSelection(pcus=(0, 2), layers=(1, 2)),
        barycenter=RxteBarycenterConfig(source_position_ref="simbad"),
        accepted_data_modes=("GoodXenon",),
    )
    different_config = RxteIngestionConfig(
        detector_selection=RxteDetectorSelection(pcus=(2,), layers=(1,)),
        barycenter=RxteBarycenterConfig(source_position_ref="simbad"),
        accepted_data_modes=("GoodXenon",),
    )

    assert config.screening_hash == same_config.screening_hash
    assert config.screening_hash != different_config.screening_hash
    assert config.detector_label == "pcu0-2_layer1-2"


def test_detector_selection_rejects_invalid_pcu() -> None:
    with pytest.raises(RxteConfigError, match="PCU"):
        RxteDetectorSelection(pcus=(5,))


def test_detector_selection_rejects_invalid_layer() -> None:
    with pytest.raises(RxteConfigError, match="layer"):
        RxteDetectorSelection(layers=(0,))


def test_barycenter_config_requires_task_when_enabled() -> None:
    with pytest.raises(RxteConfigError, match="task"):
        RxteBarycenterConfig(task_name="")
