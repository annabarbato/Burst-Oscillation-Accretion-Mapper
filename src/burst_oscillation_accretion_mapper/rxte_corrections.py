"""RXTE/PCA timing-correction wrappers for Phase 1 validation.

The only supported Solar System timing correction here is HEASoft ``barycorr``
with real RXTE spacecraft orbit files. A geocenter fallback is deliberately
rejected because it is not adequate for burst-oscillation timing validation.
"""

from __future__ import annotations

import platform
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from math import isfinite
from pathlib import Path


BARYCORR_APPLIED = "applied"
BARYCORR_ALREADY_APPLIED = "already_applied"
BARYCORR_FAILED = "failed"
BARYCORR_SKIPPED = "skipped"
NO_EPHEMERIS = "no_ephemeris"


class RxteCorrectionError(ValueError):
    """Raised when RXTE timing correction cannot be run safely."""


@dataclass(frozen=True)
class RxteCorrectionResult:
    """Provenance for one RXTE timing-correction step."""

    input_path: Path
    output_path: Path
    barycorr_command: tuple[str, ...]
    barycorr_status: str
    ephemeris: str
    refframe: str
    orbit_files: tuple[Path, ...]
    binarycorr_status: str
    ra_deg: float
    dec_deg: float
    returncode: int | None = None
    stdout: str = ""
    stderr: str = ""


def build_barycorr_command(
    *,
    input_path: Path | str,
    output_path: Path | str,
    orbit_files: tuple[Path | str, ...],
    ra_deg: float,
    dec_deg: float,
    refframe: str = "ICRS",
    ephem: str = "JPLEPH.440",
    barytime: bool = False,
    clobber: bool = True,
    executable: str = "barycorr",
) -> tuple[str, ...]:
    """Build a HEASoft ``barycorr`` command with real orbit files."""

    _validate_coordinates(ra_deg, dec_deg)
    checked_orbits = _checked_orbit_files(orbit_files)
    if refframe.upper() == "GEOCENTER":
        raise RxteCorrectionError("GEOCENTER is not allowed for Phase 1 barycorr")

    return (
        executable,
        f"infile={_as_posix(input_path)}",
        f"outfile={_as_posix(output_path)}",
        f"orbitfiles={_orbitfiles_argument(checked_orbits)}",
        f"ra={ra_deg:.12g}",
        f"dec={dec_deg:.12g}",
        f"refframe={refframe}",
        f"ephem={ephem}",
        f"barytime={'yes' if barytime else 'no'}",
        f"clobber={'yes' if clobber else 'no'}",
    )


def run_rxte_barycorr(
    *,
    input_path: Path | str,
    output_dir: Path | str,
    orbit_files: tuple[Path | str, ...],
    ra_deg: float,
    dec_deg: float,
    binary_ephemeris_ref: str = "",
    working_dir: Path | str | None = None,
    ephem: str = "JPLEPH.440",
    refframe: str = "ICRS",
    overwrite: bool = False,
) -> RxteCorrectionResult:
    """Run ``barycorr`` and return correction provenance."""

    input_file = Path(input_path)
    output_root = Path(output_dir)
    checked_orbits = _checked_orbit_files(orbit_files)
    output_root.mkdir(parents=True, exist_ok=True)
    output_file = barycorr_output_path(input_file, output_root)
    command = build_barycorr_command(
        input_path=input_file,
        output_path=output_file,
        orbit_files=checked_orbits,
        ra_deg=ra_deg,
        dec_deg=dec_deg,
        refframe=refframe,
        ephem=ephem,
        barytime=False,
        clobber=True,
    )
    binary_status = (
        "not_applied_ephemeris_available"
        if binary_ephemeris_ref.strip()
        else NO_EPHEMERIS
    )

    if output_file.exists() and not overwrite:
        return RxteCorrectionResult(
            input_path=input_file,
            output_path=output_file,
            barycorr_command=command,
            barycorr_status=BARYCORR_ALREADY_APPLIED,
            ephemeris=ephem,
            refframe=refframe,
            orbit_files=checked_orbits,
            binarycorr_status=binary_status,
            ra_deg=ra_deg,
            dec_deg=dec_deg,
            returncode=0,
        )

    completed = _run_heasoft_command(command, working_dir=working_dir)
    status = BARYCORR_APPLIED if completed.returncode == 0 else BARYCORR_FAILED
    return RxteCorrectionResult(
        input_path=input_file,
        output_path=output_file,
        barycorr_command=command,
        barycorr_status=status,
        ephemeris=ephem,
        refframe=refframe,
        orbit_files=checked_orbits,
        binarycorr_status=binary_status,
        ra_deg=ra_deg,
        dec_deg=dec_deg,
        returncode=completed.returncode,
        stdout=completed.stdout or "",
        stderr=completed.stderr or "",
    )


