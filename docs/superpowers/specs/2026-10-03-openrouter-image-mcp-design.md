# openrouter-image-mcp — Design Spec

- **Date:** 2026-10-03
- **Status:** Approved 2026-10-03
- **Repo:** `C:\Users\user\source\openrouter-image-mcp` (to be published as a public GitHub repo)

## 1. Intent

### What the user asked for
A **local MCP server** (Python, installed with one `uvx` line) that gives Claude, and other MCP clients, general-purpose **image generation and editing through any OpenRouter image model**: text in → image out, and image(s) in + prompt → image out.

The motivating case: send an architectural render (e.g. `Sample_Render_v5.jpg`, 1920×828) plus an edit prompt to OpenAI's newest image model and get a photoreal "polished" image back at the same framing. The hosted OpenRouter connector can't do this: `generate-image` is text-only and `send-message` returns text only.

### Hard requirements
1. **Per-user OAuth PKCE sign-in** to OpenRouter. No shared or hand-copied keys. Key stored in the OS credential store only. Sign out, switch account, and re-auth on 401.
2. **Central billing** through the user's OpenRouter Organization (decided: one locked org workspace; see §5.5).
3. **Live model discovery** as a first-class feature. No hard-coded model list.
4. **General tools:** generate, edit with 1..N input images, mask/inpainting, size and aspect control (including non-standard ratios such as 2.32:1), variations, outputs saved next to the input with a metadata sidecar, inline previews, cost visibility, clear moderation errors.
5. **No prompt presets in the server.** Domain know-how ships as separate skills.
6. **Team distribution:** packaging, client config snippets, README.

### Clients (decided)
Mostly Windows + Claude Desktop (MSIX), some Claude Code, and **Microsoft Copilot Code** (the new Copilot desktop app, announced 2026-09-25, which runs local MCP servers). Mac is supported but not acceptance-tested.

### Success criteria
- A teammate installs with `uv` plus one config snippet (or one plugin install in Claude Code), signs in through the browser, and can generate or edit images without ever seeing an API key.
- The sample render comes back photoreal at **exactly 1920×828**, saved next to the input with a sidecar and cost shown.
- Usage is billed to the org workspace, with per-member visibility for the admin.

### Non-goals (v1)
- A hosted remote MCP.
- AI upscaling.
- Streaming partial previews.
- A cost estimator.
- Server-side prompt templates.
- Revoking keys on OpenRouter (it needs a management key).
- Editing client config files automatically.

## 2. Verified OpenRouter facts (checked 2026-10-03)

| Fact | Source |
|---|---|
| `POST /api/v1/images` is a dedicated image endpoint. Body: `model`, `prompt`, `input_references: [{type:"image_url", image_url:{url}}]` (HTTPS or base64 data URLs), `n` (1–10), `resolution` (`512`/`768`/`1K`/`1.5K`/`2K`/`4K`), `aspect_ratio`, `size`, `quality`, `seed`, `background`, `output_format`, `output_compression`, `stream`, `provider` (routing plus `options` passthrough). Response: `data:[{b64_json, media_type}]`, `usage:{…, cost}`. | docs: guides/overview/multimodal/image-generation |
| Image billing is **all-or-nothing**: failed or cancelled generations are not charged. | same |
| `GET /api/v1/images/models` (public, no auth) and `GET /api/v1/images/models/{id}/endpoints` return typed capability descriptors (`enum` / `range` / `boolean`) per model and per provider, `allowed_passthrough_parameters`, `supports_streaming`, and pricing line items. | same; live call |
| Live sample, `openai/gpt-image-2.5-sunburst`: `aspect_ratio` ∈ {1:1, 3:2, 2:3, 4:3, 3:4, 16:9, 9:16, **21:9**, auto}; `quality` ∈ {auto, low, medium, high, xhigh, max}; `n` 1–10; `input_references` 0–16; passthrough `moderation`. | live call |
| Across all 55 live `/images` models, **no mask parameter exists**. | live call |
| Chat/completions with `modalities:["image","text"]` still works. Images come back in `choices[0].message.images[].image_url.url`. Used for models missing from `/images/models`. | prototype; docs |
| OAuth: browser to `https://openrouter.ai/auth?callback_url=…&code_challenge=…&code_challenge_method=S256&state=…&key_label=…&required_workspace_id=…`. Localhost callbacks are allowed on any port. Callback receives `?code=…&state=…`. Exchange: `POST /api/v1/auth/keys {code, code_verifier, code_challenge_method}` returns `{key, user_id}`. | docs: guides/overview/auth/oauth |
| `required_workspace_id` locks the key to a workspace. If the user's account doesn't have that workspace, the auth page shows an error and authorization is impossible. | same |
| `GET /api/v1/key` returns the current key's usage (daily, weekly, monthly, total), limit and creator. `GET /api/v1/credits` **needs a management key**, so it's not usable here. | docs: api-reference |
| Moderation errors: 403 with `error.metadata = {reasons[], flagged_input, provider_name, model_slug}`. | docs: errors-and-debugging |
| Workspaces: org admins manage billing and credits. Members see request metadata for everyone in the workspace but prompt and response content only for their own requests. **Org admins can see everyone's prompt and response content.** Workspaces can set guardrails (allowed models, budgets, data policy). | docs: guides/features/workspaces |

