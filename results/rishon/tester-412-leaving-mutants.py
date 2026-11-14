"""Tester 412 (audit-304 N2): leaving_weight of det_sector_structure for production and for my own leaving operators, run on a given src tree
(argv[1] = tree label, PYTHONPATH selects HEAD or working tree).  Mutants are injected by monkeypatching operators / constants (no source edits)."""
import sys, json, subprocess, numpy as np
from su2plaq.rishon import operators as O, physical as ph
label = sys.argv[1]
out = {"label": label, "commit": subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()}
b = ph.rishon_basis()
d = ph.det_sector_structure(b)
out["production"] = {"leaving_weight": d["leaving_weight"], "blocks": d["blocks"], "rank": d["charge_change_rank"]}
codes = O.inner_codes(); real = O.h_magnetic_inner
nib0 = codes & 15
def with_extra(M):
    O.h_magnetic_inner = lambda: real() + M
    try: return ph.det_sector_structure(b)["leaving_weight"]
    finally: O.h_magnetic_inner = real
n = len(codes); pos = {int(c): i for i, c in enumerate(codes)}
# (B) nibble0 3 -> 5 on inner codes (amplitude 1), target is an inner code
MB = np.zeros((n, n), complex)
for i, c in enumerate(codes):
    if (c & 15) == 3: MB[pos[int((c & ~15) | 5)], i] = 1.0
# (C) every inner code -> one fixed inner code
MC = np.zeros((n, n), complex); MC[17, :] = 1.0
# (D) nibble0 6 -> 9 (both in sector), amplitude 1
MD = np.zeros((n, n), complex)
for i, c in enumerate(codes):
    if (c & 15) == 6: MD[pos[int((c & ~15) | 9)], i] = 1.0
out["mutant_B_HB_plus_nibble0_3to5"] = with_extra(MB)
out["mutant_C_HB_plus_all_to_one_code"] = with_extra(MC)
out["mutant_D_HB_plus_nibble0_6to9"] = with_extra(MD)
res = {}; kc = ph.closed_indices(b); ph.closed_indices = lambda bb: kc   # closed_indices reads CODE_A
for A, Bc in ((5, 10), (6, 9), (3, 5)):
    ph.CODE_A, ph.CODE_B = A, Bc
    try: res[f"det_nibbles_{A}_{Bc}"] = ph.det_sector_structure(b)["leaving_weight"]
    except Exception as e: res[f"det_nibbles_{A}_{Bc}"] = f"EXC {e!r}"
ph.CODE_A, ph.CODE_B = 3, 12
out["mutant_det_nibble_pairs"] = res
print(json.dumps(out, indent=1))
json.dump(out, open(f"results/rishon/tester-412-leaving-mutants-{label}.json", "w"), indent=1)
