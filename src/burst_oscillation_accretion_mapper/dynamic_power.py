"""Dynamic power-spectrum products for Phase 1 targeted searches.

This module formats existing sliding targeted-search outputs into regular
window-by-frequency products for review. It does not run a new search, broaden
the frequency range, assign candidate classes, or perform plotting.
"""

from __future__ import annotations

from dataclasses import dataclass

from .oscillation_search import SlidingTargetedZ2SearchResult
from .time_intervals import TimeInterval


class DynamicPowerError(ValueError):
    """Raised when dynamic power-spectrum inputs are inconsistent."""


@dataclass(frozen=True)
class DynamicPowerPeak:
    """Best dynamic-power bin in one window-by-frequency product."""

    window: TimeInterval
    frequency_hz: float
    z2_power: float
    leahy_power: float
    photon_count: int


@dataclass(frozen=True)
class DynamicPowerSpectrum:
    """Regular dynamic power-spectrum grid for one sliding search result."""

    source_id: str
    obs_id: str
    instrument: str
    search_mode: str
    windows: tuple[TimeInterval, ...]
    frequencies_hz: tuple[float, ...]
    z2_power_grid: tuple[tuple[float, ...], ...]
    leahy_power_grid: tuple[tuple[float, ...], ...]
    photon_counts: tuple[int, ...]
    skipped_windows: tuple[TimeInterval, ...]

    @property
    def window_count(self) -> int:
        return len(self.windows)

    @property
    def frequency_count(self) -> int:
        return len(self.frequencies_hz)

    @property
    def trial_count(self) -> int:
        return self.window_count * self.frequency_count

    @property
    def best_peak(self) -> DynamicPowerPeak:
        if not self.windows or not self.frequencies_hz:
            raise DynamicPowerError("Cannot choose a best peak from an empty spectrum")

        best_window_index = 0
        best_frequency_index = 0
        best_power = self.z2_power_grid[0][0]
        for window_index, powers in enumerate(self.z2_power_grid):
            for frequency_index, power in enumerate(powers):
                if power > best_power:
                    best_window_index = window_index
                    best_frequency_index = frequency_index
                    best_power = power

        return DynamicPowerPeak(
            window=self.windows[best_window_index],
            frequency_hz=self.frequencies_hz[best_frequency_index],
            z2_power=best_power,
            leahy_power=self.leahy_power_grid[best_window_index][best_frequency_index],
            photon_count=self.photon_counts[best_window_index],
        )


def dynamic_power_spectrum_from_sliding_result(
    result: SlidingTargetedZ2SearchResult,
) -> DynamicPowerSpectrum:
    """Build a regular dynamic power-spectrum product from sliding results."""

    if not result.window_results:
        return DynamicPowerSpectrum(
            source_id=result.source_id,
            obs_id=result.obs_id,
            instrument=result.instrument,
            search_mode=result.search_mode,
            windows=(),
            frequencies_hz=(),
            z2_power_grid=(),
            leahy_power_grid=(),
            photon_counts=(),
            skipped_windows=result.skipped_windows,
        )

    frequencies_hz = tuple(
        power.frequency_hz for power in result.window_results[0].powers
    )
    if not frequencies_hz:
        raise DynamicPowerError("Sliding search window has no frequency powers")

    windows: list[TimeInterval] = []
    z2_power_grid: list[tuple[float, ...]] = []
    leahy_power_grid: list[tuple[float, ...]] = []
    photon_counts: list[int] = []

    for window_result in result.window_results:
        window_frequencies = tuple(power.frequency_hz for power in window_result.powers)
        if window_frequencies != frequencies_hz:
            raise DynamicPowerError("Sliding search windows use inconsistent grids")
        windows.append(window_result.window)
        z2_power_grid.append(tuple(power.z2_power for power in window_result.powers))
        leahy_power_grid.append(
            tuple(power.leahy_power for power in window_result.powers)
        )
        photon_counts.append(window_result.photon_count)

    return DynamicPowerSpectrum(
        source_id=result.source_id,
        obs_id=result.obs_id,
        instrument=result.instrument,
        search_mode=result.search_mode,
        windows=tuple(windows),
        frequencies_hz=frequencies_hz,
        z2_power_grid=tuple(z2_power_grid),
        leahy_power_grid=tuple(leahy_power_grid),
        photon_counts=tuple(photon_counts),
        skipped_windows=result.skipped_windows,
    )
