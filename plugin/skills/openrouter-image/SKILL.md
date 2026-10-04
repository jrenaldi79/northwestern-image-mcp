---
name: openrouter-image
description: Use when the user wants to make, generate, edit, restyle, inpaint, extend (outpaint) or vary an image with the `generate_image` or `edit_image` tools of the openrouter-image MCP server, when choosing an OpenRouter image model, or when an image call fails with a sign-in, credits, size or moderation error.
---

# OpenRouter image generation and editing

## Overview

The openrouter-image MCP server sends prompts and images to any OpenRouter image model and saves the results locally. It has no presets: picking the model, wording the prompt and keeping spend sensible is your job. Every call costs real money, billed to the user's OpenRouter organization.

## Tools

| Tool | Use it for |
|---|---|
| `account_status()` | Signed in? The key's label, its usage (today, this week, this month, total) and its spending limit. It doesn't show the workspace. |
| `auth_login(switch_account=false)` | Sign in. Returns at once; the user finishes in the browser. Then check `account_status()`. |
| `auth_logout()` | Delete the stored key. |
| `list_image_models(query?, accepts_images?, author?, sort="newest"\|"price")` | Find candidate models. `accepts_images=true` for edits. |
| `get_image_model(model_id)` | Exact aspect ratios, resolutions, quality values, max `n`, max input images, passthrough options, pricing. |
| `generate_image(prompt, model, ...)` | Text to image. Saves to the default output folder unless `output_dir` is given. |
| `edit_image(prompt, model, images, ...)` | Image(s) plus prompt to image. The first image is the primary; the rest are references. |
| `remask_image(image, mask_path, ...)` | Redo a masked edit's blend with a new mask, locally and free. |

## Before uploading client or project imagery

Ask the user for an explicit OK before the first `edit_image` call that sends a client or project image (render, photo, drawing, site image) and before any reference image from a new project. Say plainly: the image goes through OpenRouter to the model's provider (for example OpenAI or Google), and the org admin can see the prompts and outputs. An OK for one project doesn't cover another. If the user says no, stop; don't work around it with a description of the image.

## Workflow

1. **Discover first.** Don't pick a model from memory. Call `list_image_models` (with `accepts_images=true` for edits), then `get_image_model` on the one or two candidates to read their real parameters.
2. **Iterate cheaply.** Use a speed-tier model, or `quality="low"` where the model has `quality`, and `n=2` to `n=4` while the prompt is still changing.
3. **State the cost before spending.** Before a large `n` or a high/max-quality final, tell the user the likely cost: the "This call" figure from a comparable earlier result times `n`, or, if the cost is unknown, say so and run `n=1` first. `n` can be 1 to 10; above the model's maximum the server splits it into several calls, each billed.
4. **Final at full quality**, `n=1` unless the user wants options.

## Edits: paths, size and masks

- **Paths must be absolute** for `images`, `mask_path` and `output_dir`.
- **`fit="preserve"` (default) returns exactly the input's pixel size.** The server picks the model's nearest aspect ratio and crops back, or pads with blurred mirrored edges and crops. Don't pass `aspect_ratio` or `size` with `fit="preserve"`; they are rejected. A model that offers a ratio close to the input's (21:9 for a 2.32:1 render) avoids padding, which can invent content at the edges.
- **`fit="model"`** returns whatever the model made, untouched. Use it only when the user doesn't need the original size.
- **Extending or reframing** (outpainting, a new aspect ratio) needs `fit="model"` with an `aspect_ratio`: the output is no longer the input's size, and masks can't be used.
- **Masks** (`mask_path`, greyscale): white = may change, black = keep pixel-identical. The edge is feathered (`mask_feather_px`, default 0.5% of the short edge). A lighting seam can show at the mask edge; widen the feather or the white area if it does. Masks can't be combined with `fit="model"`. Black areas stay pixel-identical only with PNG output (the default); a JPEG or WebP `output_format` re-compresses them.

