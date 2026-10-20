# Akudama DevTools

## Batch GitHub commits

`tools/batch_commit.py` writes up to 150 UTF-8 text files in **one atomic Git commit** through the GitHub Git Data API. It is intended for authorized development and requires environment variables:

- `GITHUB_REPOSITORY=Garchita098/Akudama-Builder`
- `GITHUB_TOKEN`: a token with **Contents: Read and write** for this repository.

Example `changes.json`:

```json
{
  "message": "Add application screens",
  "branch": "main",
  "files": {
    "projects/demo/README.md": "Demo application\n",
    "tests/demo.json": "{\"steps\":[]}"
  }
}
```

Run: `python3 tools/batch_commit.py changes.json`.

Only provide non-secret source files to the helper. Do not commit a token, API key, or passwords. The helper uses a non-forced Git ref update, so concurrent changes are not overwritten by force.

**ChatGPT GitHub connection** can use equivalent Git tree and commit operations directly, without requiring a token to be copied into the chat.

## Build diagnostics

Every Android build now attempts to upload `Akudama-Build-Diagnostics-<project>` containing:

- `build.log`: complete Gradle output.
- `summary.md`: extracted failure and compiler error lines.

The diagnostics upload runs even after an unsuccessful Gradle build. Emulator results remain in `Android-Emulator-Diagnostics-<project>`, when that job runs.

Build reports identify likely errors but do not automatically correct code or retry builds. Fixes remain deliberate edits followed by another workflow run.
