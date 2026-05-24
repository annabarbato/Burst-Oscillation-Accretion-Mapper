"""Light-curve binning primitives for Phase 1 burst detection."""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil, isfinite
from statistics import median

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


@dataclass(frozen=True)
class BaselineEstimate:
    """Rolling robust baseline estimate for a light curve."""

    rates: tuple[float | None, ...]
    reference_bin_counts: tuple[int, ...]

    def __post_init__(self) -> None:
        if len(self.rates) != len(self.reference_bin_counts):
            raise LightCurveError("Baseline columns must have matching lengths")


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


def estimate_rolling_baseline(
    light_curve: LightCurve,
    *,
    window_bins: int,
    excluded_bins: frozenset[int] = frozenset(),
) -> BaselineEstimate:
    """Estimate a local persistent baseline with a rolling median.

    The estimator uses finite-rate bins inside `window_bins` on either side of
    each bin, including the current bin unless it is explicitly excluded. Bins
    with zero exposure are ignored. This is intentionally a preprocessing
    primitive; later burst-detection code should decide which flare or burst
    candidates to exclude and when to recompute the baseline.
    """

    if window_bins < 1:
        raise LightCurveError("window_bins must be at least 1")

    rates = light_curve.rates
    baselines: list[float | None] = []
    reference_counts: list[int] = []
    for index in range(light_curve.n_bins):
        start = max(0, index - window_bins)
        stop = min(light_curve.n_bins, index + window_bins + 1)
        reference_rates = [
            rate
            for reference_index, rate in enumerate(rates[start:stop], start=start)
            if reference_index not in excluded_bins and rate is not None
        ]
        reference_counts.append(len(reference_rates))
        baselines.append(float(median(reference_rates)) if reference_rates else None)

    return BaselineEstimate(tuple(baselines), tuple(reference_counts))


def _make_bins(interval: TimeInterval, bin_size: float) -> tuple[TimeInterval, ...]:
    n_bins = ceil(interval.duration / bin_size)
    return tuple(
        TimeInterval(
            interval.start + index * bin_size,
            min(interval.start + (index + 1) * bin_size, interval.stop),
        )
        for index in range(n_bins)
    )
