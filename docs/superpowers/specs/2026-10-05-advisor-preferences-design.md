# Advisor model preferences

Date: 2026-10-05
Status: Design approved in conversation; implementation authorized

## Purpose

Students address advisors by model family, such as Gemini, ChatGPT, or Claude. The MCP server resolves the family to the student's saved OpenRouter model ID. Students can change those preferences at any time through an inline MCP App or conversational MCP tools. This work remains local for instructor testing; student deployment waits for the organization capacity increase.

## Selection rules

- Normalize Gemini/Google, ChatGPT/Chat GPT/GPT/OpenAI, and Claude/Anthropic to their respective families. The names refer to API models, rather than consumer product subscriptions.
- An explicit OpenRouter model ID overrides a family default for that request without changing preferences.
- A request without a family uses the student's general advisor default.
- Resolve defaults on the server and return the exact selected model ID and display name.
- Preference changes apply to new advisor conversations. An existing conversation retains its selected model unless the student explicitly requests a supported switch.
- Validate saved choices against the current authenticated model catalog and required task capabilities. A missing or unavailable model prompts replacement; do not silently switch families.
- Classroom recommendations are exact model IDs validated against the current catalog. Show which models have actually passed our skill and sandbox probes. Catalog tool support alone is not evidence of successful skill execution.

## Preferences and persistence

Persist a general default and a mapping of model family to exact model ID, scoped to the authenticated owner and Northwestern workspace. Keep preference storage separate from the UI and transport so future hosted operation can use the same service with authenticated server-side storage. Local prototype storage must not claim cross-device synchronization. Credentials stay in the existing secure credential store.

Changing one family must preserve the remaining preferences. Validate a complete update before committing it, and reject stale updates rather than overwriting a more recent save. Reading settings and choosing a model must not incur inference charges.

## MCP interface and app

Expose operations to open Advisor preferences, retrieve current settings and available choices, update selected defaults, and resolve a family or explicit model ID. Use the same preference service for conversational tools and the app.

The first-use app confirms cohort/workspace, presents family dropdowns plus a general default, shows pricing and context limits, and saves the choices. The same app reopens for later changes. Include accessible labels, loading/error states, a visible save confirmation, and protection against losing edits during catalog refresh.

Support requests such as “Change my default Gemini model” and “Show my advisor settings.” A one-question model override does not save a new default. Hosts without MCP Apps use the same tools through text. Reuse the repository's MCP Apps capability negotiation while preserving the existing image preview.

Include a Change default shortcut in future advisor response cards. This preference feature does not by itself implement advisor inference or session persistence; those components must invoke the resolver when creating a new conversation.

## Student sandbox isolation and retention

Each student must have separate sandbox state, uploaded private files, advisor transcripts, and preferences. Allocate server-generated opaque container IDs per authenticated student and project/session. Validate ownership before every operation and never accept a caller-supplied container ID as authorization. Shared classroom skill sources may be copied into each student's sandbox; private student material must never be shared through a cohort-wide sandbox.

OpenRouter documents containers and uploaded files as workspace-scoped, rather than promising separate access controls for individual members of a workspace. Separate container IDs and MCP ownership checks therefore do not by themselves prove isolation when students hold API keys for the same cohort workspace. Before student rollout, test with two actual student-role accounts in the same workspace, including direct Files and Containers API requests. If one student can access another's data with their own key, change the provider workspace/authentication architecture before uploading private student material. Do not describe the shared-cohort arrangement as providing verified student isolation.

Provider retention verified from official documentation on 2026-10-05: containers sleep after five idle minutes; only files under /workspace/home survive restart; processes, environment variables, and installed system state do not. Saved container files are deleted after 30 days without container use. Uploaded or promoted workspace files do not expire automatically and require explicit deletion. Container expiration does not delete application-owned transcripts or preferences.

Provide an explicit Reset sandbox operation with clear scope. Preserve model preferences when resetting a sandbox. Allow export of desired outputs before deletion, and retain authoritative skill sources outside the disposable container so they can be resynchronized after expiration. Course-end cleanup and transcript retention need an explicit agreed policy; do not infer it from the provider's inactivity timeout or schedule destructive cleanup without authorization.

Sources: https://openrouter.ai/docs/guides/features/containers and https://openrouter.ai/docs/guides/features/files-api.

## Verification

Test alias normalization, exact-ID overrides, general defaults, partial updates, restart persistence, workspace/owner isolation, invalid or retired models, capability filtering, stale saves, and no mutation during resolution. Exercise the settings flow through real MCP requests with and without Apps capability. Verify UI load, selection, save, reopening, and error recovery in a supported host. Run the non-live regression suite and lint checks before reporting completion. Report local automated verification separately from actual Claude Desktop testing.

## Implementation state

Model-family preferences and the onboarding MCP App are implemented locally as of 2026-10-06. The general advisor default and Gemini/ChatGPT/Claude defaults share an authenticated owner/workspace-scoped SQLite service with revision checks, exact-ID overrides, and conversational tools. The app includes optional explicit tiny demos for hello, saved history, a public teaching skill, and image generation. See `docs/superpowers/specs/2026-10-06-sidecar-onboarding-design.md` for the final design and `docs/superpowers/plans/2026-10-06-sidecar-onboarding.md` for verification evidence. Automated tests and fresh stdio startup passed; actual desktop-host app mounting and live demos remain to be checked after restart. No student deployment or paid inference occurred during implementation.

## Verified file-boundary finding, 2026-10-05

A live two-account test used separate workspace-scoped keys while the instructor's Northwestern account had ordinary Member permissions. Its key could list another account's synthetic workspace upload, retrieve that file's metadata, and download the instructor's sandbox critic skill and generated report (HTTP 200, SHA256-identical owner controls). The comparison was admin/member, not a certified member/member test. No paid inference ran, the disposable uploads were removed, the temporary key was disabled, and the original Admin role was restored.

Do not treat opaque container IDs, per-student folders, or MCP ownership checks alone as a privacy boundary when students retain direct keys for this shared cohort workspace. Private student skill/file transfer through that shared workspace remains blocked pending a separately enforced and verified per-student storage/sandbox design. Public course assets can be intentionally shared. Preferences and private transcripts must also stay in authenticated per-user storage rather than these shared workspace files. See `experiments/advisor_probe/STUDENT_ISOLATION_TEST_PLAN.md` and the ignored isolation evidence directory for the exact test scope and controls.
