from hashlib import sha256
from pathlib import Path

import pytest

from burst_oscillation_accretion_mapper.raw_inventory import (
    RawInventoryError,
    inventory_raw_files,
)


def test_inventory_raw_files_records_sorted_relative_paths_and_checksums(
    tmp_path: Path,
) -> None:
    nested = tmp_path / "subdir"
    nested.mkdir()
    first = tmp_path / "a.evt"
    second = nested / "b.fits"
    first.write_bytes(b"alpha")
    second.write_bytes(b"beta")

    inventory = inventory_raw_files(tmp_path)

    assert [file.relative_path for file in inventory.files] == [
        "a.evt",
        "subdir/b.fits",
    ]
    assert [file.size_bytes for file in inventory.files] == [5, 4]
    assert inventory.total_size_bytes == 9
    assert inventory.files[0].sha256 == sha256(b"alpha").hexdigest()
    assert inventory.files[1].sha256 == sha256(b"beta").hexdigest()


def test_inventory_raw_files_allows_empty_directories(tmp_path: Path) -> None:
    inventory = inventory_raw_files(tmp_path)

    assert inventory.files == ()
    assert inventory.is_empty


def test_inventory_raw_files_rejects_missing_path(tmp_path: Path) -> None:
    with pytest.raises(RawInventoryError, match="does not exist"):
        inventory_raw_files(tmp_path / "missing")


def test_inventory_raw_files_rejects_file_path(tmp_path: Path) -> None:
    file_path = tmp_path / "single.evt"
    file_path.write_bytes(b"event")

    with pytest.raises(RawInventoryError, match="not a directory"):
        inventory_raw_files(file_path)
