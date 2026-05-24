"""SQLite development catalog writer for Phase 1 candidate reviews.

This is a small Phase 1 persistence layer for review products. It writes the
candidate/non-detection rows needed for local validation, while leaving schema
migrations, PostgreSQL support, sensitivity products, and population tables for
later roadmap work.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from math import isfinite

from .candidate_scoring import OscillationCandidateReview


OSCILLATION_CANDIDATE_TABLE = "oscillation_candidate_reviews"


class CatalogWriteError(ValueError):
    """Raised when catalog rows or write contexts are invalid."""


@dataclass(frozen=True)
class CandidateCatalogWriteContext:
    """Write-time metadata required for candidate-review catalog rows."""

    candidate_id: str
    pipeline_version: str
    burst_id: str = ""
    energy_band: str = ""
    search_config_id: str = ""
    provenance_note: str = ""

    def __post_init__(self) -> None:
        _require_text(self.candidate_id, "candidate_id")
        _require_text(self.pipeline_version, "pipeline_version")


@dataclass(frozen=True)
class CandidateCatalogRow:
    """Serializable oscillation-candidate review row for Phase 1 SQLite output."""

    candidate_id: str
    burst_id: str
    source_id: str
    obs_id: str
    instrument: str
    search_mode: str
    classification: str
    trial_count: int
    photon_count: int
    energy_band: str
    window_start: float | None
    window_stop: float | None
    frequency_hz: float | None
    expected_frequency_hz: float | None
    frequency_offset_hz: float | None
    z2_power: float | None
    n_harmonics: int | None
    fractional_rms: float | None
    phase_rad: float | None
    reasons: tuple[str, ...]
    pipeline_version: str
    search_config_id: str
    provenance_note: str


def candidate_catalog_row_from_review(
    review: OscillationCandidateReview,
    *,
    context: CandidateCatalogWriteContext,
) -> CandidateCatalogRow:
    """Create a catalog row from one scored candidate or non-detection review."""

    _validate_review(review)
    window_start = review.window.start if review.window is not None else None
    window_stop = review.window.stop if review.window is not None else None
    return CandidateCatalogRow(
        candidate_id=context.candidate_id,
        burst_id=context.burst_id,
        source_id=review.source_id,
        obs_id=review.obs_id,
        instrument=review.instrument,
        search_mode=review.search_mode,
        classification=review.classification,
        trial_count=review.trial_count,
        photon_count=review.photon_count,
        energy_band=context.energy_band,
        window_start=window_start,
        window_stop=window_stop,
        frequency_hz=review.frequency_hz,
        expected_frequency_hz=review.expected_frequency_hz,
        frequency_offset_hz=review.frequency_offset_hz,
        z2_power=review.z2_power,
        n_harmonics=review.n_harmonics,
        fractional_rms=review.fractional_rms,
        phase_rad=review.phase_rad,
        reasons=review.reasons,
        pipeline_version=context.pipeline_version,
        search_config_id=context.search_config_id,
        provenance_note=context.provenance_note,
    )


def initialize_candidate_catalog(connection: sqlite3.Connection) -> None:
    """Create the Phase 1 candidate-review table when it does not exist."""

    connection.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {OSCILLATION_CANDIDATE_TABLE} (
            candidate_id TEXT PRIMARY KEY,
            burst_id TEXT NOT NULL,
            source_id TEXT NOT NULL,
            obs_id TEXT NOT NULL,
            instrument TEXT NOT NULL,
            search_mode TEXT NOT NULL,
            classification TEXT NOT NULL,
            trial_count INTEGER NOT NULL,
            photon_count INTEGER NOT NULL,
            energy_band TEXT NOT NULL,
            window_start REAL,
            window_stop REAL,
            frequency_hz REAL,
            expected_frequency_hz REAL,
            frequency_offset_hz REAL,
            z2_power REAL,
            n_harmonics INTEGER,
            fractional_rms REAL,
            phase_rad REAL,
            reasons_json TEXT NOT NULL,
            pipeline_version TEXT NOT NULL,
            search_config_id TEXT NOT NULL,
            provenance_note TEXT NOT NULL
        )
        """
    )
    connection.commit()


