"""Astropy-based RXTE FITS event-table ingestion for Phase 1 validation.

This module reads already-local RXTE/PCA FITS or FITS.GZ event tables with
explicit event-time columns. Some RXTE GoodXenon products require HEASoft/FTOOLS
conversion before they become simple event tables; this reader fails clearly for
those products instead of inventing mission-specific decoding.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .event_products import EventProduct, EventProductProvenance
from .time_intervals import TimeInterval, merge_intervals


class RxteFitsError(ValueError):
    """Raised when a local RXTE FITS product cannot be read as an event table."""


@dataclass(frozen=True)
class RxteFitsEventReadConfig:
    """Column and extension names accepted by the Phase 1 FITS reader."""

    event_extension_names: tuple[str, ...] = ("EVENTS", "XTE_SE", "STDEVT")
    time_column_names: tuple[str, ...] = ("TIME",)
    energy_column_names: tuple[str, ...] = ("PHA", "PI", "CHANNEL", "ENERGY")
    detector_column_names: tuple[str, ...] = ("PCUID", "PCU_ID", "DETECTOR_ID")
    gti_extension_names: tuple[str, ...] = ("GTI", "STDGTI", "ALLGTI")


def read_rxte_fits_event_product(
    path: Path | str,
    *,
    source_id: str,
    obs_id: str,
    provenance: EventProductProvenance,
    config: RxteFitsEventReadConfig = RxteFitsEventReadConfig(),
    instrument: str = "RXTE/PCA",
) -> EventProduct:
    """Read one local RXTE FITS event table into an `EventProduct`."""

    try:
        from astropy.io import fits
    except Exception as exc:  # pragma: no cover - depends on optional package
        raise RxteFitsError("Astropy is required to read RXTE FITS products") from exc

    fits_path = Path(path)
    try:
        with fits.open(fits_path) as hdul:
            event_hdu = _find_event_hdu(hdul, config)
            times = tuple(float(value) for value in _column_values(event_hdu, config.time_column_names))
            if not times:
                raise RxteFitsError(f"No event times found in {fits_path}")
            energies = _optional_float_column(event_hdu, config.energy_column_names)
            detector_ids = _optional_string_column(event_hdu, config.detector_column_names)
            gtis = _read_gti_intervals(hdul, config)
    except RxteFitsError:
        raise
    except Exception as exc:
        raise RxteFitsError(f"Cannot read RXTE FITS event product: {fits_path}") from exc

    if not gtis:
        gtis = (TimeInterval(min(times), max(times) + _minimum_time_padding(times)),)

    return EventProduct(
        source_id=source_id,
        obs_id=obs_id,
        instrument=instrument,
        times=tuple(sorted(times)),
        gtis=merge_intervals(gtis),
        energies=energies,
        detector_ids=detector_ids,
        provenance=provenance,
    )


def _find_event_hdu(hdul: Any, config: RxteFitsEventReadConfig) -> Any:
    named_candidates = [
        hdu
        for hdu in hdul
        if getattr(hdu, "name", "").upper() in config.event_extension_names
    ]
    for hdu in named_candidates:
        if _has_any_column(hdu, config.time_column_names):
            return hdu
    raise RxteFitsError(
        "No RXTE event table extension with a TIME column was found; run "
        "HEASoft/FTOOLS conversion first for binned or packed RXTE mode products"
    )


def _read_gti_intervals(
    hdul: Any, config: RxteFitsEventReadConfig
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


def _optional_float_column(
    hdu: Any, column_names: tuple[str, ...]
) -> tuple[float, ...]:
    if not _has_any_column(hdu, column_names):
        return ()
    return tuple(float(value) for value in _column_values(hdu, column_names))


def _optional_string_column(
    hdu: Any, column_names: tuple[str, ...]
) -> tuple[str, ...]:
    if not _has_any_column(hdu, column_names):
        return ()
    return tuple(str(value) for value in _column_values(hdu, column_names))


def _column_values(hdu: Any, column_names: tuple[str, ...]) -> tuple[object, ...]:
    column_name = _matching_column_name(hdu, column_names)
    if column_name is None:
        raise RxteFitsError(f"Missing required FITS column: {column_names[0]}")
    values = hdu.data[column_name]
    if getattr(values, "ndim", 1) != 1:
        raise RxteFitsError(
            f"FITS column {column_name} is vector-valued; run HEASoft/FTOOLS "
            "conversion before Phase 1 event ingestion"
        )
    return tuple(values.tolist())


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


def _minimum_time_padding(times: tuple[float, ...]) -> float:
    if len(times) < 2:
        return 1.0e-6
    deltas = [
        later - earlier
        for earlier, later in zip(sorted(times), sorted(times)[1:])
        if later > earlier
    ]
    return min(deltas) if deltas else 1.0e-6
