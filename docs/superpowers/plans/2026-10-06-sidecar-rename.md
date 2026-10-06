# OpenRouter Sidecar rename implementation plan

**Goal:** Rename the MCP server to `openrouter-sidecar` without resetting user data.

**Architecture:** Change presentation and client keys only. Preserve internal
package/storage identity and rename installed configuration entries in place.

**Tech stack:** Python, JSON/TOML configuration, bundled JS MCP Apps.

- [x] Update existing CLI, Northwestern config, installer, and server tests to
  expect the new name. Include a legacy single entry in installer migration
  coverage. Run those checks before production edits.
- [x] Update `cli.py`, `server.py`, `apps.py`, installer/gallery helper, plugin
  `.mcp.json`, README, and both UI source titles/client names. The installer must
  remove the legacy single and cohort entries. Keep modules, credential labels,
  storage paths, tools, cohort settings and package commands unchanged.
- [x] Build both viewers; run covering Python/browser tests, lint and whitespace
  checks. Back up and rename Codex TOML table headers and Claude JSON server key
  in place, comparing parsed settings before and after.
- [x] Verify fresh installed stdio discovery/resource loading without inference.
  Record actual results and tell the user to restart their desktop clients.

Verified 2026-10-06: five focused tests failed on the old name before the edits;
98 covering Python tests passed afterward. Both viewer bundles built and all 35
offline browser tests passed. Ruff and whitespace checks passed. Fresh stdio
discovered 18 plain tools and 21 Apps-enabled tools, with the renamed viewer URI
loading successfully and app-only tool restrictions intact.

Codex and Claude configuration backups were created with suffix
`.sidecar-rename-20261006-063333-182283.bak`. Parsed configurations were checked
equal to their originals after only changing the entry name. The existing
2100-second Codex tool timeout was also verified by fresh stdio checks.

No paid inference, credential changes, data migration, deployment, commit or push.
Running desktop clients need a restart to replace their old server processes.
