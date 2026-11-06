"""Independent N5/N6 attack hunt. usage: python n5_n6_attacks.py <certdir> <outdir>
Each mutated certificate goes through (a) the bare Lean checker `su2plaq_cert check`, (b) su2plaq.lean.certify.check_certificate,
(c) write_theorem_file (must raise ValueError for every rejected cert; for accepted controls must write)."""
import copy, glob, json, os, subprocess, sys, time, random
sys.path.insert(0, "/home/digimonk/Projects/su2qc-encoding/src")
from su2plaq.lean import certify as C
BIN = "/home/digimonk/Projects/su2qc-encoding/lean/.lake/build/bin/su2plaq_cert"
certdir, outdir = sys.argv[1], sys.argv[2]
os.makedirs(outdir, exist_ok=True)
def load(kind):
    p = sorted(glob.glob(os.path.join(certdir, f"{kind}-o1-*.json")))[0]
    return json.load(open(p))
UE, UB = load("UE"), load("UB")
one = ["1", "0", "0", "0", "0", "0", "0", "0"]
results = []
def run(name, d, expect, theorem=True):
    p = os.path.join(outdir, name + ".json")
    json.dump(d, open(p, "w"), separators=(",", ":"))
    t0 = time.time()
    r = subprocess.run([BIN, "check", p], capture_output=True, text=True)
    line = (r.stdout.strip().splitlines() or [""])[0]
    lean = "ACCEPT" if line == "ACCEPT" else ("REJECT" if line.startswith("REJECT") else "OTHER:" + line + r.stderr[-200:])
    try:
        py = C.check_certificate(p)
        pyst, pyreason = py.status, py.reason
    except Exception as e:  # must never crash
        pyst, pyreason = "EXC", repr(e)
    thm = "n/a"
    if theorem:
        try:
            C.write_theorem_file(p, "atk", os.path.join(outdir, name + ".thm.lean")); thm = "wrote"
        except ValueError as e:
            thm = "refused"
        except Exception as e:
            thm = "EXC:" + repr(e)[:80]
    ok = (lean == expect and (pyst == "certified") == (expect == "ACCEPT") and
          (thm == ("wrote" if expect == "ACCEPT" else "refused")))
    if expect == "REJECT_LEAN_ONLY":  # not used
        pass
    results.append(dict(name=name, expect=expect, lean=lean, lean_reason=line[:150], py=pyst, py_reason=pyreason[:150], thm=thm, ok=ok, s=round(time.time()-t0, 1)))
    print(("OK  " if ok else "BAD ") + name, "| lean:", line[:110], "| py:", pyst, "| thm:", thm, flush=True)
def mut(base): return copy.deepcopy(base)

# ---------- controls
run("ctl_UE_unchanged", mut(UE), "ACCEPT")
d = mut(UE); import random as R; rr = R.Random(1)
for st in d["states"]: rr.shuffle(st["terms"])
rr.shuffle(d["states"])
run("ctl_UE_shuffled_term_and_state_order", d, "ACCEPT")
# ---------- A. fake orthonormal non-physical states (computational basis) with a UE-looking target
d = mut(UE); n = len(d["states"])
d["states"] = [{"k": k, "label": "fake", "terms": [{"code": k, "c": one}]} for k in range(n)]
run("A1_fake_computational_basis_states", d, "REJECT")
d = mut(UE)
d["states"] = [{"k": k, "label": "fake", "terms": [{"code": 5**4 + k, "c": one}]} for k in range(n)]
run("A2_fake_states_shifted_codes", d, "REJECT")
# A3: physical subspace rotated: pairs (2m,2m+1) -> (s_a+s_b)/sqrt2 ... use exact: rotation by 90deg = swap with sign (still orthonormal, physical)
d = mut(UE)
sa, sb = d["states"][0]["terms"], d["states"][1]["terms"]
def neg(c): return [("-" + x) if x not in ("0",) and not x.startswith("-") else (x[1:] if x.startswith("-") else x) for x in c]
d["states"][0]["terms"] = copy.deepcopy(sb)
d["states"][1]["terms"] = [{"code": t["code"], "c": neg(t["c"])} for t in sa]
run("A3_physical_rotated_90deg_pair", d, "REJECT")
# ---------- B. physical states permuted
d = mut(UE); s = d["states"]; s[0]["terms"], s[1]["terms"] = s[1]["terms"], s[0]["terms"]
run("B1_swap_contents_of_states_0_1", d, "REJECT")
d = mut(UE); s = d["states"]; s[0]["k"], s[1]["k"] = s[1]["k"], s[0]["k"]
run("B2_swap_k_fields_of_states_0_1", d, "REJECT")
d = mut(UE); d["states"] = d["states"][::-1]
for i, st in enumerate(d["states"]): st["k"] = i
run("B3_reverse_all_states_renumbered", d, "REJECT")
d = mut(UE); s = d["states"]; perm = list(range(len(s))); R.Random(2).shuffle(perm)
d["states"] = [{"k": k, "label": s[perm[k]].get("label"), "terms": s[perm[k]]["terms"]} for k in range(len(s))]
run("B4_random_permutation_of_all_states", d, "REJECT")
# ---------- C. one state replaced / modified
d = mut(UE); d["states"][5]["terms"] = copy.deepcopy(d["states"][6]["terms"])
run("C1_state5_replaced_by_copy_of_state6", d, "REJECT")
for k in (0, 50, 200, 432):
    d = mut(UE); d["states"][k]["terms"] = [{"code": t["code"], "c": neg(t["c"])} for t in d["states"][k]["terms"]]
    run(f"C2_state{k}_sign_flipped", d, "REJECT")
