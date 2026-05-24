"""SQLite development catalog writer for Phase 1 candidate reviews.

This is a small Phase 1 persistence layer for review products. It writes the
burst, candidate, control, and non-detection rows needed for local validation,
while leaving schema migrations, PostgreSQL support, sensitivity products, and
population tables for later roadmap work.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from math import isfinite

from .burst_detection import MultiCadenceBurstCandidateSummary
from .candidate_scoring import OscillationCandidateReview
from .control_checks import ControlSearchRun
from .control_intervals import ControlReview
from .timing_significance import z2_trial_significance


BURST_REVIEW_TABLE = "burst_reviews"
OSCILLATION_CANDIDATE_TABLE = "oscillation_candidate_reviews"
CONTROL_REVIEW_TABLE = "control_reviews"


class CatalogWriteError(ValueError):
    """Raised when catalog rows or write contexts are invalid."""


@dataclass(frozen=True)
class BurstCatalogWriteContext:
    """Write-time metadata required for burst-review catalog rows."""

    burst_id: str
    source_id: str
    obs_id: str
    instrument: str
    pipeline_version: str
    detection_config_id: str
    minbar_burst_id: str = ""
    provenance_note: str = ""

    def __post_init__(self) -> None:
        _require_text(self.burst_id, "burst_id")
        _require_text(self.source_id, "source_id")
        _require_text(self.obs_id, "obs_id")
        _require_text(self.instrument, "instrument")
        _require_text(self.pipeline_version, "pipeline_version")
        _require_text(self.detection_config_id, "detection_config_id")


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
        _require_text(self.search_config_id, "search_config_id")


@dataclass(frozen=True)
class ControlCatalogWriteContext:
    """Write-time metadata required for control-review catalog rows."""

    pipeline_version: str
    energy_band: str = ""
    search_config_id: str = ""
    provenance_note: str = ""

    def __post_init__(self) -> None:
        _require_text(self.pipeline_version, "pipeline_version")
        _require_text(self.search_config_id, "search_config_id")


@dataclass(frozen=True)
class BurstCatalogRow:
    """Serializable burst detector summary row for Phase 1 SQLite output."""

    burst_id: str
    source_id: str
    obs_id: str
    instrument: str
    t_start: float
    t_peak: float
    t_end: float
    duration: float
    bin_sizes: tuple[float, ...]
    best_bin_size: float
    review_count: int
    passed_review_count: int
    passes_review: bool
    best_peak_score: float
    best_excess_counts: float
    total_counts: int
    total_expected_counts: float
    rejection_reasons: tuple[str, ...]
    minbar_burst_id: str
    pipeline_version: str
    detection_config_id: str
    provenance_note: str


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
    leahy_power: float | None
    n_harmonics: int | None
    p_single: float | None
    p_trials: float | None
    fractional_rms: float | None
    phase_rad: float | None
    reasons: tuple[str, ...]
    pipeline_version: str
    search_config_id: str
    provenance_note: str


@dataclass(frozen=True)
class ControlCatalogRow:
    """Serializable scored control-window row for Phase 1 SQLite output."""

    control_id: str
    burst_id: str
    control_kind: str
    control_start: float
    control_stop: float
    requested_start: float
    requested_stop: float
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
    leahy_power: float | None
    n_harmonics: int | None
    p_single: float | None
    p_trials: float | None
    fractional_rms: float | None
    phase_rad: float | None
    reasons: tuple[str, ...]
    pipeline_version: str
    search_config_id: str
    provenance_note: str


def burst_catalog_row_from_summary(
    summary: MultiCadenceBurstCandidateSummary,
    *,
    context: BurstCatalogWriteContext,
) -> BurstCatalogRow:
    """Create a catalog row from one multi-cadence burst detector summary."""

    _validate_burst_summary(summary)
    return BurstCatalogRow(
        burst_id=context.burst_id,
        source_id=context.source_id,
        obs_id=context.obs_id,
        instrument=context.instrument,
        t_start=summary.start,
        t_peak=summary.peak_time,
        t_end=summary.stop,
        duration=summary.duration,
        bin_sizes=summary.bin_sizes,
        best_bin_size=summary.best_bin_size,
        review_count=summary.review_count,
        passed_review_count=summary.passed_review_count,
        passes_review=summary.passes_any_review,
        best_peak_score=summary.best_peak_score,
        best_excess_counts=summary.best_excess_counts,
        total_counts=summary.total_counts,
        total_expected_counts=summary.total_expected_counts,
        rejection_reasons=summary.rejection_reasons,
        minbar_burst_id=context.minbar_burst_id,
        pipeline_version=context.pipeline_version,
        detection_config_id=context.detection_config_id,
        provenance_note=context.provenance_note,
    )


def candidate_catalog_row_from_review(
    review: OscillationCandidateReview,
    *,
    context: CandidateCatalogWriteContext,
) -> CandidateCatalogRow:
    """Create a catalog row from one scored candidate or non-detection review."""

    _validate_review(review)
    window_start = review.window.start if review.window is not None else None
    window_stop = review.window.stop if review.window is not None else None
    p_single, p_trials = _review_significance_p_values(review)
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
        leahy_power=review.leahy_power,
        n_harmonics=review.n_harmonics,
        p_single=p_single,
        p_trials=p_trials,
        fractional_rms=review.fractional_rms,
        phase_rad=review.phase_rad,
        reasons=review.reasons,
        pipeline_version=context.pipeline_version,
        search_config_id=context.search_config_id,
        provenance_note=context.provenance_note,
    )


def control_catalog_row_from_review(
    control_review: ControlReview,
    *,
    context: ControlCatalogWriteContext,
) -> ControlCatalogRow:
    """Create a catalog row from one scored control-window review."""

    _validate_control_review(control_review)
    review = control_review.review
    control = control_review.control
    window_start = review.window.start if review.window is not None else None
    window_stop = review.window.stop if review.window is not None else None
    p_single, p_trials = _review_significance_p_values(review)
    return ControlCatalogRow(
        control_id=control.control_id,
        burst_id=control.burst_id,
        control_kind=control.kind,
        control_start=control.interval.start,
        control_stop=control.interval.stop,
        requested_start=control.requested_interval.start,
        requested_stop=control.requested_interval.stop,
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
        leahy_power=review.leahy_power,
        n_harmonics=review.n_harmonics,
        p_single=p_single,
        p_trials=p_trials,
        fractional_rms=review.fractional_rms,
        phase_rad=review.phase_rad,
        reasons=review.reasons,
        pipeline_version=context.pipeline_version,
        search_config_id=context.search_config_id,
        provenance_note=context.provenance_note,
    )


def initialize_burst_catalog(connection: sqlite3.Connection) -> None:
    """Create the Phase 1 burst-review table when it does not exist."""

    connection.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {BURST_REVIEW_TABLE} (
            burst_id TEXT PRIMARY KEY,
            source_id TEXT NOT NULL,
            obs_id TEXT NOT NULL,
            instrument TEXT NOT NULL,
            t_start REAL NOT NULL,
            t_peak REAL NOT NULL,
            t_end REAL NOT NULL,
            duration REAL NOT NULL,
            bin_sizes_json TEXT NOT NULL,
            best_bin_size REAL NOT NULL,
            review_count INTEGER NOT NULL,
            passed_review_count INTEGER NOT NULL,
            passes_review INTEGER NOT NULL,
            best_peak_score REAL NOT NULL,
            best_excess_counts REAL NOT NULL,
            total_counts INTEGER NOT NULL,
            total_expected_counts REAL NOT NULL,
            rejection_reasons_json TEXT NOT NULL,
            minbar_burst_id TEXT NOT NULL,
            pipeline_version TEXT NOT NULL,
            detection_config_id TEXT NOT NULL,
            provenance_note TEXT NOT NULL
        )
        """
    )
    connection.commit()


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
            leahy_power REAL,
            n_harmonics INTEGER,
            p_single REAL,
            p_trials REAL,
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


