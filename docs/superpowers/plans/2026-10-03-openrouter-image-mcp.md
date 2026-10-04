# openrouter-image-mcp Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local stdio MCP server, installed with `uvx` from a public GitHub repo, that gives Claude and other MCP clients image generation and editing through any OpenRouter image model. Users sign in per person with OAuth PKCE, and the server ships with companion skills and a Claude Code plugin.

**Architecture:**
- Small single-purpose modules: `keystore`, `client`, `catalog`, `imaging`, `outputs`, `auth`, and `service`.
- `service` orchestrates the image pipeline. A thin FastMCP `server` and a `cli` sit on top of it.
- `imaging` and `outputs` are pure (Pillow and stdlib only). All network access goes through `client`, which tests mock with `respx`.

**Tech Stack:** Python 3.12, `mcp` (FastMCP), `httpx`, `Pillow`, `keyring`, `hatchling`. Tests use `pytest`, `pytest-asyncio`, `respx`; lint with `ruff`. Packaging and running use `uv`/`uvx`.

**Spec:** `docs/superpowers/specs/2026-10-03-openrouter-image-mcp-design.md`. Read it before starting any task; section numbers below (§) refer to it.

## Global Constraints

- **Python and package:** Python `>=3.12`. Package `openrouter-image-mcp`, import name `openrouter_image_mcp`, console script `openrouter-image-mcp`, `__version__ = "0.1.0"`.
- **Endpoints:** API base `https://openrouter.ai/api/v1`; auth page `https://openrouter.ai/auth`.
- **Request headers:** every request sends `HTTP-Referer: https://github.com/skelly-77/openrouter-image-mcp` and `X-Title: openrouter-image-mcp`.
- **Key handling:**
  - The key exists only in `keyring` (service `openrouter-image-mcp`, username `default`).
  - There is **no** `OPENROUTER_API_KEY` support anywhere.
  - The key must never appear in logs, errors, sidecars or tool results.
- **Logging:** stdout is reserved for the MCP protocol. All logs go to stderr through the redaction filter (regex `sk-or-[A-Za-z0-9_\-]+` → `sk-or-***`).
- **Config environment variables and defaults:**

  | Variable | Default |
  |---|---|
  | `OPENROUTER_IMAGE_WORKSPACE_ID` | `DEFAULT_WORKSPACE_ID` constant; empty string → omit the param |
  | `OPENROUTER_IMAGE_OUTPUT_DIR` | `~/Pictures/OpenRouter Images` |
  | `OPENROUTER_IMAGE_MAX_INPUT_EDGE` | `2048` |
  | `OPENROUTER_IMAGE_TIMEOUT_S` | `600` |
  | `OPENROUTER_IMAGE_RATIO_TOLERANCE` | `0.03` |

  `DEFAULT_WORKSPACE_ID` is `""` until Task 14 fills it in.
- **Models:** no hard-coded model IDs in `src/`. Model IDs appear only in tests, fixtures, skills and docs.
- **Paths:** user-supplied paths must be absolute or start with `~`.
- **Commits:** end every message with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- **Blender folder:** never write to `C:\Users\user\OneDrive - Example Firm\01 Personal\Claude Blender`.

## Review Focus

