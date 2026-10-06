# Advisor timeouts implementation plan

**Goal:** Allow local advisor calls up to 30 minutes without weakening ownership.

**Architecture:** Separate advisor settings from image settings, align HTTP and
total deadlines, and reserve a longer SQLite mutation lease. Codex waits 35 minutes.

**Tech stack:** Python, asyncio, httpx, SQLite, pytest, Codex TOML configuration.

- [x] Add failing tests in `tests/test_config.py`, `tests/test_advisor.py`,
  `tests/test_advisor_store.py`, and `tests/test_server.py` for separate validated
  settings, response/control-operation deadlines, timed-out requests without retry,
  and protection/persistence at 31 minutes.
- [x] Add `Settings.advisor_timeout_s=1800`, parse `OPENROUTER_ADVISOR_TIMEOUT_S`,
  validate it, pass it into `AdvisorClient`, increase its cap to 1800 seconds and
  the store lease to 2400 seconds. Update the expired-lease regression clock.
- [x] Document local limits, restart requirements, and interruption limitations.
- [x] Run targeted tests, then offline regressions and lint. Back up and narrowly
  update Codex to 2100 seconds; verify a fresh stdio server loads 1800 seconds
  and exposes the same tools without inference.

Verification on October 6, 2026: 14 expected failures before implementation;
101 targeted tests passed after implementation; full offline suite 476 passed,
4 live tests deselected; Ruff passed. Codex configuration readback confirmed
2100 seconds and all unrelated settings preserved. Fresh stdio handshake exposed
16 tools. No paid inference or 30-minute provider soak test was performed.
