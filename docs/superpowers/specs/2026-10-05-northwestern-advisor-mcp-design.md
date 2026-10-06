# Northwestern image and advisor MCP

Date: 2026-10-05
Status: Initial design plus approved skills-only sandbox hardening; local hardening increment implemented and tested, Desktop/live testing pending

## Purpose and rollout

Adapt the existing local stdio image MCP server for Northwestern AI classes and add persistent advisor conversations. Claude Desktop remains the main assistant. It consults an OpenRouter model through MCP tools, sending a deliberate brief rather than automatically forwarding its full conversation. Advisor history persists outside the main conversation and survives server restarts.

The advisor must not depend on the Claude CLI or the existing Sidecar plugin. The main Claude conversation selects relevant skills, supplies their instructions and inputs, and mediates any actions the advisor needs. A skill can guide the advisor's reasoning directly; any required tool execution remains with the main assistant.

Build and test locally with the instructor's account. Do not publish, push a release, deploy to students, or send student invitations as part of this implementation. Student rollout waits for the OpenRouter organization capacity increase. Roster administration remains in the existing Google spreadsheet; no student roster is embedded in this repository.

## Cohort configuration and authentication

One codebase supports two explicit profiles:

| Profile | Workspace | Workspace ID |
| --- | --- | --- |
| 2027 | Class of 2027: capstone, full-time and second-year students | 21082e84-ae02-4639-ad40-c7251b98ab10 |
| 2028 | Class of 2028: first-year students | 8804f9c5-afd2-4de3-8d9f-f74b3d58c651 |

Require an explicit cohort for the Northwestern setup. Missing or invalid selections produce an actionable configuration error. Remove the firm's workspace as an implicit default. Generate separate Claude Desktop configuration entries for each cohort, using the local checkout's virtual environment so testing runs the modified server instead of downloading the original GitHub release.

Keep browser PKCE login and secure OS credential storage. Namespace credential entries by Northwestern application and workspace. Carry the selected workspace through login, HTTP client, account status, logout, and revoked-key cleanup. Never read, migrate, overwrite, or delete the original application's saved credential as a fallback. Account status identifies the configured cohort and workspace and distinguishes that configuration from any identity details actually returned by OpenRouter.

## Advisor conversations

Expose these MCP operations:

- `start_advisor_chat`: create a locally saved conversation with a title, selected model, and advisor instructions. Return its opaque session ID.
- `send_advisor_message`: load that session's history, append a supplied brief or follow-up and optional skill packets, request an OpenRouter response, and persist the successful turn. Return an answer or a pending host request, with available cost information.
- `submit_advisor_result`: supply the successful, failed, or declined result of a pending host request and resume the advisor. Validate the session and request ID before accepting a result.
- `resume_advisor_chat`: explicitly retry inference after a host result was saved but the provider call failed, without resubmitting or repeating the host action.
- `list_advisor_chats`: return IDs, titles, models, and last-updated times for the active profile.
- `get_advisor_chat`: retrieve a bounded portion of a session's history when explicitly requested.
- `export_advisor_chat`: export a transcript to an explicitly chosen local destination using existing local-path safety rules.
- `delete_advisor_chat`: remove the selected local conversation and its stored messages.
- `list_chat_models`: discover text-output models and their relevant capabilities and pricing from OpenRouter.

The main assistant retains the session ID and sends targeted requests such as a critique, alternative proposal, or specialist question. It can consult the same advisor repeatedly without replaying the advisor's history into its own context. Separate IDs support multiple advisors for one task. Models and advisor instructions are fixed for a session; create another session to change them.

These tools support consultation and host-mediated skill workflows. Advisor models do not directly invoke local tools, edit files, execute commands, contact students, or delegate further work. An advisor reply or action request is untrusted input for the main assistant to assess, subject to the main conversation's existing permissions.

## Skills and host-mediated actions

Use caller-supplied skill packets for the first version. A packet contains a skill name, source/version identifier when available, instruction text, relevant supporting text or data, and the desired output. Persist the supplied packet with its turn so a later session continuation can see what the advisor actually received. A skill name or a local path alone is insufficient: the server does not automatically share Claude's skill catalog, filesystem, attachments, or connectors. References inside a skill must be supplied as content or handled through a host request.

