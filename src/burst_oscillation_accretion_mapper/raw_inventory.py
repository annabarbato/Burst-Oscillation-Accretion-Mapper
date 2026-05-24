"""Local raw-product inventory helpers.

These helpers inspect already-local files only. They do not download mission
data, create archive directories, or interpret FITS contents.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path


class RawInventoryError(ValueError):
    """Raised when a local raw-product inventory cannot be built."""


@dataclass(frozen=True)
class RawFileRecord:
    """Checksum and size metadata for one local raw product."""

    path: Path
    relative_path: str
    size_bytes: int
    sha256: str


@dataclass(frozen=True)
class RawInventory:
    """Inventory for one local observation raw-product directory."""

    root: Path
    files: tuple[RawFileRecord, ...]

    @property
    def total_size_bytes(self) -> int:
        return sum(file.size_bytes for file in self.files)

    @property
    def is_empty(self) -> bool:
        return not self.files


def inventory_raw_files(root: Path | str) -> RawInventory:
    """Return checksums for all files below a local raw-product directory."""

    raw_root = Path(root)
    if not raw_root.exists():
        raise RawInventoryError(f"Raw path does not exist: {raw_root}")
    if not raw_root.is_dir():
        raise RawInventoryError(f"Raw path is not a directory: {raw_root}")

    files = tuple(
        _record_file(path, raw_root)
        for path in sorted(
            (candidate for candidate in raw_root.rglob("*") if candidate.is_file()),
            key=lambda candidate: candidate.relative_to(raw_root).as_posix(),
        )
    )
    return RawInventory(root=raw_root, files=files)


def _record_file(path: Path, root: Path) -> RawFileRecord:
    return RawFileRecord(
        path=path,
        relative_path=path.relative_to(root).as_posix(),
        size_bytes=path.stat().st_size,
        sha256=_sha256(path),
    )


def _sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
