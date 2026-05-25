"""External mission-tool environment snapshots.

Phase 1 code records whether HEASoft/CALDB appear configured, but this module
does not run mission tools or modify the user's shell environment.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from shutil import which as default_which


HEASOFT_ENV_VARS = ("HEADAS", "CALDB", "PFILES")


@dataclass(frozen=True)
class ExternalToolEnvironment:
    """Snapshot of local mission-tool environment state."""

    variables: dict[str, str]
    tool_paths: dict[str, str | None]

    @property
    def headas(self) -> str:
        return self.variables.get("HEADAS", "")

    @property
    def caldb(self) -> str:
        return self.variables.get("CALDB", "")

    @property
    def has_headas(self) -> bool:
        return bool(self.headas)

    @property
    def has_caldb(self) -> bool:
        return bool(self.caldb)

    @property
    def missing_tools(self) -> tuple[str, ...]:
        return tuple(tool for tool, path in self.tool_paths.items() if path is None)


def probe_external_environment(
    *,
    env: Mapping[str, str] | None = None,
    tool_names: tuple[str, ...] = (),
    which: Callable[[str], str | None] = default_which,
) -> ExternalToolEnvironment:
    """Return a read-only snapshot of HEASoft/CALDB variables and tool paths."""

    source_env = os.environ if env is None else env
    variables = {
        name: source_env[name]
        for name in HEASOFT_ENV_VARS
        if source_env.get(name)
    }
    tool_paths = {tool_name: which(tool_name) for tool_name in tool_names}
    return ExternalToolEnvironment(variables=variables, tool_paths=tool_paths)


def path_exists(path_value: str) -> bool:
    """Return whether a non-empty environment path currently exists."""

    return bool(path_value) and Path(path_value).exists()
