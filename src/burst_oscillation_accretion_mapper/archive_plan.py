"""Archive planning helpers for Phase 1 RXTE validation.

The helpers in this module do not download data or create directories. They
turn curated validation manifest rows into expected local raw-product paths so
the first RXTE ingestion backend can fail clearly when mission files are absent.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .manifests import ManifestIndex, ObservationRow, ValidationTargetContext


RXTE_INSTRUMENT = "RXTE/PCA"


@dataclass(frozen=True)
class RawObservationPlan:
    """Expected local raw-data state for one validation observation."""

    target_id: str
    source_id: str
    obs_id: str
    instrument: str
    minbar_burst_id: str
    expected_signal: str
    raw_path: Path
    raw_exists: bool
    raw_status: str
    archive_ref: str
    archive_uri: str

    @property
    def is_ready_for_ingestion(self) -> bool:
        return self.raw_exists and self.raw_status in {"downloaded", "verified"}


def build_rxte_raw_archive_plan(
    manifests: ManifestIndex,
    *,
    raw_root: Path | str,
    repo_root: Path | str | None = None,
) -> tuple[RawObservationPlan, ...]:
    """Build expected local raw-data paths for RXTE validation targets.

    When `observations.csv` provides `local_raw_path`, that value wins. Relative
    local paths are resolved against `repo_root` when supplied, otherwise the
    current working directory. Blank paths fall back to `raw_root/rxte/{obs_id}`.
    """

    return tuple(
        _plan_for_context(context, raw_root=Path(raw_root), repo_root=repo_root)
        for context in manifests.rxte_validation_contexts()
    )


def missing_raw_observations(
    plans: tuple[RawObservationPlan, ...]
) -> tuple[RawObservationPlan, ...]:
    """Return plan rows that are not ready for ingestion."""

    return tuple(plan for plan in plans if not plan.is_ready_for_ingestion)


def _plan_for_context(
    context: ValidationTargetContext,
    *,
    raw_root: Path,
    repo_root: Path | str | None,
) -> RawObservationPlan:
    observation = context.observation
    if observation.instrument != RXTE_INSTRUMENT:
        raise ValueError(f"Expected RXTE/PCA observation, got {observation.instrument}")

    raw_path = _raw_path_for_observation(
        observation, raw_root=raw_root, repo_root=repo_root
    )
    return RawObservationPlan(
        target_id=context.target.target_id,
        source_id=context.source.source_id,
        obs_id=observation.obs_id,
        instrument=observation.instrument,
        minbar_burst_id=context.target.minbar_burst_id,
        expected_signal=context.target.expected_signal,
        raw_path=raw_path,
        raw_exists=raw_path.exists(),
        raw_status=observation.raw_status,
        archive_ref=observation.archive_ref,
        archive_uri=observation.archive_uri,
    )


def _raw_path_for_observation(
    observation: ObservationRow,
    *,
    raw_root: Path,
    repo_root: Path | str | None,
) -> Path:
    if observation.local_raw_path:
        local_path = Path(observation.local_raw_path)
        if local_path.is_absolute():
            return local_path
        base = Path.cwd() if repo_root is None else Path(repo_root)
        return base / local_path

    return raw_root / _instrument_dir(observation.instrument) / observation.obs_id


def _instrument_dir(instrument: str) -> str:
    if instrument == RXTE_INSTRUMENT:
        return "rxte"
    return instrument.lower().replace("/", "_")
