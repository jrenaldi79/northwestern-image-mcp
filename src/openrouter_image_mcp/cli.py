"""Command-line entry point: serve (default), login, logout, status, print-config."""

from __future__ import annotations

import argparse
import asyncio
import glob
import importlib
import json
import os
import re
import shutil
import sys
from pathlib import Path, PureWindowsPath
from typing import Literal

import keyring.errors

from . import keystore
from .auth import LoginManager, LoginState
from .client import OpenRouterClient
from .config import load_settings
from .errors import OpenRouterError
from .keystore import InsecureKeyringError
from .logs import configure_logging, redact

REPO_URL = "git+https://github.com/skelly-77/openrouter-image-mcp"
SERVER_NAME = "openrouter-image"
DEFAULT_REF = "v0.1.0"
COPILOT_NOTE = (
    "Unverified: Copilot Code's MCP config format has not been confirmed yet. "
    "The standard stdio entry is printed to stdout."
)
SIGNED_OUT_MSG = "Not signed in. Run `openrouter-image-mcp login`."
LOGOUT_MSG = (
    "Signed out. To revoke the key on OpenRouter, delete it at "
    "https://openrouter.ai/settings/keys"
)
UVX_MISSING_MSG = (
    "Could not find uvx. Install uv first: winget install astral-sh.uv "
    "(then open a new terminal and retry)."
)

ClientName = Literal["desktop", "code", "copilot"]


def find_uvx() -> str | None:
    found = shutil.which("uvx")
    if found:
        return found
    local = os.environ.get("LOCALAPPDATA")
    if local:
        pattern = os.path.join(
            local, "Microsoft", "WinGet", "Packages", "astral-sh.uv_*", "uvx.exe"
        )
        matches = sorted(glob.glob(pattern))
        if matches:
            return matches[0]
    return None


def _uv_dir(home: Path, *parts: str) -> str:
    if re.match(r"^[A-Za-z]:", str(home)):
        return str(PureWindowsPath(str(home), ".uv", *parts))
    return str(home / ".uv" / Path(*parts))


def render_config(
    client: ClientName, uvx: str, home: Path, ref: str = DEFAULT_REF
) -> str:
    args = ["--from", f"{REPO_URL}@{ref}", "openrouter-image-mcp"]
    if client == "desktop":
        entry: dict = {
            "command": uvx,
            "args": args,
            "env": {
                "UV_PYTHON_INSTALL_DIR": _uv_dir(home, "python"),
                "UV_CACHE_DIR": _uv_dir(home, "cache"),
                "UV_TOOL_DIR": _uv_dir(home, "tools"),
            },
        }
    else:
        entry = {"command": "uvx", "args": args}
    return json.dumps({"mcpServers": {SERVER_NAME: entry}}, indent=2)


# ----------------------------------------------------------------- commands


def _serve(args: argparse.Namespace) -> int:
    configure_logging()
    importlib.import_module("openrouter_image_mcp.server").run()
    return 0


async def _login(switch: bool) -> int:
    settings = load_settings()
    client = OpenRouterClient(timeout_s=settings.timeout_s)
    try:
        manager = LoginManager(client, settings)
        started = await manager.start(switch_account=switch)
        print(started["message"])
        if started["state"] == LoginState.PENDING.value:
            try:
                final = await manager.wait()
            except (KeyboardInterrupt, asyncio.CancelledError):
                manager.cancel()  # close the listener; a late callback is ignored
                raise
        else:
            final = LoginState(started["state"])
        if final is LoginState.SIGNED_IN:
            return 0
        print(manager.status()["message"])
        return 1
    finally:
        await client.aclose()


def _login_cmd(args: argparse.Namespace) -> int:
    try:
        return asyncio.run(_login(args.switch))
    except KeyboardInterrupt:
        print("Sign-in cancelled.")
        return 130


def _logout(args: argparse.Namespace) -> int:
    keystore.delete_key()
    print(LOGOUT_MSG)
    return 0


async def _key_info(timeout_s: float) -> dict:
    client = OpenRouterClient(timeout_s=timeout_s)
    try:
        return await client.key_info()
    finally:
        await client.aclose()


def _money(value: object) -> str:
    return f"${float(value or 0):.2f}"


def _status(args: argparse.Namespace) -> int:
    if keystore.get_key() is None:
        print(SIGNED_OUT_MSG)
        return 1
    settings = load_settings()
    try:
        info = asyncio.run(_key_info(settings.timeout_s))
    except OpenRouterError as exc:
        print(exc.message)
        return 1
    if info.get("label"):
        print(redact(f"Signed in: {info['label']}"))
    else:
        print("Signed in.")
    print(
        f"Usage today: {_money(info.get('usage_daily'))} / "
        f"month: {_money(info.get('usage_monthly'))}"
    )
    return 0


def _print_config(args: argparse.Namespace) -> int:
    uvx = find_uvx()
    if uvx is None and args.client == "desktop":
        print(UVX_MISSING_MSG, file=sys.stderr)
        return 1
    if args.client == "copilot":
        print(COPILOT_NOTE, file=sys.stderr)  # keep stdout pasteable JSON
    print(render_config(args.client, uvx or "uvx", Path.home(), ref=args.ref))
    return 0


# --------------------------------------------------------------------- main


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="openrouter-image-mcp",
        description="Local stdio MCP server for OpenRouter image generation.",
    )
    parser.set_defaults(func=_serve)
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("serve", help="run the MCP server over stdio (default)").set_defaults(
        func=_serve
    )
    login = sub.add_parser("login", help="sign in to OpenRouter in your browser")
    login.add_argument("--switch", action="store_true", help="sign in as a different account")
    login.set_defaults(func=_login_cmd)
    sub.add_parser("logout", help="remove the stored API key").set_defaults(func=_logout)
    sub.add_parser("status", help="show sign-in state and usage").set_defaults(func=_status)
    pc = sub.add_parser("print-config", help="print an MCP client config snippet")
    pc.add_argument("--client", choices=["desktop", "code", "copilot"], default="desktop")
    pc.add_argument("--ref", default=DEFAULT_REF, help="git tag or branch to install")
    pc.set_defaults(func=_print_config)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        return args.func(args)
    except InsecureKeyringError as exc:
        print(redact(str(exc)), file=sys.stderr)
        return 1
    except keyring.errors.KeyringError as exc:
        print(redact(f"Couldn't access the OS credential store: {exc}"), file=sys.stderr)
        return 1
    except OSError as exc:  # e.g. the sign-in listener couldn't bind
        print(redact(str(exc)), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
