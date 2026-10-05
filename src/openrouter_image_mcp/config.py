"""Runtime configuration for openrouter-image-mcp."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

API_BASE = "https://openrouter.ai/api/v1"
AUTH_URL = "https://openrouter.ai/auth"
APP_URL = "https://github.com/skelly-77/openrouter-image-mcp"
APP_TITLE = "Northwestern AI Images"
KEYRING_SERVICE = "northwestern-openrouter-image-mcp"
COHORT_WORKSPACES = {
    "2027": "21082e84-ae02-4639-ad40-c7251b98ab10",
    "2028": "8804f9c5-afd2-4de3-8d9f-f74b3d58c651",
}
# Compatibility default for internal client helpers; runtime selection is explicit.
KEYRING_USER = COHORT_WORKSPACES["2027"]

_ENV_WORKSPACE_ID = "OPENROUTER_IMAGE_WORKSPACE_ID"
_ENV_OUTPUT_DIR = "OPENROUTER_IMAGE_OUTPUT_DIR"
_ENV_MAX_INPUT_EDGE = "OPENROUTER_IMAGE_MAX_INPUT_EDGE"
_ENV_TIMEOUT_S = "OPENROUTER_IMAGE_TIMEOUT_S"
_ENV_RATIO_TOLERANCE = "OPENROUTER_IMAGE_RATIO_TOLERANCE"


@dataclass(frozen=True)
class Settings:
    workspace_id: str
    output_dir: Path
    max_input_edge: int
    timeout_s: float
    ratio_tolerance: float

    def __post_init__(self) -> None:
        if self.workspace_id not in COHORT_WORKSPACES.values():
            raise ValueError(
                "Settings workspace must belong to a configured Northwestern cohort."
            )

    @property
    def cohort(self) -> str:
        return next(
            year
            for year, workspace in COHORT_WORKSPACES.items()
            if workspace == self.workspace_id
        )

    @property
    def target(self) -> str:
        return (
            f"Configured target: Northwestern University / Class of {self.cohort}"
            f"\nWorkspace: {self.workspace_id}"
        )


def _parse(env: Mapping[str, str], name: str, cast, default):
    raw = env.get(name)
    if raw is None:
        return default
    try:
        return cast(raw)
    except ValueError:
        raise ValueError(f"{name} must be a {cast.__name__}, got {raw!r}") from None


def load_settings(env: Mapping[str, str] = os.environ) -> Settings:
    cohort = env.get("OPENROUTER_IMAGE_COHORT")
    workspace = env.get(_ENV_WORKSPACE_ID)
    if cohort is not None and cohort not in COHORT_WORKSPACES:
        raise ValueError("OPENROUTER_IMAGE_COHORT must be 2027 or 2028.")
    if workspace is not None and workspace not in COHORT_WORKSPACES.values():
        raise ValueError(
            "OPENROUTER_IMAGE_WORKSPACE_ID must be a known Northwestern workspace."
        )
    if cohort is None and workspace is None:
        raise ValueError(
            "Select a cohort: set OPENROUTER_IMAGE_COHORT to 2027 or 2028."
        )
    if (
        cohort is not None
        and workspace is not None
        and COHORT_WORKSPACES[cohort] != workspace
    ):
        raise ValueError(
            "OPENROUTER_IMAGE_COHORT conflicts with OPENROUTER_IMAGE_WORKSPACE_ID."
        )
    if cohort is None:
        cohort = next(
            year for year, value in COHORT_WORKSPACES.items() if value == workspace
        )
    output_dir = env.get(_ENV_OUTPUT_DIR) or None  # empty means unset
    return Settings(
        workspace_id=COHORT_WORKSPACES[cohort],
        output_dir=(
            Path(output_dir).expanduser()
            if output_dir is not None
            else Path.home() / "Pictures" / "Northwestern AI" / f"Class of {cohort}"
        ),
        max_input_edge=_parse(env, _ENV_MAX_INPUT_EDGE, int, 2048),
        timeout_s=_parse(env, _ENV_TIMEOUT_S, float, 600.0),
        ratio_tolerance=_parse(env, _ENV_RATIO_TOLERANCE, float, 0.03),
    )
