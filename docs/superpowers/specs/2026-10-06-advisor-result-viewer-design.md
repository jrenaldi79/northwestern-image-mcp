# Local advisor result viewer

Status: User approved the proposed result viewer, selective handoff, streaming,
summary preview, and durable local export on October 6, 2026. Local testing only.

## Interaction

`send_advisor_message` starts a background job and promptly returns status and an
opaque job/result ID, never the answer. An MCP App displays a collapsed original
user prompt, model, status, cost, and streamed final-answer text. Do not display
the system prompt, appended skill instructions, shell output, or reasoning traces.
Viewing, scrolling, polling, exporting, and summarizing never update model context.
Only a deliberate Send action posts a previewed selection, full response, or editable
summary to the parent chat. Label the source model and result. Check host send-message
capability; unsupported hosts offer explicit copying, never silently fetch the body
into model-visible tools. `get_advisor_chat` becomes a bounded metadata/history-count
view so the model cannot inadvertently retrieve full transcripts.

## Storage and jobs

Use the existing local SQLite database for a new jobs/results table. Bind every
operation to credential fingerprint and configured workspace, and authorize the
chat before provider operations. Never accept caller-selected provider identifiers,
export paths, or API options. Background tasks are owned by this server process;
app reconnection works while the process lives. On shutdown mark unfinished work
interrupted and cancel it without retry. Use a persisted heartbeat/expiry to identify
stale work after an unexpected process exit without stealing another process's
live job. Retain labelled partial answer text for interrupted work; never label it
completed or add it as a completed turn in history. Completed transcripts stay local.

Stream only output-text events from OpenRouter under the 1800-second total deadline.
Bound accumulated answer text and event/frame sizes; reject malformed or unexpected
provider container references using existing final-answer validation. Preserve
skill cleanup receipts and the 2400-second chat lease. Suppress answers if sign-in
changes. No automatic retry, no credentials in UI or result records.

## Tools and UI contract

Public tools: `send_advisor_message` (enqueue), `get_advisor_job` (status only),
`open_advisor_result` (status plus viewer metadata), existing chat/model tools.
App-only tools: `get_advisor_result`, `summarize_advisor_result`,
`export_advisor_result`. Results use `content`/`structuredContent` only for brief
status and `_meta.advisorResult` for UI-only data. App-only visibility and ownership
are enforced separately; hiding a tool from the model is not authorization.

Job status fields: `job_id`, `chat_id`, `model`, `title`, `status`, `cost_usd`,
`cleanup_pending`, `error`, `kind`, `source_job_id`. Viewer data adds `prompt`,
`answer`, and `created_at`. Job states: queued, running, completed, failed,
interrupted. UI-only fetch returns bounded partial/final text. Poll at an interval
without overlapping requests and stop at terminal states/unmount or denied access.

Summarize uses the same owned advisor model, creates a separate summary job, and
shows an editable preview before sending. It incurs inference. A Markdown export
is a durable file under a server-selected owner/workspace export directory beside
the local database, outside provider containers; the UI displays its path.

## Verification

Synthetic streaming provider tests, known-other-user handles and workspace swaps,
credential changes during streaming, stale job recovery, exclusive chat access,
cancellation/partial results, no automatic inference retry, export containment,
and model-visible result-envelope checks. Browser tests verify no send on view or
polling, deliberate preview/send, summary review, safe hostile text rendering, and
durable export. Build packaged UI and preserve the existing image gallery.
No deployment or paid test until the local implementation is reviewed.