def initialize_control_catalog(connection: sqlite3.Connection) -> None:
    """Create the Phase 1 scored-control table when it does not exist."""

    connection.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {CONTROL_REVIEW_TABLE} (
            control_id TEXT PRIMARY KEY,
            burst_id TEXT NOT NULL,
            control_kind TEXT NOT NULL,
            control_start REAL NOT NULL,
            control_stop REAL NOT NULL,
            requested_start REAL NOT NULL,
            requested_stop REAL NOT NULL,
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
            leahy_power REAL,
            n_harmonics INTEGER,
            p_single REAL,
            p_trials REAL,
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


def write_burst_catalog_row(
    connection: sqlite3.Connection,
    row: BurstCatalogRow,
) -> None:
    """Insert one burst-review row into the SQLite development catalog."""

    initialize_burst_catalog(connection)
    connection.execute(
        f"""
        INSERT INTO {BURST_REVIEW_TABLE} (
            burst_id,
            source_id,
            obs_id,
            instrument,
            t_start,
            t_peak,
            t_end,
            duration,
            bin_sizes_json,
            best_bin_size,
            review_count,
            passed_review_count,
            passes_review,
            best_peak_score,
            best_excess_counts,
            total_counts,
            total_expected_counts,
            rejection_reasons_json,
            minbar_burst_id,
            pipeline_version,
            detection_config_id,
            provenance_note
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        _burst_row_to_sql_values(row),
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
            leahy_power,
            n_harmonics,
            p_single,
            p_trials,
            fractional_rms,
            phase_rad,
            reasons_json,
            pipeline_version,
            search_config_id,
            provenance_note
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        _row_to_sql_values(row),
    )
    connection.commit()


def write_control_catalog_row(
    connection: sqlite3.Connection,
    row: ControlCatalogRow,
) -> None:
    """Insert one scored control-window row into the SQLite catalog."""

    initialize_control_catalog(connection)
    connection.execute(
        f"""
        INSERT INTO {CONTROL_REVIEW_TABLE} (
            control_id,
            burst_id,
            control_kind,
            control_start,
            control_stop,
            requested_start,
            requested_stop,
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
            leahy_power,
            n_harmonics,
            p_single,
            p_trials,
            fractional_rms,
            phase_rad,
            reasons_json,
            pipeline_version,
            search_config_id,
            provenance_note
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        _control_row_to_sql_values(row),
    )
    connection.commit()


def write_burst_review(
    connection: sqlite3.Connection,
    summary: MultiCadenceBurstCandidateSummary,
    *,
    context: BurstCatalogWriteContext,
) -> BurstCatalogRow:
    """Create and insert one burst-review catalog row."""

    row = burst_catalog_row_from_summary(summary, context=context)
    write_burst_catalog_row(connection, row)
    return row


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


def write_control_review(
    connection: sqlite3.Connection,
    control_review: ControlReview,
    *,
    context: ControlCatalogWriteContext,
) -> ControlCatalogRow:
    """Create and insert one scored control-window catalog row."""

    row = control_catalog_row_from_review(control_review, context=context)
    write_control_catalog_row(connection, row)
    return row


def write_control_search_run(
    connection: sqlite3.Connection,
    run: ControlSearchRun,
    *,
    context: ControlCatalogWriteContext,
) -> tuple[ControlCatalogRow, ...]:
    """Insert all scored control-window rows from one control search run."""

    return tuple(
        write_control_review(connection, control_review, context=context)
        for control_review in run.control_reviews
    )


def read_burst_catalog_rows(
    connection: sqlite3.Connection,
) -> tuple[BurstCatalogRow, ...]:
    """Read Phase 1 burst-review rows from the SQLite development catalog."""

    initialize_burst_catalog(connection)
    cursor = connection.execute(
        f"""
        SELECT
            burst_id,
            source_id,
            obs_id,
            instrument,
            t_start,
            t_peak,
            t_end,
            duration,
            bin_sizes_json,
            best_bin_size,
            review_count,
            passed_review_count,
            passes_review,
            best_peak_score,
            best_excess_counts,
            total_counts,
            total_expected_counts,
            rejection_reasons_json,
            minbar_burst_id,
            pipeline_version,
            detection_config_id,
            provenance_note
        FROM {BURST_REVIEW_TABLE}
        ORDER BY burst_id
        """
    )
    return tuple(_burst_row_from_sql_values(row) for row in cursor.fetchall())


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
            leahy_power,
            n_harmonics,
            p_single,
            p_trials,
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


def read_control_catalog_rows(
    connection: sqlite3.Connection,
) -> tuple[ControlCatalogRow, ...]:
    """Read Phase 1 scored-control rows from the SQLite development catalog."""

    initialize_control_catalog(connection)
    cursor = connection.execute(
        f"""
        SELECT
            control_id,
            burst_id,
            control_kind,
            control_start,
            control_stop,
            requested_start,
            requested_stop,
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
            leahy_power,
            n_harmonics,
            p_single,
            p_trials,
            fractional_rms,
            phase_rad,
            reasons_json,
            pipeline_version,
            search_config_id,
            provenance_note
        FROM {CONTROL_REVIEW_TABLE}
        ORDER BY control_id
        """
    )
    return tuple(_control_row_from_sql_values(row) for row in cursor.fetchall())


def _burst_row_to_sql_values(row: BurstCatalogRow) -> tuple[object, ...]:
    return (
        row.burst_id,
        row.source_id,
        row.obs_id,
        row.instrument,
        row.t_start,
        row.t_peak,
        row.t_end,
        row.duration,
        json.dumps(list(row.bin_sizes), sort_keys=True),
        row.best_bin_size,
        row.review_count,
        row.passed_review_count,
        1 if row.passes_review else 0,
        row.best_peak_score,
        row.best_excess_counts,
        row.total_counts,
        row.total_expected_counts,
        json.dumps(list(row.rejection_reasons), sort_keys=True),
        row.minbar_burst_id,
        row.pipeline_version,
        row.detection_config_id,
        row.provenance_note,
    )


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
        row.leahy_power,
        row.n_harmonics,
        row.p_single,
        row.p_trials,
        row.fractional_rms,
        row.phase_rad,
        json.dumps(list(row.reasons), sort_keys=True),
        row.pipeline_version,
        row.search_config_id,
        row.provenance_note,
    )


def _control_row_to_sql_values(row: ControlCatalogRow) -> tuple[object, ...]:
    return (
        row.control_id,
        row.burst_id,
        row.control_kind,
        row.control_start,
        row.control_stop,
        row.requested_start,
        row.requested_stop,
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
        row.leahy_power,
        row.n_harmonics,
        row.p_single,
        row.p_trials,
        row.fractional_rms,
        row.phase_rad,
        json.dumps(list(row.reasons), sort_keys=True),
        row.pipeline_version,
        row.search_config_id,
        row.provenance_note,
    )


def _burst_row_from_sql_values(
    values: sqlite3.Row | tuple[object, ...],
) -> BurstCatalogRow:
    row = tuple(values)
    return BurstCatalogRow(
        burst_id=str(row[0]),
        source_id=str(row[1]),
        obs_id=str(row[2]),
        instrument=str(row[3]),
        t_start=float(row[4]),
        t_peak=float(row[5]),
        t_end=float(row[6]),
        duration=float(row[7]),
        bin_sizes=tuple(float(value) for value in json.loads(str(row[8]))),
        best_bin_size=float(row[9]),
        review_count=int(row[10]),
        passed_review_count=int(row[11]),
        passes_review=bool(row[12]),
        best_peak_score=float(row[13]),
        best_excess_counts=float(row[14]),
        total_counts=int(row[15]),
        total_expected_counts=float(row[16]),
        rejection_reasons=tuple(json.loads(str(row[17]))),
        minbar_burst_id=str(row[18]),
        pipeline_version=str(row[19]),
        detection_config_id=str(row[20]),
        provenance_note=str(row[21]),
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
        leahy_power=_optional_float(row[16]),
        n_harmonics=_optional_int(row[17]),
        p_single=_optional_float(row[18]),
        p_trials=_optional_float(row[19]),
        fractional_rms=_optional_float(row[20]),
        phase_rad=_optional_float(row[21]),
        reasons=tuple(json.loads(str(row[22]))),
        pipeline_version=str(row[23]),
        search_config_id=str(row[24]),
        provenance_note=str(row[25]),
    )


def _control_row_from_sql_values(
    values: sqlite3.Row | tuple[object, ...],
) -> ControlCatalogRow:
    row = tuple(values)
    return ControlCatalogRow(
        control_id=str(row[0]),
        burst_id=str(row[1]),
        control_kind=str(row[2]),
        control_start=float(row[3]),
        control_stop=float(row[4]),
        requested_start=float(row[5]),
        requested_stop=float(row[6]),
        source_id=str(row[7]),
        obs_id=str(row[8]),
        instrument=str(row[9]),
        search_mode=str(row[10]),
        classification=str(row[11]),
        trial_count=int(row[12]),
        photon_count=int(row[13]),
        energy_band=str(row[14]),
        window_start=_optional_float(row[15]),
        window_stop=_optional_float(row[16]),
        frequency_hz=_optional_float(row[17]),
        expected_frequency_hz=_optional_float(row[18]),
        frequency_offset_hz=_optional_float(row[19]),
        z2_power=_optional_float(row[20]),
        leahy_power=_optional_float(row[21]),
        n_harmonics=_optional_int(row[22]),
        p_single=_optional_float(row[23]),
        p_trials=_optional_float(row[24]),
        fractional_rms=_optional_float(row[25]),
        phase_rad=_optional_float(row[26]),
        reasons=tuple(json.loads(str(row[27]))),
        pipeline_version=str(row[28]),
        search_config_id=str(row[29]),
        provenance_note=str(row[30]),
    )


def _validate_burst_summary(summary: MultiCadenceBurstCandidateSummary) -> None:
    for field_name, value in (
        ("t_start", summary.start),
        ("t_peak", summary.peak_time),
        ("t_end", summary.stop),
    ):
        _require_finite(value, field_name)
    if summary.start > summary.peak_time or summary.peak_time > summary.stop:
        raise CatalogWriteError("burst times must satisfy start <= peak <= stop")
    if summary.stop <= summary.start:
        raise CatalogWriteError("burst stop must be greater than start")
    for field_name, value in (
        ("duration", summary.duration),
        ("best_bin_size", summary.best_bin_size),
        ("best_peak_score", summary.best_peak_score),
        ("best_excess_counts", summary.best_excess_counts),
        ("total_expected_counts", summary.total_expected_counts),
    ):
        _require_finite_non_negative(value, field_name)
    for field_name, value in (
        ("review_count", summary.review_count),
        ("passed_review_count", summary.passed_review_count),
        ("total_counts", summary.total_counts),
    ):
        _require_non_negative_int(value, field_name)
    if summary.passed_review_count > summary.review_count:
        raise CatalogWriteError("passed_review_count cannot exceed review_count")
    if not summary.bin_sizes:
        raise CatalogWriteError("bin_sizes is required")
    for bin_size in summary.bin_sizes:
        _require_finite_non_negative(bin_size, "bin_size")


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
    if review.z2_power is not None and review.trial_count < 1:
        raise CatalogWriteError("trial_count must be positive when z2_power is set")
    if review.z2_power is not None and review.n_harmonics is None:
        raise CatalogWriteError("n_harmonics is required when z2_power is set")
    if review.n_harmonics is not None and review.n_harmonics < 1:
        raise CatalogWriteError("n_harmonics must be positive when set")
    for field_name, value in (
        ("frequency_hz", review.frequency_hz),
        ("expected_frequency_hz", review.expected_frequency_hz),
        ("frequency_offset_hz", review.frequency_offset_hz),
        ("z2_power", review.z2_power),
        ("leahy_power", review.leahy_power),
        ("fractional_rms", review.fractional_rms),
        ("phase_rad", review.phase_rad),
    ):
        _require_optional_finite(value, field_name)


def _validate_control_review(control_review: ControlReview) -> None:
    _require_text(control_review.control.control_id, "control_id")
    _require_text(control_review.control.kind, "control_kind")
    _validate_review(control_review.review)


def _review_significance_p_values(
    review: OscillationCandidateReview,
) -> tuple[float | None, float | None]:
    if review.z2_power is None or review.n_harmonics is None or review.trial_count == 0:
        return None, None

    significance = z2_trial_significance(
        review.z2_power,
        n_harmonics=review.n_harmonics,
        trial_count=review.trial_count,
    )
    return significance.p_single, significance.p_trials


def _require_text(value: str, field: str) -> None:
    if not value.strip():
        raise CatalogWriteError(f"{field} is required")


def _require_optional_finite(value: float | None, field: str) -> None:
    if value is not None and not isfinite(value):
        raise CatalogWriteError(f"{field} must be finite when set")


def _require_finite(value: float, field: str) -> None:
    if not isfinite(value):
        raise CatalogWriteError(f"{field} must be finite")


def _require_finite_non_negative(value: float, field: str) -> None:
    if not isfinite(value) or value < 0:
        raise CatalogWriteError(f"{field} must be finite and non-negative")


def _require_non_negative_int(value: int, field: str) -> None:
    if not isinstance(value, int) or value < 0:
        raise CatalogWriteError(f"{field} must be a non-negative integer")


def _optional_float(value: object) -> float | None:
    return None if value is None else float(value)


def _optional_int(value: object) -> int | None:
    return None if value is None else int(value)
