"""Phase 2 injection/recovery product contracts.

This module defines the small, stable product shapes that Phase 2 runners must
emit. It intentionally does not simulate photons, inject signals, run searches,
or estimate sensitivity curves.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from hashlib import sha256
from math import isfinite
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "phase2-injection-recovery-contract-v1"
PRODUCT_KIND = "injection_recovery"

CONSTANT_DRIFT = "constant"
LINEAR_DRIFT = "linear"
EXPONENTIAL_DRIFT = "exponential"
QUADRATIC_DRIFT = "quadratic"
ALLOWED_DRIFT_MODELS = (
    CONSTANT_DRIFT,
    LINEAR_DRIFT,
    EXPONENTIAL_DRIFT,
    QUADRATIC_DRIFT,
)

BURST_RISE = "rise"
BURST_PEAK = "peak"
EARLY_TAIL = "early_tail"
LATE_TAIL = "late_tail"
BURST_BODY = "burst_body"
ALLOWED_BURST_PHASES = (
    BURST_RISE,
    BURST_PEAK,
    EARLY_TAIL,
    LATE_TAIL,
    BURST_BODY,
)

RECOVERED = "recovered"
NOT_RECOVERED = "not_recovered"
REVIEW = "review"
ALLOWED_RECOVERY_CLASSIFICATIONS = (RECOVERED, NOT_RECOVERED, REVIEW)


class InjectionRecoveryContractError(ValueError):
    """Raised when an injection/recovery contract product is invalid."""


@dataclass(frozen=True)
class InjectionGridSpec:
    """Hashable description of the injection/recovery grid for one run."""

    search_config_hash: str
    amplitude_grid: tuple[float, ...]
    frequency_offsets_hz: tuple[float, ...]
    drift_models: tuple[str, ...]
    burst_phases: tuple[str, ...]
    energy_bands: tuple[str, ...]
    trials_per_cell: int
    random_seed: int
    count_rate_envelope_ref: str
    schema_version: str = SCHEMA_VERSION
    product_kind: str = PRODUCT_KIND

    def __post_init__(self) -> None:
        _require_text(self.search_config_hash, "search_config_hash")
        _require_text(self.count_rate_envelope_ref, "count_rate_envelope_ref")
        _require_text(self.schema_version, "schema_version")
        _require_text(self.product_kind, "product_kind")
        if self.schema_version != SCHEMA_VERSION:
            raise InjectionRecoveryContractError(
                f"Unsupported schema_version: {self.schema_version}"
            )
        if self.product_kind != PRODUCT_KIND:
            raise InjectionRecoveryContractError(
                f"Unsupported product_kind: {self.product_kind}"
            )
        _require_non_empty(self.amplitude_grid, "amplitude_grid")
        _require_non_empty(self.frequency_offsets_hz, "frequency_offsets_hz")
        _require_non_empty(self.drift_models, "drift_models")
        _require_non_empty(self.burst_phases, "burst_phases")
        _require_non_empty(self.energy_bands, "energy_bands")
        for amplitude in self.amplitude_grid:
            _require_fraction(amplitude, "amplitude_grid")
            if amplitude == 0:
                raise InjectionRecoveryContractError(
                    "amplitude_grid values must be greater than zero"
                )
        for offset in self.frequency_offsets_hz:
            _require_finite(offset, "frequency_offsets_hz")
        for drift_model in self.drift_models:
            _require_choice(drift_model, ALLOWED_DRIFT_MODELS, "drift_models")
        for burst_phase in self.burst_phases:
            _require_choice(burst_phase, ALLOWED_BURST_PHASES, "burst_phases")
        for energy_band in self.energy_bands:
            _require_text(energy_band, "energy_bands")
        _require_positive_int(self.trials_per_cell, "trials_per_cell")
        _require_non_negative_int(self.random_seed, "random_seed")

    @property
    def payload(self) -> dict[str, object]:
        """Return the normalized payload used for hashing and provenance."""

        return asdict(self)

    @property
    def payload_json(self) -> str:
        """Return canonical JSON for this injection configuration."""

        return _canonical_json(self.payload)

    @property
    def config_hash(self) -> str:
        """Return a stable SHA-256 hash over the normalized grid."""

        return sha256(self.payload_json.encode("utf-8")).hexdigest()

    @property
    def config_id(self) -> str:
        """Return a compact identifier suitable for product rows."""

        return f"injection-recovery-{self.config_hash[:16]}"


@dataclass(frozen=True)
class InjectionTrialProduct:
    """One attempted signal injection and recovery result."""

    trial_id: str
    burst_id: str
    source_id: str
    obs_id: str
    instrument: str
    search_config_hash: str
    injection_config_hash: str
    pipeline_version: str
    injected_freq_hz: float
    injected_amp: float
    injected_phase_rad: float
    injected_burst_phase: str
    injected_drift_model: str
    injected_drift: dict[str, float]
    energy_band: str
    random_seed: int
    recovered: bool
    recovery_classification: str
    recovered_power: float | None = None
    recovered_amp: float | None = None
    recovered_freq_hz: float | None = None
    recovered_phase_rad: float | None = None
    p_single: float | None = None
    p_trials: float | None = None

    def __post_init__(self) -> None:
        for field_name, value in (
            ("trial_id", self.trial_id),
            ("burst_id", self.burst_id),
            ("source_id", self.source_id),
            ("obs_id", self.obs_id),
            ("instrument", self.instrument),
            ("search_config_hash", self.search_config_hash),
            ("injection_config_hash", self.injection_config_hash),
            ("pipeline_version", self.pipeline_version),
            ("injected_burst_phase", self.injected_burst_phase),
            ("injected_drift_model", self.injected_drift_model),
            ("energy_band", self.energy_band),
            ("recovery_classification", self.recovery_classification),
        ):
            _require_text(value, field_name)
        _require_positive(self.injected_freq_hz, "injected_freq_hz")
        _require_fraction(self.injected_amp, "injected_amp")
        if self.injected_amp == 0:
            raise InjectionRecoveryContractError("injected_amp must be greater than zero")
        _require_finite(self.injected_phase_rad, "injected_phase_rad")
        _require_choice(
            self.injected_burst_phase,
            ALLOWED_BURST_PHASES,
            "injected_burst_phase",
        )
        _require_choice(
            self.injected_drift_model,
            ALLOWED_DRIFT_MODELS,
            "injected_drift_model",
        )
        for key, value in self.injected_drift.items():
            _require_text(key, "injected_drift key")
            _require_finite(value, f"injected_drift.{key}")
        _require_non_negative_int(self.random_seed, "random_seed")
        _require_bool(self.recovered, "recovered")
        _require_choice(
            self.recovery_classification,
            ALLOWED_RECOVERY_CLASSIFICATIONS,
            "recovery_classification",
        )
        if self.recovered and self.recovery_classification != RECOVERED:
            raise InjectionRecoveryContractError(
                "recovered trials must use recovery_classification='recovered'"
            )
        if not self.recovered and self.recovery_classification == RECOVERED:
            raise InjectionRecoveryContractError(
                "recovery_classification='recovered' requires recovered=True"
            )
        _require_optional_finite_non_negative(
            self.recovered_power,
            "recovered_power",
        )
        _require_optional_fraction(self.recovered_amp, "recovered_amp")
        _require_optional_positive(self.recovered_freq_hz, "recovered_freq_hz")
        _require_optional_finite(self.recovered_phase_rad, "recovered_phase_rad")
        _require_optional_probability(self.p_single, "p_single")
        _require_optional_probability(self.p_trials, "p_trials")
        if (
            self.p_single is not None
            and self.p_trials is not None
            and self.p_trials < self.p_single
        ):
            raise InjectionRecoveryContractError(
                "p_trials must be greater than or equal to p_single"
            )

    @property
    def recovered_frequency_bias_hz(self) -> float | None:
        """Return recovered minus injected frequency when available."""

        if self.recovered_freq_hz is None:
            return None
        return self.recovered_freq_hz - self.injected_freq_hz

    @property
    def recovered_amplitude_bias(self) -> float | None:
        """Return recovered minus injected fractional rms amplitude when available."""

        if self.recovered_amp is None:
            return None
        return self.recovered_amp - self.injected_amp


@dataclass(frozen=True)
class BurstSensitivityProduct:
    """Aggregate sensitivity summary for one burst, phase, and energy band."""

    sensitivity_id: str
    burst_id: str
    source_id: str
    obs_id: str
    instrument: str
    search_config_hash: str
    injection_config_hash: str
    pipeline_version: str
    energy_band: str
    burst_phase: str
    trial_count: int
    recovered_count: int
    amp50: float | None
    amp90: float | None
    amp95: float | None
    upper_limit_amp: float | None
    curve_uri: str
    valid_for_primary_model: bool
    quality_flags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for field_name, value in (
            ("sensitivity_id", self.sensitivity_id),
            ("burst_id", self.burst_id),
            ("source_id", self.source_id),
            ("obs_id", self.obs_id),
            ("instrument", self.instrument),
            ("search_config_hash", self.search_config_hash),
            ("injection_config_hash", self.injection_config_hash),
            ("pipeline_version", self.pipeline_version),
            ("energy_band", self.energy_band),
            ("burst_phase", self.burst_phase),
            ("curve_uri", self.curve_uri),
        ):
            _require_text(value, field_name)
        _require_choice(self.burst_phase, ALLOWED_BURST_PHASES, "burst_phase")
        _require_positive_int(self.trial_count, "trial_count")
        _require_non_negative_int(self.recovered_count, "recovered_count")
        if self.recovered_count > self.trial_count:
            raise InjectionRecoveryContractError(
                "recovered_count cannot exceed trial_count"
            )
        for field_name, value in (
            ("amp50", self.amp50),
            ("amp90", self.amp90),
            ("amp95", self.amp95),
            ("upper_limit_amp", self.upper_limit_amp),
        ):
            _require_optional_fraction(value, field_name)
        _require_bool(self.valid_for_primary_model, "valid_for_primary_model")
        if self.valid_for_primary_model:
            if self.amp50 is None or self.amp90 is None or self.amp95 is None:
                raise InjectionRecoveryContractError(
                    "valid sensitivity products require amp50, amp90, and amp95"
                )
            if not (self.amp50 <= self.amp90 <= self.amp95):
                raise InjectionRecoveryContractError(
                    "sensitivity thresholds must satisfy amp50 <= amp90 <= amp95"
                )
        elif not self.quality_flags:
            raise InjectionRecoveryContractError(
                "invalid sensitivity products require quality_flags"
            )
        for quality_flag in self.quality_flags:
            _require_text(quality_flag, "quality_flags")


@dataclass(frozen=True)
class InjectionRecoveryFixture:
    """Small tracked fixture containing contract-valid Phase 2 products."""

    grid: InjectionGridSpec
    trials: tuple[InjectionTrialProduct, ...]
    sensitivities: tuple[BurstSensitivityProduct, ...]
    schema_version: str = SCHEMA_VERSION
    description: str = ""

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise InjectionRecoveryContractError(
                f"Unsupported schema_version: {self.schema_version}"
            )
        _require_non_empty(self.trials, "trials")
        _require_non_empty(self.sensitivities, "sensitivities")
        for trial in self.trials:
            _require_matching_hashes(self.grid, trial)
        for sensitivity in self.sensitivities:
            _require_matching_hashes(self.grid, sensitivity)


def injection_grid_from_mapping(payload: dict[str, object]) -> InjectionGridSpec:
    """Create an injection grid spec from JSON-compatible data."""

    return InjectionGridSpec(
        search_config_hash=str(payload["search_config_hash"]),
        amplitude_grid=_float_tuple(payload["amplitude_grid"], "amplitude_grid"),
        frequency_offsets_hz=_float_tuple(
            payload["frequency_offsets_hz"],
            "frequency_offsets_hz",
        ),
        drift_models=_str_tuple(payload["drift_models"], "drift_models"),
        burst_phases=_str_tuple(payload["burst_phases"], "burst_phases"),
        energy_bands=_str_tuple(payload["energy_bands"], "energy_bands"),
        trials_per_cell=int(payload["trials_per_cell"]),
        random_seed=int(payload["random_seed"]),
        count_rate_envelope_ref=str(payload["count_rate_envelope_ref"]),
        schema_version=str(payload.get("schema_version", SCHEMA_VERSION)),
        product_kind=str(payload.get("product_kind", PRODUCT_KIND)),
    )


def injection_trial_from_mapping(payload: dict[str, object]) -> InjectionTrialProduct:
    """Create one trial product from JSON-compatible data."""

    return InjectionTrialProduct(
        trial_id=str(payload["trial_id"]),
        burst_id=str(payload["burst_id"]),
        source_id=str(payload["source_id"]),
        obs_id=str(payload["obs_id"]),
        instrument=str(payload["instrument"]),
        search_config_hash=str(payload["search_config_hash"]),
        injection_config_hash=str(payload["injection_config_hash"]),
        pipeline_version=str(payload["pipeline_version"]),
        injected_freq_hz=float(payload["injected_freq_hz"]),
        injected_amp=float(payload["injected_amp"]),
        injected_phase_rad=float(payload["injected_phase_rad"]),
        injected_burst_phase=str(payload["injected_burst_phase"]),
        injected_drift_model=str(payload["injected_drift_model"]),
        injected_drift=_float_mapping(payload["injected_drift"], "injected_drift"),
        energy_band=str(payload["energy_band"]),
        random_seed=int(payload["random_seed"]),
        recovered=_bool(payload["recovered"], "recovered"),
        recovery_classification=str(payload["recovery_classification"]),
        recovered_power=_optional_float(payload.get("recovered_power")),
        recovered_amp=_optional_float(payload.get("recovered_amp")),
        recovered_freq_hz=_optional_float(payload.get("recovered_freq_hz")),
        recovered_phase_rad=_optional_float(payload.get("recovered_phase_rad")),
        p_single=_optional_float(payload.get("p_single")),
        p_trials=_optional_float(payload.get("p_trials")),
    )


def burst_sensitivity_from_mapping(
    payload: dict[str, object],
) -> BurstSensitivityProduct:
    """Create one burst sensitivity product from JSON-compatible data."""

    return BurstSensitivityProduct(
        sensitivity_id=str(payload["sensitivity_id"]),
        burst_id=str(payload["burst_id"]),
        source_id=str(payload["source_id"]),
        obs_id=str(payload["obs_id"]),
        instrument=str(payload["instrument"]),
        search_config_hash=str(payload["search_config_hash"]),
        injection_config_hash=str(payload["injection_config_hash"]),
        pipeline_version=str(payload["pipeline_version"]),
        energy_band=str(payload["energy_band"]),
        burst_phase=str(payload["burst_phase"]),
        trial_count=int(payload["trial_count"]),
        recovered_count=int(payload["recovered_count"]),
        amp50=_optional_float(payload.get("amp50")),
        amp90=_optional_float(payload.get("amp90")),
        amp95=_optional_float(payload.get("amp95")),
        upper_limit_amp=_optional_float(payload.get("upper_limit_amp")),
        curve_uri=str(payload["curve_uri"]),
        valid_for_primary_model=_bool(
            payload["valid_for_primary_model"],
            "valid_for_primary_model",
        ),
        quality_flags=_str_tuple(payload.get("quality_flags", ()), "quality_flags"),
    )


def injection_recovery_fixture_from_mapping(
    payload: dict[str, object],
) -> InjectionRecoveryFixture:
    """Create a contract fixture from JSON-compatible data."""

    grid = injection_grid_from_mapping(_dict(payload["grid"], "grid"))
    trials = tuple(
        injection_trial_from_mapping(_dict(item, "trial"))
        for item in _list(payload["trials"], "trials")
    )
    sensitivities = tuple(
        burst_sensitivity_from_mapping(_dict(item, "sensitivity"))
        for item in _list(payload["sensitivities"], "sensitivities")
    )
    return InjectionRecoveryFixture(
        grid=grid,
        trials=trials,
        sensitivities=sensitivities,
        schema_version=str(payload.get("schema_version", SCHEMA_VERSION)),
        description=str(payload.get("description", "")),
    )


def load_injection_recovery_fixture(path: str | Path) -> InjectionRecoveryFixture:
    """Load a tracked JSON fixture and validate the contract products."""

    with Path(path).open(encoding="utf-8") as handle:
        payload = json.load(handle)
    return injection_recovery_fixture_from_mapping(_dict(payload, "fixture"))


def _canonical_json(payload: dict[str, object]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _require_matching_hashes(
    grid: InjectionGridSpec,
    product: InjectionTrialProduct | BurstSensitivityProduct,
) -> None:
    if product.search_config_hash != grid.search_config_hash:
        raise InjectionRecoveryContractError(
            f"{product.__class__.__name__} search_config_hash does not match grid"
        )
    if product.injection_config_hash != grid.config_hash:
        raise InjectionRecoveryContractError(
            f"{product.__class__.__name__} injection_config_hash does not match grid"
        )


def _require_text(value: str, field: str) -> None:
    if not value.strip():
        raise InjectionRecoveryContractError(f"{field} is required")


def _require_non_empty(value: tuple[object, ...], field: str) -> None:
    if not value:
        raise InjectionRecoveryContractError(f"{field} is required")


def _require_choice(value: str, allowed_values: tuple[str, ...], field: str) -> None:
    if value not in allowed_values:
        allowed = ", ".join(allowed_values)
        raise InjectionRecoveryContractError(f"{field} must be one of: {allowed}")


def _require_finite(value: float, field: str) -> None:
    if not isfinite(value):
        raise InjectionRecoveryContractError(f"{field} must be finite")


def _require_positive(value: float, field: str) -> None:
    if not isfinite(value) or value <= 0:
        raise InjectionRecoveryContractError(f"{field} must be positive")


def _require_fraction(value: float, field: str) -> None:
    if not isfinite(value) or value < 0 or value > 1:
        raise InjectionRecoveryContractError(f"{field} must be between 0 and 1")


def _require_optional_finite(value: float | None, field: str) -> None:
    if value is not None:
        _require_finite(value, field)


def _require_optional_finite_non_negative(value: float | None, field: str) -> None:
    if value is not None and (not isfinite(value) or value < 0):
        raise InjectionRecoveryContractError(f"{field} must be finite and non-negative")


def _require_optional_positive(value: float | None, field: str) -> None:
    if value is not None:
        _require_positive(value, field)


def _require_optional_fraction(value: float | None, field: str) -> None:
    if value is not None:
        _require_fraction(value, field)


def _require_optional_probability(value: float | None, field: str) -> None:
    if value is not None:
        _require_fraction(value, field)


def _require_positive_int(value: int, field: str) -> None:
    if not isinstance(value, int) or value <= 0:
        raise InjectionRecoveryContractError(f"{field} must be a positive integer")


def _require_non_negative_int(value: int, field: str) -> None:
    if not isinstance(value, int) or value < 0:
        raise InjectionRecoveryContractError(
            f"{field} must be a non-negative integer"
        )


def _require_bool(value: bool, field: str) -> None:
    if not isinstance(value, bool):
        raise InjectionRecoveryContractError(f"{field} must be a boolean")


def _float_tuple(value: object, field: str) -> tuple[float, ...]:
    return tuple(float(item) for item in _list(value, field))


def _str_tuple(value: object, field: str) -> tuple[str, ...]:
    return tuple(str(item) for item in _list(value, field))


def _float_mapping(value: object, field: str) -> dict[str, float]:
    payload = _dict(value, field)
    return {str(key): float(item) for key, item in payload.items()}


def _optional_float(value: object) -> float | None:
    return None if value is None else float(value)


def _bool(value: object, field: str) -> bool:
    if not isinstance(value, bool):
        raise InjectionRecoveryContractError(f"{field} must be a boolean")
    return value


def _dict(value: object, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise InjectionRecoveryContractError(f"{field} must be an object")
    return value


def _list(value: object, field: str) -> list[object]:
    if not isinstance(value, list | tuple):
        raise InjectionRecoveryContractError(f"{field} must be a list")
    return list(value)
