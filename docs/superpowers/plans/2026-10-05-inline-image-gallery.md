# Inline Image Gallery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Show inline previews from the existing Northwestern image MCP server.

**Architecture:** A packaged HTML resource runs the official Apps SDK inside the
host iframe. Python emits structured preview data alongside existing text and
image content. One resource is shared by generation, editing, and free remasking.

**Tech Stack:** Python MCP 2.3, official ext-apps SDK, esbuild, browser tests.

## Global Constraints

- One `northwestern-images` entry; existing eight tools and cohort auth unchanged.
- No deployment or paid model calls.
- Resource `ui://northwestern-images/preview.html`, MIME `text/html;profile=mcp-app`.
- No CDN; only JPEG base64 data URIs; safe DOM/textContent, never result innerHTML.
- Missing call cost stays null; remask cost is zero; filenames without previews remain visible.
- Preserve unrelated concurrent `experiments/` and advisor design work.

### Task 1: Packaged viewer and browser verification

Files: `ui/package.json`, lockfile, `ui/src/preview.js`, `ui/src/preview.html`,
`ui/build.mjs`, browser tests, `src/openrouter_image_mcp/ui/preview.html`.
Consumes the structuredContent contract in the approved spec.
Produces bundled HTML loaded through importlib.resources by the server.

- [x] Write and run failing browser tests for initialization/tool-result rendering,
  cost-null versus zero, no-preview files, errors, and hostile strings/URLs.
- [x] Install pinned SDK/build/test dev dependencies and implement safe gallery.
  Set app.ontoolresult before app.connect(); App({name,version}, {}, {autoResize:true}).
- [x] Bundle SDK into committed HTML; package builds require no Node at runtime.
- [x] Run browser tests offline using synthetic image data and a mocked host.

### Task 2: Python protocol integration

Files: `src/openrouter_image_mcp/apps.py`, `server.py`, `tests/test_server.py`.
Consumes packaged HTML. Produces CallToolResult with the approved data contract.

- [x] Add failing protocol tests: three tool links, correct resource MIME/self-contained
  HTML, structured JPEG plus ordinary ImageContent, missing-preview and partial
  result handling, free remask, no resource URI in result text.
- [x] Run `.venv\Scripts\python.exe -m pytest tests/test_server.py -q` and verify
  expected failures before implementation.
- [x] Register resource and tool meta through SDK public APIs. Return CallToolResult
  with content and structured_content, preserving all previous content.
- [x] Repeat focused tests, then full offline suite and ruff.

### Task 3: Distribution and acceptance handoff

Files: `README.md`, distribution tests, this plan.

- [x] Verify wheel includes bundled resource and can read it after installation.
- [x] Document Node only for rebuilding the viewer, Desktop restart, host limitation,
  and a free remask acceptance path. Do not change Desktop server configuration.
- [x] Request independent code review, fix substantive findings, and rerun affected tests.
- [x] Record verified results and any outstanding actual-Claude rendering check.

Changes remain local for the user's testing; no push or deployment requested.

## Verification and handoff

- Full offline Python suite: 417 passed, 4 live tests deselected.
- Browser iframe suite: 11 passed against the bundled SDK/HTML.
- Ruff src/scripts/tests and git diff --check passed.
- Wheel build passed; importlib.resources loaded the 643,612-byte viewer from the wheel.
- Real stdio subprocess smoke passed: eight tools in both sessions, three UI links only with Apps capability, resource MIME verified, remask JPEG returned at zero cost.
- Independent Python/UI review found no outstanding actionable findings.
- A synthetic no-charge Claude request is saved in .venv/gallery-tests/claude-test-request.txt.
- Claude Desktop acceptance passed on October 5, 2026: the user ran the free remask request and supplied a screenshot showing the inline preview, filename, saved path, and $0.00 local re-blend cost. Real paid generation/editing remain separate from this free rendering check. No desktop config change or paid call was made during implementation.
- Keeping local uncommitted work on northwestern-cohorts; no deployment, push, merge, or cleanup.

## Northwestern logo addition

The user's supplied 256x256 PNG is packaged unchanged as `ui/northwestern-logo.png`.
Server, three image tools, and resource icons use embedded PNG data URIs. The
gallery heading shows a 24-pixel mark. The build source embeds the same asset.

Verified byte equality with the supplied PNG, the embedded gallery image, the
unchanged SDK script, and exact equality between packaged HTML and the updated
build template with the existing SDK bundle. Automated build/pytest/browser
reruns were unavailable: the shell command runner fails before execution with
an SSN-guard temporary-file wrapper error; Node subprocess launch reports EPERM.
The earlier 417 Python / 11 browser results precede this logo-only addition.

## Repository publication checks

On October 5, 2026, the command runner became available again. The logo-inclusive
gallery rebuilt successfully (654,640 bytes), all 11 offline browser checks
passed, and the full Python suite passed (417 tests; 4 live tests excluded).
Ruff passed. The user authorized committing and creating a separate GitHub
repository; the new repository is private at `jrenaldi79/northwestern-image-mcp`.
Student deployment remains on hold. Concurrent advisor design and experiment
files are outside this commit.
