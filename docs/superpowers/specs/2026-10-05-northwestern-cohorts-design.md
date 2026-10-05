# Northwestern cohort configuration

Status: amended to one installed server at the instructor’s explicit request. Original design approved by the instructor on October 5, 2026. Image analysis tools excluded; Claude provides analysis.

## Intended outcome

Adapt the cloned image MCP server for Northwestern University AI classes. John will test both cohort configurations in Claude Desktop with his own organization account. Student deployment remains on hold until OpenRouter increases organization capacity. Student roster data stays in the existing Google spreadsheet and does not enter the repository.

## Approach

Use one codebase with explicit cohort profiles. Two independent forks would duplicate fixes and releases. Environment overrides alone would select workspaces but leave the existing shared credential entry vulnerable to reuse across cohorts. Cohort profiles plus workspace-specific credential storage address both concerns.

## Cohorts

| Cohort | Purpose | OpenRouter workspace ID |
| --- | --- | --- |
| 2027 | Capstone, full-time and second-year students | `21082e84-ae02-4639-ad40-c7251b98ab10` |
| 2028 | First-year students | `8804f9c5-afd2-4de3-8d9f-f74b3d58c651` |

The workspace IDs were verified in the Northwestern University organization on October 5, 2026. Neither is a credential.

## Configuration and launch

- Add explicit cohort selection using `OPENROUTER_IMAGE_COHORT=2027` or `2028`.
- Remove the firm's hard-coded workspace default. Missing or invalid cohort selection must give an actionable configuration error rather than select a workspace silently.
- Retain `OPENROUTER_IMAGE_WORKSPACE_ID` as an alternative way to select either known Northwestern workspace. Reject unknown or empty workspace IDs and overrides that conflict with a selected cohort. There is no personal-account fallback in this Northwestern version.
- Generate two Claude Desktop entries, `northwestern-images-2027` and `northwestern-images-2028`, pointing to the interpreter and entry point in this checkout's local virtual environment. The test configuration must not fetch the original upstream release.
- Keep the original Git remote for provenance. Publishing, creating a GitHub fork, and choosing a distribution repository are separate future work.
- Store generated images by cohort under `~/Pictures/Northwestern AI/Class of 2027` and `Class of 2028`, with existing explicit output-directory overrides preserved.
- Merge the two entries into the current Claude Desktop configuration after backing it up. Preserve unrelated settings and MCP servers. Account for Desktop's documented Microsoft Store configuration behavior if applicable.

## Authentication and credential isolation

Continue browser sign-in with PKCE and the existing `required_workspace_id` parameter. Label new keys with Northwestern and the selected cohort. Store each key in the OS credential store under a Northwestern service namespace and a workspace-specific username.

The HTTP client, login manager, account status, logout, and invalid-key cleanup must share the same explicit credential scope. Switching, signing out, or revoking one cohort's key must not affect the other cohort or the legacy firm's credential. Do not migrate or reuse the legacy credential automatically.

Report the configured organization, cohort, and workspace in CLI status and MCP account status, including signed-out and error states. Distinguish the configured target from independently verified key metadata; do not claim that a label alone proves billing ownership. Never print keys or save them in config files, logs, or this repository.

## Classroom instructions

Update current setup documentation and the general image skill for Northwestern browser sign-in, cohort selection, output locations, visible generation costs, and appropriate permission before uploading other people's images. Keep the existing image tools and optional architectural editing skill functional. Refresh the bundled plugin skill copies when source skills change.

The README must lead with local testing and clearly mark student deployment as pending. Any future remote installation command must use the eventual Northwestern distribution source rather than accidentally install the friend's version.

## Verification

Add focused regression coverage for cohort resolution, configuration errors, separate credential storage, sign-in URL constraints, scoped logout and invalid-key cleanup, status context, and local Desktop launch configuration. Run the existing offline unit suite and lint checks. The pre-change baseline is 400 passed, four live tests deselected, and passing lint.

For acceptance testing, launch both entries through Claude Desktop, complete browser sign-in with John's organization account, inspect each key in the corresponding OpenRouter workspace, and confirm account status and catalog access. Exercise logout isolation. Offer one small image-generation test with its model and cost estimate before spending credits; do not run the entire live suite automatically.

## Deferred work

No student invitations, student deployment, public release, hosted MCP service, organization billing changes, or automatic monitoring is included. The four students with conflicting cohort information remain held for review. The seat request and enrollment status remain tracked in the existing spreadsheet.

## Single-server amendment

The instructor explicitly requested one MCP server to manage. Generate and install one entry named northwestern-images, with explicit cohort selection in the installer and print-config command. Replace the earlier northwestern-images-2027 and northwestern-images-2028 entries while preserving other servers and preferences. The instructor’s test installation selects 2027; students use their confirmed cohort. Keep one codebase, the two OpenRouter workspaces, and workspace-scoped credentials. Changing the installed cohort replaces the same entry and requires a Claude Desktop restart. This amendment supersedes references above to installing or launching two entries. Do not add dynamic cohort-switching tools or change the existing eight-tool interface.
