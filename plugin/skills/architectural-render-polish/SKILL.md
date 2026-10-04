---
name: architectural-render-polish
description: Use when the user wants an architectural render, viewport capture or visualization (Blender, Revit, Enscape, V-Ray, Lumion, Twinmotion, SketchUp) made photoreal or "polished" with AI while keeping the design, camera, people and exact pixel size unchanged, or when an AI-polished render has drifted from the original.
---

# Architectural render polish

## Overview

Turn a render into a photograph-quality image without redesigning it. The whole job is the tension between "more real" and "nothing changed": the prompt lists everything that must stay, allows only photographic realism to change, and you check the result for drift before calling it done.

**REQUIRED BACKGROUND:** the openrouter-image skill (tools, costs, sizing, masks, model choice).

## Confidentiality checkpoint

Before uploading anything, get the user's explicit OK to send this client or project render to a third-party model provider. Tell them the image goes through OpenRouter to the provider (for example OpenAI), and that the org admin can see prompts and outputs. No OK, no upload.

## Workflow

1. **Inventory the render.** Look at the image yourself and write down:
   - camera: position, height, lens feel, framing, aspect ratio, whether verticals are true;
   - architecture: structure, ceiling, walls, glazing, light fixtures, finishes;
   - furniture and objects, each with its position;
   - people: count, position, pose, clothing colours, skin tone, what each is doing;
   - palette, and any floor or wall pattern and its direction;
   - light: direction, time of day, which fixtures are on;
   - signage, text and logos (these are the most likely to get garbled).
2. **Fill in `prompt-template.md`** (in this skill's folder) from the inventory. Be concrete: "the pendant above the desk", not "lights". Delete lines that don't apply, such as people in an empty room.
3. **Cheap pass first.** Before calling, tell the user the expected cost (from a comparable earlier result times `n`). If the cost is unknown, say so and run `n=1` first, then the rest of the pass once the cost is known. Call `edit_image` with the render as the only image, a speed-tier model or `quality="low"`, `n=2` to `n=4`, `fit="preserve"`. Use these to judge the prompt, not the final quality.
4. **Final.** Precision-tier model (the prototype used `openai/gpt-image-2.5-sunburst`; confirm with `get_image_model`), `quality="high"` where the model offers `quality` (offer xhigh/max only with the cost stated), `n=1`, `fit="preserve"` so the output is exactly the input's pixel size. Prefer a model whose ratios include one close to the render's: a 2.32:1 render crops back cleanly from 21:9, but a model limited to 16:9 pads the edges.
5. **Check for drift** by comparing the output with the input side by side:
   - objects moved, added or removed; furniture redesigned;
   - people changed: face, skin tone, clothing, pose, or count;
   - pattern changes: floor direction, tile layout, mullion spacing;
   - text, logos or watermarks appearing, or existing signage garbled;
   - camera or verticals shifted.
6. **Rerun if anything drifted**, either with a tighter prompt (name the drifted item in KEEP EXACTLY with its position) or with a protective mask. Show the user the comparison and the cost before each rerun.

## Protective masks

Pass `mask_path` (absolute): white = may change, black = keep pixel-identical. That holds only with PNG output (the default); a JPEG or WebP `output_format` re-compresses the black areas too.
- **Signage and logos:** paint them black so the original pixels survive; models rarely reproduce text.
- **People:** paint them black to keep them exactly as rendered, or leave them white if making them look real is the point. Ask the user which.
- Watch for a lighting seam at the mask edge; enlarge the feather (`mask_feather_px`) or the white area if it shows. Masks need `fit="preserve"`. After a masked `edit_image` you don't need a paid rerun for this: enlarge the mask (or the feather) and call `remask_image` on the result, which re-blends the model's saved image locally for free.
- In Claude Code you can draw the mask with Pillow from rectangles around the protected areas; otherwise ask the user to paint one at the render's size.

## Where outputs go

Outputs and their `.json` sidecars land next to the render. If that folder shouldn't receive files (an issued set, a synced client folder), pass `output_dir` with an absolute path.

## Common mistakes

| Mistake | Fix |
|---|---|
| Generic prompt ("make it photoreal") | Fill the template from a real inventory; the KEEP list does the work. |
| Final run first | Cheap pass first; most drift shows up there. |
| Passing `aspect_ratio`, `size` or `fit="model"` | Don't pass `aspect_ratio` or `size` with `fit="preserve"`; keep `fit="preserve"` so the size matches the render exactly. |
| Accepting the first output | Check every drift item; people and signage drift most. |