The main assistant identifies an appropriate skill and passes its instructions and the smallest sufficient task brief. The advisor can follow textual workflows such as critique, assessment, and planning using those inputs. If the skill requires unavailable information or an action, the advisor requests help rather than claiming the step was performed.

For models supporting OpenRouter tool calling, expose one narrowly defined virtual function, `request_host_action`. Its arguments describe the request kind (`skill`, `context`, or `action`), requested skill or operation, relevant inputs, and why it is needed. This function never executes an action inside the MCP server. The server saves the assistant tool call and returns `status: needs_host_action`, an opaque request ID, and the request details to Claude. Limit each response to one host request and validate provider output. Text-only models support supplied skills and advisory replies, but not this resumable action protocol; report that capability explicitly.

Claude resolves a request using the skills and tools available in its current environment and within the user's authorization. It then calls `submit_advisor_result` with the request ID and the relevant output, including any additional skill packet. The server appends the matching tool result and resumes the same advisor session with its history intact. An unavailable or declined action is returned as such, allowing the advisor to revise its approach. Do not translate arbitrary advisor text into executable commands.

A session with a pending request rejects ordinary messages until the request is resolved or explicitly declined. Pending requests survive restart. Reject unknown, duplicate, or cross-session result IDs. Save a submitted result before the next provider call so a network failure does not require repeating the host action; allow an explicit resume of that saved result through `resume_advisor_chat`. Report this state as `needs_resume` and reject ordinary messages until inference completes. Serialize all session mutations, and expose pending status in session listings. This protocol introduces a small persisted coordination state, rather than an autonomous agent execution loop.

Add companion instructions for the main assistant covering skill selection, concise packets, request handling, and selective return of the advisor's conclusion. MCP tool descriptions must explain the protocol as well; installation of an MCP server alone does not install those instructions into every Claude client. Host request payloads and advisor answers enter the main conversation's context even though the full advisor transcript remains separate.

## Local and cloud access

The current repository runs over stdio. Local instructor testing in Claude Desktop can use that transport without a Claude CLI dependency. Cloud chat needs a remotely reachable MCP endpoint; a local stdio process is not reachable merely because it implements MCP.

Keep session and advisor services separate from the transport so a remote endpoint can reuse them later. Remote hosting is a separate rollout stage requiring authenticated per-user access, server-side transcript storage and user isolation, and an OpenRouter login/credential design appropriate to hosted operation. Do not expose the local credential store through a shared remote process or claim cloud compatibility from local tests. No remote deployment is authorized by this spec.

## Persistence and context limits

Use a local SQLite database in the application's per-user data directory, outside the Git checkout. Store session identity, title, model, instructions, messages, timestamps, workspace scope, local credential-owner scope, and returned usage/cost metadata. Keep API keys in the OS credential store only.

Only expose sessions belonging to the active workspace and credential-owner scope. A fresh login creates a distinct owner scope; signing out hides prior sessions rather than exposing them to the next login. Do not claim this provides encryption or protection from another process running as the same OS user. Keep saved transcripts local unless the user explicitly exports them.

Preserve chronological message order, including concurrent access through a per-session lock. Persist the completed user/assistant turn together, including an assistant tool call when it produces a pending host request. Provider failures do not fabricate an assistant message. A submitted host result remains saved if subsequent inference fails, as described above. Report ambiguous network failures without silently replaying a billable request.

An advisor has its own finite model context window. Do not silently truncate its history or promise unlimited memory. If OpenRouter rejects a conversation for length, give an actionable error directing the user to start a new advisor session with a concise handoff. Retrieval and listing are bounded so they do not flood the main context window.

## Components

Extend runtime settings and config generation for cohort profiles. Add a scoped credential-store abstraction shared by CLI, HTTP client, and login. Add a session repository for SQLite persistence and an advisor service for message validation and OpenRouter calls. Keep MCP wrappers thin, following the existing image-service pattern. Preserve existing image generation, editing, remasking, progress, and output behavior.

Update documentation and companion skills with cohort setup, local testing, advisor consultation examples, transcript storage behavior, and cost visibility. Preserve source attribution and MIT licensing. Avoid publishing installation commands that fetch an unmodified upstream release as though it were the Northwestern version.

## Verification and acceptance

