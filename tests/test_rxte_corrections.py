from pathlib import Path

import pytest

from burst_oscillation_accretion_mapper.rxte_corrections import (
    RxteCorrectionError,
    barycorr_output_path,
    build_barycorr_command,
)


def test_build_barycorr_command_uses_source_coordinates_and_orbit_file(
    tmp_path: Path,
) -> None:
    orbit = tmp_path / "FPorbit_Day1092"
    orbit.touch()

    command = build_barycorr_command(
        input_path=Path("data/raw/rxte/obs/pca/SE1_0100-0200.evt.gz"),
        output_path=Path("data/processed/rxte/obs/barycorr/SE1_0100-0200_bary.evt"),
        orbit_files=(orbit,),
        ra_deg=250.231657064,
        dec_deg=-53.751374474,
        refframe="ICRS",
        ephem="JPLEPH.440",
    )

    assert command[0] == "barycorr"
    assert "ra=250.231657064" in command
    assert "dec=-53.751374474" in command
    assert "refframe=ICRS" in command
    assert "ephem=JPLEPH.440" in command
    assert "barytime=no" in command
    assert "clobber=yes" in command
    assert f"orbitfiles={orbit.as_posix()}" in command


def test_build_barycorr_command_rejects_geocenter() -> None:
    with pytest.raises(RxteCorrectionError, match="GEOCENTER"):
        build_barycorr_command(
            input_path="in.evt",
            output_path="out.evt",
            orbit_files=("GEOCENTER",),
            ra_deg=1.0,
            dec_deg=2.0,
        )


def test_barycorr_output_path_uses_uncompressed_validation_name() -> None:
    assert barycorr_output_path(
        Path("SE1_0100-0200.evt.gz"),
        Path("out"),
    ) == Path("out/SE1_0100-0200_bary.evt")
    assert barycorr_output_path(
        Path("FS4f_0100-0200.gz"),
        Path("out"),
    ) == Path("out/FS4f_0100-0200_bary.fits")
