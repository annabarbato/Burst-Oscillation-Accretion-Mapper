"""RXTE/PCA ingestion preflight helpers for Phase 1.

This module stops at local raw-product readiness. It does not parse RXTE FITS
files, run HEASoft, apply barycenter corrections, or build event products.
"""

from __future__ import annotations

from dataclasses import dataclass

from .archive_plan import RXTE_INSTRUMENT, RawObservationPlan
from .raw_inventory import RawInventory, RawInventoryError, inventory_raw_files


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
