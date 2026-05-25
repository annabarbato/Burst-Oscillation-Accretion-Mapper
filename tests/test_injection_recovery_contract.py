import pytest

from burst_oscillation_accretion_mapper.injection_recovery_contract import (
    BURST_BODY,
    CONSTANT_DRIFT,
    LINEAR_DRIFT,
    NOT_RECOVERED,
    RECOVERED,
    InjectionGridSpec,
    InjectionRecoveryContractError,
    InjectionRecoveryFixture,
    InjectionTrialProduct,
    BurstSensitivityProduct,
    load_injection_recovery_fixture,
)


FIXTURE_PATH = "tests/fixtures/phase2/injection_recovery_contract.json"


def test_injection_grid_spec_has_stable_hash_and_id() -> None:
    first = _grid()
    second = _grid()

    assert first.config_hash == second.config_hash
    assert first.config_id == second.config_id
    assert first.config_id.startswith("injection-recovery-")
    assert len(first.config_id) == len("injection-recovery-") + 16


def test_injection_grid_hash_changes_when_grid_changes() -> None:
    baseline = _grid()
    wider_amplitude_grid = InjectionGridSpec(
        search_config_hash="search-hash",
        amplitude_grid=(0.03, 0.06, 0.09, 0.12),
        frequency_offsets_hz=(-0.5, 0.0, 0.5),
        drift_models=(CONSTANT_DRIFT,),
        burst_phases=(BURST_BODY,),
        energy_bands=("broad",),
        trials_per_cell=8,
        random_seed=123,
        count_rate_envelope_ref="fixture://envelope",
    )

    assert baseline.config_hash != wider_amplitude_grid.config_hash


def test_injection_trial_product_preserves_bias_terms() -> None:
    trial = _recovered_trial()

    assert trial.recovered is True
    assert trial.recovery_classification == RECOVERED
    assert trial.recovered_frequency_bias_hz == pytest.approx(0.02)
    assert trial.recovered_amplitude_bias == pytest.approx(-0.002)


def test_injection_trial_product_validates_recovery_consistency() -> None:
    with pytest.raises(InjectionRecoveryContractError, match="recovered=True"):
        InjectionTrialProduct(
            trial_id="trial",
            burst_id="burst",
            source_id="source",
            obs_id="obs",
            instrument="RXTE/PCA",
            search_config_hash="search-hash",
            injection_config_hash="injection-hash",
            pipeline_version="phase2-test",
            injected_freq_hz=581.0,
            injected_amp=0.05,
            injected_phase_rad=0.0,
            injected_burst_phase=BURST_BODY,
            injected_drift_model=CONSTANT_DRIFT,
            injected_drift={},
            energy_band="broad",
            random_seed=1,
            recovered=False,
            recovery_classification=RECOVERED,
        )


def test_contract_products_require_boolean_flags() -> None:
    with pytest.raises(InjectionRecoveryContractError, match="recovered"):
        InjectionTrialProduct(
            trial_id="trial",
            burst_id="burst",
            source_id="source",
            obs_id="obs",
            instrument="RXTE/PCA",
            search_config_hash="search-hash",
            injection_config_hash="injection-hash",
            pipeline_version="phase2-test",
            injected_freq_hz=581.0,
            injected_amp=0.05,
            injected_phase_rad=0.0,
            injected_burst_phase=BURST_BODY,
            injected_drift_model=CONSTANT_DRIFT,
            injected_drift={},
            energy_band="broad",
            random_seed=1,
            recovered="true",
            recovery_classification=RECOVERED,
        )

    with pytest.raises(InjectionRecoveryContractError, match="valid_for_primary_model"):
        BurstSensitivityProduct(
            sensitivity_id="sensitivity",
            burst_id="burst",
            source_id="source",
            obs_id="obs",
            instrument="RXTE/PCA",
            search_config_hash="search-hash",
            injection_config_hash="injection-hash",
            pipeline_version="phase2-test",
            energy_band="broad",
            burst_phase=BURST_BODY,
            trial_count=10,
            recovered_count=5,
            amp50=0.05,
            amp90=0.08,
            amp95=0.09,
            upper_limit_amp=0.08,
            curve_uri="fixture://curve",
            valid_for_primary_model="true",
        )


def test_burst_sensitivity_product_requires_monotonic_thresholds() -> None:
    with pytest.raises(InjectionRecoveryContractError, match="amp50 <= amp90 <= amp95"):
        BurstSensitivityProduct(
            sensitivity_id="sensitivity",
            burst_id="burst",
            source_id="source",
            obs_id="obs",
            instrument="RXTE/PCA",
            search_config_hash="search-hash",
            injection_config_hash="injection-hash",
            pipeline_version="phase2-test",
            energy_band="broad",
            burst_phase=BURST_BODY,
            trial_count=10,
            recovered_count=5,
            amp50=0.08,
            amp90=0.07,
            amp95=0.09,
            upper_limit_amp=0.07,
            curve_uri="fixture://curve",
            valid_for_primary_model=True,
        )


