"""Search-configuration fingerprints for Phase 1 review provenance."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from hashlib import sha256
from math import isfinite

from .candidate_scoring import CandidateScoringConfig
from .oscillation_search import SlidingWindowConfig, TargetedZ2SearchConfig


class SearchConfigError(ValueError):
    """Raised when a search-configuration fingerprint is invalid."""


@dataclass(frozen=True)
class TargetedSearchReviewConfig:
    """Deterministic fingerprint input for targeted Phase 1 candidate review."""

    window_config: SlidingWindowConfig
    search_config: TargetedZ2SearchConfig
    scoring_config: CandidateScoringConfig
    expected_frequency_hz: float | None = None
    energy_band: str = ""
    product_kind: str = "candidate_review"

    def __post_init__(self) -> None:
        if self.expected_frequency_hz is not None and (
            not isfinite(self.expected_frequency_hz) or self.expected_frequency_hz <= 0
        ):
            raise SearchConfigError("expected_frequency_hz must be positive when set")
        if not self.product_kind.strip():
            raise SearchConfigError("product_kind is required")

    @property
    def config_hash(self) -> str:
        """Return a stable SHA-256 hash over the normalized configuration."""

        return sha256(_canonical_json(self.payload).encode("utf-8")).hexdigest()

    @property
    def config_id(self) -> str:
        """Return a compact identifier suitable for Phase 1 catalog rows."""

        return f"targeted-z2-{self.config_hash[:16]}"

    @property
    def payload(self) -> dict[str, object]:
        """Return the normalized payload used for hashing and review records."""

        return {
            "energy_band": self.energy_band,
            "expected_frequency_hz": self.expected_frequency_hz,
            "product_kind": self.product_kind,
            "scoring_config": asdict(self.scoring_config),
            "search_config": asdict(self.search_config),
            "window_config": asdict(self.window_config),
        }

    @property
    def payload_json(self) -> str:
        """Return canonical JSON for the fingerprinted configuration."""

        return _canonical_json(self.payload)


def _canonical_json(payload: dict[str, object]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))
