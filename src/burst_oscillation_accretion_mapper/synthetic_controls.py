"""Synthetic Poisson null controls for Phase 1 false-alarm checks.

These helpers estimate a piecewise-constant count-rate envelope from an event
product and generate null Poisson event products with the same envelope. They do
not inject coherent oscillations, estimate sensitivity curves, or perform
trials correction.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from random import Random

from .event_products import EventProduct, EventProductProvenance
from .time_intervals import TimeInterval, clip_to_gti


class SyntheticControlError(ValueError):
    """Raised when synthetic null-control inputs are invalid."""


@dataclass(frozen=True)
class PoissonEnvelopeBin:
    """One piecewise-constant count-rate bin for a synthetic null control."""

    interval: TimeInterval
    rate_per_s: float

    def __post_init__(self) -> None:
        if not isfinite(self.rate_per_s) or self.rate_per_s < 0:
            raise SyntheticControlError("rate_per_s must be finite and non-negative")


@dataclass(frozen=True)
class PoissonEnvelopeConfig:
    """Configuration for estimating a null-control count-rate envelope."""

    bin_size_s: float

    def __post_init__(self) -> None:
        _require_positive(self.bin_size_s, "bin_size_s")


@dataclass(frozen=True)
class SyntheticPoissonControlConfig:
    """Configuration for repeatable synthetic Poisson null controls."""

    envelope_bin_size_s: float
    realization_count: int = 1
    base_seed: int = 0

    def __post_init__(self) -> None:
        _require_positive(self.envelope_bin_size_s, "envelope_bin_size_s")
        _require_positive_int(self.realization_count, "realization_count")
        _require_non_negative_int(self.base_seed, "base_seed")

    def seed_for_realization(self, realization_number: int) -> int:
        """Return a deterministic seed for a 1-based realization number."""

        _require_positive_int(realization_number, "realization_number")
        return self.base_seed + realization_number - 1


def estimate_poisson_count_rate_envelope(
    event_product: EventProduct,
    *,
    interval: TimeInterval,
    config: PoissonEnvelopeConfig,
) -> tuple[PoissonEnvelopeBin, ...]:
    """Estimate a piecewise-constant count-rate envelope from observed events."""

    envelope_bins: list[PoissonEnvelopeBin] = []
    for clipped in clip_to_gti(interval, event_product.gtis):
        start = clipped.start
        while start < clipped.stop:
            stop = min(start + config.bin_size_s, clipped.stop)
            bin_interval = TimeInterval(start, stop)
            event_count = sum(
                1 for event_time in event_product.times if bin_interval.contains(event_time)
            )
            envelope_bins.append(
                PoissonEnvelopeBin(
                    interval=bin_interval,
                    rate_per_s=event_count / bin_interval.duration,
                )
            )
            start = stop
    return tuple(envelope_bins)


def generate_synthetic_poisson_event_product(
    template_event_product: EventProduct,
    *,
    envelope: tuple[PoissonEnvelopeBin, ...],
    seed: int,
    realization_number: int = 1,
) -> EventProduct:
    """Generate a null Poisson event product from a count-rate envelope."""

    _require_non_negative_int(seed, "seed")
    _require_positive_int(realization_number, "realization_number")
    rng = Random(seed)
    times: list[float] = []
    for envelope_bin in sorted(envelope, key=lambda item: item.interval):
        times.extend(_sample_poisson_process_times(envelope_bin, rng))

    return EventProduct(
        source_id=template_event_product.source_id,
        obs_id=(
            f"{template_event_product.obs_id}-synthetic-poisson-"
            f"{realization_number:03d}"
        ),
        instrument=template_event_product.instrument,
        times=tuple(sorted(times)),
        gtis=tuple(envelope_bin.interval for envelope_bin in envelope),
        provenance=_synthetic_provenance(
            template_event_product.provenance,
            seed=seed,
            realization_number=realization_number,
            envelope_bin_count=len(envelope),
        ),
    )


def _sample_poisson_process_times(
    envelope_bin: PoissonEnvelopeBin, rng: Random
) -> tuple[float, ...]:
    if envelope_bin.rate_per_s == 0:
        return ()

    times: list[float] = []
    event_time = envelope_bin.interval.start
    while True:
        event_time += rng.expovariate(envelope_bin.rate_per_s)
        if event_time >= envelope_bin.interval.stop:
            break
        times.append(round(event_time, 12))
    return tuple(times)


def _synthetic_provenance(
    template: EventProductProvenance,
    *,
    seed: int,
    realization_number: int,
    envelope_bin_count: int,
) -> EventProductProvenance:
    note = (
        "synthetic_poisson_null; "
        f"seed={seed}; "
        f"realization={realization_number}; "
        f"envelope_bins={envelope_bin_count}"
    )
    notes = f"{template.notes}; {note}" if template.notes else note
    return EventProductProvenance(
        raw_uri=f"synthetic-poisson:{template.raw_uri}",
        software_version=template.software_version,
        caldb_version=template.caldb_version,
        screening_hash=template.screening_hash,
        barycorr_ref=template.barycorr_ref,
        barycorr_applied=template.barycorr_applied,
        binarycorr_ref=template.binarycorr_ref,
        binarycorr_applied=template.binarycorr_applied,
        notes=notes,
    )


def _require_positive(value: float, field: str) -> None:
    if not isfinite(value) or value <= 0:
        raise SyntheticControlError(f"{field} must be finite and positive")


def _require_positive_int(value: int, field: str) -> None:
    if type(value) is not int or value < 1:
        raise SyntheticControlError(f"{field} must be a positive integer")


def _require_non_negative_int(value: int, field: str) -> None:
    if type(value) is not int or value < 0:
        raise SyntheticControlError(f"{field} must be a non-negative integer")