**Fix a seam with `remask_image`, not a new edit.** A masked edit also saves the model's image before the blend as `<result>.unmasked.png`. If the new content is good but blends badly (a ghosted edge where the model drew past the mask, or the mask was too small or too large), draw a corrected mask and call `remask_image(image=<result>, mask_path=<new mask>)`. It re-blends locally: free, nothing uploaded, no new consent needed. It needs a masked result from server v0.2.0 or later and the original input unchanged; otherwise it says so, and only then is a new `edit_image` warranted.

## Results

Each image is saved next to the primary input (edits) with a `.json` sidecar holding the prompt, model, parameters, cost and fit details, and inline previews come back in the result. Use `output_dir` when the input folder shouldn't receive files. The result ends with the call cost and today's/this month's usage; relay the cost to the user.

## Errors

| Message | Do this |
|---|---|
| Not signed in / "call `auth_login`" (401) | Call `auth_login()`, ask the user to finish in the browser, confirm with `account_status()`. Never retry in a loop. |
| Out of credits (402) | Tell the user to ask the org admin to top up. |
| "Blocked by … moderation … Not charged" | Nothing was billed. Reword neutrally (drop violent, body or brand wording), or check `get_image_model` for a `moderation` passthrough and offer it as a flat `provider_options={"moderation": "low"}` (the server routes it to each provider that allows it; other keys are rejected before spend), or switch to a model that isn't moderated. Tell the user which you chose. |
| Invalid parameter (lists allowed values) | Pick from the list; nothing was billed. |
| Model replied with text, no image | Treat as a refusal; rephrase or change model. |

## Model rules of thumb (As of 2026-10)

These go stale fast. `list_image_models` and `get_image_model` are the source of truth; check them before relying on anything below.

- **OpenAI GPT Image 2.5 Sunburst** (`openai/gpt-image-2.5-sunburst`, precision tier) and **Flare** (`openai/gpt-image-2.5-flare`, speed tier): Sunburst for detailed work, Flare for high-volume everyday work. Up to 16 input images, ratios up to 21:9, `quality` from low to max, `n` up to 10, transparent `background`. Both are moderated. No `seed`. The catalog listed the same token prices for both, so Flare's advantage is speed; use `quality="low"` for cheap drafts.
- **Google Nano Banana 2** (`google/gemini-3.1-flash-image`) and **Nano Banana Pro** (`google/gemini-3-pro-image`): up to 14 input images, ratios including 21:9, resolution tiers up to 4K, `n=1`. Pro is Google's most advanced for reasoning and real-world grounding; Nano Banana 2 is the faster one, and also offers extreme ratios (1:8 to 8:1). Nano Banana 2 Lite (`google/gemini-3.1-flash-lite-image`) is the fastest, cheapest Gemini option at 1K.
- **ByteDance Seedream 5.0 Pro** (`bytedance-seed/seedream-5-0-pro`, precise editing control, lifelike scenes) and **Flash** (`bytedance-seed/seedream-5-0-flash`, fast and cost-efficient): up to 14 input images, the widest ratio list (including 20:9 and 21:9), 1K/2K, `seed` support, `n=1`.
- **Black Forest Labs FLUX.3** (`black-forest-labs/flux-3-image`): flagship generation and multi-reference editing with up to 10 input images, resolution tiers 768 to 4K, ratios including 21:9, `n=1`.
- **Microsoft MAI-Image-2.6** (`microsoft/mai-image-2.6`, precision) and **MAI-Image-2.6 Flash** (lower latency and cost): design-ready visuals, up to 5 input images, ratios only up to 16:9, so wide renders get padded under `fit="preserve"`.
- **Recraft vector models** (names ending `-vector`, such as `recraft/recraft-v4.1-vector`): output SVG, saved as `.svg` with no fitting and no preview. Recraft "styles" models require at least one style reference image.
- **Legible text in the image:** Qwen Image 3 / 3 Pro (`qwen/qwen-image-3`, `qwen/qwen-image-3-pro`) advertise text and detail down to 10px.
