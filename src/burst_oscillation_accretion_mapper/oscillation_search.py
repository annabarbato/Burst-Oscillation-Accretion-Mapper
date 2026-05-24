"""Targeted event-based oscillation search primitives for Phase 1.

This module implements a narrow `Z_n^2` search around known source frequencies
for RXTE validation bursts. It is not a blind 500 Hz to 1 kHz scanner, does not
assign candidate classes, and does not perform trials correction yet.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import cos, floor, isfinite, pi, sin

from .event_products import EventProduct
from .time_intervals import TimeInterval


TARGETED_SEARCH_MODE = "targeted_known_frequency"


class OscillationSearchError(ValueError):
    """Raised when targeted oscillation-search inputs are invalid."""


@dataclass(frozen=True)
class TargetedFrequencyGrid:
    """Symmetric search grid around a known spin or burst-oscillation frequency."""

    center_hz: float
    half_width_hz: float
    step_hz: float

    def __post_init__(self) -> None:
        if not isfinite(self.center_hz) or self.center_hz <= 0:
            raise OscillationSearchError(f"Invalid center_hz: {self.center_hz}")
        if not isfinite(self.half_width_hz) or self.half_width_hz < 0:
            raise OscillationSearchError(
                f"Invalid half_width_hz: {self.half_width_hz}"
            )
        if not isfinite(self.step_hz) or self.step_hz <= 0:
            raise OscillationSearchError(f"Invalid step_hz: {self.step_hz}")

    @property
    def frequencies_hz(self) -> tuple[float, ...]:
        steps_each_side = floor(self.half_width_hz / self.step_hz)
        return tuple(
            round(self.center_hz + step * self.step_hz, 12)
            for step in range(-steps_each_side, steps_each_side + 1)
        )


@dataclass(frozen=True)
class TargetedZ2SearchConfig:
    """Configuration for one targeted `Z_n^2` search window."""

    frequency_grid: TargetedFrequencyGrid
    n_harmonics: int = 1
    min_photons: int = 1
    reference_time: float | None = None

    def __post_init__(self) -> None:
        if self.n_harmonics < 1:
            raise OscillationSearchError("n_harmonics must be at least 1")
        if self.min_photons < 1:
            raise OscillationSearchError("min_photons must be at least 1")
        if self.reference_time is not None and not isfinite(self.reference_time):
            raise OscillationSearchError("reference_time must be finite when set")


@dataclass(frozen=True)
class SlidingWindowConfig:
    """Configuration for sliding targeted-search windows."""

    window_size_s: float
    step_s: float

    def __post_init__(self) -> None:
        if not isfinite(self.window_size_s) or self.window_size_s <= 0:
            raise OscillationSearchError(f"Invalid window_size_s: {self.window_size_s}")
        if not isfinite(self.step_s) or self.step_s <= 0:
            raise OscillationSearchError(f"Invalid step_s: {self.step_s}")


@dataclass(frozen=True)
class Z2FrequencyPower:
    """`Z_n^2` power measured at one trial frequency."""

    frequency_hz: float
    z2_power: float
    n_harmonics: int
    photon_count: int


@dataclass(frozen=True)
class TargetedZ2SearchResult:
    """Intermediate targeted oscillation-search result for one event window."""

    source_id: str
    obs_id: str
    instrument: str
    window: TimeInterval
    effective_exposure_s: float
    search_mode: str
    powers: tuple[Z2FrequencyPower, ...]

    @property
    def photon_count(self) -> int:
        return self.powers[0].photon_count if self.powers else 0

    @property
    def n_harmonics(self) -> int:
        return self.powers[0].n_harmonics if self.powers else 0

    @property
    def best_power(self) -> Z2FrequencyPower:
        if not self.powers:
            raise OscillationSearchError("Cannot choose a best power from no trials")
        return max(self.powers, key=lambda power: (power.z2_power, -power.frequency_hz))

    @property
    def best_frequency_hz(self) -> float:
        return self.best_power.frequency_hz

    @property
    def best_z2_power(self) -> float:
        return self.best_power.z2_power


@dataclass(frozen=True)
class SlidingTargetedZ2SearchResult:
    """Targeted `Z_n^2` search results over multiple sliding windows."""

    source_id: str
    obs_id: str
    instrument: str
    search_mode: str
    window_results: tuple[TargetedZ2SearchResult, ...]
    skipped_windows: tuple[TimeInterval, ...]

    @property
    def searched_window_count(self) -> int:
        return len(self.window_results)

    @property
    def skipped_window_count(self) -> int:
        return len(self.skipped_windows)

    @property
    def trial_count(self) -> int:
        return sum(len(result.powers) for result in self.window_results)

    @property
    def best_result(self) -> TargetedZ2SearchResult:
        if not self.window_results:
            raise OscillationSearchError("Cannot choose a best result from no windows")
        return max(
            self.window_results,
            key=lambda result: (
                result.best_z2_power,
                -result.window.start,
                -result.best_frequency_hz,
            ),
        )

    @property
    def best_frequency_hz(self) -> float:
        return self.best_result.best_frequency_hz

    @property
    def best_z2_power(self) -> float:
        return self.best_result.best_z2_power


def z_n_squared(
    times: tuple[float, ...],
    *,
    frequency_hz: float,
    n_harmonics: int = 1,
    reference_time: float | None = None,
) -> float:
    """Compute the event-based `Z_n^2` statistic for one trial frequency."""

    _validate_times(times)
    _validate_frequency(frequency_hz)
    if n_harmonics < 1:
        raise OscillationSearchError("n_harmonics must be at least 1")
    if reference_time is not None and not isfinite(reference_time):
        raise OscillationSearchError("reference_time must be finite when set")

    time_zero = times[0] if reference_time is None else reference_time
    power_sum = 0.0
    for harmonic in range(1, n_harmonics + 1):
        cosine_sum = 0.0
        sine_sum = 0.0
        for time in times:
            phase = 2.0 * pi * harmonic * frequency_hz * (time - time_zero)
            cosine_sum += cos(phase)
            sine_sum += sin(phase)
        power_sum += cosine_sum * cosine_sum + sine_sum * sine_sum

    return 2.0 * power_sum / len(times)


def make_sliding_windows(
    interval: TimeInterval, *, config: SlidingWindowConfig
) -> tuple[TimeInterval, ...]:
    """Create full sliding windows inside a requested search interval."""

    if interval.duration < config.window_size_s:
        return ()

    n_steps = floor((interval.duration - config.window_size_s) / config.step_s) + 1
    return tuple(
        TimeInterval(
            round(interval.start + index * config.step_s, 12),
            round(interval.start + index * config.step_s + config.window_size_s, 12),
        )
        for index in range(n_steps)
    )


def search_event_product_targeted_z2(
    event_product: EventProduct,
    *,
    window: TimeInterval,
    config: TargetedZ2SearchConfig,
) -> TargetedZ2SearchResult:
    """Search one event-product window over a targeted known-frequency grid."""

    selected = event_product.select_time_interval(window)
    if selected.n_events < config.min_photons:
        raise OscillationSearchError(
            f"Window has {selected.n_events} photons; "
            f"minimum is {config.min_photons}"
        )

    powers = tuple(
        Z2FrequencyPower(
            frequency_hz=frequency_hz,
            z2_power=z_n_squared(
                selected.times,
                frequency_hz=frequency_hz,
                n_harmonics=config.n_harmonics,
                reference_time=config.reference_time,
            ),
            n_harmonics=config.n_harmonics,
            photon_count=selected.n_events,
        )
        for frequency_hz in config.frequency_grid.frequencies_hz
    )
    return TargetedZ2SearchResult(
        source_id=event_product.source_id,
        obs_id=event_product.obs_id,
        instrument=event_product.instrument,
        window=window,
        effective_exposure_s=selected.exposure_s,
        search_mode=TARGETED_SEARCH_MODE,
        powers=powers,
    )


def search_event_product_sliding_targeted_z2(
    event_product: EventProduct,
    *,
    interval: TimeInterval,
    window_config: SlidingWindowConfig,
    search_config: TargetedZ2SearchConfig,
) -> SlidingTargetedZ2SearchResult:
    """Run targeted known-frequency searches over sliding event windows."""

    windows = make_sliding_windows(interval, config=window_config)
    window_results: list[TargetedZ2SearchResult] = []
    skipped_windows: list[TimeInterval] = []

    for window in windows:
        selected = event_product.select_time_interval(window)
        if selected.n_events < search_config.min_photons:
            skipped_windows.append(window)
            continue
        window_results.append(
            search_event_product_targeted_z2(
                event_product,
                window=window,
                config=search_config,
            )
        )

    return SlidingTargetedZ2SearchResult(
        source_id=event_product.source_id,
        obs_id=event_product.obs_id,
        instrument=event_product.instrument,
        search_mode=TARGETED_SEARCH_MODE,
        window_results=tuple(window_results),
        skipped_windows=tuple(skipped_windows),
    )


def _validate_frequency(frequency_hz: float) -> None:
    if not isfinite(frequency_hz) or frequency_hz <= 0:
        raise OscillationSearchError(f"Invalid frequency_hz: {frequency_hz}")


def _validate_times(times: tuple[float, ...]) -> None:
    if not times:
        raise OscillationSearchError("At least one event time is required")
    for time in times:
        if not isfinite(time):
            raise OscillationSearchError(f"Event time must be finite: {time}")