## 3. Architecture

Python 3.12, stdio transport. Dependencies: official `mcp` SDK (FastMCP), `httpx`, `Pillow`, `keyring`. Dev dependencies: `pytest`, `pytest-asyncio`, `respx`, `ruff`.

| Module | Responsibility | Depends on |
|---|---|---|
| `server.py` | Registers MCP tools; thin wrappers that validate arguments and format results | all below |
| `auth.py` | PKCE pair, auth URL, one-shot localhost callback listener (background), code exchange, login state machine (`idle → pending → signed_in / failed / expired`) | `keystore`, `client` |
| `keystore.py` | get/set/delete the key in the OS credential store. The **only** code that touches the key. | `keyring` |
| `client.py` | OpenRouter HTTP: `/images`, chat fallback, `/key`, `/generation`, catalogs. Maps HTTP errors to typed exceptions. Retries. Redaction. | `keystore` |
| `catalog.py` | Fetches and caches (10 min) `/images/models` plus endpoints; normalizes them into a `ModelCapabilities` dataclass | `client` |
| `imaging.py` | Pure Pillow functions: prepare inputs, plan aspect ratio, crop back, pad, composite masks, make previews. No network. | `Pillow` |
| `outputs.py` | Output paths, collision handling, temp-then-rename writes, JSON sidecars. No network. | stdlib |
| `config.py` | Defaults plus environment overrides | stdlib |
| `cli.py` | `openrouter-image-mcp [serve\|login\|logout\|status\|print-config]`; `serve` is the default | `auth`, `server` |

**Data flow for an edit:**
1. `server` looks up the model's capabilities in `catalog` and validates the arguments.
2. `imaging.prepare_input` processes each input image.
3. `imaging.plan_fit` decides the aspect-ratio strategy.
4. `client` calls `/images`, or chat/completions as the fallback.
5. `imaging.apply_fit` crops back to the input size, then `imaging.composite_mask` applies any mask.
6. `outputs` saves the images and sidecars.
7. `server` returns a text summary plus inline previews.

### 3.1 Config (environment variables, all optional)
| Var | Default |
|---|---|
| `OPENROUTER_IMAGE_WORKSPACE_ID` | the org workspace UUID baked into the release (empty string means personal account) |
| `OPENROUTER_IMAGE_OUTPUT_DIR` | `~/Pictures/OpenRouter Images` |
| `OPENROUTER_IMAGE_MAX_INPUT_EDGE` | `2048` |
| `OPENROUTER_IMAGE_TIMEOUT_S` | `600` |
| `OPENROUTER_IMAGE_RATIO_TOLERANCE` | `0.03` |

