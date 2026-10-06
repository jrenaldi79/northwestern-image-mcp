# Recent models and compact inline setup

User-authorized changes: add a preferred Open Weight model; allow only GLM,
Qwen, Kimi, MiniMax and DeepSeek in that group; omit Claude from setup; exclude
models older than six months; apply the same filters to the general default;
reduce app height in the narrow inline chat environment.

Server preferences classify Google, OpenAI and approved canonical open-weight
families. Both settings and public chat-model discovery use this eligible catalog.
Choices require a valid integer OpenRouter `created` timestamp in an inclusive,
rolling six-calendar-month UTC window. Month-end days clamp to the target month.
Missing, malformed, and future dates are excluded. OpenRouter documents this
field as the date added to its catalog, not an independently verified release
date: https://openrouter.ai/docs/guides/overview/models.

Defaults are google, openai, and open_weight. Open Weight aliases resolve the
shared preferred open-weight choice. Legacy family JSON normalizes on read and
is persisted in the new shape on a valid update. An ineligible general default
does not silently switch models; it prompts replacement. Existing chats retain
their chosen model and history. Scope, revision, and ownership protections remain.

The UI applies the same catalog eligibility checks, never adds excluded saved
IDs as dropdown options, and replaces the Claude field and examples. Narrow
model fields use smaller spacing and a single collapsed pricing/details panel.
Inline height requests cap at 620px; overflow remains scrollable. Fullscreen
presentation can use natural height. Content measurement remains independent
of the viewport and does not report host width or mutate the document root.

Verification covers all five model families, calendar boundaries and malformed
dates, legacy migration, valid saves and invalid atomic rejection, filtering in
general and family dropdowns, no Claude in setup, compact 360px layout, expandable
pricing, stable resizing, and offline advisor/wire regressions. No inference or
deployment is required.

Final polish uses the installed Impeccable skill and preserves Northwestern purple. Model fields are grouped without nested cards; decorative heading labels are removed; pricing stays in one collapsed disclosure; the account status is concise. Narrow layouts retain keyboard focus and an internal scroll area. No deployment or paid calls were performed.

Backend verification: 638 passed, 1 skipped, 4 deselected. Fresh stdio verification exposed 22 plain tools and 28 App-capable tools with valid UI resources.
Final browser verification: 58 passed using installed Chrome with two workers; narrow and desktop captures inspected. High-concurrency startup timeouts resolved on the lower-concurrency rerun.
