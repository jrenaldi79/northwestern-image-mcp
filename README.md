# Northwestern AI image MCP

Local image generation and editing for Northwestern University AI classes. Each student signs in individually to the Northwestern OpenRouter organization. Claude supplies image analysis; this server retains its eight image and account tools.

**Instructor testing only. Student deployment is on hold until OpenRouter increases organization capacity.**

Repository: [jrenaldi79/northwestern-image-mcp](https://github.com/jrenaldi79/northwestern-image-mcp)
(private). Adapted from [skelly-77/openrouter-image-mcp](https://github.com/skelly-77/openrouter-image-mcp),
with the original MIT license and commit history retained.

## Cohorts

| Cohort | Students | Required OpenRouter workspace |
| --- | --- | --- |
| 2027 | Capstone, full-time and second-year | Class of 2027 (`21082e84-ae02-4639-ad40-c7251b98ab10`) |
| 2028 | First-year | Class of 2028 (`8804f9c5-afd2-4de3-8d9f-f74b3d58c651`) |

Set `OPENROUTER_IMAGE_COHORT=2027` or `2028`. Missing, empty, unknown or conflicting selection fails before sign-in. `OPENROUTER_IMAGE_WORKSPACE_ID` can alternatively select either ID above. There is no personal-account or original-firm fallback.

## Local Claude Desktop setup

Use this checkout and Python 3.12 or newer. Prepare an environment with uv:

```powershell
uv venv --python 3.13 .venv
uv pip install --python .venv\Scripts\python.exe --group dev -e .
.venv\Scripts\python.exe -m openrouter_image_mcp.cli print-config --cohort 2027
```

On macOS/Linux use `.venv/bin/python` instead. `print-config` produces one `northwestern-images` entry using this interpreter and checkout. Use `--cohort 2028` for a first-year student. Use **Settings → This computer → Developer → Edit config** to locate the active file; the usual Windows location is `%APPDATA%\Claude\claude_desktop_config.json`.

**Fully exit Claude Desktop through File → Exit before editing.** Closing its window can leave it running. Back up the configuration and merge these `mcpServers` entries, preserving other settings and servers. Reopen Claude Desktop and confirm the single Northwestern entry shows **Running** in Developer settings. Manually configured local servers are managed there, separately from remote connector setup in Customize. Keep the checkout and environment in place.

Maintain one server and one installation entry. Each student receives the same server configured with their confirmed cohort; the two class workspaces remain in OpenRouter. Student release instructions will follow instructor testing and the capacity increase. The original upstream release does not contain these changes.

## Instructor test

1. Select the 2027 tools in Claude Desktop and ask for `account_status`. Confirm the configured workspace above.
2. Ask for `auth_login` on that server and finish browser consent with your Northwestern organization account. Organization/workspace membership must be granted separately; this server does not enroll users.
3. Ask for `account_status` again and inspect the created key in the corresponding OpenRouter workspace. The target is configuration; a key label alone does not independently prove billing ownership.
4. To test 2028 later, fully exit Claude, rerun the installer with --cohort 2028, and reopen it. This replaces the same entry. Saved credentials remain isolated by workspace.
5. List image models and inspect pricing. Before a paid test, agree on one image (`n=1`), the model and likely cost. Startup and tool discovery do not require paid generation.

Terminal testing selects a cohort first:

```powershell
$env:OPENROUTER_IMAGE_COHORT = "2027"
.venv\Scripts\python.exe -m openrouter_image_mcp.cli status
.venv\Scripts\python.exe -m openrouter_image_mcp.cli login
.venv\Scripts\python.exe -m openrouter_image_mcp.cli logout
```

Change the cohort to `2028` for that profile. If `OPENROUTER_IMAGE_WORKSPACE_ID` is also set, it must match. `login --switch` replaces only this cohort's credential. Keys use the OS credential store under `northwestern-openrouter-image-mcp`, indexed by workspace ID. Legacy credentials are neither copied nor reused. Logout removes the local key; revoke it separately in OpenRouter if needed.

## Tools

| Tool | What it does |
| --- | --- |
| `account_status` | Shows configured Northwestern cohort/workspace, sign-in state, key label, spending and available limits. |
| `auth_login` | Starts browser sign-in constrained to this workspace. |
| `auth_logout` | Removes this cohort's saved credential. |
| `list_image_models` | Discovers available image models and pricing. |
| `get_image_model` | Shows model parameters, providers and prices. |
| `generate_image` | Generates images with metadata and reported costs. |
| `edit_image` | Edits local images using references, masks and output sizing. |
| `remask_image` | Re-blends a saved masked edit locally, with no upload or model charge. |

New images default to `~/Pictures/Northwestern AI/Class of 2027` or `Class of 2028`. Edits save beside the primary input. Existing explicit output overrides remain available. Files are not overwritten; JSON sidecars record prompts, settings and reported costs. Keep those files in mind when sharing coursework.

Prompts and input images go through OpenRouter to third-party providers. Get explicit permission before uploading other people's images, research materials or confidential project information. Start with one low-cost draft and relay reported spending. Use the live catalog for model choice and prices. Organization/workspace budgets are administered in OpenRouter; this server does not create or increase them.

## Inline image previews

The existing server includes an MCP Apps gallery for `generate_image`, `edit_image`,
and `remask_image`. Hosts advertising MCP Apps HTML support receive a bundled viewer
with JPEG previews, filenames, saved paths, reported usage/cost, notes and failures.
Original files still save locally. Clients without that capability keep receiving
ordinary text and image content. SVGs and files beyond the preview limit show their
saved filenames without an inline preview. The gallery needs no network connection.

After updating the checkout, fully exit and reopen Claude Desktop, then start a new
chat to refresh tool metadata. Actual inline rendering depends on the installed
host's MCP Apps support for local servers. Claude's web app cannot reach this local
stdio server directly.

To check the gallery without paying for a model call, prepare a synthetic fixture:

```powershell
.venv\Scripts\python.exe scripts\prepare_gallery_test.py
```

Paste the printed `remask_image` request into the new Claude Desktop chat. It creates
a local preview with a $0.00 cost and uploads nothing. An existing masked edit can
also be re-masked for free; a plain generated image lacks the required mask sidecar.

## Companion skills and local plugin

`skills/openrouter-image` carries the general workflow; `skills/architectural-render-polish` remains optional. Run `python scripts/sync_plugin_skills.py` after source skill changes. The bundled Claude Code plugin contains one instructor entry configured for 2027 and uses `uv run --no-sync` against the prepared checkout; it requires an installed environment and `uv` on the client's PATH. It is not a published Northwestern distribution.

## Development

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\ruff.exe check .
```

Live tests are excluded by default because they use OpenRouter and may cost money. Original project provenance remains in the Git remote and MIT license. Keep student roster data in the roster spreadsheet.

The gallery HTML is committed in the Python package. Node is only needed to change
or rebuild it, not to run the server:

```powershell
cd ui
npm ci
npm run build
npm test
```

Browser tests use Playwright Chromium, or set `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH` to an
existing Chrome executable. They exercise the bundled viewer with a synthetic
image and a mock MCP Apps host, without OpenRouter calls.
