from pathlib import Path

from burst_oscillation_accretion_mapper.external_tools import (
    path_exists,
    probe_external_environment,
)


def test_probe_external_environment_captures_heasoft_variables() -> None:
    env = {"HEADAS": "/opt/heasoft", "CALDB": "/caldb", "IGNORED": "value"}

    snapshot = probe_external_environment(env=env)

    assert snapshot.headas == "/opt/heasoft"
    assert snapshot.caldb == "/caldb"
    assert snapshot.has_headas
    assert snapshot.has_caldb


def test_probe_external_environment_records_missing_and_available_tools() -> None:
    def fake_which(tool_name: str) -> str | None:
        return f"/tools/{tool_name}" if tool_name == "barycorr" else None

    snapshot = probe_external_environment(
        env={}, tool_names=("barycorr", "xtefilt"), which=fake_which
    )

    assert snapshot.tool_paths == {"barycorr": "/tools/barycorr", "xtefilt": None}
    assert snapshot.missing_tools == ("xtefilt",)


def test_path_exists_checks_non_empty_paths(tmp_path: Path) -> None:
    assert path_exists(str(tmp_path))
    assert not path_exists("")
    assert not path_exists(str(tmp_path / "missing"))