There is **no `OPENROUTER_API_KEY` fallback**.

## 4. Tools

### Account
- **`account_status()`** — signed in or not, key label, usage (day/week/month/total) and limit remaining from `GET /key`, and the current login state if a login is pending. It doesn't show the workspace (`GET /key` doesn't return it).
- **`auth_login(switch_account=false)`** — starts the login in the background and returns at once with "finish in your browser" plus the auth URL, which contains no secret. If already signed in it does nothing unless `switch_account=true`. When switching, the old key is kept until the new one is stored.
- **`auth_logout()`** — deletes the stored key and links the dashboard keys page for revoking it on OpenRouter.

### Discovery
- **`list_image_models(query?, accepts_images?, author?, sort="newest"|"price")`** — a compact table: id, name, accepts images and the maximum count, aspect ratios, resolution tiers, quality values, maximum `n`, seed support, `is_moderated`, and a pricing summary.
- **`get_image_model(model_id)`** — description, per-provider capabilities, passthrough options, and pricing line items.

### Images (shared implementation)
- **`generate_image(prompt, model, n=1, aspect_ratio?, resolution?, size?, quality?, seed?, background?, output_format?, output_dir?, filename_prefix?, provider_options?)`**
- **`edit_image(prompt, model, images:[path,…], mask_path?, mask_feather_px?, fit="preserve"|"model", n=1, …same optional params)`**

Rules:
- Parameters are validated against the model's capabilities **before** any spend; an invalid value fails with the list of allowed values.
- `n` must be 1–10. If it exceeds the model's maximum, the server makes `ceil(n / max_n)` calls of up to `max_n` images each and says so in the result.
- `provider_options` is a flat dict. Before spend, its keys are checked against the union of the model endpoints' `allowed_passthrough_parameters`; it is sent as `provider.options` keyed by provider slug (`{"options": {"openai": {"moderation": "low"}}}`), one entry per endpoint that allows the keys. The sidecar records the flat dict.
- The result is a text summary (saved paths, sidecar paths, model, provider, seed, cost, elapsed time, fit notes, usage line) **plus** inline JPEG previews (longest edge 1024 px, quality 80, at most 4).

## 5. Authentication and key storage

### 5.1 Login flow
1. Create the PKCE values: the verifier is 64 random bytes in base64url; the challenge is S256 of the verifier. Create a random `state`.
2. Start an HTTP listener on `127.0.0.1:0` (any free port) in a background thread. It:
   - accepts exactly one `GET /callback`;
   - rejects a mismatched `state`;
   - serves a "Signed in — you can close this tab" page;
   - stops after one callback or after 5 minutes, at which point the state becomes `expired`.
3. Open the browser with `webbrowser.open` at `https://openrouter.ai/auth` with:
   - `callback_url=http://localhost:{port}/callback`
   - `code_challenge`, `code_challenge_method=S256`, `state`
   - `key_label=openrouter-image-mcp ({hostname})`
   - `required_workspace_id={config workspace}`, left out if the workspace setting is empty
4. Exchange: `POST /api/v1/auth/keys` with `{code, code_verifier, code_challenge_method:"S256"}`.
5. Store the key, then confirm it with `GET /key`. State becomes `signed_in`.

The CLI `login` command runs the same flow in the foreground and prints the result. It is the fallback when a client sandbox blocks opening a browser.

### 5.2 Storage
- `keyring`: service `openrouter-image-mcp`, username `default`. That's Windows Credential Manager on Windows and Keychain on macOS.
- Only the key is stored; everything else comes from `GET /key` when needed.
- If the active backend is insecure (`fail`, `null` or plaintext), the server refuses to store the key and explains why. There is no plaintext fallback.

### 5.3 Logging
- Logs go to stderr only.
- A logging filter masks `sk-or-[A-Za-z0-9-_]+` patterns.
- Response bodies are truncated and redacted before logging.

