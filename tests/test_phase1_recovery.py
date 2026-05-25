import pytest

from burst_oscillation_accretion_mapper.candidate_scoring import (
    MARGINAL_CANDIDATE,
    NON_DETECTION,
    PROBABLE_DETECTION,
)
from burst_oscillation_accretion_mapper.catalog_writer import (
    CandidateCatalogRow,
    ControlCatalogRow,
)
from burst_oscillation_accretion_mapper.phase1_recovery import (
    NOT_RECOVERED,
    RECOVERED,
    REVIEW,
    classify_phase1_recovery,
)
from burst_oscillation_accretion_mapper.time_intervals import TimeInterval


def test_phase1_recovery_accepts_probable_known_detection_with_clear_controls() -> None:
    status = classify_phase1_recovery(
        candidate=_candidate(PROBABLE_DETECTION, z2_power=30.0),
        control_rows=(_control(NON_DETECTION, z2_power=5.0),),
        validation_goal="known_oscillation_recovery",
        expected_signal="secure_detection",
        burst_window=TimeInterval(10.0, 20.0),
        correction_status="applied",
    )

    assert status.recovery_status == RECOVERED
    assert status.p_trials == pytest.approx(0.02)
    assert status.empirical_control_fap == pytest.approx(0.0)
    assert status.phase_window == "burst_body"
    assert "known_signal_frequency_consistent_control_cleared" in status.reason_codes


def test_phase1_recovery_marks_marginal_expected_non_detection_for_review() -> None:
    status = classify_phase1_recovery(
        candidate=_candidate(MARGINAL_CANDIDATE, z2_power=17.0),
        control_rows=(_control(NON_DETECTION, z2_power=5.0),),
        validation_goal="non_detection_control",
        expected_signal="non_detection",
        burst_window=TimeInterval(10.0, 20.0),
        correction_status="already_applied",
    )

    assert status.recovery_status == REVIEW
    assert "expected_non_detection_marginal_review" in status.reason_codes


def test_phase1_recovery_keeps_non_detection_as_not_recovered_control() -> None:
    status = classify_phase1_recovery(
        candidate=_candidate(NON_DETECTION, z2_power=8.0),
        control_rows=(_control(NON_DETECTION, z2_power=5.0),),
        validation_goal="non_detection_control",
        expected_signal="non_detection",
        burst_window=TimeInterval(10.0, 20.0),
        correction_status="applied",
    )

    assert status.recovery_status == NOT_RECOVERED
    assert "expected_non_detection_no_candidate" in status.reason_codes


def _candidate(classification: str, *, z2_power: float) -> CandidateCatalogRow:
    return CandidateCatalogRow(
        candidate_id="candidate",
        burst_id="burst",
        source_id="source",
        obs_id="obs",
        instrument="RXTE/PCA",
        search_mode="targeted_known_frequency",
        classification=classification,
        trial_count=41,
        photon_count=100,
        energy_band="full",
        window_start=12.0,
        window_stop=16.0,
        frequency_hz=581.0,
        expected_frequency_hz=581.0,
        frequency_offset_hz=0.0,
        z2_power=z2_power,
        leahy_power=z2_power,
        n_harmonics=1,
        p_single=0.001,
        p_trials=0.02,
        fractional_rms=0.1,
        phase_rad=1.0,
        reasons=(),
        pipeline_version="phase1-test",
        search_config_id="targeted",
        provenance_note="fixture",
    )


def _control(classification: str, *, z2_power: float) -> ControlCatalogRow:
    return ControlCatalogRow(
        control_id="control",
        burst_id="burst",
        control_kind="pre_burst",
        control_start=0.0,
        control_stop=4.0,
        requested_start=0.0,
        requested_stop=4.0,
        source_id="source",
        obs_id="obs",
        instrument="RXTE/PCA",
        search_mode="targeted_known_frequency",
        classification=classification,
        trial_count=41,
        photon_count=100,
        energy_band="full",
        window_start=0.0,
        window_stop=4.0,
        frequency_hz=581.0,
        expected_frequency_hz=581.0,
        frequency_offset_hz=0.0,
        z2_power=z2_power,
        leahy_power=z2_power,
        n_harmonics=1,
        p_single=0.1,
        p_trials=0.5,
        fractional_rms=0.1,
        phase_rad=1.0,
        reasons=(),
        pipeline_version="phase1-test",
        search_config_id="targeted",
        provenance_note="fixture",
    )
