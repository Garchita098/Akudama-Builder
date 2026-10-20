#!/usr/bin/env bash
set -Eeuo pipefail
mkdir -p test-results
save_diagnostics() {
  adb exec-out screencap -p > test-results/screenshot.png 2>/dev/null || true
  adb logcat -d -v time > test-results/logcat.txt 2>/dev/null || true
}
trap save_diagnostics EXIT
APK=$(find apk -type f -name '*.apk' -print -quit)
if [[ -z "$APK" ]]; then
  echo "No APK found in downloaded artifact"
  find . -maxdepth 3 -type f | head -50
  exit 1
fi
adb install -r "$APK"
PACKAGE=$("$ANDROID_HOME/build-tools/35.0.0/aapt" dump badging "$APK" | sed -n "s/^package: name='\([^']*\)'.*/\1/p" | head -n 1)
test -n "$PACKAGE"
echo "Package: $PACKAGE"
adb logcat -c
adb shell monkey -p "$PACKAGE" -c android.intent.category.LAUNCHER 1 | tee test-results/launch.txt
sleep 8
adb shell pidof "$PACKAGE" | tee test-results/pid.txt
adb logcat -d -v time > test-results/logcat.txt
if grep -A 25 'FATAL EXCEPTION' test-results/logcat.txt | grep -F "Process: $PACKAGE,"; then
  echo "App crashed during smoke test"
  exit 1
fi
echo "Smoke test passed: $PACKAGE"
