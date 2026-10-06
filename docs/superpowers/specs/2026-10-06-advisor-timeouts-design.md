# Longer local advisor calls

Authorized by the request to extend timeouts for long advisor tasks.

Advisor inference defaults to 1800 seconds, configured separately by
`OPENROUTER_ADVISOR_TIMEOUT_S`. Accept only finite positive values at most 1800.
Keep image inference at its existing 600-second default and other advisor HTTP
operations at 30 seconds. Enforce both total and HTTP timeouts; do not retry an
uncertain billed request. Keep a 2400-second exclusive chat lease so inference,
upload cleanup, and transcript persistence finish before it expires.

Set this computer's Codex `northwestern-images.tool_timeout_sec` to 2100,
preserving unrelated configuration and backing it up before editing. Existing
processes require a restart. Do not change startup timeout or credentials.

Long synchronous waits are the selected approach for this local test. Background
jobs would support reconnection but require a separate implementation. Pings alone
cannot guarantee an extended request deadline. Provider/network limits and app
shutdown can still interrupt calls; this change does not promise recovery.

Verify configuration validation, independent image/advisor limits, actual HTTP
deadline propagation and cancellation, and lease protection beyond 30 minutes.
Run offline regressions and stdio discovery without paid inference. No deployment.
