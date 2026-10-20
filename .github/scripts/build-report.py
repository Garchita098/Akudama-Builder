#!/usr/bin/env python3
"""Summarize Android build output for humans and coding assistants."""
from pathlib import Path
import re
p=Path("build-results/build.log")
lines=p.read_text(errors="replace").splitlines() if p.exists() else []
patterns=[r"^FAILURE:",r"^\* What went wrong:",r"^Execution failed for task",r"^> .*(failed|error|not found|could not)",r"^.*\.java:\d+: error:",r"^.*\.kt:\d+:\d+.*error:",r"^\* Exception is:",r"^BUILD (FAILED|SUCCESSFUL)"]
hits=[]
for i,line in enumerate(lines):
    if any(re.search(pattern,line,re.I) for pattern in patterns):
        hits.append((i+1,line.strip()[:350]))
output=["# Akudama build diagnostics","","## Result",""]
outcome="FAILED" if any("BUILD FAILED" in x or "FAILURE:" in x for x in lines) else ("SUCCESS" if any("BUILD SUCCESSFUL" in x for x in lines) else "UNKNOWN")
output.append("**"+outcome+"**")
output.extend(["","## Key error lines",""])
if hits:
    output.extend(f"- Line {n}: `{s.replace(chr(96),chr(39))}`" for n,s in hits[:35])
else: output.append("No recognized Gradle errors. Inspect the full build.log.")
output.extend(["","Full output: build.log. Report is heuristic; consult logs for context."])
Path("build-results").mkdir(exist_ok=True)
Path("build-results/summary.md").write_text("\n".join(output)+"\n")
print("\n".join(output[:45]))