def barycorr_output_path(input_path: Path | str, output_dir: Path | str) -> Path:
    """Return the ignored barycentered output path for one RXTE input file."""

    input_file = Path(input_path)
    output_root = Path(output_dir)
    name = input_file.name
    if name.endswith(".gz"):
        name = name[:-3]
    if name.endswith(".evt"):
        stem = name[:-4]
        suffix = ".evt"
    else:
        parsed = Path(name)
        stem = parsed.stem if parsed.suffix else parsed.name
        suffix = parsed.suffix or ".fits"
    return output_root / f"{stem}_bary{suffix}"


def correction_result_to_json(result: RxteCorrectionResult) -> dict[str, object]:
    """Return a JSON-serializable correction summary."""

    return {
        "input_path": str(result.input_path),
        "output_path": str(result.output_path),
        "barycorr_command": list(result.barycorr_command),
        "barycorr_status": result.barycorr_status,
        "ephemeris": result.ephemeris,
        "refframe": result.refframe,
        "orbit_files": [str(path) for path in result.orbit_files],
        "binarycorr_status": result.binarycorr_status,
        "ra_deg": result.ra_deg,
        "dec_deg": result.dec_deg,
        "returncode": result.returncode,
    }


def _run_heasoft_command(
    command: tuple[str, ...],
    *,
    working_dir: Path | str | None,
) -> subprocess.CompletedProcess[str]:
    cwd = None if working_dir is None else Path(working_dir)
    if shutil.which(command[0]):
        return subprocess.run(
            command,
            cwd=cwd,
            text=True,
            capture_output=True,
            check=False,
        )
    if platform.system().lower().startswith("win") and shutil.which("wsl"):
        return _run_wsl_heasoft_command(command, working_dir=cwd)
    return subprocess.CompletedProcess(
        args=command,
        returncode=127,
        stdout="",
        stderr=f"Cannot find HEASoft command: {command[0]}",
    )


def _run_wsl_heasoft_command(
    command: tuple[str, ...],
    *,
    working_dir: Path | None,
) -> subprocess.CompletedProcess[str]:
    if working_dir is None:
        raise RxteCorrectionError("working_dir is required for WSL HEASoft execution")

    conda_base = "/home/anna/miniforge3"
    conda_env = "henv"
    wsl_cwd = _windows_path_to_wsl(working_dir)
    command_line = " ".join(shlex.quote(arg) for arg in command)
    script = "\n".join(
        (
            "set -eo pipefail",
            f"cd {shlex.quote(wsl_cwd)}",
            f"source {conda_base}/etc/profile.d/conda.sh",
            f"conda activate {shlex.quote(conda_env)} >/dev/null",
            command_line,
        )
    )
    return subprocess.run(
        ("wsl", "bash", "-lc", script),
        text=True,
        capture_output=True,
        check=False,
    )


def _windows_path_to_wsl(path: Path) -> str:
    resolved = path.resolve()
    drive = resolved.drive.rstrip(":").lower()
    if not drive:
        return resolved.as_posix()
    tail = resolved.as_posix().split(":", maxsplit=1)[1].lstrip("/")
    return f"/mnt/{drive}/{tail}"


def _checked_orbit_files(orbit_files: tuple[Path | str, ...]) -> tuple[Path, ...]:
    checked = tuple(Path(path) for path in orbit_files)
    if not checked:
        raise RxteCorrectionError("At least one real RXTE orbit file is required")
    for path in checked:
        if str(path).upper() == "GEOCENTER" or path.name.upper() == "GEOCENTER":
            raise RxteCorrectionError("GEOCENTER is not allowed for Phase 1 barycorr")
        if not path.exists():
            raise RxteCorrectionError(f"Missing RXTE orbit file: {path}")
    return checked


def _orbitfiles_argument(orbit_files: tuple[Path, ...]) -> str:
    if len(orbit_files) == 1:
        return _as_posix(orbit_files[0])
    return ",".join(_as_posix(path) for path in orbit_files)


def _as_posix(path: Path | str) -> str:
    return Path(path).as_posix()


def _validate_coordinates(ra_deg: float, dec_deg: float) -> None:
    if not isfinite(ra_deg) or ra_deg < 0.0 or ra_deg >= 360.0:
        raise RxteCorrectionError(f"Invalid source RA: {ra_deg}")
    if not isfinite(dec_deg) or dec_deg < -90.0 or dec_deg > 90.0:
        raise RxteCorrectionError(f"Invalid source Dec: {dec_deg}")