1. **Paths containing spaces, commas and non-ASCII characters** (the user's real paths look like `…\Example Firm, INC\01 Personal\…`). Input loading, output naming and sidecars must all work. *Tests: Task 3 and Task 5.*
2. **Inputs larger than `MAX_INPUT_EDGE`** (e.g. a 7680×3300 render). The image sent to the model is downscaled, but `fit="preserve"` returns the **original** full size, and the mask composite uses the full-resolution original. *Tests: Task 3 and Task 9.*
3. **A typo'd or retired model ID.** Fails before any spend with "unknown model" and up to 3 close matches (`difflib.get_close_matches`). *Test: Task 7.*
4. **`auth_login` called again while a login is pending.** Returns the same pending URL and does not start a second listener. *Test: Task 8.*
5. **Catalog unreachable (offline or OpenRouter down).** Discovery and image tools return a clear "couldn't reach the OpenRouter catalog" tool error, not a traceback. If a cached catalog is less than 24 h old, the image tools use it. *Tests: Task 7 and Task 10.*

---

### Task 1: Project scaffold and config

**Files:**
- Create: `pyproject.toml`, `.gitignore`, `src/openrouter_image_mcp/__init__.py`, `src/openrouter_image_mcp/config.py`, `tests/conftest.py`, `tests/test_config.py`

**Interfaces:**
- Produces:
  - `config.DEFAULT_WORKSPACE_ID: str`
  - `@dataclass(frozen=True) class Settings: workspace_id: str; output_dir: Path; max_input_edge: int; timeout_s: float; ratio_tolerance: float`
  - `config.load_settings(env: Mapping[str, str] = os.environ) -> Settings`
  - constants `API_BASE`, `AUTH_URL`, `APP_URL`, `APP_TITLE`, `KEYRING_SERVICE = "openrouter-image-mcp"`, `KEYRING_USER = "default"`

- [ ] **Step 1: Write `pyproject.toml`**
  - hatchling build backend with a `src/` layout.
  - Dependencies: `mcp`, `httpx`, `pillow`, `keyring`, each with a lower bound equal to the version `uv lock` resolves today.
  - `[dependency-groups] dev`: `pytest`, `pytest-asyncio`, `respx`, `ruff`.
  - `[project.scripts] openrouter-image-mcp = "openrouter_image_mcp.cli:main"`.
  - Pytest settings: `asyncio_mode = "auto"`, `markers = ["live: hits real OpenRouter, needs signed-in key"]`, `addopts = "-m 'not live'"`.
  - `.gitignore`: `.venv/`, `__pycache__/`, `*.egg-info`, `dist/`, `.pytest_cache/`, `.ruff_cache/`.
- [ ] **Step 2: Write the failing tests** in `tests/test_config.py`:
  - `test_defaults`: `load_settings({})` gives `output_dir == Path.home()/"Pictures"/"OpenRouter Images"`, `max_input_edge == 2048`, `timeout_s == 600`, `ratio_tolerance == 0.03`, `workspace_id == DEFAULT_WORKSPACE_ID`.
  - `test_env_overrides`: every variable overrides its field, and `~` in `OUTPUT_DIR` expands.
  - `test_empty_workspace_env_means_personal`: `{"OPENROUTER_IMAGE_WORKSPACE_ID": ""}` → `workspace_id == ""`.
  - `test_bad_int_raises`: `MAX_INPUT_EDGE="abc"` raises `ValueError` with the variable name in the message.
- [ ] **Step 3: Run** `uv run pytest tests/test_config.py -v`. Expected: FAIL (module missing).
- [ ] **Step 4: Implement `config.py`** and `__init__.py` (with `__version__`).
- [ ] **Step 5: Run** `uv run pytest -v && uv run ruff check`. Expected: all pass, no lint errors.
- [ ] **Step 6: Commit** `feat: project scaffold and settings`.

### Task 2: Keystore and log redaction

**Files:**
- Create: `src/openrouter_image_mcp/keystore.py`, `src/openrouter_image_mcp/logs.py`, `tests/test_keystore.py`, `tests/test_logs.py`
- Modify: `tests/conftest.py` (add a `memory_keyring` fixture: an in-memory `keyring.backend.KeyringBackend` subclass with `priority = 1`, installed with `keyring.set_keyring` and restored afterwards)

**Interfaces:**
- Produces:
  - `keystore.get_key() -> str | None`
  - `keystore.set_key(key: str) -> None`
  - `keystore.delete_key() -> None` (no error if absent)
  - `class InsecureKeyringError(RuntimeError)`
  - `logs.redact(text: str) -> str`
  - `logs.configure_logging(level=logging.INFO) -> None` (a stderr handler with a `RedactingFilter` that redacts `record.msg` and `args`)

- [ ] **Step 1: Write the failing tests:**
  - `test_roundtrip(memory_keyring)`
  - `test_delete_absent_ok`
  - `test_refuses_insecure_backend`: parametrized over `keyring.backends.fail.Keyring()`, `keyring.backends.null.Keyring()`, and a dummy class named `PlaintextKeyring`. `set_key` and `get_key` raise `InsecureKeyringError`, and the message says no plaintext fallback exists.
  - `test_redact`: `redact("Bearer sk-or-v1-abc_DEF-123 x") == "Bearer sk-or-*** x"`.
  - `test_log_filter_redacts_args`: log `"key=%s"` with a key argument and capture stderr; the key is not present.
- [ ] **Step 2: Run** `uv run pytest tests/test_keystore.py tests/test_logs.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement both modules.**
  - Insecure check: the backend class's module is `keyring.backends.fail` or `keyring.backends.null`, **or** the class name contains `Plaintext`.
  - Unwrap `keyring.backends.chainer.ChainerBackend` and check each of its backends.
- [ ] **Step 4: Run the tests.** Expected: PASS.
- [ ] **Step 5: Commit** `feat: keystore with insecure-backend refusal and log redaction`.

### Task 3: Imaging — input preparation and previews

**Files:**
- Create: `src/openrouter_image_mcp/imaging.py`, `tests/test_imaging_inputs.py`, `tests/helpers.py` (synthetic image makers: `make_grid(w, h) -> Image`, `save(img, path, fmt, exif_orientation=None)`)

**Interfaces:**
- Produces:
  - `class InputError(ValueError)`
  - `@dataclass class PreparedImage: path: Path; sha256: str; original: Image.Image; original_size: tuple[int,int]; encoded: bytes; mime: str; sent_size: tuple[int,int]`
    - `original` is the full-resolution, EXIF-rotated, mode-converted image; `sha256` is the hash of the file bytes.
    - The `data_url` property returns `f"data:{mime};base64,…"`.
  - `resolve_user_path(p: str) -> Path`: expands `~`, raises `InputError` if the path is relative or missing.
  - `prepare_input(path: str, max_edge: int) -> PreparedImage`
  - `make_preview(img: Image.Image, max_edge: int = 1024, quality: int = 80) -> bytes` (JPEG)

- [ ] **Step 1: Write the failing tests:**
  - `test_relative_path_rejected`
  - `test_missing_file_rejected`
  - `test_unsupported_format_rejected` (a `.gif` file)
  - `test_exif_rotation_applied`: 200×100 with orientation 6 → `original_size == (100, 200)`.
  - `test_jpeg_reencoded_without_exif`: the `encoded` bytes contain no `Exif`/GPS block (assert `Image.open(BytesIO(encoded)).getexif()` is empty); `mime == "image/jpeg"`.
  - `test_png_and_alpha_stay_png`: an RGBA source → `mime == "image/png"`, mode `RGBA`.
  - `test_16bit_and_cmyk_converted`: becomes RGB, 8-bit.
  - `test_downscale_only_sent_copy`: 7680×3300 with `max_edge=2048` → `sent_size == (2048, 880)`, `original_size == (7680, 3300)`. (Review Focus 2)
  - `test_1920x828_not_downscaled`: `sent_size == (1920, 828)`.
  - `test_path_with_spaces_commas_unicode(tmp_path)`: directory `tmp_path/"Example Firm, INC"/"01 Personal"/"Café renders"` loads fine. (Review Focus 1)
  - `test_preview_bounds`: a 1920×828 input gives a JPEG preview with `max(size) == 1024`.
- [ ] **Step 2: Run** `uv run pytest tests/test_imaging_inputs.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement.**
  - Accepted formats: JPEG, PNG, WEBP, TIFF, BMP (Pillow `format`).
  - Apply `ImageOps.exif_transpose`.
  - Downscale with LANCZOS.
  - Encode PNG if the image has alpha or the source format is PNG; otherwise JPEG at quality 95. Never pass `exif=`.
- [ ] **Step 4: Run the tests.** Expected: PASS.
- [ ] **Step 5: Commit** `feat: input preparation and previews`.

### Task 4: Imaging — aspect fit, padding, masks

**Files:**
- Modify: `src/openrouter_image_mcp/imaging.py`
- Create: `tests/test_imaging_fit.py`

**Interfaces:**
- Consumes: `PreparedImage` (Task 3).
- Produces:
  - `RESOLUTION_TIERS = {"512":512,"768":768,"1K":1024,"1.5K":1536,"2K":2048,"4K":4096}`
  - `@dataclass class FitPlan: strategy: Literal["crop_back","pad","none_supported","model"]; aspect_ratio: str | None; resolution: str | None; target_size: tuple[int,int]; content_box: tuple[float,float,float,float] | None` (fractions of the padded frame; only set for `"pad"`)
  - `plan_fit(target_size, aspect_ratios: list[str] | None, resolutions: list[str] | None, tolerance: float) -> FitPlan`
  - `pad_to_ratio(img: Image.Image, ratio: str) -> tuple[Image.Image, tuple[float,float,float,float]]`
  - `@dataclass class FitReport: strategy: str; requested_ratio: str | None; raw_size: tuple[int,int]; final_size: tuple[int,int]; crop_box: tuple[int,int,int,int] | None; padded: bool; upscaled: bool`
  - `apply_fit(output: Image.Image, plan: FitPlan) -> tuple[Image.Image, FitReport]`
  - `composite_mask(output: Image.Image, original: Image.Image, mask_path: str, feather_px: int | None) -> tuple[Image.Image, int]` (returns the feather actually used)

- [ ] **Step 1: Write the failing tests:**
  - `test_plan_picks_21_9_for_sample_render`: `plan_fit((1920,828), ["1:1","3:2","2:3","4:3","3:4","16:9","9:16","21:9","auto"], None, 0.03)` → `FitPlan("crop_back","21:9",None,(1920,828),None)`.
  - `test_plan_pads_when_outside_tolerance`: `(3000,1000)` with `["1:1","16:9"]` → strategy `"pad"`, ratio `"16:9"`, `content_box` is not None.
  - `test_plan_no_ratio_support`: `aspect_ratios=None` → `"none_supported"`, `aspect_ratio is None`.
  - `test_plan_resolution_smallest_covering`: `(1920,828)` with `["1K","2K","4K"]` → `"2K"`; `(5000,2000)` with `["1K","2K"]` → `"2K"` (the largest available).
  - `test_auto_ignored_in_choice`: `["auto"]` only → `"none_supported"`.
  - `test_crop_back_exact_size`: a simulated 2016×864 output → final `(1920,828)`, `report.crop_box == (6,0,1926,828)`, `upscaled is False`.
  - `test_crop_back_upscales_small_output`: a 1344×576 output → final `(1920,828)`, `upscaled is True`.
  - `test_pad_roundtrip_grid`: pad a 3000×1000 grid to 16:9, "generate" by resizing the padded frame to 1792×1008, `apply_fit` → `(3000,1000)`, and the mean absolute pixel difference from the original grid is `< 8`.
  - `test_pad_uses_mirrored_blur_not_flat`: pixels in the padded band are not all one colour (stddev > 1).
  - `test_mask_black_region_identical`: the mask is the left half black, right half white, with `feather_px=4`. Pixels with `x < W/2 - 12` equal the `original` exactly (`ImageChops.difference(...).getbbox() is None` on that crop). Pixels with `x > W/2 + 12` equal the `output`.
  - `test_mask_default_feather`: a 1920×828 target → returned feather `== 4` (`max(1, round(0.005*828))`).
  - `test_mask_resized_to_target`: a 100×43 mask works on a 1920×828 image.
- [ ] **Step 2: Run** `uv run pytest tests/test_imaging_fit.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement.**
  - **Ratio choice:** argmin over r of `abs(log(r/(W/H)))`, excluding `"auto"`. Use `crop_back` when the relative error `abs(a-r)/r <= tolerance`, otherwise `pad`.
  - **`crop_back`:** scale factor `s = max(W/ow, H/oh)`, resize with LANCZOS to `(round(ow*s), round(oh*s))`, centre-crop to W×H. `crop_box` is in scaled coordinates.
  - **`pad`:** the padded frame keeps the original's long side. Fill the bands by mirroring the edge strip (`ImageOps.mirror`/`flip`) and blurring it with `GaussianBlur(radius=max(8, band/4))`. `apply_fit` crops `content_box × output size`, then resizes to W×H.
  - **`none_supported`:** same path as `crop_back`. **`model`:** return the output unchanged.
  - **Mask:** convert to `L`, resize to W×H, apply `GaussianBlur(feather)`, then `Image.composite(output, original, mask)`. Convert the modes of `output` and `original` to match first.
- [ ] **Step 4: Run the tests.** Expected: PASS.
- [ ] **Step 5: Commit** `feat: aspect-ratio fit planning, padding and mask compositing`.

### Task 5: Outputs — naming, atomic save, sidecars

**Files:**
- Create: `src/openrouter_image_mcp/outputs.py`, `tests/test_outputs.py`

**Interfaces:**
- Produces:
  - `model_short(model_id: str) -> str` (the part after the last `/`)
  - `prompt_slug(prompt: str) -> str` (first 6 words, lowercase, runs of non-`[a-z0-9]` → `-`, stripped, max 60 chars, `"image"` if empty)
  - `choose_dir(preferred: Path | None, fallback: Path) -> tuple[Path, str | None]` (returns a note if it fell back because the folder wasn't writable; checks by creating and deleting a temp file)
  - `output_path(directory: Path, stem: str, model_id: str, index: int, ext: str, now: datetime) -> Path` (`{stem}__{model_short}_{%Y%m%d-%H%M%S}_{index}{ext}`, adds `-2`, `-3`… before the extension if the name exists)
  - `write_bytes_atomic(path: Path, data: bytes) -> None` (writes `path.with_suffix(path.suffix + ".tmp")`, then `os.replace`)
  - `write_sidecar(image_path: Path, meta: dict) -> Path` (`image_path.with_suffix(".json")`, UTF-8, `indent=2`, `ensure_ascii=False`, adds `schema_version: 1` and `server_version`)
  - `encode_image(img: Image.Image, output_format: str | None) -> tuple[bytes, str]` (returns bytes and extension: PNG by default; `"jpeg"`/`"webp"` at quality 95)

- [ ] **Step 1: Write the failing tests:**
  - `test_name_format`: `output_path(d, "Sample_Render_v5", "openai/gpt-image-2.5-sunburst", 1, ".png", datetime(2026,10,3,22,15,0))`, name `== "Sample_Render_v5__gpt-image-2.5-sunburst_20261003-221500_1.png"`.
  - `test_collision_suffix`: an existing file gives `…_1-2.png`, then `…_1-3.png`.
  - `test_prompt_slug`: `"A Red Panda, astronaut! floating in deep space today"` → `"a-red-panda-astronaut-floating-in"`.
  - `test_atomic_write_leaves_no_tmp`
  - `test_sidecar_contents`: includes `schema_version == 1`, `server_version == "0.1.0"`, preserves non-ASCII text in `prompt`, contains no key matching `sk-or-`.
  - `test_choose_dir_fallback_when_unwritable`: monkeypatch the probe to raise `PermissionError` → returns the fallback plus a note.
  - `test_spaces_commas_unicode_dir(tmp_path)`: same directory shape as in Task 3. (Review Focus 1)
- [ ] **Step 2: Run** `uv run pytest tests/test_outputs.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run the tests.** Expected: PASS.
- [ ] **Step 5: Commit** `feat: output naming, atomic writes and sidecars`.

### Task 6: OpenRouter HTTP client and error mapping

**Files:**
- Create: `src/openrouter_image_mcp/errors.py`, `src/openrouter_image_mcp/client.py`, `tests/test_client.py`

**Interfaces:**
- Consumes: `keystore.get_key/delete_key`, `config.API_BASE`, `APP_URL`, `APP_TITLE`.
- Produces:
  - `errors.OpenRouterError(Exception)` with `.message: str`. Subclasses:
    - `AuthRequiredError` (401 or no key)
    - `InsufficientCreditsError` (402)
    - `ModerationError(reasons: list[str], flagged_input: str | None, provider: str | None)`
    - `ForbiddenError` (other 403)
    - `BadRequestError` (400)
    - `RateLimitError` (429 after retries)
    - `ProviderError` (5xx after retry)
    - `NoImageError(text: str)`
    - `CatalogUnavailableError`
  - `@dataclass class GeneratedImage: data: bytes; media_type: str | None`
  - `@dataclass class GenerationResult: images: list[GeneratedImage]; cost_usd: float | None; usage: dict; generation_id: str | None; provider: str | None; raw_text: str | None`
  - `class OpenRouterClient(timeout_s: float, transport: httpx.AsyncBaseTransport | None = None)`, all methods async:
    - `images(payload: dict) -> GenerationResult`: `POST /images`; decodes `data[].b64_json`.
    - `chat_image(model, prompt, data_urls: list[str], aspect_ratio: str | None) -> GenerationResult`: `POST /chat/completions` with `modalities=["image","text"]`, user content = the text plus the `image_url` parts, `image_config={"aspect_ratio":…}` only when set; decodes `choices[0].message.images[].image_url.url`.
    - `key_info() -> dict` (`GET /key` → `data`)
    - `generation(gen_id: str) -> dict` (`GET /generation?id=`)
    - `image_models() -> list[dict]` (`GET /images/models`, **unauthenticated**)
    - `image_model_endpoints(model_id: str) -> list[dict]`
    - `image_models_meta() -> list[dict]` (`GET /models?output_modalities=image`, unauthenticated)
    - `exchange_code(code: str, verifier: str) -> str` (`POST /auth/keys` body `{"code","code_verifier","code_challenge_method":"S256"}`, unauthenticated, returns `key`)

- [ ] **Step 1: Write the failing tests** (`respx`, plus the `memory_keyring` fixture with a stored key):
  - `test_images_payload_and_headers`: the request carries `Authorization: Bearer <key>` and the `HTTP-Referer`/`X-Title` headers, and the body is exactly the given payload. The response `{"data":[{"b64_json":<png b64>,"media_type":"image/png"}],"usage":{"cost":0.21}}` gives one image and `cost_usd == 0.21`.
  - `test_chat_image_parsing`: a `message.images[0].image_url.url` data URL decodes; `message.content` goes into `raw_text`.
  - `test_chat_no_image_raises_noimage`: `images` absent, content `"I can't help with that"` → `NoImageError` whose text includes it.
  - `test_401_deletes_key_and_raises`: afterwards `keystore.get_key() is None`; the message mentions `auth_login`.
  - `test_no_key_raises_auth_required_without_request`
  - `test_402_credits`: the message mentions the org admin.
  - `test_403_moderation_metadata`: `{"error":{"code":403,"message":"flagged","metadata":{"reasons":["violence"],"flagged_input":"…","provider_name":"OpenAI","model_slug":"x"}}}` → `ModerationError` with those fields; the message contains `"Not charged"`.
  - `test_content_policy_code_is_moderation`: a 400 with `"content_policy"` in `error.code` or `error.message` → `ModerationError`.
  - `test_429_retries_twice_honours_retry_after`: monkeypatch `asyncio.sleep` to record calls. Two 429s then a 200 succeed, with sleeps `== [1.0, 1.0]` for `Retry-After: 1`. Three 429s → `RateLimitError`.
  - `test_5xx_retries_once`: 502 then 200 succeeds; two 502s → `ProviderError` whose message contains `"not charged"`.
  - `test_error_text_never_contains_key`: a 400 whose body echoes the key → `str(exc)` doesn't contain it.
  - `test_exchange_code_body`
  - `test_catalog_network_error_maps`: `httpx.ConnectError` on `image_models()` → `CatalogUnavailableError`.
- [ ] **Step 2: Run** `uv run pytest tests/test_client.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement.**
  - One `httpx.AsyncClient` per instance, `base_url=API_BASE`, `timeout=timeout_s`.
  - A single `_request(method, path, *, auth: bool, json=None, params=None)` that does the retry and error mapping.
  - Moderation check comes before the generic 403 mapping.
  - All exception messages pass through `logs.redact`.
  - `provider` comes from the response's `provider` field when present.
- [ ] **Step 4: Run the tests.** Expected: PASS.
- [ ] **Step 5: Commit** `feat: OpenRouter client with typed errors and retries`.

### Task 7: Model catalog and parameter validation

**Files:**
- Create: `src/openrouter_image_mcp/catalog.py`, `tests/test_catalog.py`, `tests/fixtures/images_models.json`, `tests/fixtures/models_image.json`, `tests/fixtures/endpoints_gpt-image-2.5-sunburst.json`

**Interfaces:**
- Consumes: `OpenRouterClient.image_models/image_models_meta/image_model_endpoints`, `CatalogUnavailableError`.
- Produces:
  - `@dataclass class ModelCapabilities: id: str; name: str; description: str; created: int; route: Literal["images","chat"]; accepts_images: bool; max_input_images: int; aspect_ratios: list[str] | None; resolutions: list[str] | None; qualities: list[str] | None; backgrounds: list[str] | None; output_formats: list[str] | None; max_n: int; seed: bool; size: bool; is_moderated: bool | None; pricing: dict[str,str]`
  - `class Catalog(client, ttl_s: float = 600, stale_ok_s: float = 86400, clock=time.monotonic)`, with methods:
    - `async all() -> list[ModelCapabilities]`
    - `async get(model_id) -> ModelCapabilities` (raises `UnknownModelError(model_id, suggestions: list[str])`, defined in `errors.py` as a subclass of `OpenRouterError` so that `server` maps it to a tool error like the others)
    - `async endpoints(model_id) -> list[dict]`
  - `price_key(m: ModelCapabilities) -> float`
  - `validate_params(m: ModelCapabilities, *, n, aspect_ratio, resolution, quality, background, output_format, seed, size, input_count) -> list[str]` (returns notes, e.g. `"model max n is 1; will make 4 sequential calls"`; raises `BadRequestError` listing allowed values on invalid input)

- [ ] **Step 1: Capture the fixtures.**
  - Run `curl -s https://openrouter.ai/api/v1/images/models > tests/fixtures/images_models.json`.
  - Run the same for `/models?output_modalities=image` and for `/images/models/openai/gpt-image-2.5-sunburst/endpoints`.
  - Check each file parses as JSON.
- [ ] **Step 2: Write the failing tests** (respx serves the fixtures):
  - `test_sunburst_caps`: `aspect_ratios` contains `"21:9"`, `qualities[-1] == "max"`, `max_n == 10`, `max_input_images == 16`, `accepts_images`, `route == "images"`, `is_moderated is True`, `pricing["image_output"] == "0.00003"`.
  - `test_chat_only_models_routed_to_chat`: `openrouter/auto` has `route == "chat"`.
  - `test_missing_params_mean_unsupported`: a model with no `aspect_ratio` → `aspect_ratios is None`; no `n` → `max_n == 1`; no `seed` → `False`.
  - `test_unknown_model_suggestions`: `get("openai/gpt-image-2.5-sunbrust")` → `UnknownModelError` with `"openai/gpt-image-2.5-sunburst"` in `suggestions`. (Review Focus 3)
  - `test_cache_ttl`: two calls within the TTL make 1 request; after the TTL (fake clock), 2.
  - `test_stale_cache_used_when_offline`: fetch once, advance past the TTL, make the next fetch raise `ConnectError` → returns cached data. Past `stale_ok_s` → `CatalogUnavailableError`. (Review Focus 5)
  - `test_validate_bad_quality_lists_allowed`: `quality="ultra"` on sunburst → `BadRequestError` whose message contains `"auto, low, medium, high, xhigh, max"`.
  - `test_validate_n_over_max_returns_note`
  - `test_validate_seed_unsupported_raises`
  - `test_validate_too_many_inputs_raises`
  - `test_chat_route_rejects_non_aspect_params`: `quality` on a chat-route model raises.
  - `test_price_sort`: `price_key` uses `image_output`, else `image`, else `completion`, else `inf`.
- [ ] **Step 3: Run** `uv run pytest tests/test_catalog.py -v`. Expected: FAIL.
- [ ] **Step 4: Implement.**
  - Merge `/images/models` (capabilities) with `/models?output_modalities=image` (name, pricing, `top_provider.is_moderated`) by `id`.
  - IDs only in the meta list → `route="chat"`, with `accepts_images` taken from `input_modalities`. Chat-route models support only `aspect_ratio`, and their `aspect_ratios` is `None` (meaning unknown, so the value passes through unvalidated).
  - Suggestions: `difflib.get_close_matches(id, ids, n=3, cutoff=0.6)`.
- [ ] **Step 5: Run the tests.** Expected: PASS.
- [ ] **Step 6: Commit** `feat: live image model catalog with validation and offline cache`.

### Task 8: OAuth PKCE login manager

**Files:**
- Create: `src/openrouter_image_mcp/auth.py`, `tests/test_auth.py`

**Interfaces:**
- Consumes: `OpenRouterClient.exchange_code/key_info`, `keystore.set_key/get_key`, `Settings.workspace_id`.
- Produces:
  - `make_pkce() -> tuple[str, str]` (verifier, challenge)
  - `challenge_for(verifier: str) -> str`
  - `build_auth_url(port: int, challenge: str, state: str, workspace_id: str, label: str) -> str`
  - `class LoginState(StrEnum): IDLE, PENDING, SIGNED_IN, FAILED, EXPIRED`
  - `class LoginManager(client, settings, open_browser=webbrowser.open, timeout_s=300)`:
    - `async start(switch_account: bool = False) -> dict` returns `{"state", "url", "message"}`
    - `status() -> dict` returns `{"state", "message", "url"}`
    - `async wait() -> LoginState` (used by the CLI)

- [ ] **Step 1: Write the failing tests:**
  - `test_rfc7636_vector`: `challenge_for("dBjftJeZ4CVP-mJ92K92zW8zdD3nULvOtEu4Iz5VgSg") == "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"`.
  - `test_make_pkce_lengths`: the verifier is 43–128 characters from `[A-Za-z0-9-._~]`.
  - `test_auth_url_params`: parse the query → `callback_url == "http://localhost:5123/callback"`, `code_challenge_method == "S256"`, `state`, `key_label == "openrouter-image-mcp (HOST)"`, and `required_workspace_id` is present only when the workspace is non-empty.
  - `test_full_flow_success`:
    - `open_browser` is a stub that captures the URL; then use real `httpx` to `GET http://127.0.0.1:{port}/callback?code=abc&state={state}`.
    - The response is HTML containing `"Signed in"`.
    - Mock `exchange_code` → `"sk-or-test"` and `key_info` → `{}`.
    - `await` until state is `SIGNED_IN`; `keystore.get_key() == "sk-or-test"`.
  - `test_state_mismatch_rejected`: a wrong `state` returns 400; state stays `PENDING`.
  - `test_timeout_expires`: `timeout_s=0.2` → `EXPIRED`; the message mentions needing an org invite.
  - `test_already_signed_in_noop`: returns a message containing "already signed in"; `open_browser` is not called.
  - `test_switch_keeps_old_key_until_success`: the old key stays stored while pending and is replaced after the callback.
  - `test_second_start_while_pending_returns_same_url`: `open_browser` is called once and only one port is bound. (Review Focus 4)
  - `test_exchange_failure_sets_failed`
- [ ] **Step 2: Run** `uv run pytest tests/test_auth.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement.**
  - The listener is a stdlib `http.server.HTTPServer` bound to `("127.0.0.1", 0)` and run by `serve_forever` in a daemon thread. It handles one valid callback, then shuts itself down.
  - The handler hands `code` to the asyncio loop with `loop.call_soon_threadsafe`.
  - A watchdog `asyncio` task expires the login after `timeout_s`.
  - Callback page text: `"Signed in to OpenRouter — you can close this tab and return to Claude."`
  - `HOST` is `socket.gethostname()`.
- [ ] **Step 4: Run the tests.** Expected: PASS.
- [ ] **Step 5: Commit** `feat: OAuth PKCE login manager with localhost callback`.

### Task 9: Image service (shared generate/edit pipeline)

**Files:**
- Create: `src/openrouter_image_mcp/service.py`, `tests/test_service.py`

**Interfaces:**
- Consumes: Tasks 3–7 (`prepare_input`, `plan_fit`, `pad_to_ratio`, `apply_fit`, `composite_mask`, `make_preview`, outputs functions, `OpenRouterClient`, `Catalog`, `validate_params`).
- Produces:
  - `ProgressFn = Callable[[float, str], Awaitable[None]]`
  - `@dataclass class SavedImage: path: Path; sidecar: Path; preview_jpeg: bytes | None; cost_usd: float | None; note: str | None`
  - `@dataclass class ServiceResult: images: list[SavedImage]; failures: list[str]; notes: list[str]; model: str; provider: str | None; call_cost_usd: float | None; usage_line: str; elapsed_s: float`
  - `class ImageService(client, catalog, settings, clock=datetime.now)`:
    - `async generate(prompt, model, *, n=1, aspect_ratio=None, resolution=None, size=None, quality=None, seed=None, background=None, output_format=None, output_dir=None, filename_prefix=None, provider_options=None, progress: ProgressFn | None = None) -> ServiceResult`
    - `async edit(prompt, model, images: list[str], *, mask_path=None, mask_feather_px=None, fit="preserve", …same keyword arguments…) -> ServiceResult`

- [ ] **Step 1: Write the failing tests** (respx with fixtures; `/images` returns a synthetic PNG of the requested-ratio size):
  - `test_edit_sample_render_shape`:
    - The input is a synthetic 1920×828 JPEG in `tmp_path`; `/images` returns 2016×864.
    - The request body has `aspect_ratio == "21:9"` and 1 `input_references` entry with a `data:image/jpeg;base64,` URL.
    - The saved file is exactly 1920×828, next to the input, named by the Task 5 convention.
    - The sidecar `fit.strategy == "crop_back"`, `fit.crop_box == [6,0,1926,828]`, `cost_usd == 0.21`.
  - `test_large_input_preserve_returns_original_size`: a 7680×3300 input gives a sent image of 2048 px and a saved 7680×3300 file with `fit.upscaled is True`. (Review Focus 2)
  - `test_generate_saves_to_output_dir_with_slug`
  - `test_validation_before_spend`: `quality="ultra"` raises and respx records 0 `/images` calls.
  - `test_variations_loop`: on a model with `max_n=1` and `n=3`, 3 calls are made and the notes include the sequential-calls note. If the 2nd call fails with `ProviderError`, 2 images are saved and `failures` has 1 entry.
  - `test_mask_applied_after_fit`
  - `test_fit_model_untouched`: provider bytes are saved unchanged (same sha256).
  - `test_chat_route_used_for_chat_models`
  - `test_cost_fallback_via_generation`: no `usage.cost` but an `id` present → calls `/generation`, cost filled in.
  - `test_usage_line`: `key_info` returns `{"usage_daily":1.84,"usage_monthly":12.4}` → `usage_line == "This call: $0.2100 · Key usage today: $1.84 / month: $12.40"`; `key_info` is cached for 60 s.
  - `test_progress_heartbeat`: a slow mocked response (0.35 s) with the interval patched to 0.1 s → progress called ≥ 3 times.
  - `test_svg_output_saved_raw_no_preview`
- [ ] **Step 2: Run** `uv run pytest tests/test_service.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement.**
  - **Order:** catalog `get` → `validate_params` → prepare inputs → `plan_fit` (aspect ratios and resolutions from the capabilities; pad the primary if the plan says so) → build the payload (only non-None keys; `provider: {"options": provider_options}` when set) → call with the heartbeat (interval constant `HEARTBEAT_S = 10`) → for each image: decode, `apply_fit` against `PreparedImage.original`, optional `composite_mask` against the full-resolution original, `encode_image`, save, sidecar (exactly the §7.2 fields) → `make_preview` for the first 4.
  - **Per-image cost:** `call_cost / len(images)`.
  - **Fallback directory:** edits fall back to `settings.output_dir` through `choose_dir`.
- [ ] **Step 4: Run the tests.** Expected: PASS.
- [ ] **Step 5: Commit** `feat: image service pipeline for generate and edit`.

### Task 10: MCP server tools

**Files:**
- Create: `src/openrouter_image_mcp/server.py`, `tests/test_server.py`

**Interfaces:**
- Consumes: `ImageService`, `Catalog`, `LoginManager`, `keystore`, `OpenRouterClient.key_info`, error classes.
- Produces: `build_server(settings: Settings, client: OpenRouterClient | None = None) -> FastMCP` registering the seven tools in spec §4, with the exact names and parameters given there; and `run() -> None` (stdio).

- [ ] **Step 1: Write the failing tests** (an in-process client: `mcp.shared.memory.create_connected_server_and_client_session(server._mcp_server)`, or whatever the installed SDK's in-memory helper is):
  - `test_tool_names`: exactly `{"account_status","auth_login","auth_logout","list_image_models","get_image_model","generate_image","edit_image"}`.
  - `test_edit_image_returns_text_and_images`: the result has 1 `TextContent` containing the saved path and `"This call: $"`, plus 1 `ImageContent` with `mimeType == "image/jpeg"`.
  - `test_errors_are_tool_errors`: `ModerationError` → `isError is True` with the text "Blocked by OpenAI moderation"; `AuthRequiredError` → text contains `auth_login`.
  - `test_list_image_models_table`: `accepts_images=True, sort="price"` → markdown table rows sorted by `price_key`, with columns `id | name | inputs | aspect ratios | resolutions | quality | max n | seed | moderated | price`.
  - `test_catalog_unavailable_is_clean_error`: `list_image_models` with the network down and no cache → `isError` with the text "couldn't reach the OpenRouter catalog". (Review Focus 5)
  - `test_account_status_signed_out`: the text says not signed in and suggests `auth_login`.
  - `test_auth_logout_message_links_dashboard`: contains `https://openrouter.ai/settings/keys`.
  - `test_no_key_in_any_result`: across all tools in a session with the key `sk-or-secret`, no output contains `"sk-or-secret"`.
- [ ] **Step 2: Run** `uv run pytest tests/test_server.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement.**
  - Each tool has a docstring written for an LLM caller (when to use it and what each parameter means). Include the mask-seam caveat in `edit_image` and "call `list_image_models` first" in both image tools.
  - Raise `mcp.server.fastmcp.exceptions.ToolError(exc.message)` for every `OpenRouterError`/`InputError`.
  - Progress: `ctx.report_progress`.
  - Text summary format: one line per saved image (`path` + `sidecar`), then the notes, the failures, the model/provider/seed/elapsed line, and the usage line.
- [ ] **Step 4: Run** `uv run pytest -v`. Expected: the whole suite passes.
- [ ] **Step 5: Commit** `feat: MCP server with seven tools`.

### Task 11: CLI (`serve`, `login`, `logout`, `status`, `print-config`)

**Files:**
- Create: `src/openrouter_image_mcp/cli.py`, `tests/test_cli.py`

**Interfaces:**
- Consumes: `server.run`, `LoginManager`, `keystore`, `OpenRouterClient.key_info`.
- Produces: `main(argv: list[str] | None = None) -> int`; `find_uvx() -> str | None`; `render_config(client: Literal["desktop","code","copilot"], uvx: str, home: Path, ref: str = "v0.1.0") -> str`

- [ ] **Step 1: Write the failing tests:**
  - `test_default_is_serve`: monkeypatch `server.run`; `main([])` calls it.
  - `test_desktop_config_shape`: `json.loads(render_config("desktop", r"C:\u\uvx.exe", Path(r"C:\Users\user")))["mcpServers"]["openrouter-image"]` has `command == r"C:\u\uvx.exe"`, `args == ["--from","git+https://github.com/skelly-77/openrouter-image-mcp@v0.1.0","openrouter-image-mcp"]`, and `env` with `UV_PYTHON_INSTALL_DIR == r"C:\Users\user\.uv\python"`, `UV_CACHE_DIR`, `UV_TOOL_DIR` likewise.
  - `test_code_config_is_mcp_json`: top-level `mcpServers`, `command == "uvx"`, no `env`.
  - `test_copilot_config_marked_unverified`: the output starts with a comment line saying the format is unverified for Copilot Code, followed by the standard stdio JSON.
  - `test_find_uvx_falls_back_to_winget_glob`: `shutil.which` returns None and a fake `%LOCALAPPDATA%\Microsoft\WinGet\Packages\astral-sh.uv_*\uvx.exe` exists → returns it.
  - `test_status_signed_out_exit_code_1`
  - `test_logout_deletes_key`
- [ ] **Step 2: Run** `uv run pytest tests/test_cli.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement** with `argparse` subcommands. `login` runs `LoginManager.start()` and `wait()`, printing the URL and the final state. `print-config` defaults to the client `desktop`.
- [ ] **Step 4: Run** `uv run pytest -v`, then `uv run openrouter-image-mcp print-config --client desktop`. Expected: tests pass; the printed JSON contains this machine's real `uvx.exe` path.
- [ ] **Step 5: Commit** `feat: CLI with login, status and print-config`.

### Task 12: Skills, plugin, marketplace, README, CI

**Files:**
- Create:
  - `skills/openrouter-image/SKILL.md`
  - `skills/architectural-render-polish/SKILL.md`
  - `skills/architectural-render-polish/prompt-template.md`
  - `plugin/.claude-plugin/plugin.json`
  - `plugin/.mcp.json`
  - `.claude-plugin/marketplace.json`
  - `scripts/sync_plugin_skills.py`
  - `tests/test_distribution.py`
  - `README.md`
  - `.github/workflows/ci.yml`
- Generated: `plugin/skills/**` (by the sync script)

**Interfaces:**
- Consumes: the tool names and parameters from Task 10; `render_config` output from Task 11 for the README snippets.

- [ ] **Step 1: Write the failing tests:**
  - `test_plugin_skills_in_sync`: the file tree and bytes under `plugin/skills` equal those under `skills/`.
  - `test_skill_frontmatter`: each `SKILL.md` starts with `---` frontmatter containing `name` (matching its folder) and a `description` under 1024 characters.
  - `test_plugin_mcp_json`: `plugin/.mcp.json` equals `render_config("code", …)` parsed.
  - `test_marketplace_points_to_plugin`: `plugins[0].source == "./plugin"`, `name == "openrouter-image"`.
  - `test_versions_match`: `plugin.json` version `== __version__`.
  - `test_skills_reference_real_tools`: every backticked `snake_case` tool name in the skills is one of the 7 tool names.
- [ ] **Step 2: Write the two skills using the superpowers:writing-skills skill.**
  - Content per spec §8.2.
  - `prompt-template.md` adapts the KEEP/IMPROVE structure of `reference/ai_polish.py`, with `{inventory}` placeholders for Claude to fill in after looking at the render.
  - Both skills must tell Claude to **ask the user before uploading client imagery**.
  - The model rules of thumb are headed "As of 2026-10".
- [ ] **Step 3: Write the plugin, marketplace and sync script** (`marketplace.json`: `name "skelly-77-tools"`, `owner {"name":"skelly-77"}`), then run `uv run python scripts/sync_plugin_skills.py`.
- [ ] **Step 4: Write `README.md`** covering:
  - what the server is and its 7 tools;
  - prerequisites (`winget install astral-sh.uv`);
  - install for Claude Code (plugin), Claude Desktop (snippet; back up the config first; use Settings → Developer → Edit Config if edits vanish) and Copilot Code (marked "to be confirmed");
  - first sign-in;
  - the org/billing and privacy notes from spec §5.5 verbatim in substance;
  - troubleshooting (401, MSIX `UV_*` variables, Credential Manager entry `openrouter-image-mcp`);
  - future remote MCP;
  - development (`uv run pytest`, `-m live`).
- [ ] **Step 5: Write `ci.yml`:** matrix `windows-latest`, `macos-latest`, `ubuntu-latest`; `astral-sh/setup-uv`; `uv run ruff check`; `uv run pytest`.
- [ ] **Step 6: Run** `uv run pytest -v && uv run ruff check`. Expected: all pass.
- [ ] **Step 7: Commit** `feat: companion skills, Claude Code plugin, README and CI`.

### Task 13: Opt-in live tests

**Files:**
- Create: `tests/live/test_live.py`

- [ ] **Step 1: Write tests marked `@pytest.mark.live`.** They are skipped with the reason "run `openrouter-image-mcp login` first" when `keystore.get_key()` is None.
  - `test_live_catalog`: ≥ 1 model with `route == "images"` and `accepts_images`.
  - `test_live_account`: `key_info()` returns `usage_daily`.
  - `test_live_generate_cheapest`:
    - Choose the cheapest images-route model by `price_key` that supports `quality`, falling back to the cheapest overall.
    - Use the prompt "a small red cube on a white table", `n=1`, plus `quality="low"` when supported.
    - Assert 1 file exists and `cost_usd is not None`.
  - `test_live_edit_synthetic_wide`: build a synthetic 1920×828 grid JPEG in `tmp_path`, edit it with the cheapest image-input model that supports `aspect_ratio`, and assert the output is exactly `(1920, 828)`.
- [ ] **Step 2: Run** `uv run pytest -v`. Expected: live tests deselected, suite green.
- [ ] **Step 3: Commit** `test: opt-in live tests`. Live tests run in Task 16 after login.

### Task 14: OpenRouter Organization and workspace setup (Claude in Chrome, user-confirmed)

**Files:**
- Modify: `src/openrouter_image_mcp/config.py` (`DEFAULT_WORKSPACE_ID`), `tests/test_config.py` (the `test_defaults` expectation), `README.md` (the departing-member answer)

This is not TDD. It's a guided browser procedure. **Confirm each action with the user in chat before clicking.** The user handles sign-in, payment and credit purchases themselves.

- [ ] **Step 1:** Load the Claude in Chrome tools and open `https://openrouter.ai/settings/organization` (or wherever the dashboard currently puts "Create organization"). Take a screenshot and describe what's on screen to the user.
- [ ] **Step 2:** With the user's OK, create the Organization (name chosen by the user, e.g. "Example Firm").
- [ ] **Step 3:** With the user's OK, create the workspace "Image Tools". Read its UUID from the URL or the settings page.
- [ ] **Step 4:** Show the user the guardrail options (budget, allowed models, data policy). Set only what they choose.
- [ ] **Step 5:** Read the org docs or settings and find out what happens to a removed member's keys. Record the answer in the README org section.
- [ ] **Step 6:** Invites: ask the user for the email list, confirm it, then send. (Optional; may happen later.)
- [ ] **Step 7:** Put the UUID into `DEFAULT_WORKSPACE_ID` and update `test_defaults`. Run `uv run pytest -v`. Expected: PASS.
- [ ] **Step 8: Commit** `chore: set org workspace default`.

### Task 15: Publish the public GitHub repo and tag v0.1.0 (user-confirmed)

- [ ] **Step 1:** Show the user what will become public. Run `git ls-files` and confirm it includes nothing from the Blender folder or any client imagery, and no keys (`git grep -n "sk-or-"` should match only test fixtures that use `sk-or-test`/`sk-or-secret`). **Get an explicit yes to publish.**
- [ ] **Step 2:** `"C:\Program Files\GitHub CLI\gh.exe" repo create skelly-77/openrouter-image-mcp --public --source . --push --description "Local MCP server for OpenRouter image generation and editing"`
- [ ] **Step 3:** Wait for CI with `gh run watch`. Expected: green on all 3 OSes. Fix failures with systematic-debugging before tagging.
- [ ] **Step 4:** `git tag v0.1.0 && git push origin v0.1.0`
- [ ] **Step 5:** Run `uvx --from git+https://github.com/skelly-77/openrouter-image-mcp@v0.1.0 openrouter-image-mcp print-config --client desktop` from a fresh shell. Expected: it prints the snippet, which proves the install line works.

### Task 16: Manual acceptance on this machine

These checks follow spec §9. Record the results in `docs/acceptance-2026-10.md` and commit that file.

- [ ] **Step 1: Terminal login.** Run `uvx --from git+https://github.com/skelly-77/openrouter-image-mcp@v0.1.0 openrouter-image-mcp login`. The user completes the browser step. `cmdkey /list | findstr openrouter-image-mcp` shows the entry. `… status` shows the org workspace.
- [ ] **Step 2: Live tests.** `uv run pytest -m live -v` passes.
- [ ] **Step 3: Claude Desktop (MSIX).**
  - Back up `%APPDATA%\Claude\claude_desktop_config.json` to `…json.bak-2026-10-03`.
  - Add the `print-config --client desktop` entry. If the app drops the edit, use Settings → Developer → Edit Config.
  - Restart. `account_status` should see the key saved from the terminal.
  - Then `auth_logout` and `auth_login` from Desktop, and the terminal `status` should see the new key.
- [ ] **Step 4: Claude Code.** `/plugin marketplace add skelly-77/openrouter-image-mcp`, then `/plugin install openrouter-image`. Both skills are listed, and `list_image_models` works.
- [ ] **Step 5: End to end.**
  - **Ask the user for explicit OK to upload `C:\Users\user\OneDrive - Example Firm\01 Personal\Claude Blender\renders\Sample_Render_v5.jpg`.**
  - With the OK, run the `architectural-render-polish` skill against it.
  - **Output location:** the server saves next to the input by default, and the Blender folder must not be written to. So pass `output_dir="C:\Users\user\Pictures\OpenRouter Images\acceptance"`, unless the user explicitly says saving next to the render is fine.
  - Verify 1920×828, the sidecar, and the cost in the result. Show both images to the user side by side.
- [ ] **Step 6: 401 path.** The user deletes the key in the OpenRouter dashboard. The next tool call gives the "call `auth_login`" error, and re-login works.
- [ ] **Step 7: Copilot Code.** Record it as deferred and list what to check (config location, skills folder, whether it can open a browser and reach the credential store).
- [ ] **Step 8: Commit** `docs: acceptance results`.
