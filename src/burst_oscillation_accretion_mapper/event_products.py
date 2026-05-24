"""In-memory event product primitives for Phase 1 RXTE validation.

These classes are deliberately small and mission-neutral. RXTE-specific readers
can build these products after archive extraction, screening, and time
correction are implemented.
"""

from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass, field
from math import isfinite

from .time_intervals import TimeInterval, clip_to_gti, merge_intervals, total_duration


class EventProductError(ValueError):
    """Raised when an event product is internally inconsistent."""


@dataclass(frozen=True)
class EventProductProvenance:
    """Minimal provenance carried by Phase 1 event products."""

    raw_uri: str = ""
    software_version: str = ""
    caldb_version: str = ""
    screening_hash: str = ""
    barycorr_ref: str = ""
    barycorr_applied: bool = False
    binarycorr_ref: str = ""
    binarycorr_applied: bool = False
    notes: str = ""


@dataclass(frozen=True)
class EventProduct:
    """A screened event list with metadata and GTI provenance.

    Event times use the product's documented time system. Intervals are
    half-open and event arrays must be sorted by time.
    """

    source_id: str
    obs_id: str
    instrument: str
    times: tuple[float, ...]
    gtis: tuple[TimeInterval, ...]
    energies: tuple[float, ...] = ()
    detector_ids: tuple[str, ...] = ()
    provenance: EventProductProvenance = field(
        default_factory=EventProductProvenance
    )

    def __post_init__(self) -> None:
        times = tuple(self.times)
        gtis = merge_intervals(self.gtis)
        energies = tuple(self.energies)
        detector_ids = tuple(self.detector_ids)

        _require_value(self.source_id, "source_id")
        _require_value(self.obs_id, "obs_id")
        _require_value(self.instrument, "instrument")
        _require_finite_times(times)
        _require_sorted_times(times)
        _require_optional_column_length("energies", energies, len(times))
        _require_optional_column_length("detector_ids", detector_ids, len(times))
        _require_events_inside_gtis(times, gtis)

        object.__setattr__(self, "times", times)
        object.__setattr__(self, "gtis", gtis)
        object.__setattr__(self, "energies", energies)
        object.__setattr__(self, "detector_ids", detector_ids)

    @property
    def n_events(self) -> int:
        return len(self.times)

    @property
    def exposure_s(self) -> float:
        return total_duration(self.gtis)

    def select_time_interval(self, interval: TimeInterval) -> "EventProduct":
        """Return events in one requested interval clipped to this product's GTIs."""

        return self.select_time_intervals((interval,))

    def select_time_intervals(
        self, intervals: tuple[TimeInterval, ...]
    ) -> "EventProduct":
        """Return events in requested intervals after clipping to GTIs."""

        clipped = tuple(
            clipped_interval
            for interval in intervals
            for clipped_interval in clip_to_gti(interval, self.gtis)
        )
        clipped = merge_intervals(clipped)
        indices = _indices_in_intervals(self.times, clipped)
        return self._subset(indices, clipped)

    def select_energy_range(self, low: float, high: float) -> "EventProduct":
        """Return events in a half-open energy range: ``low <= energy < high``."""

        if not self.energies:
            raise EventProductError("Cannot select an energy range without energies")
        if not isfinite(low) or not isfinite(high) or high <= low:
            raise EventProductError(f"Invalid energy range: {low}, {high}")

        indices = tuple(
            index
            for index, energy in enumerate(self.energies)
            if low <= energy < high
        )
        return self._subset(indices, self.gtis)

    def _subset(
        self, indices: tuple[int, ...], gtis: tuple[TimeInterval, ...]
    ) -> "EventProduct":
        return EventProduct(
            source_id=self.source_id,
            obs_id=self.obs_id,
            instrument=self.instrument,
            times=tuple(self.times[index] for index in indices),
            gtis=gtis,
            energies=tuple(self.energies[index] for index in indices)
            if self.energies
            else (),
            detector_ids=tuple(self.detector_ids[index] for index in indices)
            if self.detector_ids
            else (),
            provenance=self.provenance,
        )


def _require_value(value: str, field_name: str) -> None:
    if not value.strip():
        raise EventProductError(f"{field_name} is required")


def _require_finite_times(times: tuple[float, ...]) -> None:
    for time in times:
        if not isfinite(time):
            raise EventProductError(f"Event time must be finite: {time}")


def _require_sorted_times(times: tuple[float, ...]) -> None:
    for earlier, later in zip(times, times[1:]):
        if later < earlier:
            raise EventProductError("Event times must be sorted")


def _require_optional_column_length(
    field_name: str, values: tuple[object, ...], n_events: int
) -> None:
    if values and len(values) != n_events:
        raise EventProductError(
            f"{field_name} length {len(values)} does not match event count {n_events}"
        )


def _require_events_inside_gtis(
    times: tuple[float, ...], gtis: tuple[TimeInterval, ...]
) -> None:
    if not gtis and times:
        raise EventProductError("Event products with events must include GTIs")

    intervals = merge_intervals(gtis)
    for time in times:
        if not any(interval.contains(time) for interval in intervals):
            raise EventProductError(f"Event time falls outside GTIs: {time}")


def _indices_in_intervals(
    times: tuple[float, ...], intervals: tuple[TimeInterval, ...]
) -> tuple[int, ...]:
    indices: list[int] = []
    for interval in intervals:
        start_index = bisect_left(times, interval.start)
        stop_index = bisect_left(times, interval.stop)
        indices.extend(range(start_index, stop_index))
    return tuple(indices)