### 5.4 Errors during auth
- **401 from any call:** delete the stored key and return a "call `auth_login`" error. Never open the browser automatically.
- **Login expires:** the status message notes that a non-member of the org cannot authorize and needs an invite.

### 5.5 Organizations (README content)
- Keys minted with `required_workspace_id` belong to the org workspace and spend **org credits**.
- Only org admins buy credits or see billing.
- Admins can set per-workspace guardrails: allowed models, budgets, data policy.
- **Privacy note for the team:** org admins can view everyone's prompts and outputs, and client renders pass through OpenRouter to the model provider.
- **To verify during org setup:** what happens to a departing member's keys.

**Org setup procedure** (an implementation-plan task, after spec approval). Done through Claude in Chrome with the user's confirmation at each click:
1. Create the Organization.
2. Create the workspace (e.g. "Image Tools").
3. Record the workspace UUID into the config default.
4. Invite teammates, confirming the email list with the user first.

The user does credits, payment and any sign-in personally.

## 6. Image handling

### 6.1 Input preparation
- Paths must be absolute (or start with `~`); a relative path is rejected.
- Accepted formats: JPEG, PNG, WebP, TIFF, BMP.
- Apply the EXIF orientation, then convert to 8-bit RGB (or RGBA if the image has an alpha channel).
- **Always re-encode and strip metadata:** PNG if the image has alpha or the source was PNG, otherwise JPEG at quality 95.
- Downscale so the longest edge is at most `MAX_INPUT_EDGE`.
- The first image is the primary and sets the output size. The rest are references, and their count is checked against `input_references.max`.

### 6.2 Aspect ratio planning (`fit="preserve"`, the default for edits)
Let the primary be W×H with ratio r = W/H. From the model's supported `aspect_ratio` values (excluding `auto`), pick the ratio a minimizing |ln(a/r)|.

1. **Crop-back** (relative error ≤ tolerance, 3% by default):
   - Request `aspect_ratio=a`.
   - If `resolution` is supported, also request the smallest tier at or above max(W, H).
   - Scale the output to cover W×H, then centre-crop to exactly W×H.
   - *Sample render:* r = 2.319, a = 21:9 = 2.333, error 0.6%.
2. **Pad, then crop** (no supported ratio within tolerance):
   - Pad the primary to ratio a with blurred mirrored edges.
   - Record the content box as fractions of the padded image.
   - After generation, crop that box out of the output and resize it to W×H.
   - The result notes that padding was used.
3. **No `aspect_ratio` support at all:** send the image unchanged, then crop back as in option 1 and note how much was cropped.

If the output is smaller than W×H, upscale with Lanczos and note "upscaled from X".

`fit="model"` skips all of the above and returns the model's output untouched. `generate_image` uses the arguments as given and does no fitting.

### 6.3 Masks (local compositing)
- The mask is greyscale: white = take new pixels, black = keep the original. It is resized to W×H.
- Feather it with a Gaussian blur, radius `mask_feather_px` (default 0.5% of the short edge).
- After fitting: `final = output·m + original·(1−m)`. Black areas stay **byte-identical** to the prepared original.
- The tool description notes the possible lighting seam at the mask edge.

### 6.4 Output decoding
- Decode `b64_json` (or the chat data URL) and check the format with Pillow.
- No post-processing → save the provider's bytes as-is.
- Post-processed → save as PNG, or JPEG/WebP at quality 95 if `output_format` asks for one.
- SVG outputs are saved as `.svg` with no fitting and no preview, and a note says so.

## 7. Outputs, metadata, cost, errors

### 7.1 Naming
- **Edits:** next to the primary input, as `{stem}__{model-short}_{YYYYMMDD-HHMMSS}_{i}.{ext}`.
- **Generate:** in `OUTPUT_DIR`, as `{filename_prefix or prompt-slug(6 words)}__{model-short}_{ts}_{i}.{ext}`.
- `output_dir` overrides both. If the target isn't writable, fall back to `OUTPUT_DIR` and say so.
- Never overwrite: append `-2`, `-3`, and so on.
- Write to `*.tmp`, then `os.replace` into place.