# state replaced by a different physical state's multiple (norm-preserving, i * psi)
d = mut(UE)
def mul_i(c):  # (a + b i + ...) * i = -b + a i ...; components order a,b,c,d,e,f,g,h = 1, i, sqrt2, i sqrt2, sqrt3, i sqrt3, sqrt6, i sqrt6
    from fractions import Fraction as F
    v = [F(x) for x in c]; out = []
    for j in range(0, 8, 2): out += [-v[j+1], v[j]]
    return [str(x) if x.denominator == 1 else f"{x.numerator}/{x.denominator}" for x in out]
d["states"][50]["terms"] = [{"code": t["code"], "c": mul_i(t["c"])} for t in d["states"][50]["terms"]]
run("C3_state50_times_i", d, "REJECT")
d = mut(UE); d["states"][7]["terms"] = d["states"][7]["terms"][:-1] if len(d["states"][7]["terms"]) > 1 else d["states"][7]["terms"]
run("C4_state7_term_deleted", d, "REJECT")
d = mut(UE); d["states"][7]["terms"].append({"code": 0, "c": ["0"]*8})
run("C5_zero_coefficient_term_added", d, "REJECT")
d = mut(UE); t = d["states"][7]["terms"][0]; 
d["states"][7]["terms"] = d["states"][7]["terms"][1:] + [{"code": t["code"], "c": t["c"]}]  # same data, rotated order => control
run("ctl_C6_term_order_rotated", d, "ACCEPT")
d = mut(UE); d["states"].pop(); run("C7_432_states", d, "REJECT")
d = mut(UE); d["states"].append(copy.deepcopy(d["states"][0])); d["states"][-1]["k"] = 433
run("C8_434_states", d, "REJECT")
# ---------- D. different target
d = mut(UE); d["target"]["kind"] = "UB"; run("D1_UE_blocks_labelled_UB", d, "REJECT")
d = mut(UE); d["target"]["kind"] = "step"; run("D2_UE_blocks_labelled_step1", d, "REJECT")
d = mut(UE); d["target"]["kind"] = "step"; d["target"]["order"] = 2; run("D3_UE_blocks_labelled_step2", d, "REJECT")
d = mut(UE); d["target"]["blocks"] = copy.deepcopy(UB["target"]["blocks"]); run("D4_UB_blocks_kind_UE", d, "REJECT")
d = mut(UE); d["target"]["blocks"] = copy.deepcopy(UB["target"]["blocks"]); d["target"]["kind"] = "UB"; run("D5_UB_blocks_kind_UB_UE_circuit", d, "REJECT")
d = mut(UE); d["target"]["kind"] = "bogus"; run("D6_unknown_kind", d, "REJECT")
d = mut(UE); del d["target"]["kind"]; run("D7_no_kind", d, "REJECT")
d = mut(UE); b = d["target"]["blocks"][3]; b["entries"][0][2][0][1][0] = "1/3"; run("D8_one_target_coefficient_changed", d, "REJECT")
d = mut(UE); d["target"]["blocks"][0], d["target"]["blocks"][1] = d["target"]["blocks"][1], d["target"]["blocks"][0]; run("D9_two_target_blocks_swapped", d, "REJECT")
d = mut(UE); d["base"]["d_alpha"] *= 2; run("D10_base_doubled_exponents_not_scaled", d, "REJECT")
d = mut(UE); d["base"]["d_beta"] *= 3; run("D11_beta_base_tripled_not_scaled", d, "REJECT")
# legit rescale of base: all exponents x2 (gates, phase, target) -> ACCEPT (same statement)
d = mut(UE); f = 2
d["base"]["d_alpha"] *= f; d["base"]["d_beta"] *= f
for g in d["gates"]:
    if "m" in g: g["m"] = [g["m"][0] * f, g["m"][1] * f]
d["phase"]["m"] = [d["phase"]["m"][0] * f, d["phase"]["m"][1] * f]
for b in d["target"]["blocks"]:
    for e in b["entries"]:
        for term in e[2]: term[0] = [term[0][0] * f, term[0][1] * f]
run("ctl_E1_legit_rescale_base_x2", d, "ACCEPT")
# ---------- N6 zero denominators / malformed rationals
for where, fn in (("state_coeff", lambda d: d["states"][3]["terms"][0]["c"].__setitem__(0, "1/0")),
                  ("target_coeff", lambda d: d["target"]["blocks"][0]["entries"][0][2][0][1].__setitem__(0, "1/0")),
                  ("phase", lambda d: d["phase"]["k"].__setitem__(0, "1/0")),
                  ("zero_over_zero", lambda d: d["states"][3]["terms"][0]["c"].__setitem__(1, "0/0")),
                  ("neg_denominator", lambda d: d["states"][3]["terms"][0]["c"].__setitem__(1, "1/-2")),
                  ("spaces", lambda d: d["states"][3]["terms"][0]["c"].__setitem__(1, "1 /2")),
                  ("double_slash", lambda d: d["states"][3]["terms"][0]["c"].__setitem__(1, "1/2/3")),
                  ("empty_string", lambda d: d["states"][3]["terms"][0]["c"].__setitem__(1, "")),
                  ("float_number", lambda d: d["states"][3]["terms"][0]["c"].__setitem__(1, 0.5)),
                  ("huge_exp_gate", lambda d: d["gates"][0].__setitem__("m", [10**30, 0])),
                  ("base_zero", lambda d: d["base"].__setitem__("d_alpha", 0)),
                  ("base_zero_beta", lambda d: d["base"].__setitem__("d_beta", 0))):
    d = mut(UE); fn(d); run("N6_" + where, d, "REJECT")
json.dump(results, open(os.path.join(outdir, "summary.json"), "w"), indent=1)
bad = [r for r in results if not r["ok"]]
print("TOTAL", len(results), "BAD", len(bad))
for r in bad: print(r)
