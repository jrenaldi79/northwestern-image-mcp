"""Runtime configuration for openrouter-image-mcp."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

API_BASE = "https://openrouter.ai/api/v1"
AUTH_URL = "https://openrouter.ai/auth"
APP_URL = "https://github.com/skelly-77/openrouter-image-mcp"
APP_TITLE = "openrouter-image-mcp"
KEYRING_SERVICE = "openrouter-image-mcp"
KEYRING_USER = "default"

# The "Image Tools" workspace of the firm's OpenRouter organization. Not a secret:
# only members of the organization can use it. Setting OPENROUTER_IMAGE_WORKSPACE_ID
# to an empty string means "personal workspace" (the workspace param is omitted).
DEFAULT_WORKSPACE_ID = "42861d2b-4736-477d-aaeb-0f300c31596f"

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


def _parse(env: Mapping[str, str], name: str, cast, default):
    raw = env.get(name)
    if raw is None:
        return default
    try:
        return cast(raw)
    except ValueError:
        raise ValueError(f"{name} must be a {cast.__name__}, got {raw!r}") from None


def load_settings(env: Mapping[str, str] = os.environ) -> Settings:
    output_dir = env.get(_ENV_OUTPUT_DIR) or None  # empty means unset
    return Settings(
        workspace_id=env.get(_ENV_WORKSPACE_ID, DEFAULT_WORKSPACE_ID),
        output_dir=(
            Path(output_dir).expanduser()
            if output_dir is not None
            else Path.home() / "Pictures" / "OpenRouter Images"
        ),
        max_input_edge=_parse(env, _ENV_MAX_INPUT_EDGE, int, 2048),
        timeout_s=_parse(env, _ENV_TIMEOUT_S, float, 600.0),
        ratio_tolerance=_parse(env, _ENV_RATIO_TOLERANCE, float, 0.03),
    )
