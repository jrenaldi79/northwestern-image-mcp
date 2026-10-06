# Model selection and automatic saving

The user requested batch variants removed, an obvious required model-selection task,
automatic persistence on selection, and visible USD pricing per million tokens.

The existing Northwestern palette and inline 620px height limit remain. The Models
tab gets a text cue and accent border when the general advisor is missing or no
longer eligible. General is required to finish setup; brand preferences are optional.
Pricing sits immediately under each select, with input/output per million tokens.
Image and request charges retain their actual units. Unknown prices say unavailable.

Each selection sends one revision-checked preference write. Controls are disabled
while saving so writes cannot overlap. Confirmation updates the current revision.
Failure preserves the proposed choice, refreshes ownership when rejected, and shows
a deliberate Retry save action. Account changes clear the old choice. No retry or
overwrite happens automatically after a conflict. Navigation and teardown make no
extra writes. Completion uses the existing explicit tool call.

Batch token matching checks both canonical ID and display name on the server and
in the App. Existing vendor and six-month catalog filters remain.

Following the user's visual feedback, the header and active step use Northwestern
purple with white text. A distinct white surface emphasizes the general advisor;
brand rows use separators. Price amounts use larger, heavier type, while context
limits use secondary text. Required and selected states retain text cues and focus
rings. The 620px inline limit remains; supporting catalog notes are collapsed.

Implementation sequence: add regression checks; implement backend exclusion;
replace explicit Save with autosave and safe retry; replace collapsed pricing with
inline per-million amounts; update prior interaction tests; build and verify with
offline Python and browser tests; inspect narrow and desktop captures. No deployment.

Verification: 91 preference/MCP tests passed; 62 browser tests passed using installed
Chrome with one worker, including safe retry, scope changes, per-million pricing,
batch exclusion, resize stability, and light/dark narrow layouts. Ruff and diff
whitespace checks passed. Narrow and desktop renders inspected. No paid calls.
