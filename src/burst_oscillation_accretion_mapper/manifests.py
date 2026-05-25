"""Load curated repository manifests for early RXTE validation work.

This module is intentionally small and standard-library only. Phase 1 ingestion
code can use it to consume the selected RXTE/PCA ObsIDs without duplicating CSV
parsing or silently drifting from the tracked manifests.
"""

from __future__ import annotations

import csv
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar


T = TypeVar("T")


SOURCE_COLUMNS = (
    "source_id",
    "canonical_name",
    "aliases",
    "ra_deg",
    "dec_deg",
    "coordinate_ref",
    "source_class",
    "known_spin_hz",
    "spin_ref",
    "binary_ephemeris_ref",
    "minbar_name",
    "rxte_priority",
    "notes",
)

OBSERVATION_COLUMNS = (
    "observation_id",
    "source_id",
    "instrument",
    "obs_id",
    "archive_uri",
    "archive_ref",
    "start_time",
    "stop_time",
    "exposure_s",
    "data_mode",
    "raw_status",
    "local_raw_path",
    "checksum",
    "event_product_uri",
    "software_version",
    "caldb_version",
    "screening_hash",
    "barycorr_ref",
    "quality_flags",
    "notes",
)

VALIDATION_TARGET_COLUMNS = (
    "target_id",
    "source_id",
    "instrument",
    "obs_id",
    "minbar_burst_id",
    "validation_goal",
    "expected_signal",
    "expected_frequency_hz",
    "frequency_ref",
    "burst_time_ref",
    "priority",
    "notes",
)


class ManifestLoadError(ValueError):
    """Raised when curated manifests cannot be loaded into a consistent index."""


@dataclass(frozen=True)
class SourceRow:
    source_id: str
    canonical_name: str
    aliases: tuple[str, ...]
    ra_deg: float
    dec_deg: float
    coordinate_ref: str
    source_class: str
    known_spin_hz: float | None
    spin_ref: str
    binary_ephemeris_ref: str
    minbar_name: str
    rxte_priority: str
    notes: str


@dataclass(frozen=True)
class ObservationRow:
    observation_id: str
    source_id: str
    instrument: str
    obs_id: str
    archive_uri: str
    archive_ref: str
    start_time: str
    stop_time: str
    exposure_s: float | None
    data_mode: str
    raw_status: str
    local_raw_path: str
    checksum: str
    event_product_uri: str
    software_version: str
    caldb_version: str
    screening_hash: str
    barycorr_ref: str
    quality_flags: tuple[str, ...]
    notes: str


@dataclass(frozen=True)
class ValidationTargetRow:
    target_id: str
    source_id: str
    instrument: str
    obs_id: str
    minbar_burst_id: str
    validation_goal: str
    expected_signal: str
    expected_frequency_hz: float | None
    frequency_ref: str
    burst_time_ref: tuple[str, ...]
    priority: str
    notes: str


@dataclass(frozen=True)
class ValidationTargetContext:
    target: ValidationTargetRow
    source: SourceRow
    observation: ObservationRow


@dataclass(frozen=True)
class ManifestIndex:
    sources: dict[str, SourceRow]
    observations_by_obs_id: dict[str, ObservationRow]
    validation_targets: tuple[ValidationTargetRow, ...]

    def validation_contexts(
        self, *, instrument: str | None = None
    ) -> tuple[ValidationTargetContext, ...]:
        contexts = []
        for target in self.validation_targets:
            if instrument is not None and target.instrument != instrument:
                continue
            try:
                source = self.sources[target.source_id]
                observation = self.observations_by_obs_id[target.obs_id]
            except KeyError as exc:
                raise ManifestLoadError(
                    f"{target.target_id} is missing a source or observation link"
                ) from exc
            contexts.append(ValidationTargetContext(target, source, observation))
        return tuple(contexts)

    def rxte_validation_contexts(self) -> tuple[ValidationTargetContext, ...]:
        return self.validation_contexts(instrument="RXTE/PCA")

    def non_detection_controls(self) -> tuple[ValidationTargetContext, ...]:
        return tuple(
            context
            for context in self.rxte_validation_contexts()
            if context.target.validation_goal == "non_detection_control"
            or context.target.expected_signal == "non_detection"
        )


def load_phase1_manifests(manifest_dir: Path | str) -> ManifestIndex:
    """Load the curated Phase 1 RXTE validation manifests."""

    root = Path(manifest_dir)
    source_rows = _read_rows(root / "sources.csv", SOURCE_COLUMNS, _source_from_row)
    observation_rows = _read_rows(
        root / "observations.csv", OBSERVATION_COLUMNS, _observation_from_row
    )
    validation_targets = _read_rows(
        root / "validation_targets.csv",
        VALIDATION_TARGET_COLUMNS,
        _validation_target_from_row,
    )

    _check_unique((row.source_id for row in source_rows), "source_id")
    _check_unique((row.obs_id for row in observation_rows), "obs_id")
    _check_unique((row.target_id for row in validation_targets), "target_id")

    sources = {row.source_id: row for row in source_rows}
    observations = {row.obs_id: row for row in observation_rows}

    index = ManifestIndex(sources, observations, validation_targets)
    index.validation_contexts()
    return index