def write_candidate_catalog_row(
    connection: sqlite3.Connection,
    row: CandidateCatalogRow,
) -> None:
    """Insert one candidate-review row into the SQLite development catalog."""

    initialize_candidate_catalog(connection)
    connection.execute(
        f"""
        INSERT INTO {OSCILLATION_CANDIDATE_TABLE} (
            candidate_id,
            burst_id,
            source_id,
            obs_id,
            instrument,
            search_mode,
            classification,
            trial_count,
            photon_count,
            energy_band,
            window_start,
            window_stop,
            frequency_hz,
            expected_frequency_hz,
            frequency_offset_hz,
            z2_power,
            n_harmonics,
            fractional_rms,
            phase_rad,
            reasons_json,
            pipeline_version,
            search_config_id,
            provenance_note
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        _row_to_sql_values(row),
    )
    connection.commit()


def write_candidate_review(
    connection: sqlite3.Connection,
    review: OscillationCandidateReview,
    *,
    context: CandidateCatalogWriteContext,
) -> CandidateCatalogRow:
    """Create and insert one candidate-review catalog row."""

    row = candidate_catalog_row_from_review(review, context=context)
    write_candidate_catalog_row(connection, row)
    return row


def read_candidate_catalog_rows(
    connection: sqlite3.Connection,
) -> tuple[CandidateCatalogRow, ...]:
    """Read Phase 1 candidate-review rows from the SQLite development catalog."""

    initialize_candidate_catalog(connection)
    cursor = connection.execute(
        f"""
        SELECT
            candidate_id,
            burst_id,
            source_id,
            obs_id,
            instrument,
            search_mode,
            classification,
            trial_count,
            photon_count,
            energy_band,
            window_start,
            window_stop,
            frequency_hz,
            expected_frequency_hz,
            frequency_offset_hz,
            z2_power,
            n_harmonics,
            fractional_rms,
            phase_rad,
            reasons_json,
            pipeline_version,
            search_config_id,
            provenance_note
        FROM {OSCILLATION_CANDIDATE_TABLE}
        ORDER BY candidate_id
        """
    )
    return tuple(_row_from_sql_values(row) for row in cursor.fetchall())


def _row_to_sql_values(row: CandidateCatalogRow) -> tuple[object, ...]:
    return (
        row.candidate_id,
        row.burst_id,
        row.source_id,
        row.obs_id,
        row.instrument,
        row.search_mode,
        row.classification,
        row.trial_count,
        row.photon_count,
        row.energy_band,
        row.window_start,
        row.window_stop,
        row.frequency_hz,
        row.expected_frequency_hz,
        row.frequency_offset_hz,
        row.z2_power,
        row.n_harmonics,
        row.fractional_rms,
        row.phase_rad,
        json.dumps(list(row.reasons), sort_keys=True),
        row.pipeline_version,
        row.search_config_id,
        row.provenance_note,
    )


def _row_from_sql_values(values: sqlite3.Row | tuple[object, ...]) -> CandidateCatalogRow:
    row = tuple(values)
    return CandidateCatalogRow(
        candidate_id=str(row[0]),
        burst_id=str(row[1]),
        source_id=str(row[2]),
        obs_id=str(row[3]),
        instrument=str(row[4]),
        search_mode=str(row[5]),
        classification=str(row[6]),
        trial_count=int(row[7]),
        photon_count=int(row[8]),
        energy_band=str(row[9]),
        window_start=_optional_float(row[10]),
        window_stop=_optional_float(row[11]),
        frequency_hz=_optional_float(row[12]),
        expected_frequency_hz=_optional_float(row[13]),
        frequency_offset_hz=_optional_float(row[14]),
        z2_power=_optional_float(row[15]),
        n_harmonics=_optional_int(row[16]),
        fractional_rms=_optional_float(row[17]),
        phase_rad=_optional_float(row[18]),
        reasons=tuple(json.loads(str(row[19]))),
        pipeline_version=str(row[20]),
        search_config_id=str(row[21]),
        provenance_note=str(row[22]),
    )


def _validate_review(review: OscillationCandidateReview) -> None:
    for field_name, value in (
        ("source_id", review.source_id),
        ("obs_id", review.obs_id),
        ("instrument", review.instrument),
        ("search_mode", review.search_mode),
        ("classification", review.classification),
    ):
        _require_text(value, field_name)
    if review.trial_count < 0:
        raise CatalogWriteError("trial_count cannot be negative")
    if review.photon_count < 0:
        raise CatalogWriteError("photon_count cannot be negative")
    for field_name, value in (
        ("frequency_hz", review.frequency_hz),
        ("expected_frequency_hz", review.expected_frequency_hz),
        ("frequency_offset_hz", review.frequency_offset_hz),
        ("z2_power", review.z2_power),
        ("fractional_rms", review.fractional_rms),
        ("phase_rad", review.phase_rad),
    ):
        _require_optional_finite(value, field_name)


def _require_text(value: str, field: str) -> None:
    if not value.strip():
        raise CatalogWriteError(f"{field} is required")


def _require_optional_finite(value: float | None, field: str) -> None:
    if value is not None and not isfinite(value):
        raise CatalogWriteError(f"{field} must be finite when set")


def _optional_float(value: object) -> float | None:
    return None if value is None else float(value)


def _optional_int(value: object) -> int | None:
    return None if value is None else int(value)
