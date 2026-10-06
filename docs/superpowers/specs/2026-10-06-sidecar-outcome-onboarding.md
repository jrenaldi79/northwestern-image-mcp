# Outcome-focused Sidecar walkthrough

The instructor requested a visual inspection of every screen and substantially
less text. The image guide should explain the benefit of consistent edits rather
than masks, file formats, blending, or model implementation details.

## Changes

- Setup introduces three outcomes and a short main-chat/advisor diagram. Remove
  duplicated privacy paragraphs, workspace instructions and the global subtitle.
- Models keeps controls, provider logos, visible token prices and autosave. Display
  readable model names; put exact model IDs in expandable model details.
- Advisor uses three short stages: ask, explore, bring back. Explain the skill
  handoff in one sentence; keep privacy/sharing details behind a disclosure.
- Images shows the real MPD task-light concept and focused coral edit as an
  accessible before/after slider. Explain preservation of the surrounding image.
  Remove mask diagrams, creation tutorials, feathering, re-masking and file details
  from onboarding. The underlying image tools remain available.
  A compact Create/Edit tab pair now distinguishes both capabilities without
  adding another step to the main navigation. Create opens first, pairing the
  saved generated concept with a short example request; Edit retains the focused
  before/after comparison. Tabs support arrow keys, Home and End, and switching
  previews never triggers inference or modifies preferences.
- Finish gives one short request example and the next action.
- Chat keeps the generated answer intact, hides redundant completed-answer labels,
  moves the result identifier into the collapsed prompt details and reduces helper
  copy. Compact review controls at narrow widths; preserve explicit reviewed sends,
  summary cost disclosure, safe rich text and ownership revalidation.

The image wording describes the result of a focused edit. It does not claim that
the underlying model never renders a full candidate image. Local compositing is
what preserves unchanged regions in the existing focused editing flow.

The comparison reuses saved images. Slider movements make no inference requests,
do not update parent context and do not modify the saved images. No paid generation
is required for this refinement.

## Validation

Browser coverage checks keyboard operation of the comparison, narrow layouts,
limited visible walkthrough copy, privacy disclosure, unchanged autosave and
reviewed handoff behavior. Screenshots capture every step at 360 and 900 pixels,
plus the comparison endpoints and the real advisor reply.

Verified the built UI at 360 and 900 pixels across all five onboarding screens,
the advisor reply and the send review. The browser suite passed 70 of 71 checks;
the remaining check expected the previous summary-cost wording. After updating
that expectation, all 24 advisor checks passed, including the summary flow.
The UI build and `git diff --check` passed. No new paid model calls were made.
