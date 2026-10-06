# OpenRouter Sidecar name

The instructor selected `openrouter-sidecar` after reviewing the proposal to
rename the server across Codex, Claude, installers, display names and docs.

Use `openrouter-sidecar` for client entry keys and the MCP server identity.
Use OpenRouter Sidecar for viewer titles, with Image preview and Advisor result
suffixes. Resource URIs use `ui://openrouter-sidecar/`.

The Claude installer removes legacy `northwestern-images` and the two legacy
cohort entries before generating the selected cohort entry. Existing installed
Codex and Claude configurations are backed up and their entry names are changed
in place, preserving every launch/environment/timeout value and unrelated setting.
Refuse conflicting destination entries. No credentials or saved data are read or
moved: package modules, credential service names, storage paths, tool names,
OpenRouter organization and workspace configuration remain unchanged.

Verify CLI/plugin config consistency, legacy installer migration and actual MCP
discovery/resource metadata with existing tests. Build both offline viewers and
run browser coverage. Verify fresh installed stdio with no inference.
