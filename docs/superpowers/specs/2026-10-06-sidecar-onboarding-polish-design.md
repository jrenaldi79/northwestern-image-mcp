# Sidecar onboarding polish

User-authorized scope: polish onboarding, investigate Models shaking, replace
Try it with visual explanation, and explain reuse of relevant available skills.

Retain four steps: Setup, Models, How it works, Finish. Use a restrained purple
visual language, responsive cards, and a diagram showing a deliberate main-chat
brief and relevant shareable skill instructions going to an advisor. The advisor
has separate history; results are reviewed and selectively returned or saved.
Also illustrate model defaults and image generation. No live-demo controls,
inference, automatic skill scanning, or automatic plugin/file synchronization.

Preserve scoped revision-checked preference saving, same-owner conflict recovery,
account-switch clearing, literal rendering of catalog text, and teardown guards.
Keep existing backend demo endpoints for independent test harnesses.

The SDK auto-resizer mutates the document root height to measure max-content,
observing both root and body. The basic offline host did not reproduce the user's
desktop shaking. Isolate measurement to the naturally sized app content, avoid
root-style mutations and viewport-relative sizing, batch and deduplicate height
notifications, and keep scrollbar width stable. Verify convergence under a
height-constrained host and at narrow widths; actual desktop confirmation follows.

Verification: browser settings/state tests, resize regressions, light/dark and
narrow visual inspection, rebuilt bundled apps, distribution/wire Python checks.
No deployment or paid model calls.

## Verification evidence

- Old bundled app failed the new guide regression (missing How it works) and
  root-mutation regression (two document style changes on Models).
- After rebuilding, the full browser suite passed: 55 tests. This includes five
  resize checks, constrained 320px/700px hosts, safe catalog rendering, settings
  ownership/revisions, no guide inference, teardown, and advisor/preview coverage.
- An existing summary handoff test read host messages before async ownership
  revalidation and Send completed. It now waits for the confirmed handoff status;
  no advisor production code changed.
- Offline Python MCP/distribution checks: 11 passed. Ruff and diff checks passed.
- All three bundled apps built. Fresh installed stdio discovery verified 22
  plain tools and 28 Apps tools and read the updated How it works resource.
- Desktop screenshots were inspected for the guide and model selection. Actual
  Codex shaking was not reproduced in the basic fixture; the root-mutation and
  width-reporting pathways were removed and bounded host convergence verified.

The rebuilt onboarding tool was invoked in this chat for user review. No paid
inference, deployment, or changes to stored model preferences occurred.
