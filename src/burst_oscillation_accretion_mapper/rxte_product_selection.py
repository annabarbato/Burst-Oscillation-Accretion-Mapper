"""RXTE/PCA validation-product selection for Phase 1 closeout.

The selector keeps fallback behavior explicit. It prefers barycentered
``XTE_SE`` event tables, then raw ``XTE_SE`` tables, then successful ``make_se``
outputs, and only then SingleBit binned products for validation targets that
lack convertible paired GoodXenon inputs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .time_intervals import TimeInterval


class RxteProductSelectionError(ValueError):
    """Raised when no usable RXTE validation product can be selected."""


@dataclass(frozen=True)
class RxteProductSelection:
    """Selected RXTE product plus the fallback rationale."""

    selected_product_path: Path
    reader_type: str
    data_mode: str
    selection_reason: str
    fallback_status: str
    is_barycentered: bool = False


@dataclass(frozen=True)
class _ProductCandidate:
    path: Path
    rank: int
    reader_type: str
    data_mode: str
    selection_reason: str
    fallback_status: str
    is_barycentered: bool = False


_RXTE_HEX_INTERVAL = re.compile(r"_([0-9a-fA-F]{5,})-([0-9a-fA-F]{5,})")


def select_rxte_phase1_product(
    *,
    raw_obs_path: Path | str,
    processed_obs_path: Path | str,
    target_time_met: float | None = None,
) -> RxteProductSelection:
    """Select the highest-ranked burst-covering RXTE product for Phase 1."""

    raw_path = Path(raw_obs_path)
    processed_path = Path(processed_obs_path)
    candidates = tuple(
        candidate
        for candidate in _candidate_products(raw_path, processed_path)
        if _covers_target_time(candidate.path, target_time_met)
    )
    if not candidates:
        raise RxteProductSelectionError(
            f"No burst-covering RXTE validation product found under {raw_path}"
        )

    best = min(candidates, key=lambda candidate: (candidate.rank, candidate.path.name))
    return RxteProductSelection(
        selected_product_path=best.path,
        reader_type=best.reader_type,
        data_mode=best.data_mode,
        selection_reason=best.selection_reason,
        fallback_status=best.fallback_status,
        is_barycentered=best.is_barycentered,
    )


def rxte_filename_time_interval(path: Path | str) -> TimeInterval | None:
    """Return the mission-time interval encoded in common RXTE file names."""

    match = _RXTE_HEX_INTERVAL.search(Path(path).name)
    if match is None:
        return None
    start = int(match.group(1), 16)
    stop = int(match.group(2), 16)
    if stop <= start:
        return None
    return TimeInterval(float(start), float(stop))


def _candidate_products(
    raw_obs_path: Path,
    processed_obs_path: Path,
) -> tuple[_ProductCandidate, ...]:
    pca_path = raw_obs_path / "pca"
    barycorr_path = processed_obs_path / "barycorr"
    make_se_path = processed_obs_path / "make_se"
    candidates: list[_ProductCandidate] = []

    candidates.extend(
        _ProductCandidate(
            path=path,
            rank=0,
            reader_type="fits",
            data_mode="XTE_SE",
            selection_reason="barycentered XTE_SE event table",
            fallback_status="none",
            is_barycentered=True,
        )
        for path in _glob_many(barycorr_path, ("SE*.evt", "SE*.fits", "SE*.evt.gz"))
    )
    candidates.extend(
        _ProductCandidate(
            path=path,
            rank=1,
            reader_type="fits",
            data_mode="XTE_SE",
            selection_reason="raw XTE_SE event table pending barycorr",
            fallback_status="raw_xte_se_pending_barycorr",
            is_barycentered=False,
        )
        for path in _glob_many(pca_path, ("SE*.evt", "SE*.evt.gz", "SE*.fits"))
    )
    candidates.extend(
        _ProductCandidate(
            path=path,
            rank=2,
            reader_type="fits",
            data_mode="make_se",
            selection_reason="successful make_se event-table output",
            fallback_status="make_se_output",
            is_barycentered=False,
        )
        for path in _glob_many(make_se_path, ("*.evt", "*.evt.gz", "*.fits"))
    )
    candidates.extend(
        _ProductCandidate(
            path=path,
            rank=3,
            reader_type="singlebit",
            data_mode="SingleBit",
            selection_reason="barycentered SingleBit validation fallback",
            fallback_status="singlebit_binned_fallback",
            is_barycentered=True,
        )
        for path in _glob_many(barycorr_path, ("FS4f*_bary.fits",))
    )
    candidates.extend(
        _ProductCandidate(
            path=path,
            rank=4,
            reader_type="singlebit",
            data_mode="SingleBit",
            selection_reason="SingleBit binned validation fallback",
            fallback_status="singlebit_binned_fallback",
            is_barycentered=False,
        )
        for path in _glob_many(pca_path, ("FS4f_*",))
    )
    return tuple(candidates)


def _glob_many(root: Path, patterns: tuple[str, ...]) -> tuple[Path, ...]:
    if not root.exists():
        return ()
    paths: list[Path] = []
    for pattern in patterns:
        paths.extend(path for path in root.glob(pattern) if path.is_file())
    return tuple(sorted(set(paths)))


def _covers_target_time(path: Path, target_time_met: float | None) -> bool:
    if target_time_met is None:
        return True
    interval = rxte_filename_time_interval(path)
    if interval is None:
        return True
    return interval.start <= target_time_met <= interval.stop
