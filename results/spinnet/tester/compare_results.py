"""Compare regenerated results JSON (scratch) against committed results/spinnet/*.json; report numeric diffs."""
import json, sys, math, pathlib
new, old = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
def walk(a, b, path, out):
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b: out.append((path + "/" + k, "missing", None)); continue
            walk(a[k], b[k], path + "/" + k, out)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b): out.append((path, "len", (len(a), len(b)))); return
        for i, (x, y) in enumerate(zip(a, b)): walk(x, y, f"{path}[{i}]", out)
    elif isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool):
        if a != b: out.append((path, "num", (a, b, abs(a - b))))
    elif a != b: out.append((path, "val", (str(a)[:60], str(b)[:60])))
for n in ("UE", "UB", "step"):
    out = []; walk(json.load(open(new / f"{n}.json")), json.load(open(old / f"{n}.json")), "", out)
    print(n, len(out), "differences")
    for o in out[:40]: print("  ", o)

print("\n=== filtered (ignore timing, file paths/sha, provenance) ===")
IGN = ("seconds", "/files/", "provenance", "wall_seconds")
for n in ("UE", "UB", "step"):
    out = []; walk(json.load(open(new / f"{n}.json")), json.load(open(old / f"{n}.json")), "", out)
    keep = [o for o in out if not any(s in o[0] for s in IGN)]
    nums = [o for o in keep if o[1] == "num"]
    other = [o for o in keep if o[1] != "num"]
    print(n, "non-ignored:", len(keep), "numeric:", len(nums), "non-numeric:", len(other))
    for o in other: print("   NONNUM", o)
    big = sorted(nums, key=lambda o: -o[2][2])[:5]
    for o in big: print("   max abs diff", o[0], o[2])
    rel = [o for o in nums if abs(o[2][1]) > 1e-9 and o[2][2] / abs(o[2][1]) > 1e-9]
    print("   numeric diffs with rel > 1e-9 on |old|>1e-9:", len(rel))
    for o in rel: print("   REL", o)
    ints = [o for o in nums if float(o[2][0]).is_integer() and float(o[2][1]).is_integer()]
    print("   integer-valued numeric diffs:", len(ints))
