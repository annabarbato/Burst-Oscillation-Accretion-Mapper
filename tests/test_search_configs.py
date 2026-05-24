import json

import pytest

from burst_oscillation_accretion_mapper.candidate_scoring import CandidateScoringConfig
from burst_oscillation_accretion_mapper.oscillation_search import (
    SlidingWindowConfig,
    TargetedFrequencyGrid,
    TargetedZ2SearchConfig,
)
from burst_oscillation_accretion_mapper.search_configs import (
    SearchConfigError,
    TargetedSearchReviewConfig,
)


def test_targeted_search_review_config_id_is_stable_and_prefixed() -> None:
    first = _review_config()
    second = _review_config()

    assert first.config_id == second.config_id
    assert first.config_hash == second.config_hash
    assert first.config_id.startswith("targeted-z2-")
    assert len(first.config_id) == len("targeted-z2-") + 16


def test_targeted_search_review_config_hash_changes_with_search_settings() -> None:
    baseline = _review_config()
    wider_grid = _review_config(
        search_config=TargetedZ2SearchConfig(
            frequency_grid=TargetedFrequencyGrid(
                center_hz=581.0,
                half_width_hz=2.0,
                step_hz=0.5,
            ),
            min_photons=8,
        )
    )

    assert baseline.config_id != wider_grid.config_id
    assert baseline.config_hash != wider_grid.config_hash


def test_targeted_search_review_config_payload_is_canonical_json() -> None:
    config = _review_config()

    payload = json.loads(config.payload_json)

    assert payload["energy_band"] == "2-20 keV"
    assert payload["expected_frequency_hz"] == 581.0
    assert payload["product_kind"] == "candidate_review"
    assert payload["window_config"] == {
        "step_s": 0.5,
        "window_size_s": 2.0,
    }
    assert payload["search_config"]["frequency_grid"] == {
        "center_hz": 581.0,
        "half_width_hz": 1.0,
        "step_hz": 0.5,
    }


def test_targeted_search_review_config_validates_review_metadata() -> None:
    with pytest.raises(SearchConfigError, match="expected_frequency_hz"):
        _review_config(expected_frequency_hz=0.0)

    with pytest.raises(SearchConfigError, match="product_kind"):
        _review_config(product_kind="")


def _review_config(
    *,
    search_config: TargetedZ2SearchConfig | None = None,
    expected_frequency_hz: float | None = 581.0,
    product_kind: str = "candidate_review",
) -> TargetedSearchReviewConfig:
    if search_config is None:
        search_config = TargetedZ2SearchConfig(
            frequency_grid=TargetedFrequencyGrid(
                center_hz=581.0,
                half_width_hz=1.0,
                step_hz=0.5,
            ),
            min_photons=8,
        )

    return TargetedSearchReviewConfig(
        window_config=SlidingWindowConfig(window_size_s=2.0, step_s=0.5),
        search_config=search_config,
        scoring_config=CandidateScoringConfig(
            marginal_z2_threshold=10.0,
            probable_z2_threshold=20.0,
            secure_z2_threshold=30.0,
            max_frequency_offset_hz=1.0,
        ),
        expected_frequency_hz=expected_frequency_hz,
        energy_band="2-20 keV",
        product_kind=product_kind,
    )
