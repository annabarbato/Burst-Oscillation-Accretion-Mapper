"""GoodXenon conversion preflight for Phase 1 RXTE validation.

This module records when ``make_se`` can be run safely and when it cannot. It
does not hide an unpaired GoodXenon data set behind a successful conversion
claim; SingleBit fallback remains explicit in product-selection provenance.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path


GOODXENON1_PREFIX = "GoodXenon1"
GOODXENON2_PREFIX = "GoodXenon2"

MAKE_SE_NO_GOODXENON = "no_goodxenon"
MAKE_SE_UNPAIRED_GOODXENON = "unpaired_goodxenon"
MAKE_SE_SUCCEEDED = "conversion_succeeded"
MAKE_SE_FAILED = "conversion_failed"


class RxteGoodXenonError(ValueError):
    """Raised when GoodXenon conversion inputs are invalid."""


@dataclass(frozen=True)
class RxteDataModeFile:
    """One PCA file with a detected RXTE DATAMODE value."""

    path: Path
    datamode: str


@dataclass(frozen=True)
class RxteGoodXenonConversionResult:
    """Result of a guarded ``make_se`` conversion attempt."""

    input_dir: Path
    output_dir: Path
    make_se_status: str
    goodxenon1_count: int
    goodxenon2_count: int
    output_paths: tuple[Path, ...]
    command: tuple[str, ...] = ()
    log_path: Path | None = None
    message: str = ""


def scan_rxte_datamode_files(pca_dir: Path | str) -> tuple[RxteDataModeFile, ...]:
    """Scan a PCA directory for files with FITS ``DATAMODE`` keywords."""

    root = Path(pca_dir)
    if not root.exists():
        raise RxteGoodXenonError(f"Missing PCA directory: {root}")

    return tuple(
        mode_file
        for path in sorted(root.iterdir())
        if path.is_file()
        for mode_file in _datamode_file_or_empty(path)
    )


def run_make_se_if_paired(
    *,
    pca_dir: Path | str,
    output_dir: Path | str,
    make_se_executable: str = "make_se",
    runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
) -> RxteGoodXenonConversionResult:
    """Run ``make_se`` only when paired GoodXenon1/GoodXenon2 inputs exist."""

    input_root = Path(pca_dir)
    output_root = Path(output_dir)
    mode_files = scan_rxte_datamode_files(input_root)
    goodxenon1 = tuple(
        item for item in mode_files if item.datamode.startswith(GOODXENON1_PREFIX)
    )
    goodxenon2 = tuple(
        item for item in mode_files if item.datamode.startswith(GOODXENON2_PREFIX)
    )

    if not goodxenon1 and not goodxenon2:
        return RxteGoodXenonConversionResult(
            input_dir=input_root,
            output_dir=output_root,
            make_se_status=MAKE_SE_NO_GOODXENON,
            goodxenon1_count=0,
            goodxenon2_count=0,
            output_paths=(),
            message="No GoodXenon inputs found",
        )
    if len(goodxenon1) != len(goodxenon2):
        return RxteGoodXenonConversionResult(
            input_dir=input_root,
            output_dir=output_root,
            make_se_status=MAKE_SE_UNPAIRED_GOODXENON,
            goodxenon1_count=len(goodxenon1),
            goodxenon2_count=len(goodxenon2),
            output_paths=(),
            message="GoodXenon inputs are not paired; make_se was not run",
        )

    output_root.mkdir(parents=True, exist_ok=True)
    fits_list_path = output_root / "fits_files.txt"
    fits_list_path.write_text(
        "\n".join(str(item.path.resolve()) for item in mode_files) + "\n",
        encoding="utf-8",
    )
    log_path = output_root / "make_se.log"
    command = (
        make_se_executable,
        f"infile={fits_list_path.name}",
        "outfile=se",
        "clobber=yes",
    )
    completed = _run_make_se(command, cwd=output_root, runner=runner)
    log_path.write_text(
        (completed.stdout or "") + (completed.stderr or ""),
        encoding="utf-8",
    )
    output_paths = tuple(
        sorted(
            path
            for path in output_root.glob("se*")
            if path.is_file() and path.suffix.lower() in {".evt", ".fits"}
        )
    )
    status = MAKE_SE_SUCCEEDED if completed.returncode == 0 else MAKE_SE_FAILED
    return RxteGoodXenonConversionResult(
        input_dir=input_root,
        output_dir=output_root,
        make_se_status=status,
        goodxenon1_count=len(goodxenon1),
        goodxenon2_count=len(goodxenon2),
        output_paths=output_paths,
        command=command,
        log_path=log_path,
        message=f"make_se exited with status {completed.returncode}",
    )


def _datamode_file_or_empty(path: Path) -> tuple[RxteDataModeFile, ...]:
    datamode = _read_datamode(path)
    if not datamode:
        return ()
    return (RxteDataModeFile(path=path, datamode=datamode),)


def _read_datamode(path: Path) -> str:
    try:
        from astropy.io import fits
    except Exception as exc:  # pragma: no cover - optional dependency guard
        raise RxteGoodXenonError(
            "Astropy is required to inspect RXTE DATAMODE keywords"
        ) from exc

    try:
        with fits.open(path) as hdul:
            for hdu in hdul:
                datamode = str(hdu.header.get("DATAMODE", "")).strip()
                if datamode:
                    return datamode
    except Exception:
        return ""
    return ""


def _run_make_se(
    command: tuple[str, ...],
    *,
    cwd: Path,
    runner: Callable[..., subprocess.CompletedProcess[str]] | None,
) -> subprocess.CompletedProcess[str]:
    if runner is not None:
        return runner(command, cwd=cwd, text=True, capture_output=True)
    return subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)
