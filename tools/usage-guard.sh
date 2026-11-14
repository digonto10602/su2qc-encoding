#!/usr/bin/env bash
# PostToolUse hook (Digonto, 2026-11-13): if Claude plan usage (5-hour or 7-day, from the status-line JSON saved by
# tools/statusline-usage.sh) is >= 95 %, tell the coordinator to save work and schedule a resume at the reset time.
f=/home/digimonk/Projects/su2qc-encoding/scratch/usage/statusline.json
[ -s "$f" ] || exit 0
python3 - "$f" <<'PY'
import json, sys, datetime
try:
    r = json.load(open(sys.argv[1])).get("rate_limits") or {}
except Exception:
    sys.exit(0)
hits = []
for k in ("five_hour", "seven_day"):
    v = r.get(k) or {}
    p, t = v.get("used_percentage"), v.get("resets_at")
    if p is not None and float(p) >= 95:
        when = datetime.datetime.fromtimestamp(float(t)).strftime("%Y-%m-%d %H:%M %Z") if t else "unknown"
        hits.append(f"{k} {float(p):.0f}% (resets {when}, epoch {t})")
if hits:
    msg = ("USAGE GUARD: Claude usage >= 95 %: " + "; ".join(hits) + ". Digonto's rule: stop all agents (TaskStop), "
           "commit + push everything, update STATUS (Next action), then CronCreate a one-shot resume a few minutes after "
           "the LATEST reset time listed, and tell Digonto the time. Do not start new agents.")
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": msg}}))
PY
exit 0
