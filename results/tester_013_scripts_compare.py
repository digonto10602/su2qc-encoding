import json, math, pathlib, re, sys
S = pathlib.Path("/tmp/claude-1000/-home-digimonk-Projects-su2qc-encoding/6f24cad7-b2eb-5b02-89d1-34310bbf63e6/scratchpad")
RP = pathlib.Path("/home/digimonk/Projects/su2qc-encoding/results")
O = S / "reg/out"
pairs = [("adv1.json", S / "adv1.json"), ("adv2.json", S / "adv2.json"), ("adv3.json", S / "adv3.json"), ("adv3_agree.json", S / "adv3_agree.json"),
         ("adv4.json", S / "adv4.json"), ("adv5.json", S / "adv5.json"), ("adv6.json", S / "adv6.json"), ("adv7.json", S / "adv7.json"),
         ("m0_step07_check1.json", RP / "m0_step07_check1.json"), ("m0_step07_recheck_AB.json", RP / "m0_step07_recheck_AB.json"),
         ("m0_step07_recheck_aer.json", RP / "m0_step07_recheck_aer.json"), ("m0_step07_recheck_C.json", RP / "m0_step07_recheck_C.json"),
         ("m0_step07_recheck_timing.json", RP / "m0_step07_recheck_timing.json"), ("m0_step07_recheck_timingb.json", RP / "m0_step07_recheck_timingb.json"),
         ("t1.json", S / "t1.json"), ("t2.json", S / "t2.json"), ("t3.json", S / "t3.json"), ("t4.json", S / "t4.json"), ("t4_table.json", S / "t4_table.json"),
         ("tester_m0_step03_algebra.json", RP / "tester_m0_step03_algebra.json"), ("out1.json", S / "out1.json"), ("out2.json", S / "out2.json")]
TIMEKEYS = re.compile(r"sec|time|wall|_s$|^t_(build|run|eval)|timestamp|elapsed|ms$", re.I)
diffs = []
def cmp(a, b, path, key=""):
    if TIMEKEYS.search(key): return
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b: diffs.append((path + "/" + k, "key missing in " + ("new" if k not in a else "old"))); continue
            cmp(a[k], b[k], path + "/" + k, k)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b): diffs.append((path, f"len {len(a)} vs {len(b)}")); return
        for i, (x, y) in enumerate(zip(a, b)): cmp(x, y, f"{path}[{i}]", key)
    elif isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool) and not isinstance(b, bool):
        if a == b or (isinstance(a, float) and isinstance(b, float) and math.isnan(a) and math.isnan(b)): return
        # tiny numbers: absolute 1e-13; else relative 1e-6
        if abs(a - b) <= 1e-13 or abs(a - b) <= 1e-6 * max(abs(a), abs(b)): return
        diffs.append((path, f"{a!r} vs {b!r}"))
    elif a != b:
        # strings containing numbers with timing: strip floats ending with s
        diffs.append((path, f"{str(a)[:80]!r} vs {str(b)[:80]!r}"))
tot = 0
for new, old in pairs:
    n, o = O / new, pathlib.Path(old)
    if not n.exists(): print(f"{new}: NEW FILE MISSING"); continue
    if not o.exists(): print(f"{new}: OLD MISSING {o}"); continue
    diffs.clear()
    try:
        cmp(json.loads(n.read_text()), json.loads(o.read_text()), "")
    except Exception as e:
        print(new, "ERR", e); continue
    print(f"{new}: {len(diffs)} differences")
    for d in diffs[:8]: print("    ", d)
    tot += len(diffs)
print("TOTAL", tot)
