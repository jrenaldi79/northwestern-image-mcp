# openrouter-image-mcp

A local MCP server that lets Claude generate and edit images with any model on [OpenRouter](https://openrouter.ai). Models are discovered live, nothing is hard-coded, and results are saved with a metadata sidecar and the cost shown: edits next to the input image, new images in `~/Pictures/OpenRouter Images` by default.

It runs on your machine over stdio and is installed with `uvx` straight from this repo. You sign in once in the browser; you never see or paste an API key.

## Tools

| Tool | What it does |
|---|---|
| `account_status` | Shows whether you are signed in, the key's label, its usage (today, this week, this month, total) and its spending limit. It does not show the workspace. |
| `auth_login` | Starts browser sign-in. Returns at once; you finish in the browser. |
| `auth_logout` | Deletes the stored key from this machine. |
| `list_image_models` | Lists image models live from OpenRouter, with filters for search, image input, author and sort order. |
| `get_image_model` | Shows one model's real aspect ratios, resolutions, quality values, limits and pricing. |
| `generate_image` | Text to image. Saves to `~/Pictures/OpenRouter Images` unless you give `output_dir`. |
| `edit_image` | One or more input images plus a prompt to a new image. Supports masks and exact output sizes. |

The `skills/` folder holds two companion skills: `openrouter-image` (model choice, cost habits, masks, moderation) and `architectural-render-polish`.

## Prerequisites

Install [uv](https://docs.astral.sh/uv/) and [Git](https://git-scm.com/) (uv uses Git to fetch the server from this repo):

```
winget install astral-sh.uv      # Windows
winget install Git.Git           # Windows
brew install uv git              # macOS (or run `xcode-select --install` for Apple's Git)
```

Open a new terminal afterwards so `uvx` and `git` are on your PATH, and **restart Claude (quit it fully) after installing uv or Git** so it sees them too.

## Install

### Claude Code

```
/plugin marketplace add skelly-77/openrouter-image-mcp
/plugin install openrouter-image@skelly-77-tools
```

This installs the server config and both skills.

### Claude Desktop (Windows)

1. Print a config snippet filled in with this machine's paths:

   ```
   uvx --from git+https://github.com/skelly-77/openrouter-image-mcp@v0.1.0 openrouter-image-mcp print-config --client desktop
   ```

2. Open the config file through **Settings → Developer → Edit Config** and merge the `openrouter-image` entry into its `mcpServers` object (back the file up first). Use this route on the Microsoft Store (MSIX) build in particular: edits made by hand under `%APPDATA%\Claude` can be redirected or vanish there. The command only prints; it never edits files.
3. Restart Claude Desktop fully (quit from the tray icon).

**Why the `UV_*` variables?** The Microsoft Store (MSIX) build of Claude Desktop virtualizes writes under `AppData`, so uv's default cache, tools and Python folders can be hidden or discarded. The snippet sets `UV_PYTHON_INSTALL_DIR`, `UV_CACHE_DIR` and `UV_TOOL_DIR` to real folders under `%USERPROFILE%\.uv`, written out literally because the config file does not expand variables.

**Skills for Desktop:** download the repo for the release tag ([v0.1.0 zip](https://github.com/skelly-77/openrouter-image-mcp/archive/refs/tags/v0.1.0.zip)), unzip it, then zip each folder under `skills/` on its own (so each zip contains the skill folder with its `SKILL.md`) and upload them in Settings → Capabilities.

### GitHub Copilot Code (to be confirmed)

Not yet verified: the config file location, its exact format and the skills folder are still open. The standard stdio entry is below. `print-config --client copilot` prints the same JSON to stdout (so you can pipe or paste it) and an "unverified" note to stderr.

```json
{
  "mcpServers": {
    "openrouter-image": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/skelly-77/openrouter-image-mcp@v0.1.0",
        "openrouter-image-mcp"
      ]
    }
  }
}
```

If its sandbox cannot open a browser or reach the credential store, sign in from a terminal (below).

## First sign-in

Either run this in a terminal:

```
uvx --from git+https://github.com/skelly-77/openrouter-image-mcp@v0.1.0 openrouter-image-mcp login
```

or just ask Claude to run `auth_login`, then approve in the browser. The key is stored in your operating system's credential store (Windows Credential Manager, macOS Keychain) and nowhere else. Other commands: `status`, `logout`, `login --switch` (different account).

## Organization billing and privacy

- Keys are locked to your firm's OpenRouter organization's image workspace, so every call spends **org credits**, not personal ones.
- Credits must be added by an org admin (account switcher → the organization → Credits) before anyone can generate. Only org admins buy credits or see billing.
- Organizations are limited to 10 members by default (contact OpenRouter support for more).
- **Privacy:** members see request metadata (model, cost, tokens, creator) for everyone's requests in the workspace, but prompt and response content only for their own requests. Org admins can view everyone's prompts and outputs.
- Client renders and other uploaded images pass through OpenRouter to the model provider (for example OpenAI or Google). **Get the client's or project lead's OK before uploading client imagery.** The skills make Claude ask first.
- Admins can set guardrails on the workspace: allowed models, budgets and data policy.
- **Members who leave:** a member who leaves or is removed from the organization loses access to its credits and API keys. A member who still has active API keys in a workspace can't be removed from that workspace until those keys are deleted — delete their keys first (Workspace → API Keys).

## Configuration

All settings are optional environment variables. Set them in the `env` block of the server's MCP config entry.

| Variable | Default | Meaning |
|---|---|---|
| `OPENROUTER_IMAGE_WORKSPACE_ID` | the organization's image workspace | Workspace that sign-in creates keys in. An empty string means your personal account. |
| `OPENROUTER_IMAGE_OUTPUT_DIR` | `~/Pictures/OpenRouter Images` | Where `generate_image` saves, and the fallback when an edit's folder isn't writable. Empty means the default. |
| `OPENROUTER_IMAGE_MAX_INPUT_EDGE` | `2048` | Input images are downscaled to this longest edge (pixels) before upload. |
| `OPENROUTER_IMAGE_TIMEOUT_S` | `600` | Seconds to wait for one generation. |
| `OPENROUTER_IMAGE_RATIO_TOLERANCE` | `0.03` | How close (3%) a model's aspect ratio must be to the input's for `fit="preserve"` to crop instead of pad. |

## Cost visibility

Each generation reports its cost and the sidecar records it. Failed or cancelled generations are not charged. Ask Claude for `account_status` for today's and this month's usage. Larger `n` and max-quality settings cost more, so iterate cheaply first.

## Troubleshooting

| Symptom | Fix |
|---|---|
| 401 or "not signed in" | The key was deleted or revoked. Ask Claude to run `auth_login` and sign in again. |
| Server won't start in Desktop, or uv errors about permissions or missing folders | Add the `UV_*` environment variables from `print-config --client desktop` (see the MSIX note above). |
| Sign-in doesn't stick | Check Windows Credential Manager for an entry named `openrouter-image-mcp` (`cmdkey /list` may show it as `default@openrouter-image-mcp`). Delete it and sign in again if it looks stale. |
| "Git executable not found" or "Failed to clone" when the server starts | Install Git (`winget install Git.Git`, or `brew install git` / `xcode-select --install` on macOS), then quit and restart Claude so it picks up the new PATH. |
| "Couldn't reach the OpenRouter catalog" | A network or proxy problem fetching the model list. Retry; check you can open https://openrouter.ai/api/v1/images/models in a browser. |
| Moderation refusal | The model's provider declined the prompt or image. Reword the prompt, drop the flagged element, or try another model. |

## Future work

A hosted remote MCP (streamable HTTP plus OAuth) would remove the need for a local `uv` install, but it means running a service that holds user keys, so it is out of scope for v1.

## Development

```
uv sync
uv run pytest                                  # unit tests, no network
uv run pytest -m live                          # hits real OpenRouter; sign in first
uv run ruff check
uv run python scripts/sync_plugin_skills.py    # after editing skills/, refresh plugin/skills/
```

CI runs ruff and the unit tests on Windows, macOS and Ubuntu.

## License

MIT, see [LICENSE](LICENSE).
