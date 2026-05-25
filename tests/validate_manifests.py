"""Validate tracked CSV manifests.

This is intentionally a small standard-library check. It protects the source,
observation, validation-target, and reference manifests independently of the
Phase 1 Python package.
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_DIR = ROOT / "data" / "manifests"

SOURCE_COLUMNS = [
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
]

VALIDATION_TARGET_COLUMNS = [
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
]

OBSERVATION_COLUMNS = [
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
]

REFERENCE_COLUMNS = [
    "ref_id",
    "category",
    "title",
    "url",
    "doi",
    "bibcode",
    "version_or_date",
    "checked_date",
    "authoritative_for",
    "notes",
]

REFERENCE_CATEGORIES = {
    "mission_status",
    "instrument_spec",
    "catalog",
    "software_doc",
    "literature",
    "ephemeris",
}

VALIDATION_GOALS = {
    "burst_detection",
    "known_oscillation_recovery",
    "non_detection_control",
    "false_positive_control",
    "timing_fixture",
}

EXPECTED_SIGNALS = {
    "secure_detection",
    "probable_detection",
    "non_detection",
    "control",
    "unknown",
}

PRIORITIES = {"high", "medium", "low"}
RAW_STATUSES = {"candidate", "selected", "downloaded", "verified", "rejected"}
ID_PATTERN = re.compile(r"^[a-z0-9_]+$")
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
URL_PATTERN = re.compile(r"^https?://")


class ManifestError(ValueError):
    """Raised when a manifest fails validation."""


def read_csv(path: Path, expected_columns: list[str]) -> list[dict[str, str]]:
    if not path.exists():
        raise ManifestError(f"Missing manifest: {path}")

    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != expected_columns:
            raise ManifestError(
                f"{path.name} columns differ from schema:\n"
                f"  expected: {expected_columns}\n"
                f"  found:    {reader.fieldnames}"
            )
        rows = list(reader)
        for line_number, row in enumerate(rows, start=2):
            if None in row:
                raise ManifestError(
                    f"{path.name} row {line_number} has too many columns"
                )

            missing = [field for field, value in row.items() if value is None]
            if missing:
                raise ManifestError(
                    f"{path.name} row {line_number} has too few columns: {missing}"
                )

        return rows


def require(row: dict[str, str], field: str, row_name: str) -> str:
    value = row.get(field, "").strip()
    if not value:
        raise ManifestError(f"{row_name} is missing required field {field}")
    return value


def require_id(value: str, row_name: str, field: str) -> None:
    if not ID_PATTERN.match(value):
        raise ManifestError(f"{row_name} has invalid {field}: {value}")


def require_url_or_ref(value: str, row_name: str, field: str, ref_ids: set[str]) -> None:
    if value in ref_ids or URL_PATTERN.match(value):
        return
    raise ManifestError(
        f"{row_name} field {field} must be a known ref_id or URL, got: {value}"
    )


def parse_float(value: str, row_name: str, field: str) -> float:
    try:
        return float(value)
    except ValueError as exc:
        raise ManifestError(f"{row_name} has non-numeric {field}: {value}") from exc


def check_unique(rows: list[dict[str, str]], field: str, manifest_name: str) -> None:
    seen: set[str] = set()
    for row in rows:
        value = require(row, field, manifest_name)
        if value in seen:
            raise ManifestError(f"{manifest_name} has duplicate {field}: {value}")
        seen.add(value)


def validate_references() -> set[str]:
    rows = read_csv(MANIFEST_DIR / "references.csv", REFERENCE_COLUMNS)
    check_unique(rows, "ref_id", "references.csv")

    ref_ids: set[str] = set()
    for row in rows:
        ref_id = require(row, "ref_id", "references.csv")
        require_id(ref_id, ref_id, "ref_id")
        ref_ids.add(ref_id)

        category = require(row, "category", ref_id)
        if category not in REFERENCE_CATEGORIES:
            raise ManifestError(f"{ref_id} has invalid category: {category}")

        require(row, "title", ref_id)
        url = require(row, "url", ref_id)
        if not URL_PATTERN.match(url):
            raise ManifestError(f"{ref_id} has invalid URL: {url}")

        checked_date = require(row, "checked_date", ref_id)
        if not DATE_PATTERN.match(checked_date):
            raise ManifestError(f"{ref_id} has invalid checked_date: {checked_date}")

        require(row, "authoritative_for", ref_id)

    return ref_ids


def validate_sources(ref_ids: set[str]) -> set[str]:
    rows = read_csv(MANIFEST_DIR / "sources.csv", SOURCE_COLUMNS)
    check_unique(rows, "source_id", "sources.csv")

    source_ids: set[str] = set()
    for row in rows:
        source_id = require(row, "source_id", "sources.csv")
        require_id(source_id, source_id, "source_id")
        source_ids.add(source_id)

        require(row, "canonical_name", source_id)
        ra_deg = parse_float(require(row, "ra_deg", source_id), source_id, "ra_deg")
        dec_deg = parse_float(require(row, "dec_deg", source_id), source_id, "dec_deg")
        if not 0.0 <= ra_deg < 360.0:
            raise ManifestError(f"{source_id} ra_deg out of range: {ra_deg}")
        if not -90.0 <= dec_deg <= 90.0:
            raise ManifestError(f"{source_id} dec_deg out of range: {dec_deg}")

        require(row, "coordinate_ref", source_id)

        spin = row.get("known_spin_hz", "").strip()
        if spin:
            if parse_float(spin, source_id, "known_spin_hz") <= 0:
                raise ManifestError(f"{source_id} known_spin_hz must be positive")
            spin_ref = require(row, "spin_ref", source_id)
            require_url_or_ref(spin_ref, source_id, "spin_ref", ref_ids)

        priority = row.get("rxte_priority", "").strip()
        if priority and priority not in PRIORITIES:
            raise ManifestError(f"{source_id} has invalid rxte_priority: {priority}")

    return source_ids


def validate_observations(source_ids: set[str], ref_ids: set[str]) -> set[str]:
    rows = read_csv(MANIFEST_DIR / "observations.csv", OBSERVATION_COLUMNS)
    check_unique(rows, "observation_id", "observations.csv")

    obs_ids: set[str] = set()
    for row in rows:
        observation_id = require(row, "observation_id", "observations.csv")
        require_id(observation_id, observation_id, "observation_id")

        source_id = require(row, "source_id", observation_id)
        if source_id not in source_ids:
            raise ManifestError(
                f"{observation_id} references unknown source_id: {source_id}"
            )

        instrument = require(row, "instrument", observation_id)
        if instrument != "RXTE/PCA":
            raise ManifestError(
                f"{observation_id} is not Phase 0/1 RXTE/PCA: {instrument}"
            )

        obs_id = require(row, "obs_id", observation_id)
        if obs_id in obs_ids:
            raise ManifestError(f"observations.csv has duplicate obs_id: {obs_id}")
        obs_ids.add(obs_id)

        archive_ref = row.get("archive_ref", "").strip()
        if archive_ref:
            require_url_or_ref(archive_ref, observation_id, "archive_ref", ref_ids)

        archive_uri = row.get("archive_uri", "").strip()
        if archive_uri and not URL_PATTERN.match(archive_uri):
            raise ManifestError(
                f"{observation_id} has invalid archive_uri: {archive_uri}"
            )

        exposure = row.get("exposure_s", "").strip()
        if exposure and parse_float(exposure, observation_id, "exposure_s") < 0:
            raise ManifestError(f"{observation_id} exposure_s cannot be negative")

        raw_status = row.get("raw_status", "").strip()
        if raw_status and raw_status not in RAW_STATUSES:
            raise ManifestError(f"{observation_id} has invalid raw_status: {raw_status}")

    return obs_ids


def validate_targets(
    source_ids: set[str], ref_ids: set[str], observation_obs_ids: set[str]
) -> None:
    rows = read_csv(MANIFEST_DIR / "validation_targets.csv", VALIDATION_TARGET_COLUMNS)
    check_unique(rows, "target_id", "validation_targets.csv")

    for row in rows:
        target_id = require(row, "target_id", "validation_targets.csv")
        require_id(target_id, target_id, "target_id")

        source_id = require(row, "source_id", target_id)
        if source_id not in source_ids:
            raise ManifestError(f"{target_id} references unknown source_id: {source_id}")

        instrument = require(row, "instrument", target_id)
        if instrument != "RXTE/PCA":
            raise ManifestError(f"{target_id} is not Phase 1 RXTE/PCA: {instrument}")

        obs_id = row.get("obs_id", "").strip()
        if obs_id and obs_id not in observation_obs_ids:
            raise ManifestError(
                f"{target_id} references obs_id without observations.csv row: {obs_id}"
            )

        goal = require(row, "validation_goal", target_id)
        if goal not in VALIDATION_GOALS:
            raise ManifestError(f"{target_id} has invalid validation_goal: {goal}")

        signal = require(row, "expected_signal", target_id)
        if signal not in EXPECTED_SIGNALS:
            raise ManifestError(f"{target_id} has invalid expected_signal: {signal}")

        priority = require(row, "priority", target_id)
        if priority not in PRIORITIES:
            raise ManifestError(f"{target_id} has invalid priority: {priority}")

        expected_frequency = row.get("expected_frequency_hz", "").strip()
        frequency_ref = row.get("frequency_ref", "").strip()
        if expected_frequency:
            if parse_float(expected_frequency, target_id, "expected_frequency_hz") <= 0:
                raise ManifestError(f"{target_id} expected_frequency_hz must be positive")
            if not frequency_ref:
                raise ManifestError(f"{target_id} has frequency but no frequency_ref")
            require_url_or_ref(frequency_ref, target_id, "frequency_ref", ref_ids)

        if signal == "secure_detection" and not expected_frequency:
            raise ManifestError(f"{target_id} secure_detection requires a frequency")


def main() -> int:
    try:
        ref_ids = validate_references()
        source_ids = validate_sources(ref_ids)
        observation_obs_ids = validate_observations(source_ids, ref_ids)
        validate_targets(source_ids, ref_ids, observation_obs_ids)
    except ManifestError as exc:
        print(f"Manifest validation failed: {exc}", file=sys.stderr)
        return 1

    print("Manifest validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
