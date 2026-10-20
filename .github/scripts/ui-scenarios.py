#!/usr/bin/env python3
"""Run declarative Android UI checks from tests/<project>.json."""
import json, os, re, subprocess, sys, time
from pathlib import Path
import xml.etree.ElementTree as ET

out=Path("test-results");out.mkdir(exist_ok=True)
steps=json.loads(Path(os.environ["TEST_CONFIG"]).read_text())["steps"]
report=["# Android UI checks",""]
def adb(*args,check=True):
    return subprocess.run(["adb",*args],capture_output=True,text=True,check=check)
def capture(label):
    subprocess.run(["adb","exec-out","screencap","-p"],stdout=(out/(label+".png")).open("wb"),check=True)
    adb("shell","uiautomator","dump","/sdcard/window.xml")
    xml=subprocess.run(["adb","exec-out","cat","/sdcard/window.xml"],capture_output=True,check=True).stdout
    (out/(label+".xml")).write_bytes(xml)
    root=ET.fromstring(xml)
    return root
def recover_system_dialog(root):
    """Dismiss Android emulator launcher ANR, not application failures."""
    if not any("Quickstep isn't responding" in n.get("text","") for n in root.iter("node")):
        return False
    buttons=[n for n in root.iter("node") if n.get("resource-id")=="android:id/aerr_close"]
    if not buttons: raise AssertionError("Quickstep ANR dialog lacks Close app")
    coords=re.findall(r"\d+",buttons[0].get("bounds",""))
    if len(coords)!=4: raise AssertionError("Quickstep ANR close button missing bounds")
    x1,y1,x2,y2=map(int,coords)
    adb("shell","input","tap",str((x1+x2)//2),str((y1+y2)//2))
    time.sleep(3)
    return True
def nodes(root):
    return list(root.iter("node"))
def matching(root,text):
    t=text.casefold()
    return [n for n in nodes(root) if t in (n.get("text","")+" "+n.get("content-desc","")).casefold()]
previous=None
try:
    for i,step in enumerate(steps,1):
        action=step["action"]
        root=capture(f"step-{i:02d}-before")
        if recover_system_dialog(root):
            report.append("- RECOVERED emulator Quickstep ANR dialog")
            root=capture(f"step-{i:02d}-retry")
        if action=="tap_text":
            matches=[n for n in matching(root,step["text"]) if n.get("enabled")=="true" and n.get("clickable")=="true"]
            if not matches: raise AssertionError("Clickable control not found: "+step["text"])
            nums=re.findall(r"\d+",matches[0].get("bounds",""))
            if len(nums)!=4: raise AssertionError("Invalid bounds")
            x1,y1,x2,y2=map(int,nums)
            adb("shell","input","tap",str((x1+x2)//2),str((y1+y2)//2))
            time.sleep(float(step.get("wait",2)))
            previous=ET.tostring(root)
        elif action=="assert_text":
            if not matching(root,step["text"]): raise AssertionError("Expected text missing: "+step["text"])
        elif action=="assert_changed":
            if previous is None or previous==ET.tostring(root): raise AssertionError("UI tree did not change after tap")
        elif action=="wait":
            time.sleep(min(float(step.get("seconds",2)),30))
        else: raise ValueError("Unknown action: "+action)
        report.append(f"- PASS step {i}: {action} {step.get('text','')}")
    capture("final")
except Exception as e:
    report.append(f"- FAIL step {i}: {e}")
    print(f"::error::{e}",file=sys.stderr)
    raise
finally:
    (out/"report.md").write_text("\n".join(report)+"\n")
    subprocess.run(["adb","logcat","-d","-v","time"],stdout=(out/"logcat.txt").open("w"))