def _read_rows(
    path: Path, expected_columns: tuple[str, ...], factory: Callable[[dict[str, str]], T]
) -> tuple[T, ...]:
    if not path.exists():
        raise ManifestLoadError(f"Missing manifest: {path}")

    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fieldnames = tuple(reader.fieldnames or ())
        if fieldnames != expected_columns:
            raise ManifestLoadError(
                f"{path.name} columns differ from schema: "
                f"expected {expected_columns}, found {fieldnames}"
            )
        rows = tuple(reader)
        for line_number, row in enumerate(rows, start=2):
            if None in row:
                raise ManifestLoadError(
                    f"{path.name} row {line_number} has too many columns"
                )

            missing = [field for field, value in row.items() if value is None]
            if missing:
                raise ManifestLoadError(
                    f"{path.name} row {line_number} has too few columns: {missing}"
                )

        return tuple(factory(row) for row in rows)


def _source_from_row(row: dict[str, str]) -> SourceRow:
    return SourceRow(
        source_id=_required(row, "source_id"),
        canonical_name=_required(row, "canonical_name"),
        aliases=_pipe_list(row["aliases"]),
        ra_deg=_float_or_error(row["ra_deg"], "ra_deg"),
        dec_deg=_float_or_error(row["dec_deg"], "dec_deg"),
        coordinate_ref=_required(row, "coordinate_ref"),
        source_class=row["source_class"].strip(),
        known_spin_hz=_optional_float(row["known_spin_hz"], "known_spin_hz"),
        spin_ref=row["spin_ref"].strip(),
        binary_ephemeris_ref=row["binary_ephemeris_ref"].strip(),
        minbar_name=row["minbar_name"].strip(),
        rxte_priority=row["rxte_priority"].strip(),
        notes=row["notes"].strip(),
    )


def _observation_from_row(row: dict[str, str]) -> ObservationRow:
    return ObservationRow(
        observation_id=_required(row, "observation_id"),
        source_id=_required(row, "source_id"),
        instrument=_required(row, "instrument"),
        obs_id=_required(row, "obs_id"),
        archive_uri=row["archive_uri"].strip(),
        archive_ref=row["archive_ref"].strip(),
        start_time=row["start_time"].strip(),
        stop_time=row["stop_time"].strip(),
        exposure_s=_optional_float(row["exposure_s"], "exposure_s"),
        data_mode=row["data_mode"].strip(),
        raw_status=row["raw_status"].strip(),
        local_raw_path=row["local_raw_path"].strip(),
        checksum=row["checksum"].strip(),
        event_product_uri=row["event_product_uri"].strip(),
        software_version=row["software_version"].strip(),
        caldb_version=row["caldb_version"].strip(),
        screening_hash=row["screening_hash"].strip(),
        barycorr_ref=row["barycorr_ref"].strip(),
        quality_flags=_pipe_list(row["quality_flags"]),
        notes=row["notes"].strip(),
    )


def _validation_target_from_row(row: dict[str, str]) -> ValidationTargetRow:
    return ValidationTargetRow(
        target_id=_required(row, "target_id"),
        source_id=_required(row, "source_id"),
        instrument=_required(row, "instrument"),
        obs_id=_required(row, "obs_id"),
        minbar_burst_id=row["minbar_burst_id"].strip(),
        validation_goal=_required(row, "validation_goal"),
        expected_signal=_required(row, "expected_signal"),
        expected_frequency_hz=_optional_float(
            row["expected_frequency_hz"], "expected_frequency_hz"
        ),
        frequency_ref=row["frequency_ref"].strip(),
        burst_time_ref=_pipe_list(row["burst_time_ref"], separator=";"),
        priority=_required(row, "priority"),
        notes=row["notes"].strip(),
    )


def _required(row: dict[str, str], field: str) -> str:
    value = row[field].strip()
    if not value:
        raise ManifestLoadError(f"Missing required field: {field}")
    return value


def _optional_float(value: str, field: str) -> float | None:
    stripped = value.strip()
    if not stripped:
        return None
    return _float_or_error(stripped, field)


def _float_or_error(value: str, field: str) -> float:
    try:
        return float(value)
    except ValueError as exc:
        raise ManifestLoadError(f"Invalid numeric value for {field}: {value}") from exc


def _pipe_list(value: str, *, separator: str = "|") -> tuple[str, ...]:
    return tuple(part.strip() for part in value.split(separator) if part.strip())


def _check_unique(values: Iterable[str], field: str) -> None:
    seen: set[str] = set()
    for value in values:
        if value in seen:
            raise ManifestLoadError(f"Duplicate manifest value for {field}: {value}")
        seen.add(value)