def test_invalid_burst_sensitivity_product_requires_quality_flags() -> None:
    with pytest.raises(InjectionRecoveryContractError, match="quality_flags"):
        BurstSensitivityProduct(
            sensitivity_id="sensitivity",
            burst_id="burst",
            source_id="source",
            obs_id="obs",
            instrument="RXTE/PCA",
            search_config_hash="search-hash",
            injection_config_hash="injection-hash",
            pipeline_version="phase2-test",
            energy_band="broad",
            burst_phase=BURST_BODY,
            trial_count=10,
            recovered_count=0,
            amp50=None,
            amp90=None,
            amp95=None,
            upper_limit_amp=None,
            curve_uri="fixture://curve",
            valid_for_primary_model=False,
        )


def test_fixture_loads_contract_valid_products() -> None:
    fixture = load_injection_recovery_fixture(FIXTURE_PATH)

    assert isinstance(fixture, InjectionRecoveryFixture)
    assert fixture.grid.config_hash == (
        "9dfb586ed84f08b62b771b7d58cfbf548526b3100386227191c6a91e7bc50125"
    )
    assert fixture.grid.config_id == "injection-recovery-9dfb586ed84f08b6"
    assert [trial.trial_id for trial in fixture.trials] == [
        "fixture-trial-001",
        "fixture-trial-002",
    ]
    assert [trial.recovery_classification for trial in fixture.trials] == [
        RECOVERED,
        NOT_RECOVERED,
    ]
    assert fixture.sensitivities[0].amp50 == pytest.approx(0.052)
    assert fixture.sensitivities[0].amp90 == pytest.approx(0.081)
    assert fixture.sensitivities[0].amp95 == pytest.approx(0.094)


def test_fixture_rejects_mismatched_injection_hash() -> None:
    grid = _grid()
    trial = _recovered_trial(injection_config_hash="wrong-hash")
    sensitivity = _sensitivity(injection_config_hash=grid.config_hash)

    with pytest.raises(InjectionRecoveryContractError, match="injection_config_hash"):
        InjectionRecoveryFixture(
            grid=grid,
            trials=(trial,),
            sensitivities=(sensitivity,),
        )


def _grid() -> InjectionGridSpec:
    return InjectionGridSpec(
        search_config_hash="search-hash",
        amplitude_grid=(0.03, 0.06, 0.09),
        frequency_offsets_hz=(-0.5, 0.0, 0.5),
        drift_models=(CONSTANT_DRIFT,),
        burst_phases=(BURST_BODY,),
        energy_bands=("broad",),
        trials_per_cell=8,
        random_seed=123,
        count_rate_envelope_ref="fixture://envelope",
    )


def _recovered_trial(
    *,
    injection_config_hash: str | None = None,
) -> InjectionTrialProduct:
    grid = _grid()
    return InjectionTrialProduct(
        trial_id="trial",
        burst_id="burst",
        source_id="source",
        obs_id="obs",
        instrument="RXTE/PCA",
        search_config_hash=grid.search_config_hash,
        injection_config_hash=injection_config_hash or grid.config_hash,
        pipeline_version="phase2-test",
        injected_freq_hz=581.0,
        injected_amp=0.06,
        injected_phase_rad=0.0,
        injected_burst_phase=BURST_BODY,
        injected_drift_model=LINEAR_DRIFT,
        injected_drift={"nudot_hz_per_s": 0.1},
        energy_band="broad",
        random_seed=1,
        recovered=True,
        recovery_classification=RECOVERED,
        recovered_power=30.0,
        recovered_amp=0.058,
        recovered_freq_hz=581.02,
        recovered_phase_rad=0.1,
        p_single=0.0001,
        p_trials=0.01,
    )


def _sensitivity(
    *,
    injection_config_hash: str | None = None,
) -> BurstSensitivityProduct:
    grid = _grid()
    return BurstSensitivityProduct(
        sensitivity_id="sensitivity",
        burst_id="burst",
        source_id="source",
        obs_id="obs",
        instrument="RXTE/PCA",
        search_config_hash=grid.search_config_hash,
        injection_config_hash=injection_config_hash or grid.config_hash,
        pipeline_version="phase2-test",
        energy_band="broad",
        burst_phase=BURST_BODY,
        trial_count=10,
        recovered_count=8,
        amp50=0.05,
        amp90=0.08,
        amp95=0.09,
        upper_limit_amp=0.08,
        curve_uri="fixture://curve",
        valid_for_primary_model=True,
    )
