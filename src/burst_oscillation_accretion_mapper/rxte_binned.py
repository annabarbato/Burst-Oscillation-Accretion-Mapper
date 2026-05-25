"""RXTE/PCA high-time binned product ingestion for Phase 1 validation.

Some early RXTE validation targets expose burst-covering high-time Science
Array products but not paired GoodXenon files that `make_se` can convert. This
module reads those binned products as event-equivalent timing products by
placing counts at deterministic bin centers. The provenance must keep the
original binned mode visible; these products are validation inputs, not a
replacement for full event-mode reduction when paired GoodXenon data exist.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from pathlib import Path
from typing import Any

from .event_products import EventProduct, EventProductProvenance
from .time_intervals import TimeInterval, merge_intervals


class RxteBinnedError(ValueError):
    """Raised when an RXTE binned timing product cannot be read."""


@dataclass(frozen=True)
class RxteBinnedReadConfig:
    """Accepted high-time binned RXTE/PCA product shape."""

    table_extension_names: tuple[str, ...] = ("XTE_SA",)
    time_column_names: tuple[str, ...] = ("TIME",)
    count_column_names: tuple[str, ...] = ("XECNT",)
    gti_extension_names: tuple[str, ...] = ("GTI", "STDGTI", "ALLGTI")
    datamode_prefixes: tuple[str, ...] = ("SB_125us",)


def read_rxte_singlebit_event_product(
    path: Path | str,
    *,
    source_id: str,
    obs_id: str,
    provenance: EventProductProvenance,
    config: RxteBinnedReadConfig = RxteBinnedReadConfig(),
    instrument: str = "RXTE/PCA",
) -> EventProduct:
    """Read an RXTE/PCA SingleBit binned file as an event-equivalent product."""

    try:
        from astropy.io import fits
    except Exception as exc:  # pragma: no cover - depends on optional package
        raise RxteBinnedError("Astropy is required to read RXTE binned products") from exc

    fits_path = Path(path)
    try:
        with fits.open(fits_path) as hdul:
            table_hdu = _find_binned_hdu(hdul, config)
            datamode = str(table_hdu.header.get("DATAMODE", ""))
            _validate_datamode(datamode, config)
            times = _column_values(table_hdu, config.time_column_names)
            counts_by_row = _column_values(table_hdu, config.count_column_names)
            time_delta = _time_delta(table_hdu, times)
            gtis = _read_gti_intervals(hdul, config)
            event_times = _expand_counts_to_bin_centers(
                times,
                counts_by_row,
                time_delta=time_delta,
                gtis=gtis,
            )
    except RxteBinnedError:
        raise
    except Exception as exc:
        raise RxteBinnedError(f"Cannot read RXTE binned timing product: {fits_path}") from exc

    if not event_times:
        raise RxteBinnedError(f"No binned events found in {fits_path}")
    if not gtis:
        gtis = (TimeInterval(min(event_times), max(event_times)),)

    return EventProduct(
        source_id=source_id,
        obs_id=obs_id,
        instrument=instrument,
        times=tuple(event_times),
        gtis=merge_intervals(gtis),
        provenance=provenance,
    )


def _find_binned_hdu(hdul: Any, config: RxteBinnedReadConfig) -> Any:
    for hdu in hdul:
        if getattr(hdu, "name", "").upper() not in config.table_extension_names:
            continue
        if _has_any_column(hdu, config.time_column_names) and _has_any_column(
            hdu,
            config.count_column_names,
        ):
            return hdu
    raise RxteBinnedError("No supported RXTE binned timing table was found")


def _validate_datamode(datamode: str, config: RxteBinnedReadConfig) -> None:
    if not any(datamode.startswith(prefix) for prefix in config.datamode_prefixes):
        raise RxteBinnedError(f"Unsupported RXTE binned DATAMODE: {datamode}")


def _time_delta(hdu: Any, times: tuple[object, ...]) -> float:
    value = hdu.header.get("TIMEDEL")
    if value is not None:
        time_delta = float(value)
        if isfinite(time_delta) and time_delta > 0:
            return time_delta
    if len(times) > 1:
        time_delta = float(times[1]) - float(times[0])
        if isfinite(time_delta) and time_delta > 0:
            return time_delta
    raise RxteBinnedError("Cannot determine binned timing row duration")


def _expand_counts_to_bin_centers(
    row_times: tuple[object, ...],
    counts_by_row: tuple[object, ...],
    *,
    time_delta: float,
    gtis: tuple[TimeInterval, ...],
) -> list[float]:
    event_times: list[float] = []
    gti_intervals = merge_intervals(gtis)
    for row_time, counts in zip(row_times, counts_by_row):
        count_values = tuple(int(value) for value in counts)
        if not count_values:
            continue
        bin_width = time_delta / len(count_values)
        row_start = float(row_time)
        for bin_index, count in enumerate(count_values):
            if count <= 0:
                continue
            event_time = row_start + (bin_index + 0.5) * bin_width
            if gti_intervals and not any(
                interval.contains(event_time) for interval in gti_intervals
            ):
                continue
            event_times.extend([event_time] * count)
    event_times.sort()
    return event_times


def _read_gti_intervals(
    hdul: Any,
    config: RxteBinnedReadConfig,
) -> tuple[TimeInterval, ...]:
    intervals: list[TimeInterval] = []
    for hdu in hdul:
        if getattr(hdu, "name", "").upper() not in config.gti_extension_names:
            continue
        if not _has_any_column(hdu, ("START",)) or not _has_any_column(hdu, ("STOP",)):
            continue
        starts = _column_values(hdu, ("START",))
        stops = _column_values(hdu, ("STOP",))
        intervals.extend(
            TimeInterval(float(start), float(stop))
            for start, stop in zip(starts, stops)
            if float(stop) > float(start)
        )
    return tuple(intervals)


def _column_values(hdu: Any, column_names: tuple[str, ...]) -> tuple[object, ...]:
    column_name = _matching_column_name(hdu, column_names)
    if column_name is None:
        raise RxteBinnedError(f"Missing required FITS column: {column_names[0]}")
    return tuple(hdu.data[column_name].tolist())


def _has_any_column(hdu: Any, column_names: tuple[str, ...]) -> bool:
    return _matching_column_name(hdu, column_names) is not None


def _matching_column_name(hdu: Any, column_names: tuple[str, ...]) -> str | None:
    if not hasattr(hdu, "columns"):
        return None
    names = {name.upper(): name for name in (hdu.columns.names or ())}
    for column_name in column_names:
        if column_name.upper() in names:
            return names[column_name.upper()]
    return None
