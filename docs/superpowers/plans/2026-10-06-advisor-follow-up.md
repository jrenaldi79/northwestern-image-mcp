# Advisor follow-up and bounded reading Implementation Plan

**Goal:** Keep long responses manageable and continue the same advisor chat from the MCP App.

**Architecture:** Bound the rich-text answer with vertical scrolling; preserve full text for export and handoff. A composer submits `send_advisor_message` with the owned displayed chat ID and follows the returned background job through private result polling. Existing server ownership checks, saved history and inference accounting remain authoritative.

**Tech Stack:** MCP Apps SDK, native HTML/CSS, JavaScript, Playwright.

## Constraints

- No automatic paid retry or parent-chat context update.
- Follow-ups use the same chat/model. No implicit new skill transfer.
- Busy, blocked and unsupported hosts cannot send. Failed submissions retain drafts.
- Validate returned chat ID, distinct job ID and answer kind before switching results.
- Clear old sharing previews when switching jobs; preserve explicit review and send.
- Cap answer height at 360px, 280px on narrow screens; scrolling remains keyboard accessible.
- Streaming follows the bottom only when the reader was already at the bottom.

## Steps

- Add browser coverage for long-content scrolling, successful same-chat submission,
  busy controls, failed draft retention, malformed job rejection and no handoff.
- Observe failure against the current UI.
- Add composer and bounded answer styles in `ui/src/advisor.html`.
- Add submission state, validation and reader-aware scrolling in `ui/src/advisor.js`.
- Rebuild packaged UI; run advisor and Markdown checks, capture long-answer screenshots.
- Inspect wide/narrow screenshots together and refresh the local review gallery.

## Verification

The initial browser checks failed against the old unbounded reply and absent
composer. After implementation the build succeeded and all 33 advisor checks
passed, covering follow-ups, draft retention, streaming reader position, rich-text
safety, ownership validation and explicit sharing. Wide and narrow long-reply
screenshots were visually inspected. No live inference was needed for these checks.