### 7.2 Sidecar: `<image>.json`, one per image
```json
{
  "schema_version": 1, "server_version": "0.1.0", "tool": "edit_image",
  "created_at": "2026-10-03T22:15:00-05:00",
  "model": "openai/gpt-image-2.5-sunburst", "provider": "openai",
  "prompt": "…",
  "params": {"aspect_ratio": "21:9", "resolution": null, "quality": "high", "n": 1, "seed": null, "provider_options": {}},
  "seed": 12345, "generation_id": "gen-…", "elapsed_s": 74.2,
  "usage": {"prompt_tokens": 0, "completion_tokens": 0}, "cost_usd": 0.21, "call_cost_usd": 0.21,
  "inputs": [{"path": "C:/…/v5.jpg", "sha256": "…", "size": [1920, 828]}],
  "mask": null,
  "fit": {"strategy": "crop_back", "requested_ratio": "21:9", "raw_size": [2016, 864], "final_size": [1920, 828], "crop_box": [6, 0, 1926, 828], "padded": false, "upscaled": false}
}
```
`crop_box` is expressed in the coordinates of the output *after* it has been scaled to cover W×H. In the example, 2016×864 × 0.958 = 1932×828, cropped to 1920×828.

The sidecar never contains the key, its label, or the user ID.

### 7.3 Cost
- Taken from `usage.cost`. If it's missing, look it up with `GET /api/v1/generation?id=…`.
- Each result ends with a usage line: `This call: $X · Key usage today: $Y / month: $Z`. `/key` is cached for 60 s.

### 7.4 Error mapping
| Condition | Behaviour |
|---|---|
| 401 | Delete the key; "sign-in no longer valid, call `auth_login`" |
| 402 | "Out of credits, ask the org admin to top up" |
| 403 with moderation metadata, or a provider `content_policy` code | "Blocked by {provider} moderation: {reasons}. Flagged: '…'. Not charged." Suggests rewording, the `moderation` passthrough if the model allows it, or a different model |
| 403 other (guardrail) | Pass OpenRouter's message through |
| 200 with no image | Refusal error, including the model's text reply |
| 400 | Pass OpenRouter's message through |
| 429 | Up to 2 retries honouring `Retry-After` |
| 5xx | 1 retry, then "failed, not charged" |
| Timeout | `TIMEOUT_S`; MCP progress notifications every 10 s while waiting |
| Sequential variations, some fail | Keep the successes, list the failures |
| Local validation (missing file, format, relative path, too many references, folder not writable) | Fails before any network call |

## 8. Skills and distribution

### 8.1 Repo layout
```
openrouter-image-mcp/
├─ pyproject.toml            # console script: openrouter-image-mcp
├─ src/openrouter_image_mcp/{server,auth,keystore,client,catalog,imaging,outputs,config,cli}.py
├─ tests/  (unit, mcp-level, fixtures/ with real catalog JSON captured 2026-10-03, live/ opt-in)
├─ skills/
│  ├─ openrouter-image/SKILL.md
│  └─ architectural-render-polish/{SKILL.md, prompt-template.md}
├─ plugin/{.claude-plugin/plugin.json, .mcp.json, skills/ (copied from /skills by a sync script)}
├─ .claude-plugin/marketplace.json
├─ .github/workflows/ci.yml
├─ reference/ai_polish.py    # prototype, not packaged
├─ docs/superpowers/{specs,plans}/
└─ README.md
```

### 8.2 Skills (plain `SKILL.md` with frontmatter)
- **`openrouter-image`** covers:
  - discover models before choosing one;
  - iterate cheaply, then make the final at full quality;
  - state the likely cost before a large `n` or max-quality job;
  - use absolute paths and `fit="preserve"` for edits;
  - masks;
  - handling moderation refusals;
  - **get the user's OK before sending client images to a third-party provider**;
  - dated rules of thumb for which model to use for what.
