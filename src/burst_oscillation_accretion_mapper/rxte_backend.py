"""RXTE/PCA ingestion preflight helpers for Phase 1.

This module stops at local raw-product readiness and provenance. FITS event
tables are read by ``rxte_fits``; HEASoft execution and barycenter correction
remain explicit downstream steps.
"""

from __future__ import annotations

from dataclasses import dataclass

from .archive_plan import RXTE_INSTRUMENT, RawObservationPlan
from .event_products import EventProductProvenance
from .external_tools import ExternalToolEnvironment
from .raw_inventory import RawInventory, RawInventoryError, inventory_raw_files
from .rxte_config import RxteIngestionConfig


READY_RAW_STATUSES = frozenset({"downloaded", "verified"})


class RxtePreflightError(ValueError):
    """Raised when a planned RXTE observation is not ready for ingestion."""


@dataclass(frozen=True)
class RxtePreparedObservation:
    """A ready local RXTE observation plus raw-file inventory."""

    plan: RawObservationPlan
    inventory: RawInventory

    @property
    def obs_id(self) -> str:
        return self.plan.obs_id

    @property
    def n_raw_files(self) -> int:
        return len(self.inventory.files)


def prepare_rxte_observation(plan: RawObservationPlan) -> RxtePreparedObservation:
    """Validate one RXTE raw observation plan and inventory local files."""

    if plan.instrument != RXTE_INSTRUMENT:
        raise RxtePreflightError(f"Expected RXTE/PCA plan, got {plan.instrument}")
    if plan.raw_status not in READY_RAW_STATUSES:
        raise RxtePreflightError(
            f"{plan.obs_id} raw_status is {plan.raw_status!r}; "
            "expected downloaded or verified"
        )

    try:
        inventory = inventory_raw_files(plan.raw_path)
    except RawInventoryError as exc:
        raise RxtePreflightError(f"{plan.obs_id} raw inventory failed: {exc}") from exc

    if inventory.is_empty:
        raise RxtePreflightError(f"{plan.obs_id} raw directory contains no files")

    return RxtePreparedObservation(plan=plan, inventory=inventory)


def prepare_rxte_observations(
    plans: tuple[RawObservationPlan, ...]
) -> tuple[RxtePreparedObservation, ...]:
    """Validate and inventory multiple RXTE observations."""

    return tuple(prepare_rxte_observation(plan) for plan in plans)


def build_rxte_event_provenance(
    prepared: RxtePreparedObservation,
    *,
    config: RxteIngestionConfig,
    environment: ExternalToolEnvironment,
) -> EventProductProvenance:
    """Build event-product provenance for local RXTE event-table ingestion."""

    software_parts = []
    if environment.headas:
        software_parts.append(f"HEADAS={environment.headas}")
    if environment.tool_paths:
        available = sorted(
            tool for tool, path in environment.tool_paths.items() if path is not None
        )
        missing = sorted(environment.missing_tools)
        if available:
            software_parts.append("tools=" + "|".join(available))
        if missing:
            software_parts.append("missing_tools=" + "|".join(missing))

    return EventProductProvenance(
        raw_uri=str(prepared.plan.raw_path),
        software_version=";".join(software_parts),
        caldb_version=environment.caldb,
        screening_hash=config.screening_hash,
        barycorr_ref=config.barycenter.ephemeris
        if config.barycenter.apply_barycenter
        else "",
        barycorr_applied=False,
        notes=(
            f"RXTE preflight only; detector={config.detector_label}; "
            f"raw_files={prepared.n_raw_files}"
        ),
    )
