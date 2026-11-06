"""Tester 215 probe (e): recount of structure_facts values from H_B^in = (i/beta) logm(U_B^in(beta)) (own route: spectrum + rows) and
from the pair vectors (own GF(2) affine test); Lean literals by regex on the source."""
import json, re, subprocess, collections
import numpy as np, scipy.linalg as sl
import su2plaq.rishon.compress as RC
from su2plaq.rishon import operators as ops
from su2plaq.rishon.compress import spec as S
f = {x["name"]: x for x in S.structure_facts()["facts"]}
beta = 0.04
U = ops.inner_target("UB", 0.0, beta)
H = (1j / beta) * sl.logm(U)
print("unitary err", np.abs(U.conj().T @ U - np.eye(1296)).max(), "H hermitian err", np.abs(H - H.conj().T).max(), "imag max", np.abs(H.imag).max())
H = (H + H.conj().T).real / 2
ev = np.linalg.eigvalsh(H)
cnt = collections.Counter(np.round(ev, 6).tolist())
print("spectrum multiplicities", sorted(cnt.items()))
zero_rows = int(np.sum(np.abs(H).sum(axis=1) < 1e-9)); print("dark codes (zero rows of H)", zero_rows)
r = {}
r["dark_codes"] = zero_rows
k42 = round(4 * np.sqrt(2), 6)
r["kappa"] = {"1": cnt[1.0], "2": cnt[2.0], "4sqrt2": cnt[k42]}      # + side counts = number of pairs with that kappa
r["spectrum_symmetric"] = all(cnt[a] == cnt[-a] for a in (1.0, 2.0, k42))
r["n_pairs"] = sum(r["kappa"].values())
r["zero_modes"] = cnt[0.0]
claim = f["hb_bright_pairs"]["value"]
print("claim", claim, "own", r)
assert claim["dark_codes"] == r["dark_codes"] == 990
assert claim["n_pairs"] == r["n_pairs"] == 81 and claim["kappa_multiset"] == {"1": r["kappa"]["1"], "2": r["kappa"]["2"], "4*sqrt2": r["kappa"]["4sqrt2"]} and r["spectrum_symmetric"]
# reconstruct H from the pairs
pairs = ops.bright_pairs(); Hp = np.zeros((1296, 1296))
for u, v, k in pairs: Hp -= k * (np.outer(u, v) + np.outer(v, u))
print("H from pairs vs logm route: max diff", np.abs(Hp - H).max()); assert np.abs(Hp - H).max() < 1e-6
# commuting blocks / orthonormal vectors
G = np.array([x for u, v, _ in pairs for x in (u, v)]); print("pair vectors orthonormal", np.abs(G @ G.T - np.eye(162)).max())
# supports: own affine test
codes = ops.inner_codes(); aff = True; mx = 0; alph = set()
for u, v, _ in pairs:
    for x in (u, v):
        s = set(int(c) for c in codes[np.abs(x) > 1e-13]); mx = max(mx, len(s))
        d = np.log2(len(s)); aff &= (d == int(d)) and all((a ^ b ^ c) in s for a in s for b in s for c in s) if len(s) <= 16 else False
        alph |= set(np.round(np.abs(x[np.abs(x) > 1e-13]), 9).tolist())
print("supports affine", aff, "max support", mx, "alphabet", sorted(alph, reverse=True))
assert aff == f["pair_supports"]["value"]["supports_are_affine"] and mx == f["pair_supports"]["value"]["max_support"]
assert sorted(alph, reverse=True) == f["amplitude_alphabet"]["value"]
# heights / W
W = ops.plaquette_W_inner(); print("W^3 max", np.abs(W @ W @ W).max(), "nnz", int((np.abs(W) > 1e-12).sum()), "claim", f["heights_raising"]["value"]["W_nonzero_entries"])
# Lean literals
src = lambda p: open(f"lean/Su2Plaq/Rishon/{p}").read()
lit = {"card_rishon_physical": re.search(r"theorem card_rishon_physical[^=]*=\s*(\d+)", src("Counts.lean")).group(1),
       "card_rishon_closed": re.search(r"theorem card_rishon_closed[^=]*=\s*(\d+)", src("Counts.lean")).group(1),
       "card_inner_codes": re.search(r"theorem card_inner_codes[^=]*=\s*(\d+)", src("UESemantics.lean")).group(1),
       "corner_kernel_dims": re.search(r"theorem corner_kernel_dims : \(List\.range (\d+)", src("CornerKernel.lean")).group(1)}
print("lean literals", lit, "facts", {k: f[k]["value"] for k in lit})
assert all(int(lit[k]) == f[k]["value"] for k in lit)
print("3^4 =", 3 ** 4, " 6^4 =", 6 ** 4, "ops.inner_codes", len(codes), "U(1) sectors fact", f["u1_sectors"]["value"], "inner_span_rank", f["inner_span_rank"]["value"])
sk = ["bilinear_string_free_8", "ue_exact_all_codes"]
print("theorem names in facts", [(x["name"], x["theorem"]) for x in S.structure_facts()["facts"] if x["proved_by"] == "decide"])
# structure json equals fresh facts
d = json.load(open("compress/specs/rishon-structure.json")); print("json == structure_facts():", d == json.loads(json.dumps(S.structure_facts())))
# spec text == render_spec
print("md == render_spec:", open("compress/specs/rishon-step.md").read() == S.render_spec(S.rishon_spec("step")))
# hashes of lean sources in provenance
import hashlib, pathlib
bad = [k for k, h in S.structure_facts()["provenance"]["lean_sources"].items() if hashlib.sha256(pathlib.Path(k).read_bytes()).hexdigest() != h]
print("lean source hash mismatches", bad)
json.dump(dict(commit=subprocess.check_output(["git","rev-parse","--short","HEAD"],text=True).strip(), own=r, lean_literals=lit, beta=beta), open("results/rishon/tester-215-structure.json", "w"), indent=1)
