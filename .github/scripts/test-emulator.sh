#!/usr/bin/env bash
set -Eeuo pipefail
mkdir -p test-results
APK=$(find apk -type f -name '*.apk' -print -quit)
[[ -n "$APK" ]] || { echo "::error::No APK found"; exit 1; }
adb install -r "$APK"
PACKAGE=$("$ANDROID_HOME/build-tools/35.0.0/aapt" dump badging "$APK" | sed -n "s/^package: name='\([^']*\)'.*/\1/p" | head -n 1)
[[ -n "$PACKAGE" ]] || { echo "::error::Could not read APK package"; exit 1; }
adb logcat -c
adb shell monkey -p "$PACKAGE" -c android.intent.category.LAUNCHER 1 > test-results/launch.txt
sleep 5
# UIAutomator needs an idle window; dungeon repaints every 450ms.
# Relaunch its Activity with simulation disabled for deterministic UI controls testing.
if [ "$PACKAGE" = "com.akudama.dungeon" ]; then
  adb shell am force-stop "$PACKAGE"
  adb shell am start -n "$PACKAGE/.MainActivity" --ez ui_test true > test-results/test-mode-launch.txt
  sleep 3
fi
adb shell pidof "$PACKAGE" > test-results/pid-before.txt || { echo "::error::App failed to stay running"; exit 1; }
python3 .github/scripts/ui-scenarios.py
adb shell pidof "$PACKAGE" > test-results/pid-after.txt || { echo "::error::App process exited"; exit 1; }
if grep -A 25 'FATAL EXCEPTION' test-results/logcat.txt | grep -F "Process: $PACKAGE,"; then
  echo "::error::App crashed during UI scenario"
  exit 1
fi
echo "Scenario passed for $PACKAGE"
