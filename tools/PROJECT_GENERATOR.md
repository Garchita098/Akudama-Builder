# Android Project Generator

The **Generate Android Project** GitHub Actions workflow creates a new native Android (Java) project automatically, commits it and dispatches the existing APK build and emulator smoke tests.

## Phone workflow

1. Open **Actions → Generate Android Project → Run workflow**.
2. Enter a unique slug, such as `dungeon`, and a title, such as `Living Dungeon`.
3. Run workflow and wait for the generation job.
4. Open **Build and Test Android APK** to watch the requested project's build, then download `Akudama-APK-dungeon` from the successful build.

Generated files:
- `projects/<slug>/settings.gradle`
- `projects/<slug>/build.gradle`
- `projects/<slug>/app/build.gradle`
- `projects/<slug>/app/src/main/AndroidManifest.xml`
- `projects/<slug>/app/src/main/java/com/akudama/<slug>/MainActivity.java` (underscores removed in the package)
- `tests/<slug>.json`

To generate a project locally: `python3 tools/create_project.py --slug dungeon --title "Living Dungeon"`.

**Limits:** This is a functional **starter application**, not a game generator or an AI coder. It creates a basic screen and smoke tests. The user or coding assistant adds project functionality afterward. Duplicate slugs are rejected to avoid overwriting an existing project. Generated projects do not modify Akudama Studio.

**Security:** The workflow uses the short-lived GitHub Actions token and does not require a personal access token in the Android application. On a repository with protected branches, the commit may need a PR-based workflow instead.
