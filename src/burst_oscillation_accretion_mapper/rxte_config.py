"""RXTE/PCA Phase 1 ingestion configuration primitives."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from hashlib import sha256


class RxteConfigError(ValueError):
    """Raised when RXTE ingestion configuration is invalid."""


@dataclass(frozen=True)
class RxteDetectorSelection:
    """Detector metadata to carry into event products and provenance."""

    pcus: tuple[int, ...] = (2,)
    layers: tuple[int, ...] = (1,)

    def __post_init__(self) -> None:
        if not self.pcus:
            raise RxteConfigError("At least one PCU must be selected")
        if not self.layers:
            raise RxteConfigError("At least one PCA layer must be selected")
        for pcu in self.pcus:
            if pcu < 0 or pcu > 4:
                raise RxteConfigError(f"PCU out of RXTE/PCA range 0-4: {pcu}")
        for layer in self.layers:
            if layer < 1 or layer > 3:
                raise RxteConfigError(f"PCA layer out of range 1-3: {layer}")


@dataclass(frozen=True)
class RxteBarycenterConfig:
    """Barycenter correction policy and reference metadata."""

    apply_barycenter: bool = True
    ephemeris: str = "DE405"
    task_name: str = "barycorr"
    source_position_ref: str = ""

    def __post_init__(self) -> None:
        if self.apply_barycenter and not self.ephemeris.strip():
            raise RxteConfigError("Barycenter ephemeris is required when enabled")
        if self.apply_barycenter and not self.task_name.strip():
            raise RxteConfigError("Barycenter task name is required when enabled")


@dataclass(frozen=True)
class RxteIngestionConfig:
    """Configuration metadata for the first RXTE ingestion backend."""

    detector_selection: RxteDetectorSelection = RxteDetectorSelection()
    barycenter: RxteBarycenterConfig = RxteBarycenterConfig()
    accepted_data_modes: tuple[str, ...] = ("GoodXenon", "event")
    time_system: str = "TDB"

    def __post_init__(self) -> None:
        if not self.accepted_data_modes:
            raise RxteConfigError("At least one accepted data mode is required")
        if not self.time_system.strip():
            raise RxteConfigError("time_system is required")

    @property
    def screening_hash(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return sha256(payload.encode("utf-8")).hexdigest()

    @property
    def detector_label(self) -> str:
        pcus = "-".join(str(pcu) for pcu in self.detector_selection.pcus)
        layers = "-".join(str(layer) for layer in self.detector_selection.layers)
        return f"pcu{pcus}_layer{layers}"
