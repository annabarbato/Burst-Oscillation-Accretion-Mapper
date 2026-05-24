"""RXTE time-system helpers for Phase 1 MINBAR validation."""

from __future__ import annotations

from math import isfinite


RXTE_MJDREFI = 49353
RXTE_MJDREFF = 0.000696574074
RXTE_MJDREF_TT = RXTE_MJDREFI + RXTE_MJDREFF


class RxteTimeError(ValueError):
    """Raised when RXTE time conversion inputs or dependencies are invalid."""


def utc_mjd_to_rxte_met(mjd_utc: float) -> float:
    """Convert a UTC MJD timestamp, such as MINBAR burst time, to RXTE MET.

    RXTE event files use TT seconds relative to the RXTE MJD reference. MINBAR
    burst pages report event times as MJD UTC, so validation windows must cross
    that time-system boundary before comparing to FITS event times.
    """

    if not isfinite(mjd_utc):
        raise RxteTimeError(f"mjd_utc must be finite: {mjd_utc}")

    try:
        from astropy.time import Time
    except Exception as exc:  # pragma: no cover - depends on optional package
        raise RxteTimeError("Astropy is required for UTC-to-TT conversion") from exc

    mjdref_tt = Time(RXTE_MJDREF_TT, format="mjd", scale="tt")
    timestamp_tt = Time(mjd_utc, format="mjd", scale="utc").tt
    return float((timestamp_tt.mjd - mjdref_tt.mjd) * 86400.0)
