# Advisor result viewer implementation plan

**Goal:** Keep full advisor answers local and let students choose what enters the
parent chat through a streaming MCP App.

**Architecture:** Background jobs extend the existing owner/workspace-scoped
advisor service. Public tool envelopes carry status only; app-only fetches carry
display text in `_meta`. A bundled viewer polls and sends content only on user action.

**Tech stack:** Python/SQLite/asyncio/httpx, MCP 2.x, existing ext-apps/esbuild/Playwright.

Global constraints: local testing only; no provider selectors, credentials in UI,
automatic inference retries, or cross-student results. Total inference deadline
1800 seconds, chat lease 2400 seconds. App-only visibility does not replace ownership.

- [x] Backend task: add failing tests, then streaming adapter/service callbacks and
  persisted owned jobs with status/view/summarize/export/shutdown operations. Own
  `advisor.py`, `advisor_client.py`, `advisor_jobs.py`, `advisor_results.py`, and
  their new tests; preserve existing synchronous service API for internal testing.
- [x] UI task: create separate bundled `advisor.html` and `advisor.js`, extend build,
  and browser tests for previewed selection/full/summary handoff, polling, error
  states, export, collapsed prompt and safe rendering. Use agreed tool contract.
- [x] Integration task: wire job lifecycle, safe public and app-only tool envelopes,
  capability negotiation, resource registration, and scoped metadata-only chat view.
  Add actual MCP wire tests and update intentional discovery/result contracts.
- [x] Review/test task: review ownership and context separation independently;
  run covering tests and browser tests/build, then full offline suite and lint;
  verify fresh stdio discovery. Document restart/test steps and actual host limits.

Verification completed locally on 2026-10-06:

- Full offline Python suite: 510 passed, 1 skipped, 4 live tests deselected.
  The skip requires native Windows symlink creation privileges; simulated reparse
  path protection passed.
- Browser suite: 35 passed (24 advisor viewer, 11 image viewer); bundled UI build passed.
- Ruff and git diff whitespace checks passed.
- Fresh stdio: 18 tools without Apps capability, 21 with Apps capability;
  app-only access restrictions and packaged viewer resource verified.
- Independent ownership/context review completed; action-time Send/Copy access
  checks, interrupted cleanup flags, and partial handoff labels rechecked.

No paid inference, deployment, commit, or push was performed. Restart Codex Desktop
or Claude Desktop to load the updated server, then test the viewer and explicit
handoff in that host. Actual host rendering/messaging remains unverified; offline
browser tests exercise the bundled SDK through a simulated iframe host. Jobs do
not continue after the local server shuts down; interrupted partial results remain
labelled and are not retried automatically.
