# Advisor Ownership Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to execute inline in the existing Northwestern feature checkout. User approved the hardening recommendations on 2026-10-05.

**Goal:** Ship a local advisor MCP path that cannot select or fetch another credential owner's container through its exposed tools.

**Architecture:** Bind every operation to the active workspace and credential fingerprint, persist opaque chat/container mappings in a local SQLite repository, and build provider requests entirely on the server. A narrow advisor HTTP adapter accepts only typed operations, pins the credential for the operation, disables redirects and inference retries, and never exposes arbitrary URLs or provider payloads through MCP.

**Tech Stack:** Existing Python, sqlite3, httpx, MCP SDK, pytest; no new dependencies.

## Global constraints

- Keep instructor-only rollout and the existing Northwestern feature checkout. Do not deploy, invite students, change browser accounts, or modify saved credentials.
- Shared OpenRouter cohort storage is accepted for shareable skills only. MCP ownership is not provider-enforced confidentiality.
- API keys are used only in HTTP authorization headers and kept in the existing OS credential store; no keys in SQLite, prompts, containers, or responses.
- Local transcript isolation uses credential-owner scope, not a claim of verified university identity. New OAuth credentials get new scope.
- No raw container IDs, file IDs, workspace overrides, HTTP URLs, provider tool configuration, or shell network settings in exposed tool parameters.
- Hosted shell network policy is explicitly disabled and engine fixed to OpenRouter.
- Only deliberately supplied skill text is uploaded, with server-assigned names. Upload IDs are recorded before inference and explicitly deleted afterward; failed cleanup remains queued locally and blocks reuse until retried.
- No workspace file listing/download/promotion or generic container fetching tools. Container reset rotates the owned ID; it does not claim deletion of provider files.
- No automatic inference retry. An ambiguous failure may have been billed. Stored transcripts contain user briefs and final answers, never raw model reasoning or tool outputs.
- Generated home-directory files may survive for 30 days. `/tmp` use and model-directed cleanup are best effort, not an enforced deletion guarantee. Do not claim otherwise.

## Task 1: Scoped local repository

Files: create `src/openrouter_image_mcp/advisor_store.py` and `tests/test_advisor_store.py`.

- [x] Write tests for A/B and workspace rejection using known foreign chat IDs, restart persistence, reset rotation preserving history, missing IDs returning the same denial, and owned upload-cleanup receipts.
- [x] Run `.venv/Scripts/python.exe -m pytest tests/test_advisor_store.py -q` and observe missing behavior.
- [x] Implement `AdvisorStore(path)`, `create(scope, model, title)`, `get(scope, chat_id)`, `list(scope)`, `append_turn(scope, chat_id, prompt, answer)`, `reset(scope, chat_id)`, `delete(scope, chat_id)`, and cleanup-receipt methods. Every query/mutation includes owner and workspace; IDs are random, and SQLite handles are short lived.
- [x] Verify focused tests pass.

## Task 2: Provider adapter and guarded advisor service

Files: create `src/openrouter_image_mcp/advisor_client.py`, `src/openrouter_image_mcp/advisor.py`, and `tests/test_advisor.py`.

- [x] Write HTTP-boundary tests: foreign known IDs generate zero HTTP requests; malformed IDs cannot affect URLs; network policy is disabled; credentials never enter payloads; malicious provider container IDs are rejected; cleanup runs on success/failure; failed cleanup prevents another inference; account switches cannot reveal an in-flight answer; no automatic inference retry.
- [x] Run focused pytest to observe failure before implementation.
- [x] Implement `AdvisorService` operations `start`, `send`, `list`, `get`, `reset`, `delete`, and `models`. Capture the active credential and scope once; authorize before HTTP and recheck before returning/saving replies. Serialize chat mutations across service instances using database state, and release locks after failure.
- [x] Implement only public model discovery, skill upload, exact owned upload deletion, and Responses inference in the HTTP adapter. Build shell environment and skill filenames internally. Parse final message text only and validate container references without retaining reasoning.
- [x] Verify focused tests and Ruff.

## Task 3: Actual MCP integration and documentation

Files: modify `src/openrouter_image_mcp/server.py`, `README.md`, `tests/test_server.py`, `tests/test_distribution.py`; create `tests/test_advisor_mcp.py`.

- [x] Add failing real MCP client tests for schemas without arbitrary target selectors and account B failing to read/send/reset/delete account A's handle without provider calls.
- [x] Register `list_chat_models`, `start_advisor_chat`, `send_advisor_message`, `list_advisor_chats`, `get_advisor_chat`, `reset_advisor_sandbox`, and `delete_advisor_chat`. Load the local store lazily and support a programmatic test-only repository path override; do not expose it in MCP.
- [x] Document skill packets, local transcript location, provider retention, account-key scope, reset semantics, and the direct-API limitation. Add approved scope to the advisor design.
- [x] Run the full non-live suite, experimental regression tests, Ruff, and diff review. No paid or real-account test during this change. Report automated verification separately from Claude Desktop/live testing.

## Verification and review

Completed locally on the existing `northwestern-cohorts` branch; changes remain
uncommitted for review. No credentials, browser accounts, student invitations, or
deployment state were changed.

- Full non-live suite: **463 passed, 4 live tests deselected**.
- Focused ownership/service/MCP suite: **46 passed**.
- Existing offline probe regressions: **27 passed**.
- `ruff check src tests experiments/advisor_probe`: passed.
- Compilation and `git diff --check`: passed.
- Independent read-only review: no remaining blocking findings after fixes.

Review regressions reproduced and fixed active-credential title persistence,
history-cap checking after lease acquisition, intermediate-message persistence,
missing total HTTP deadlines, confirmed upload deletion after receipt-write failure,
and stale-lease cleanup targeting a subsequent operation's upload. Known foreign
handles are rejected through actual MCP client calls before HTTP. These accounts
use synthetic credentials; this is not a new live member/member provider test.

Claude Desktop and a paid OpenRouter call with the new production advisor path
have not been exercised. Provider home-file cleanup remains best effort, and the
previously observed shared-workspace direct-API access limitation remains accepted
only for the documented shareable-skills/nonconfidential-task scope.
