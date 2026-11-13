"""Tester 408: independent check of the raw-bit facts of compress/specs/lsh-structure.json.
Enumeration of inner codes from the LSH rules written from scratch; coupling/partner from the production H_B
(entries of the 433x433 magnetic Hamiltonian), NOT from the Lean tables or loop.py."""
import json, subprocess, itertools, sys
import numpy as np
sys.path.insert(0, "src")
from su2plaq.encodings.lsh import LSH

bit = lambda x, k: (x >> k) & 1
def site(x, c): return (x >> (3 * c)) & 7
def N(s):   # bit0=l12 (l_pn), bit1=l23 (l_nv), bit2=l31 (l_vp)
    l12, l23, l31 = s & 1, (s >> 1) & 1, (s >> 2) & 1
    return (l31 + l12, l12 + l23, l23 + l31)
valid = lambda s: N(s)[0] <= 1 and N(s)[1] <= 1
codes = [x for x in range(4096)
         if all(valid(site(x, c)) for c in range(4))
         and all(N(site(x, c))[1] == N(site(x, (c + 1) % 4))[0] for c in range(4))]
out = {"n_inner": len(codes), "site_valid": [s for s in range(8) if valid(s)]}
enc = LSH()
prod_codes = sorted(int(c) for c in enc.inner_codes())
out["codes_match_production"] = (codes == prod_codes)
out["codes_match_lean_text"] = None
txt = open("lean/Su2Plaq/LSH/Circuit.lean").read()
import re
lean_codes = [int(v) for v in re.search(r"def lshInnerCodes : List Nat := \[([0-9, ]+)\]", txt).group(1).split(",")]
out["codes_match_lean_text"] = (lean_codes == codes)

# coupling/partner from H_B
HB = enc.h_magnetic()
pc = [int(c) for c in enc._codes]
idx = {c: i for i, c in enumerate(pc)}
dark = lambda x: any(bit(x, 3*c+1) and bit(x, 3*c+2) for c in range(4))
partner, coup = {}, {}
for x in codes:
    # use outer part from any physical state with data code x (take the first)
    cand = [c for c in pc if (c & 0xFFF) == x]
    c = cand[0]; i = idx[c]
    row = np.nonzero(np.abs(HB[:, i]) > 1e-12)[0]
    offdiag = [j for j in row if j != i]
    # each non-dark code has exactly one partner state in the same outer pattern
    sameouter = [j for j in offdiag if (pc[j] >> 12) == (c >> 12)]
    assert len(sameouter) == len(offdiag), "H_B changes outer bits"
    if dark(x):
        assert len(offdiag) == 0, ("dark code has off-diagonal", x)
        continue
    assert len(offdiag) == 1, (x, len(offdiag))
    partner[x] = pc[offdiag[0]] & 0xFFF
    coup[x] = HB[offdiag[0], i]
out["n_bright"] = len(partner); out["n_dark"] = len(codes) - len(partner)
out["dark_iff_site_AND"] = all(dark(x) == (x not in partner) for x in codes)
out["n_dark_by_rule"] = sum(dark(x) for x in codes)
# coupling vs y-weight
ratio = {}
for x in partner:
    sy = sum(bit(x, 3*c+1) for c in range(4)); sz = sum(bit(x, 3*c+2) for c in range(4))
    ratio.setdefault(sy, set()).add(round(float(np.real(coup[x])), 10)); assert abs(coup[x].imag) < 1e-12 and sy == sz and sy <= 2
out["coupling_by_ysum"] = {str(k): sorted(v) for k, v in sorted(ratio.items())}
vals = {k: list(v)[0] for k, v in ratio.items()}
out["coupling_ratio_to_k_pattern(-2,1,-1/2)"] = [vals[0]/-2, vals[1]/1, vals[2]/-0.5]
out["one_value_per_ysum"] = all(len(v) == 1 for v in ratio.values())
# parity invariant
out["y_parity_invariant"] = all(sum(bit(x,3*c+1) for c in range(4)) % 2 == sum(bit(partner[x],3*c+1) for c in range(4)) % 2 for x in partner)
out["parity_equals_flag(sy odd <-> K>0)"] = all((sum(bit(x,3*c+1) for c in range(4)) % 2 == 1) == (np.real(coup[x]) > 0) for x in partner)
# link bit two ways
out["link_bit_two_ways"] = all((bit(x,3*c)^bit(x,3*c+1)) == (bit(x,3*((c+1)%4))^bit(x,3*((c+1)%4)+2)) for x in codes for c in range(4))
# move per site
mv = {0: set(), 1: set()}
for x in partner:
    d = x ^ partner[x]
    for c in range(4):
        w = bit(x,3*c+1) ^ bit(x,3*c+2); mv[w].add((d >> (3*c)) & 7)
out["move_per_site"] = {"w0": sorted(mv[0]), "w1": sorted(mv[1])}
out["n_distinct_differences"] = len({x ^ partner[x] for x in partner})
# the json
d = json.load(open("compress/specs/lsh-structure.json")); f = {e["name"]: e["value"] for e in d["facts"]}
out["json_agrees"] = {
 "card_inner_codes": f["card_inner_codes"] == out["n_inner"],
 "card_bright": f["card_bright_codes"] == out["n_bright"], "card_dark": f["card_dark_codes"] == out["n_dark"],
 "site_valid_list": f["site_valid_list"] == out["site_valid"],
 "coupling_by_y_weight": {k: v for k, v in f["coupling_by_y_weight"].items()} == {"0": -4, "1": 2, "2": -1},
 "move_per_site": f["move_per_site"] == {"w0": 1, "w1": 6} and out["move_per_site"] == {"w0": [1], "w1": [6]},
 "eight_differences": f["eight_differences"] == out["n_distinct_differences"],
 "card_states": f["card_states_lsh"] == len(pc),
 "n_outer_patterns": f["n_outer_site_patterns"] == len({c >> 12 for c in pc}),
}
# coupling_by_y_weight ints = 2K, and K in H_B units: ratio (-2,1,-1/2) up to constant
out["2K_ratios_in_json"] = [f["coupling_by_y_weight"][k] for k in "012"]
# provenance sha of lean files
import hashlib
out["lean_sha_match"] = {k: hashlib.sha256(open(k,'rb').read()).hexdigest() == v for k, v in d["provenance"]["lean_files"].items()}
out["commit"] = subprocess.check_output(["git","rev-parse","--short","HEAD"]).decode().strip()
json.dump(out, open("results/lsh_tester/tester-408-structure-facts.json","w"), indent=1, default=str)
print(json.dumps(out, indent=1, default=str))
