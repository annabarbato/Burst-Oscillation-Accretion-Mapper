from pathlib import Path
from subprocess import CompletedProcess

from astropy.io import fits

from burst_oscillation_accretion_mapper.rxte_goodxenon import (
    MAKE_SE_SUCCEEDED,
    MAKE_SE_UNPAIRED_GOODXENON,
    run_make_se_if_paired,
    scan_rxte_datamode_files,
)


def test_goodxenon_converter_refuses_unpaired_inputs(tmp_path: Path) -> None:
    pca_dir = tmp_path / "pca"
    pca_dir.mkdir()
    _write_datamode_file(pca_dir / "gx1.fits", "GoodXenon1_16s")

    result = run_make_se_if_paired(
        pca_dir=pca_dir,
        output_dir=tmp_path / "make_se",
        runner=_failing_runner,
    )

    assert result.make_se_status == MAKE_SE_UNPAIRED_GOODXENON
    assert result.goodxenon1_count == 1
    assert result.goodxenon2_count == 0
    assert result.command == ()
    assert result.output_paths == ()


def test_goodxenon_converter_runs_only_when_inputs_are_paired(tmp_path: Path) -> None:
    pca_dir = tmp_path / "pca"
    pca_dir.mkdir()
    _write_datamode_file(pca_dir / "gx1.fits", "GoodXenon1_16s")
    _write_datamode_file(pca_dir / "gx2.fits", "GoodXenon2_16s")

    result = run_make_se_if_paired(
        pca_dir=pca_dir,
        output_dir=tmp_path / "make_se",
        runner=_successful_runner,
    )

    assert result.make_se_status == MAKE_SE_SUCCEEDED
    assert result.goodxenon1_count == 1
    assert result.goodxenon2_count == 1
    assert result.command[0] == "make_se"
    assert result.log_path is not None
    assert result.log_path.read_text(encoding="utf-8") == "ok"


def test_scan_rxte_datamode_files_reads_fits_headers(tmp_path: Path) -> None:
    pca_dir = tmp_path / "pca"
    pca_dir.mkdir()
    _write_datamode_file(pca_dir / "gx1.fits", "GoodXenon1_16s")
    _write_datamode_file(pca_dir / "std2.fits", "Standard2a")

    mode_files = scan_rxte_datamode_files(pca_dir)

    assert [mode_file.datamode for mode_file in mode_files] == [
        "GoodXenon1_16s",
        "Standard2a",
    ]


def _write_datamode_file(path: Path, datamode: str) -> None:
    fits.HDUList(
        [
            fits.PrimaryHDU(header=fits.Header({"DATAMODE": datamode})),
        ]
    ).writeto(path)


def _successful_runner(command, *, cwd, text, capture_output):
    assert text
    assert capture_output
    return CompletedProcess(args=command, returncode=0, stdout="ok", stderr="")


def _failing_runner(*args, **kwargs):
    raise AssertionError("make_se should not run for unpaired inputs")
