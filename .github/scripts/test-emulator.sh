#!/usr/bin/env bash
set -Eeuo pipefail
mkdir -p test-results
REPORT=test-results/report.md
printf '# Android emulator UI smoke test\n\n' > "$REPORT"
capture() {
  local label="$1"
  adb exec-out screencap -p > "test-results/${label}.png" 2>/dev/null || true
  adb shell uiautomator dump /sdcard/window.xml >/dev/null 2>&1 || true
  adb exec-out cat /sdcard/window.xml > "test-results/${label}.xml" 2>/dev/null || true
}
diagnostics() {
  adb logcat -d -v time > test-results/logcat.txt 2>/dev/null || true
  capture final
}
trap diagnostics EXIT
APK=$(find apk -type f -name '*.apk' -print -quit)
if [[ -z "$APK" ]]; then
  echo "No APK found"
  exit 1
fi
adb install -r "$APK"
PACKAGE=$("$ANDROID_HOME/build-tools/35.0.0/aapt" dump badging "$APK" | sed -n "s/^package: name='\\([^']*\\)'.*/\\1/p" | head -n 1)
test -n "$PACKAGE"
printf 'Package: `%s`\n\n' "$PACKAGE" >> "$REPORT"
adb logcat -c
adb shell monkey -p "$PACKAGE" -c android.intent.category.LAUNCHER 1 > test-results/launch.txt
sleep 5
adb shell pidof "$PACKAGE" > test-results/pid-before.txt
capture before-tap
printf -- '- ✅ Application launched and stayed running\n' >> "$REPORT"

# Inspect the foreground UI. Select the first enabled clickable control in
# the app's content area (not the status or navigation bars).
XY=$(python3 - <<'PY'
import re, xml.etree.ElementTree as ET
try:
    root=ET.parse('test-results/before-tap.xml').getroot()
    candidates=[]
    for node in root.iter('node'):
        a=node.attrib
        if a.get('clickable')!='true' or a.get('enabled')!='true':
            continue
        coords=[int(v) for v in re.findall('[0-9]+', a.get('bounds',''))]
        if len(coords)!=4:
            continue
        x1,y1,x2,y2=coords
        if x2<=x1 or y2<=y1 or y1<100:
            continue
        candidates.append(((x2-x1)*(y2-y1), (x1+x2)//2, (y1+y2)//2, a.get('text','')))
    if candidates:
        _,x,y,label=sorted(candidates)[0]
        print(f'{x} {y}')
except Exception as e:
    print(f'UI inspection failed: {e}',file=__import__('sys').stderr)
PY
)
if [[ "$XY" =~ ^[0-9]+\ [0-9]+$ ]]; then
  read -r X Y <<< "$XY"
  echo "Tapping clickable UI control at ($X, $Y)"
  adb shell input tap "$X" "$Y"
  sleep 3
  adb shell pidof "$PACKAGE" > test-results/pid-after.txt
  capture after-tap
  printf -- '- ✅ Clickable control tapped at (%s, %s); process remains alive\n' "$X" "$Y" >> "$REPORT"
else
  printf -- '- ℹ️ No accessible clickable UI control found; tap test skipped\n' >> "$REPORT"
fi

adb logcat -d -v time > test-results/logcat.txt
if grep -A 25 'FATAL EXCEPTION' test-results/logcat.txt | grep -F "Process: $PACKAGE,"; then
  printf -- '- ❌ Application crash found in logcat\n' >> "$REPORT"
  exit 1
fi
printf -- '- ✅ No matching application crash found in logcat\n' >> "$REPORT"
echo "UI smoke test passed: $PACKAGE"
