# Sidecar onboarding implementation plan

**Goal:** Let students choose and change model defaults and learn by tiny demos.

**Architecture:** Scoped preferences and demo receipts share the local SQLite
file. A bundled settings app calls the same services as conversational tools.
Full answers use existing UI-only result jobs. No live inference in tests.

**Tech stack:** Python/SQLite/asyncio, MCP SDK, ext-apps/esbuild/Playwright.

- [x] Preferences task: create `preferences.py` and `tests/test_preferences.py`;
  implement the service contract in the spec, test aliases/saves/persistence/
  identity changes before integration. No changes to advisor code or tools.
- [x] Demos task: create `onboarding.py`, `tests/test_onboarding.py`; add internal
  limited demo job support in `advisor.py` and `advisor_jobs.py`. Persist claim
  before inference; cover limits/history/skill/idempotency/ownership/restarts.
- [x] UI task: create `ui/src/settings.html`, `ui/src/settings.js`, fixture and
  browser tests; extend build; add settings shortcut in advisor viewer.
- [x] Integration task: create `preference_tools.py`, wire services/tools/resource
  in server/apps, resolve new chats, add optional image demo with idempotent
  scoped receipt, update discovery/distribution tests and README.
- [x] Review/test task: independent scope/cost/context review; full offline Python
  and browser suite/build/lint, fresh stdio; fix findings before completion.

Execute in this session using subagent-driven-development with independent file
ownership; root handles integration. Preserve all existing uncommitted work,
package/storage identifiers, configured cohort and credentials. No deployment,
paid calls, commits or push; actual desktop-host verification reported separately.

## Completion evidence, 2026-10-06

- Full offline Python suite: 596 passed, 1 skipped, 4 deselected. The final
  image eligibility and catalog checks also passed: 45 tests, including malformed
  reference-image requirements added after the full suite started.
- Full browser run: 58 passed. Subsequent pricing and recovery changes passed
  7 targeted checks and then 5 additional numeric-price checks. All three app
  bundles built successfully.
- Ruff and `git diff --check` passed. Independent review found no remaining
  material P1/P2 issues after fixes.
- Fresh installed stdio startup verified 22 tools without Apps capability and
  28 with Apps capability, including the bundled onboarding resource. No paid
  inference occurred.

General and Gemini/ChatGPT/Claude defaults are editable through the same scoped,
revision-checked service. Optional hello, saved-history, public skill, and image
demos require an explicit Run action; navigation and saving preferences do not
run inference. Full responses remain in the app until an explicit handoff.

Actual Codex/Claude Desktop app mounting and live demos remain a user acceptance
check after restarting the host to discover the new tools. No deployment,
commit, push, or paid calls were performed during this implementation.
