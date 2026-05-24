"""Light-curve binning primitives for Phase 1 burst detection."""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil, isfinite

from .event_products import EventProduct
from .time_intervals import TimeInterval, clip_to_gti, total_duration


class LightCurveError(ValueError):
    """Raised when a light-curve request is invalid."""


@dataclass(frozen=True)
class LightCurve:
    """A binned event light curve with GTI-corrected exposure."""

    bin_size: float
    bin_starts: tuple[float, ...]
    bin_stops: tuple[float, ...]
    counts: tuple[int, ...]
    exposures: tuple[float, ...]

    def __post_init__(self) -> None:
        lengths = {
            len(self.bin_starts),
            len(self.bin_stops),
            len(self.counts),
            len(self.exposures),
        }
        if len(lengths) != 1:
            raise LightCurveError("Light-curve columns must have matching lengths")
        if not isfinite(self.bin_size) or self.bin_size <= 0:
            raise LightCurveError(f"Invalid bin_size: {self.bin_size}")

    @property
    def n_bins(self) -> int:
        return len(self.counts)

    @property
    def total_counts(self) -> int:
        return sum(self.counts)

    @property
    def total_exposure(self) -> float:
        return sum(self.exposures)

    @property
    def rates(self) -> tuple[float | None, ...]:
        return tuple(
            count / exposure if exposure > 0 else None
            for count, exposure in zip(self.counts, self.exposures)
        )

    @property
    def bin_intervals(self) -> tuple[TimeInterval, ...]:
        return tuple(
            TimeInterval(start, stop)
            for start, stop in zip(self.bin_starts, self.bin_stops)
        )


def make_light_curve(
    event_product: EventProduct, *, interval: TimeInterval, bin_size: float
) -> LightCurve:
    """Bin event times over one requested interval.

    Bins are half-open and the final bin is truncated when the requested
    interval is not an exact multiple of `bin_size`. Exposure is computed from
    the overlap between each bin and the event product GTIs.
    """

    if not isfinite(bin_size) or bin_size <= 0:
        raise LightCurveError(f"Invalid bin_size: {bin_size}")

    bins = _make_bins(interval, bin_size)
    counts = [0 for _ in bins]
    for time in event_product.times:
        if not interval.contains(time):
            continue
        index = int((time - interval.start) // bin_size)
        if 0 <= index < len(counts):
            counts[index] += 1

    exposures = tuple(
        total_duration(clip_to_gti(bin_interval, event_product.gtis))
        for bin_interval in bins
    )
    return LightCurve(
        bin_size=bin_size,
        bin_starts=tuple(bin_interval.start for bin_interval in bins),
        bin_stops=tuple(bin_interval.stop for bin_interval in bins),
        counts=tuple(counts),
        exposures=exposures,
    )


def _make_bins(interval: TimeInterval, bin_size: float) -> tuple[TimeInterval, ...]:
    n_bins = ceil(interval.duration / bin_size)
    return tuple(
        TimeInterval(
            interval.start + index * bin_size,
            min(interval.start + (index + 1) * bin_size, interval.stop),
        )
        for index in range(n_bins)
    )
