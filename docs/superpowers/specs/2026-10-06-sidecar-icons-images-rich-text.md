# Sidecar onboarding and result-viewer refinement

## Onboarding

Five compact navigation steps: Setup, Models, Advisor, Images, Finish. Consistent
decorative line icons complement labels. Northwestern purple anchors the header;
amber identifies model setup, teal identifies the advisor flow, coral identifies
images. Brand and general defaults autosave. Grok/xAI is a supported family with
the same rolling six-month and batch-exclusion policy.

Input/output prices remain visible per million tokens. Native disclosure controls
collapse context and model details. Optional rows have reduced spacing in narrow
views; inline app height remains capped at 620 pixels with internal scrolling.

Images has a real AI-generated fictional MPD product concept, a modular desk task
light, created through Sidecar using Gemini 3 Pro Image. A real masked edit changes
the lamp head from teal to coral; its saved original, mask and result illustrate
local compositing. The variation is collapsed initially to preserve space. Assets
are compressed and embedded as data URLs, so viewing makes no remote requests
or inference calls. Original generation cost $0.13479; masked edit cost $0.135676.

## Advisor result

Replace user-facing Prepare labels with Review selected text, Review full answer,
and Review a summary. A return-arrow graphic labels Bring insights back to your
main chat; the final explicit action says Send to main chat. Review remains a
separate step before sharing. Summary generation costs a new model call.

Markdown is rendered with Marked and DOMPurify: headings, emphasis, lists, code,
tables and quotes. Raw HTML is shown literally; images are rendered as alt text;
unsafe links are removed. No provider output can trigger an image/network fetch.
Full-answer handoffs retain original Markdown; selections use selected visible
text. Metadata-only polling preserves rendered nodes and selections. Existing
ownership revalidation before sharing and copying stays in place.

Provider marks from the MIT-licensed public Lobe Icons collection are bundled
locally. They appear beside model defaults and in the advisor result's model
identity. No Anthropic assets or choices are included. Logos identify vendors,
not the particular provider endpoint serving an OpenRouter request.

## Streaming

The existing background job receives Responses SSE chunks and saves partial text
locally. The MCP App opens while queued and polls app-only result access at roughly
one-second intervals, serially and with ownership checks. Completed text stays
out of parent model context until an explicit reviewed handoff. This is a streamed
provider response with polled UI updates, not a browser-side SSE connection.

Screenshots include every onboarding step at 360 and 900 pixels, an expanded mask
example, and the real synthetic classroom-advice demo in the updated chat viewer.
Onboarding model names/prices in screenshots are offline fixtures. Product visuals
and the classroom-advice response are actual Sidecar generations.

The final 23 UI layout/screenshot checks passed, including narrow model settings,
mask disclosure, all onboarding steps and the real chat demo. Rich Markdown and
the existing ownership/handoff scenarios passed in the preceding browser run.
The complete offline Python suite passed: 647 tests, one skipped, four live tests
deselected. Targeted Ruff checks and the asset build passed. Final screenshots
are saved in `experiments/ui-review/`; `index.html` compares all narrow/wide views.
