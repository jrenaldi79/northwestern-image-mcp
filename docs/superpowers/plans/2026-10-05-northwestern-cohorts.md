# Northwestern cohort implementation plan

For agentic workers: execute this plan using the executing-plans workflow.

Goal: configure the local image server for Northwestern's two cohorts, keeping student deployment on hold.

1. Establish failing regressions in `tests/test_northwestern.py` for explicit cohort selection, rejected ambiguous configuration, credential isolation, 401 cleanup, constrained login, and local Desktop configuration. Run `.venv/Scripts/python.exe -m pytest tests/test_northwestern.py -q`. Completed: twelve expected failures.
2. Implement `COHORT_WORKSPACES`, validated `load_settings`, and cohort output directories in `config.py`. Add `workspace_id` keyword arguments to credential functions and the HTTP client. Pass this scope through authentication and server account tools. Display the configured target without claiming it independently verifies billing ownership.
3. Generate two local entries using `render_local_config(project: Path, executable: Path)`. Update CLI login/status/logout to select the same settings and scope. Remove remote installation from the active configuration workflow. Adjust existing fixtures to the new explicit configuration contract.
4. Update classroom setup instructions and source image skill; synchronize plugin copies. Keep the original eight tools. Mark local testing and the deployment hold prominently. Replace the plugin's upstream-release launcher with a local checkout launcher.
5. Run focused regressions, the complete offline suite, and lint. Investigate failures and rerun affected checks. Smoke-test MCP initialization, tool discovery, and signed-out status for both actual local launch entries without paid generation.
6. Back up and merge Claude Desktop configuration, preserving unrelated settings. Verify the saved entries. Leave browser consent and paid generation testing to the instructor. Report what is installed, test evidence, and remaining account/testing steps. Do not publish, deploy, or invite students.

Completion evidence, October 5, 2026: 409 offline tests passed, four live tests deselected; lint passed. Both generated profiles initialized as real stdio subprocesses, exposed eight tools, displayed the correct workspace, and reported signed out. A read-only review found no important production issues. Claude Desktop's configuration was backed up and both local entries merged; readback confirmed the entries and preserved prior preferences. Browser sign-in, authenticated workspace/key inspection, and any paid image generation remain instructor acceptance steps. No student deployment or publication occurred.

Single-server amendment: add red regressions for one generated entry in either selected cohort and migration of two older entries; change generator, installer and bundled plugin to one entry; update instructions; run focused checks; fully quit Claude, back up and merge the selected 2027 entry, reopen and verify Running. Deployment remains on hold.
