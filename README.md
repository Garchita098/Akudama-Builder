# Akudama Builder

Android APK builds and emulator UI tests in GitHub Actions.

## Projects

- Existing demo: `project.zip`, test scenario `tests/legacy.json`, project name `legacy`.
- Additional project: `projects/NAME/project.zip`, test scenario `tests/NAME.json`.
- Use short project names with letters, digits, underscores or dashes, for example `chess` or `notes`.

To build a named project, open **Actions → Build and Test Android APK → Run workflow**, enter `NAME` in the `project` field and start the workflow.

Changes to the legacy `project.zip`, workflow and test scripts still trigger a default `legacy` build automatically. Other projects are built on demand (not every push).

## UI test scenario

Example `tests/notes.json`:

```json
{
  "steps": [
    {"action": "assert_text", "Notes"},
    {"action": "tap_text", "New note"},
    {"action": "assert_text", "Save"},
    {"action": "assert_changed"}
  ]
}
```

Supported actions: `assert_text`, `tap_text`, `assert_changed`, `wait` (up to 30 seconds).

`tap_text` locates an accessible enabled clickable control using its text or content description. `assert_changed` checks the UI tree against the screen captured immediately before the last tap. For custom-drawn interfaces without accessibility labels, other test strategies will be needed.

Successful runs upload an APK artifact and emulator diagnostics including a Markdown report, screenshots and logcat. A green check confirms only the configured checks, not the entire application.

## Project ZIP requirements

The ZIP must contain an Android Gradle project at archive root, with an `app` module producing `app/build/outputs/apk/debug/*.apk`. The current runner uses Java 17, Android SDK 35, and Gradle 8.9. These settings can be expanded per project later.

Debug APKs produced by different build environments are not suitable as a stable release-signing strategy. For seamless installed-app updates, use a persistent release signing key and version-code management.
