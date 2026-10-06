# Sidecar onboarding and editable model defaults

Build requested in conversation; extends the approved advisor preferences design.
Local instructor testing only; deployment remains on hold. No live inference is
needed for implementation verification. Prefer advisor, history and skill demos,
with optional image demo, unless the instructor selects another mix.

## Student experience

One offline MCP App opens with mode onboarding or settings. It confirms the
configured cohort/workspace and sign-in, offers a general advisor default and
Google/Gemini, OpenAI/ChatGPT, Anthropic/Claude defaults, then a short walkthrough.
Choices come from the authenticated supported chat catalog. Show exact IDs,
context limits and per-token pricing; no static claim about the newest/best model.
Saving is free, explicit, atomic and revision checked. Partial updates preserve
other choices. Settings can reopen through a tool and an advisor-card shortcut.
Existing chats keep their original models. Explicit IDs override for one new chat.
Family aliases resolve server-side; an absent choice or retired model errors with
instructions to reopen settings. Do not silently substitute another model.

Demo buttons are explicit paid actions and optional. Use fixed synthetic prompts:
hello (short answer), history (follow-up on that hello), skill (bundled public
three-bullet teaching-review skill). Text jobs use <=256 output tokens and <=1
tool call; token limits are not a hard dollar cap or a promise of sandbox support.
Failed or ambiguous calls are not retried automatically. Persist demo receipts
before starting work, so repeated button/RPC requests reuse an existing job.
Image demo is optional, uses one image, selected exact image model, fixed prompt
and no private files; show catalog pricing first. It can be unavailable when the
catalog has no usable image choice. No inference occurs on page load or Next.

Display text demo results only through app `_meta`, with ownership checks and
polling. Teach preview/edit/Send, summary cost, durable save, deliberate context
and skills handoff, and the fact that advisor memory is separate from parent chat.
Viewing never updates the parent model context. Reuse existing result viewer for
full preview, summarization and file export. Persist walkthrough completion as an
explicit action; it is not required to use or change preferences.

## Backend contract

`PreferenceService(advisors)` uses SQLite alongside advisor data, scoped by
credential fingerprint/workspace; no cloud/shared files and no API keys in rows.
Synchronous `get()` returns `{settings_id,revision,general_default,family_defaults,
onboarding_completed}`. IDs are server-generated opaque stable per scope.
Async `view()` adds `{models,workspace_id,cohort}`. Model entries carry
`id,name,pricing,context_length,family` (family is google/openai/anthropic or null).
Async `update(settings_id,expected_revision,general_default=None,
family_defaults=None,onboarding_completed=None)` validates all choices before a
transaction, merges provided fields, rejects wrong ID/stale revision and returns
new `get()` shape. Null means unchanged; empty string clears a model default.
Async `resolve(model=None)` returns `{model,name,source}`; accepted aliases are
Gemini/Google, ChatGPT/Chat GPT/GPT/OpenAI, Claude/Anthropic. Exact IDs must validate
against the current catalog. Scope is rechecked after every await and before write.
`assert_context(settings_id)` rejects a stale account/window before any effect.

`OnboardingDemos(advisors,jobs,preferences)` provides
`async run(demo,settings_id,expected_revision)` for hello/history/skill and returns
job status with demo. Repeated requests for a given settings revision/demo reuse
the receipt. History requires completed hello and uses its chat. Skill uses an
owned separate chat. Demo state is persisted/scoped; local process restarts do
not retry ambiguous work. App-only `run_sidecar_demo` calls this with image handled
by root integration. A server-generated nonce/receipt is claimed transactionally
before first paid action. App never supplies arbitrary prompts, container IDs,
HTTP options, paths or credentials to this tool.

Tool contract: public `open_sidecar_settings(mode='onboarding')` attaches
`ui://openrouter-sidecar/settings.html`; `get_sidecar_preferences()` returns
preferences; `set_sidecar_preferences(settings_id,expected_revision,
general_default=None,family_defaults=None,onboarding_completed=None)` saves;
`resolve_advisor_model(model=None)` resolves. App-only `get_sidecar_settings()`
returns safe visible status plus `_meta.sidecarSettings` with complete view and
image_models list. App-only `run_sidecar_demo(demo,settings_id,expected_revision,
image_model=None)` returns status/job or `_meta.sidecarDemo` for an image.
`start_advisor_chat(model=None,title='Advisor')` uses the resolver. Public settings
and resolution are bounded; private demo answer bodies remain UI-only.
`open_sidecar_settings` may open while signed out; UI offers auth_login followed
by explicit Refresh. Preferences APIs otherwise require active credentials.

## Checks

Aliases, exact overrides, partial/atomic saves, retired and wrong-family models,
restart persistence, stale revision/settings ID, two credentials and two cohorts;
live-account switch during catalog reads or jobs; no key in UI/storage/errors;
demo limits, same-chat history, duplicate requests, no retries, upload cleanup,
Apps negotiation with and without support, wire body separation. Browser tests
cover onboarding/settings/reopen/save/refresh conflict, explicit demos, result
polling, skipped demos, no auto Send, hostile values, errors and unmount. Rebuild
all assets, run full offline suite and lint, independent review and fresh stdio.
