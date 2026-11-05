import sys, subprocess, json
root = sys.argv[1]
sys.path.insert(0, root + "/src")
from su2plaq.metrics.provenance import provenance
import su2plaq.metrics.provenance as P
p = provenance({"a": 1})
head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=root, capture_output=True, text=True).stdout.strip()
print("root used:", P._ROOT, "| commit", p["git_commit"], "git:", head, "EQUAL" if p["git_commit"] == head else "DIFF", "| dirty", p["git_dirty"])
if len(sys.argv) > 2:
    print(json.dumps(p["versions"]), p["platform"], p["cpu_count"], p["timestamp_utc"], p["seeds"])