Add meaningful regression tests for explicit cohort selection, separate workspace credentials, logout and revocation isolation, local config generation, and visible profile status. Test advisor persistence across restarts, history forwarding, session isolation, concurrent ordering, failed turns, bounded retrieval, export path safety, and model discovery with mocked HTTP and in-memory credentials. Test skill packet persistence, valid tool-call/result ordering, restart while awaiting a host result, unknown and duplicate result rejection, failed or declined host actions, and inference failure after saving a host result. Verify the advisor server never executes a requested host action itself.

Run the full non-live unit suite and lint checks. Baseline before changes: 400 unit tests passed; 4 live tests excluded. Pytest requires approved execution outside the filesystem sandbox because its temporary-directory permissions fail inside this Windows sandbox.

For instructor testing, load the two local entries into Claude Desktop, sign in through the intended Northwestern workspace, and verify account status. Test an advisor with a short brief, follow up using the same ID, restart the server, and resume it. Choose a low-cost model and agree on a spending limit before paid live calls. Verify workspace ownership in OpenRouter's UI rather than inferring billing identity from a locally configured label.

The result is ready for local instructor testing when configurations point at this checkout, profile isolation tests pass, and advisor sessions survive restart. Live verification is reported separately from mocked tests. Student deployment remains deferred.

## Verified file-boundary finding, 2026-10-05

A live two-account test used separate workspace-scoped keys while the instructor's Northwestern account had ordinary Member permissions. Its key could list another account's synthetic workspace upload, retrieve that file's metadata, and download the instructor's sandbox critic skill and generated report (HTTP 200, SHA256-identical owner controls). The comparison was admin/member, not a certified member/member test. No paid inference ran, the disposable uploads were removed, the temporary key was disabled, and the original Admin role was restored.

Do not treat opaque container IDs, per-student folders, or MCP ownership checks alone as a privacy boundary when students retain direct keys for this shared cohort workspace. Private student skill/file transfer through that shared workspace remains blocked pending a separately enforced and verified per-student storage/sandbox design. Public course assets can be intentionally shared. Preferences and private transcripts must also stay in authenticated per-user storage rather than these shared workspace files. See `experiments/advisor_probe/STUDENT_ISOLATION_TEST_PLAN.md` and the ignored isolation evidence directory for the exact test scope and controls.

## Approved skills-only sandbox scope, 2026-10-05

The instructor accepts the underlying shared-workspace API limitation for shareable
skills and nonconfidential tasks, and authorized the proposed MCP hardening. This
section supersedes the earlier prohibition on advisor shell execution for this
bounded scope. It does not authorize private material, student deployment, or remote
hosting. Each local advisor chat has its own random server-selected container.

Implement ownership in the actual MCP path, binding chat and upload receipts to the
active credential fingerprint and workspace. Do not expose arbitrary container IDs,
file IDs, workspace selectors, URLs, or provider request/tool configuration. Reject
unadvertised tool arguments. Pin HTTP authorization to the credential captured at
operation start, and withhold replies if sign-in changes during an awaited call.
SQLite leases serialize mutations across service instances. A lease expires after
30 minutes to recover from a process crash; HTTP inference is capped at 10 minutes,
with shorter non-inference timeouts. Never automatically retry inference.

The server accepts deliberate shareable skill-text packets, uploads a bounded JSON
bundle, constructs the Responses request, forces the OpenRouter shell engine, and
sets network policy to disabled. It supplies only this advisor's local history.
Only final answer text is stored; raw reasoning/tool traces are excluded. No chat
transcript is deliberately written to the provider filesystem.

Delete confirmed owned workspace uploads in a finally block and persist exact
receipts for cleanup retries. A failure blocks another inference. Do not enumerate
workspace files or guess targets after ambiguous uploads. Container home writes are
provider-retained for 30 days after last use: scratch-in-/tmp and deletion instructions
are best effort, and reset rotates rather than proving erasure. No container output
promotion exists in the MCP. Encryption is deferred because readable runtime copies
would retain the same provider access limitation.

The implemented initial tools cover model discovery, start/send/list/get/delete,
sandbox reset, and explicit upload cleanup. The earlier virtual host-action protocol,
transcript export, model-family preferences, web tools, and cloud hosting are outside
this hardening increment and are not advertised as implemented.