- **`architectural-render-polish`:**
  1. Inventory the render: camera, architecture, furniture, people, palette, light.
  2. Fill in the "keep exactly / improve only realism" template, derived from `reference/ai_polish.py`.
  3. Run a cheap variation pass, then the final with `fit="preserve"`.
  4. Check the output against the input for drift (moved objects, changed people, altered patterns) and rerun with a tighter prompt or a protective mask if needed.
  - It also covers masks for signage and people, and the confidentiality checkpoint.

### 8.3 Installation per client
Prerequisite: `uv` (`winget install astral-sh.uv`).

- **Claude Code:** `/plugin marketplace add skelly-77/openrouter-image-mcp`, then `/plugin install openrouter-image`. This installs the server config and both skills.
- **Claude Desktop:** `claude_desktop_config.json` entry with:
  - the absolute `uvx.exe` path;
  - args `["--from","git+https://github.com/skelly-77/openrouter-image-mcp@v0.1.0","openrouter-image-mcp"]`;
  - env `UV_PYTHON_INSTALL_DIR`, `UV_CACHE_DIR`, `UV_TOOL_DIR` pointing at `%USERPROFILE%\.uv\…` (written out literally, because the config doesn't expand variables).

  Skills are uploaded as zips under Settings → Capabilities. The README covers backing up the config first and the Settings → Developer → Edit Config route.
- **Copilot Code:** a standard stdio entry. The config location and the skills folder are **open items**, to be confirmed once the app is available.
- **`print-config --client desktop|code|copilot`** prints a snippet filled in with this machine's paths. It never writes files.
- **Versioning:** semver git tags. Configs pin a tag.
- **Hosting:** **public GitHub repo** (decided). Possible later move to PyPI.

### 8.4 Future work (README only)
A hosted remote MCP (streamable HTTP plus OAuth) would remove the need for local `uv`, but it means running a service that holds user keys.

## 9. Testing

- **Unit tests (default, no network):**
  - `imaging`: ratio choice, exact 1920×828 crop-back, pad-then-crop round trip on a grid image, mask byte-identity, EXIF handling, metadata stripping, downscaling, alpha, previews.
  - `outputs`: naming, collisions, temp-then-rename writes, sidecar schema.
  - `catalog`: normalization against **real captured fixtures**, cache expiry.
  - `auth`: PKCE against the RFC 7636 vector, URL parameters, the listener (real localhost request, `state` mismatch, timeout), exchange.
  - `keystore`: in-memory backend, insecure backend refused.
  - `client` (via `respx`): request shapes, chat fallback parsing, every error mapping, retries, cost lookup, redaction.
- **MCP-level tests:** an in-process FastMCP client calls every tool against mocked HTTP, checking schemas, error results, image content, progress notifications and partial success.
- **Live tests** (`-m live`, opt-in, need a signed-in key): list models, account status, one cheap text-to-image, one edit of a **synthetic** 1920×828 image with the exact-size check.
- **CI:** GitHub Actions running ruff and the unit tests on Windows, macOS and Ubuntu with Python 3.12.
- **Manual acceptance on this machine (after org setup):**
  1. Terminal `login` via `uvx` from the tag; `cmdkey /list` shows the entry.
  2. Desktop (MSIX) reads the key saved from the terminal, and the reverse.
  3. Claude Code plugin install: skills listed, tools work.
  4. End-to-end sample render polish (**only after explicit user OK to upload**): exactly 1920×828, sidecar and cost present, visual check.
  5. Delete the key in the dashboard → clean 401 → re-login works.
  6. Copilot Code: deferred.

## 10. Open items
1. Copilot Code: MCP config location and format, skills folder, whether its sandbox allows opening a browser and reaching the credential store (CLI `login` is the fallback).
2. What happens to a departing org member's keys (check during org setup).
3. ~~GitHub owner~~ Resolved: `github.com/skelly-77/openrouter-image-mcp` (public).
4. Org workspace UUID (produced by the org setup task).
