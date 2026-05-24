"""Conservative oscillation-candidate scoring primitives for Phase 1.

This module turns targeted search products into review records with configured
candidate classes. It does not compute p-values, perform trials correction, or
write catalog rows. Secure labels require explicit evidence flags so missing
control, sensitivity, coherence, or phase-evolution checks remain visible.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from .oscillation_search import (
    SlidingTargetedZ2SearchResult,
    TargetedZ2SearchResult,
    Z2FrequencyPower,
)
from .time_intervals import TimeInterval


SECURE_DETECTION = "secure_detection"
PROBABLE_DETECTION = "probable_detection"
MARGINAL_CANDIDATE = "marginal_candidate"
NON_DETECTION = "non_detection"


class CandidateScoringError(ValueError):
    """Raised when candidate-scoring inputs are invalid."""


@dataclass(frozen=True)
class CandidateEvidenceFlags:
    """External evidence needed for conservative candidate promotion."""

    physically_plausible_phase: bool = True
    control_clearance: bool = False
    sensitivity_confirmed: bool = False
    coherent_structure: bool = False
    phase_evolution_ok: bool = False

    @property
    def supports_secure_detection(self) -> bool:
        return (
            self.physically_plausible_phase
            and self.control_clearance
            and self.sensitivity_confirmed
            and self.coherent_structure
            and self.phase_evolution_ok
        )

    @property
    def missing_secure_reasons(self) -> tuple[str, ...]:
        reasons: list[str] = []
        if not self.physically_plausible_phase:
            reasons.append("phase_not_physically_plausible")
        if not self.control_clearance:
            reasons.append("control_clearance_missing")
        if not self.sensitivity_confirmed:
            reasons.append("sensitivity_confirmation_missing")
        if not self.coherent_structure:
            reasons.append("coherent_structure_missing")
        if not self.phase_evolution_ok:
            reasons.append("phase_evolution_check_missing")
        return tuple(reasons)


@dataclass(frozen=True)
class CandidateScoringConfig:
    """Configured `Z_n^2` thresholds for candidate review classes."""

    marginal_z2_threshold: float
    probable_z2_threshold: float
    secure_z2_threshold: float
    max_frequency_offset_hz: float | None = None

    def __post_init__(self) -> None:
        _require_positive(self.marginal_z2_threshold, "marginal_z2_threshold")
        _require_positive(self.probable_z2_threshold, "probable_z2_threshold")
        _require_positive(self.secure_z2_threshold, "secure_z2_threshold")
        if not (
            self.marginal_z2_threshold
            <= self.probable_z2_threshold
            <= self.secure_z2_threshold
        ):
            raise CandidateScoringError(
                "Z2 thresholds must satisfy marginal <= probable <= secure"
            )
        if self.max_frequency_offset_hz is not None and (
            not isfinite(self.max_frequency_offset_hz)
            or self.max_frequency_offset_hz < 0
        ):
            raise CandidateScoringError(
                f"Invalid max_frequency_offset_hz: {self.max_frequency_offset_hz}"
            )


@dataclass(frozen=True)
class OscillationCandidateReview:
    """Scored candidate or non-detection summary for one search product."""

    source_id: str
    obs_id: str
    instrument: str
    search_mode: str
    classification: str
    trial_count: int
    photon_count: int
    window: TimeInterval | None
    frequency_hz: float | None
    expected_frequency_hz: float | None
    frequency_offset_hz: float | None
    z2_power: float | None
    n_harmonics: int | None
    fractional_rms: float | None
    phase_rad: float | None
    reasons: tuple[str, ...]

    @property
    def is_detection_like(self) -> bool:
        return self.classification in {
            SECURE_DETECTION,
            PROBABLE_DETECTION,
            MARGINAL_CANDIDATE,
        }


def score_targeted_z2_result(
    result: TargetedZ2SearchResult,
    *,
    config: CandidateScoringConfig,
    expected_frequency_hz: float | None,
    evidence: CandidateEvidenceFlags = CandidateEvidenceFlags(),
) -> OscillationCandidateReview:
    """Score one targeted search window without applying trials correction."""

    return _score_best_power(
        source_id=result.source_id,
        obs_id=result.obs_id,
        instrument=result.instrument,
        search_mode=result.search_mode,
        window=result.window,
        best_power=result.best_power,
        trial_count=len(result.powers),
        expected_frequency_hz=expected_frequency_hz,
        config=config,
        evidence=evidence,
    )


def score_sliding_targeted_z2_result(
    result: SlidingTargetedZ2SearchResult,
    *,
    config: CandidateScoringConfig,
    expected_frequency_hz: float | None,
    evidence: CandidateEvidenceFlags = CandidateEvidenceFlags(),
) -> OscillationCandidateReview:
    """Score the best window from a sliding targeted search result."""

    if not result.window_results:
        return OscillationCandidateReview(
            source_id=result.source_id,
            obs_id=result.obs_id,
            instrument=result.instrument,
            search_mode=result.search_mode,
            classification=NON_DETECTION,
            trial_count=0,
            photon_count=0,
            window=None,
            frequency_hz=None,
            expected_frequency_hz=expected_frequency_hz,
            frequency_offset_hz=None,
            z2_power=None,
            n_harmonics=None,
            fractional_rms=None,
            phase_rad=None,
            reasons=("no_searched_windows",),
        )

    best_result = result.best_result
    return _score_best_power(
        source_id=result.source_id,
        obs_id=result.obs_id,
        instrument=result.instrument,
        search_mode=result.search_mode,
        window=best_result.window,
        best_power=best_result.best_power,
        trial_count=result.trial_count,
        expected_frequency_hz=expected_frequency_hz,
        config=config,
        evidence=evidence,
    )


def _score_best_power(
    *,
    source_id: str,
    obs_id: str,
    instrument: str,
    search_mode: str,
    window: TimeInterval,
    best_power: Z2FrequencyPower,
    trial_count: int,
    expected_frequency_hz: float | None,
    config: CandidateScoringConfig,
    evidence: CandidateEvidenceFlags,
) -> OscillationCandidateReview:
    frequency_offset = _frequency_offset(best_power.frequency_hz, expected_frequency_hz)
    reasons = _scoring_reasons(best_power, frequency_offset, config, evidence)
    classification = _classification(best_power, frequency_offset, config, evidence)

    return OscillationCandidateReview(
        source_id=source_id,
        obs_id=obs_id,
        instrument=instrument,
        search_mode=search_mode,
        classification=classification,
        trial_count=trial_count,
        photon_count=best_power.photon_count,
        window=window,
        frequency_hz=best_power.frequency_hz,
        expected_frequency_hz=expected_frequency_hz,
        frequency_offset_hz=frequency_offset,
        z2_power=best_power.z2_power,
        n_harmonics=best_power.n_harmonics,
        fractional_rms=best_power.first_harmonic_fractional_rms,
        phase_rad=best_power.first_harmonic_phase_rad,
        reasons=reasons,
    )


def _classification(
    best_power: Z2FrequencyPower,
    frequency_offset: float | None,
    config: CandidateScoringConfig,
    evidence: CandidateEvidenceFlags,
) -> str:
    if best_power.z2_power < config.marginal_z2_threshold:
        return NON_DETECTION

    frequency_consistent = _frequency_is_consistent(frequency_offset, config)
    if not frequency_consistent:
        return MARGINAL_CANDIDATE

    if (
        best_power.z2_power >= config.secure_z2_threshold
        and evidence.supports_secure_detection
    ):
        return SECURE_DETECTION

    if (
        best_power.z2_power >= config.probable_z2_threshold
        and evidence.physically_plausible_phase
    ):
        return PROBABLE_DETECTION

    return MARGINAL_CANDIDATE


def _scoring_reasons(
    best_power: Z2FrequencyPower,
    frequency_offset: float | None,
    config: CandidateScoringConfig,
    evidence: CandidateEvidenceFlags,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if best_power.z2_power < config.marginal_z2_threshold:
        reasons.append("z2_below_marginal_threshold")
    elif best_power.z2_power < config.probable_z2_threshold:
        reasons.append("z2_below_probable_threshold")
    elif best_power.z2_power < config.secure_z2_threshold:
        reasons.append("z2_below_secure_threshold")

    if not _frequency_is_consistent(frequency_offset, config):
        reasons.append("frequency_offset_above_threshold")

    if best_power.z2_power >= config.secure_z2_threshold:
        reasons.extend(evidence.missing_secure_reasons)

    return tuple(reasons)


def _frequency_offset(
    frequency_hz: float, expected_frequency_hz: float | None
) -> float | None:
    if expected_frequency_hz is None:
        return None
    _require_positive(expected_frequency_hz, "expected_frequency_hz")
    return abs(frequency_hz - expected_frequency_hz)


def _frequency_is_consistent(
    frequency_offset: float | None, config: CandidateScoringConfig
) -> bool:
    if config.max_frequency_offset_hz is None or frequency_offset is None:
        return True
    return frequency_offset <= config.max_frequency_offset_hz


def _require_positive(value: float, field: str) -> None:
    if not isfinite(value) or value <= 0:
        raise CandidateScoringError(f"{field} must be positive")
