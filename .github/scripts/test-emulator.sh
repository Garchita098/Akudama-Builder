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

# Strict test for the current demo project.
# Update expected labels when building a different app.
export EXPECT_BUTTON_TEXT="ПРОВЕРИТЬ"
export EXPECT_AFTER_TEXT="Работает!"
XY=$(python3 - <<'PY'
import os, re, sys, xml.etree.ElementTree as ET
root=ET.parse('test-results/before-tap.xml').getroot()
target=os.environ['EXPECT_BUTTON_TEXT'].casefold()
for node in root.iter('node'):
    a=node.attrib
    if a.get('clickable')!='true' or a.get('enabled')!='true':
        continue
    text=(a.get('text','')+' '+a.get('content-desc','')).casefold()
    if target not in text:
        continue
    coords=[int(v) for v in re.findall(r'\d+',a.get('bounds',''))]
    if len(coords)==4:
        x1,y1,x2,y2=coords
        if x2>x1 and y2>y1:
            print(f'{(x1+x2)//2} {(y1+y2)//2}')
            sys.exit(0)
sys.exit(2)
PY
) || { echo "::error::Expected clickable button not found"; exit 1; }
read -r X Y <<< "$XY"
adb shell input tap "$X" "$Y"
sleep 3
adb shell pidof "$PACKAGE" > test-results/pid-after.txt
capture after-tap
test -s test-results/after-tap.xml || { echo "::error::Missing UI after tap"; exit 1; }
python3 - <<'PY'
import os,sys,xml.etree.ElementTree as ET
def tree(path):
    return '\n'.join((n.get('text','')+' '+n.get('content-desc','')) for n in ET.parse(path).getroot().iter('node'))
before=tree('test-results/before-tap.xml')
after=tree('test-results/after-tap.xml')
expected=os.environ['EXPECT_AFTER_TEXT']
if expected.casefold() not in after.casefold() or before==after:
    print('ERROR: Expected UI text not displayed or UI tree did not change')
    sys.exit(1)
print('Verified UI changed and expected text appeared')
PY
printf -- '- ✅ Button found, tapped, and expected UI change verified\n' >> "$REPORT"

adb logcat -d -v time > test-results/logcat.txt
if grep -A 25 'FATAL EXCEPTION' test-results/logcat.txt | grep -F "Process: $PACKAGE,"; then
  printf -- '- ❌ Application crash found in logcat\n' >> "$REPORT"
  exit 1
fi
printf -- '- ✅ No matching application crash found in logcat\n' >> "$REPORT"
echo "UI smoke test passed: $PACKAGE"
