#!/usr/bin/env bash
# Claude Code status line: saves the raw status JSON (incl. rate_limits, if the CLI sends them) to
# scratch/usage/statusline.json so the coordinator can read usage % and reset times; prints a short line.
d=/home/digimonk/Projects/su2qc-encoding/scratch/usage
mkdir -p "$d"
in=$(cat)
printf '%s\n' "$in" > "$d/statusline.json.tmp" && mv "$d/statusline.json.tmp" "$d/statusline.json"
printf '%s' "$in" | python3 -c '
import json,sys,datetime
try: j=json.load(sys.stdin)
except Exception: print("su2qc"); sys.exit()
r=j.get("rate_limits") or {}
out=[]
for k in ("five_hour","seven_day"):
    v=r.get(k) or {}
    p=v.get("used_percentage"); t=v.get("resets_at")
    if p is not None:
        s=f"{k}: {p:.0f}%"
        if t:
            try: s+=" (reset "+datetime.datetime.fromtimestamp(float(t)).strftime("%a %H:%M")+")"
            except Exception: s+=f" (reset {t})"
        out.append(s)
print(" | ".join(out) if out else (j.get("model",{}) or {}).get("display_name","su2qc"))'
