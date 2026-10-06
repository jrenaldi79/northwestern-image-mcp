# Student Isolation Probe Implementation Plan

**Goal:** Prepare a reproducible two-member file-access experiment without using real student data or claiming untested sandbox isolation.

**Architecture:** An experimental CLI enrolls A and B credentials through a masked local terminal prompt into Windows Credential Manager. Operator-attested account/role evidence stays in an ignored local manifest. A first, inference-free stage checks workspace file listing and metadata in both directions, records owner controls, and deletes only its enumerated synthetic uploads. Remaining sandbox checks stay explicitly untested until accounts and inference budgets are available.

**Tech stack:** Existing Python environment, httpx, keyring, pytest; no new dependencies or production MCP changes.

## Constraints

- Two distinct member identities and keys, same Class of 2028 workspace.
- Account identity is operator-attested, not established merely by distinct keys.
- Admin/member runs must be explicitly marked preliminary.
- No paid inference in this stage. No real student files. No key strings in output or manifests.
- A 400, auth failure, missing owner control, malformed response, or incomplete pagination is inconclusive.
- Cleanup accepts only exact test filenames and IDs from its saved manifest.

## Task 1: Access classification, identity validation, and complete pagination

Files: `experiments/advisor_probe/isolation_probe.py`, `experiments/advisor_probe/test_isolation_probe.py`.

- [x] Write failing cases for duplicate keys, duplicate member identities, admin roles, unsupported access errors, successful foreign access, missing owner control, second-page visibility, and cursor loops.
- [x] Run `.venv/Scripts/python.exe -m pytest experiments/advisor_probe/test_isolation_probe.py -q`; confirm missing behavior fails.
- [x] Implement `validate_pair(identities, keys, preliminary=False)`, `classify_access(response, owner_ok)`, and `list_files(api, workspace)` with fail-closed validation and bounded pagination.
- [x] Rerun those cases and check all pass.

## Task 2: Synthetic upload, evidence, and bounded cleanup

- [x] Add HTTP-transport coverage where B sees A's canary on a later list page, where owner controls fail, and where a cleanup manifest names an unrelated file. Owner-control and cleanup guard tests failed before implementation; the complete paginated run was added as integration regression coverage.
- [x] Implement `run_files(clients, workspace, manifest_path)` and `cleanup_file(api, fixture)`; save every created fixture before subsequent requests, use exact owner metadata as a cleanup guard, and retain cleanup failures in evidence.
- [x] Add CLI `enroll`, `run-files`, and `cleanup`; enrollment prompts with `getpass`, validates the key read-only, refuses silent credential replacement, and stores credentials under an isolated keyring service.
- [x] Run focused pytest, Ruff, compilation, and CLI help. Never exercise live uploads without the two enrolled identities.

## Task 3: Live prerequisites and reporting

- [x] Read workspace membership in browser and request missing identities while finishing independent work. Only the instructor's Org Admin account was present; no two member credentials were provided.
- [ ] Once both are enrolled, run the inference-free stage and inspect actual evidence. Any metadata visibility fails the intended private-file policy. Passing this stage alone is not full isolation success.
- [ ] Continue the separately documented sandbox/attachment/download/reuse/restore matrix only after account setup and bounded inference are ready.

The instructor already authorized proceeding with the two-user matrix. Work remains in the existing Northwestern feature branch; only experimental files are touched. No production deployment, merge, or new member invitation is part of this implementation.
