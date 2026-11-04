"""Tester's independent route-B checks (M0 step 0.6). Own 6j (sympy), own gauge routine, own corner brute force."""
import sys, json, itertools, math, subprocess
import numpy as np
sys.path.insert(0, "/home/digimonk/Projects/su2qc-encoding/src")
sys.path.insert(0, "/home/digimonk/Projects/su2qc-encoding")
from sympy import Rational as R
from sympy.physics.wigner import wigner_6j, wigner_3j, clebsch_gordan
from functools import lru_cache

out = {}
HALF = 0.5

def rat(x):
    return R(int(round(2 * x)), 2)

@lru_cache(maxsize=None)
def sixj(a, b, c, d, e, f):
    return float(wigner_6j(rat(a), rat(b), rat(c), rat(d), rat(e), rat(f)))

@lru_cache(maxsize=None)
def cg(j1, j2, j3, m1, m2, m3):
    return float(clebsch_gordan(rat(j1), rat(j2), rat(j3), rat(m1), rat(m2), rat(m3)))

def tri(a, b, c):
    a2, b2, c2 = (int(round(2 * x)) for x in (a, b, c))
    return abs(a2 - b2) <= c2 <= a2 + b2 and (a2 + b2 + c2) % 2 == 0

# ---------- own gauge routine (independent of compare.gauge_align): BFS spanning tree ----------
def my_gauge(A, B, tol=1e-9):
    n = A.shape[0]
    D = np.ones(n, dtype=complex); seen = np.zeros(n, bool)
    for r in range(n):
        if seen[r]: continue
        seen[r] = True; st = [r]
        while st:
            i = st.pop()
            for j in np.nonzero(np.abs(B[i]) > tol)[0]:
                if seen[j]: continue
                # A_ij = D_i B_ij conj(D_j)  ->  D_j = conj(A_ij/(D_i B_ij))^{-1}... solve for D_j
                x = A[i, j] / (D[i] * B[i, j])          # = conj(D_j)
                D[j] = np.conj(x) / abs(x)
                seen[j] = True; st.append(j)
    res = np.abs(A - D[:, None] * B * D.conj()[None, :]).max()
    return D, res

# ---------- (3) route A / B objects ----------
from su2plaq.exact import spinnet
from su2plaq.exact.physical import physical_basis
from su2plaq.exact.operators import h_magnetic_phys, h_electric_inner

basis = physical_basis(jmax=0.5, convention="cg")
HB_A, _ = h_magnetic_phys(basis)
HE_A = np.diag(h_electric_inner(basis)) if np.ndim(h_electric_inner(basis)) == 1 else h_electric_inner(basis)
labs = spinnet.labels(jmax=0.5)
perm = np.array([basis.index(l) for l in labs])
HB_A = np.asarray(HB_A)[np.ix_(perm, perm)]; HE_A = np.asarray(HE_A)[np.ix_(perm, perm)]
HB_B = spinnet.h_magnetic_phys_6j(labs); HE_B = spinnet.h_electric_6j(labs)
n = len(labs); print("n labels", n)

# ---------- (2) my own derivation ----------
# Corner = scalar product of two rank-1/2 tensor operators E (acting on inner end p) and E (inner end n);
# Edmonds 7.1.6: <(jp' jn')J|E_p . E_n|(jp jn)J> = (-1)^{jp+jn'+J} {J jn' jp'; 1/2 jp jn} <jp'||E||jp><jn'||E||jn>.
# Reduced elements of the CG-defined end operator E^a|j m> = sum_m' <j m 1/2 a|j' m'>|j' m'> from Wigner-Eckart numerically.
def red(j, jp):
    # <j' m'|E^a|j m> = <j m 1/2 a|j' m'> = (-1)^{j'-m'} (j' 1/2 j; -m' a m) <j'||E||j>
    m, a = j, HALF; mp = m + a
    if abs(mp) > jp + 1e-9: m, a = j, -HALF; mp = m + a
    c = cg(j, HALF, jp, m, a, mp)
    w = float(wigner_3j(rat(jp), R(1, 2), rat(j), rat(-mp), rat(a), rat(m)))
    ph = (-1) ** int(round(jp - mp))
    return c / (ph * w)

RED = {(j, jp): red(j, jp) for j in (0, .5, 1) for jp in (j - .5, j + .5) if jp >= 0 and tri(j, .5, jp)}
print("reduced elements (j->j'):", {k: round(v, 6) for k, v in RED.items()})
print("   vs sqrt(2j'+1):", {k: round(math.sqrt(2 * k[1] + 1), 6) for k in RED})

PN = [(3, 0), (0, 1), (1, 2), (2, 3)]
def my_corner(J, jp, jn, jpp, jnn, phase_mode="edmonds"):
    w = sixj(J, jnn, jpp, HALF, jp, jn)
    if w == 0: return 0.0
    if phase_mode == "edmonds":
        ph = np.exp(1j * np.pi * (jp + jnn + J))
    else:
        ph = 1.0
    return ph * w * RED[(jp, jpp)] * RED[(jn, jnn)]

def my_P(labels, phase_mode="edmonds", linknorm=True):
    idx = {l: i for i, l in enumerate(labels)}
    P = np.zeros((len(labels),) * 2, dtype=complex)
    for col, (j, Jl) in enumerate(labels):
        for sg in itertools.product((.5, -.5), repeat=4):
            jn = list(j)
            for e in range(4): jn[e] = j[e] + sg[e]
            new = (tuple(jn), Jl)
            if new not in idx: continue
            amp = 1.0
            for c, (ep, en) in enumerate(PN):
                amp = amp * my_corner(Jl[c], j[ep], j[en], jn[ep], jn[en], phase_mode)
                if amp == 0: break
            if amp == 0: continue
            if linknorm:
                for e in range(4): amp *= math.sqrt((2 * j[e] + 1) / (2 * jn[e] + 1))
            P[idx[new], col] += amp
    return P

il = spinnet.inner_labels(0.5)
K_b = spinnet.K_inner(0.5)
Pm = my_P(il)
print("my P (Edmonds phase): max|imag| =", np.abs(Pm.imag).max())
# global phase from (-1)^{1/2}-type factors: 4 corners
Pm_real_candidate = Pm
# magnitude comparison: builder P vs mine
P_b = spinnet.plaquette_P(il)
mag_diff = np.abs(np.abs(Pm) - np.abs(P_b)).max()
print("max ||P_mine|-|P_builder|| =", mag_diff)
out["magnitude_P_mine_vs_builder_47"] = float(mag_diff)
# compare as matrices up to diagonal gauge
Km = -(Pm + Pm.conj().T)
Dg, resg = my_gauge(Km, K_b.astype(complex))
print("gauge-align (own routine) K_mine ~ D K_builder D^+ : residual", resg, " |D| dev", np.abs(np.abs(Dg) - 1).max(), "D real?", np.abs(Dg.imag).max())
out["K_mine_vs_builder_gauge_resid"] = float(resg); out["K_mine_vs_builder_D_imag_max"] = float(np.abs(Dg.imag).max())
# direct (no gauge) difference
out["K_mine_vs_builder_direct"] = float(np.abs(Km - K_b).max())
print("direct |K_mine-K_builder| =", out["K_mine_vs_builder_direct"], " number of sign flips in P entries:",
      int(np.sum((np.abs(P_b) > 1e-12) & (np.sign(Pm.real) != np.sign(P_b)))), "/", int(np.sum(np.abs(P_b) > 1e-12)))
# is the Edmonds phase a pure global (overall) factor? ratio per nonzero entry
nz = np.abs(P_b) > 1e-12
ratio = Pm[nz] / P_b[nz]
print("ratio P_mine/P_builder over entries: unique values", np.unique(np.round(ratio, 10)))

# variants (negative controls: the discriminating power of the comparison)
variants = {
    "no_Edmonds_phase": my_P(il, phase_mode="none"),
    "no_link_norm": my_P(il, linknorm=False),
}
for name, Pv in variants.items():
    Kv = -(Pv + Pv.conj().T)
    mod = np.abs(np.abs(Kv) - np.abs(K_b)).max()
    Dv, rv = my_gauge(Kv, K_b.astype(complex))
    print(f"variant {name}: max||K|-|Kb|| = {mod:.3e}, gauge residual = {rv:.3e}")
    out[f"variant_{name}"] = {"mod_diff": float(mod), "gauge_resid": float(rv)}
# wrong corner mapping: swap (p,n) at one corner -> should break
PN_save = PN[:]
PN[0] = (0, 3)
Pw = my_P(il); Kw = -(Pw + Pw.conj().T); PN[:] = PN_save
Dw, rw = my_gauge(Kw, K_b.astype(complex)); modw = np.abs(np.abs(Kw) - np.abs(K_b)).max()
print(f"variant swap p<->n at c0: max||K|-|Kb|| = {modw:.3e}, gauge residual = {rw:.3e}")
out["variant_swap_pn_c0"] = {"mod_diff": float(modw), "gauge_resid": float(rw)}
# wrong 6j argument order e.g. use jn instead of jn' etc: f(J, jp, jn, 1/2, jp', jn') (swap roles of the primed)
def alt_P():
    idx = {l: i for i, l in enumerate(il)}
    P = np.zeros((47, 47))
    from su2plaq.su2.wigner import f_symbol
    for col, (j, Jl) in enumerate(il):
        for sg in itertools.product((.5, -.5), repeat=4):
            jn = list(j)
            for e in range(4): jn[e] = j[e] + sg[e]
            new = (tuple(jn), Jl)
            if new not in idx: continue
            amp = 1.0
            for c, (ep, en) in enumerate(PN):
                amp *= f_symbol(Jl[c], j[ep], j[en], .5, jn[ep], jn[en])   # swapped primes
            P[idx[new], col] += amp
    return P
Pa = alt_P(); Ka = -(Pa + Pa.T)
Da, ra = my_gauge(Ka.astype(complex), K_b.astype(complex)); moda = np.abs(np.abs(Ka) - np.abs(K_b)).max()
print(f"variant swapped primed args in f_symbol: max||K|-|Kb|| = {moda:.3e}, gauge residual = {ra:.3e}")
out["variant_swapped_primes"] = {"mod_diff": float(moda), "gauge_resid": float(ra)}

# also compare my full 433 route-B (own formula) vs route A
Pm433 = my_P(labs); H433 = -(Pm433 + Pm433.conj().T)
Dm, rm = my_gauge(HB_A.astype(complex), H433)
print("433: route A vs MY route-B, gauge residual", rm, " |D-real| imag max", np.abs(Dm.imag).max())
out["A_vs_mine_433_gauge_resid"] = float(rm); out["A_vs_mine_433_modulus"] = float(np.abs(np.abs(HB_A) - np.abs(H433)).max())
out["A_vs_builder_433_gauge_resid"] = float(my_gauge(HB_A.astype(complex), HB_B.astype(complex))[1])
out["A_vs_builder_433_modulus"] = float(np.abs(np.abs(HB_A) - np.abs(HB_B)).max())
print("433 A vs builder: gauge resid", out["A_vs_builder_433_gauge_resid"], "modulus diff", out["A_vs_builder_433_modulus"])

# ---------- (3) spectra ----------
specs = {}
for g2 in (0.5, 1.0, 2.0):
    eA = np.linalg.eigvalsh(0.5 * g2 * HE_A + HB_A / g2)
    eB = np.linalg.eigvalsh(0.5 * g2 * HE_B + HB_B / g2)
    eM = np.linalg.eigvalsh(0.5 * g2 * HE_B + H433.real / g2) if np.abs(H433.imag).max() < 1e-12 else None
    specs[g2] = {"A_vs_B": float(np.abs(eA - eB).max()), "A_vs_mine": None if eM is None else float(np.abs(eA - eM).max()),
                 "Emin": float(eA[0]), "Emax": float(eA[-1])}
    print("g2", g2, specs[g2])
eAh, eBh = np.linalg.eigvalsh(HB_A), np.linalg.eigvalsh(HB_B)
specs["HB_only"] = float(np.abs(eAh - eBh).max())
vals, cnt = np.unique(np.round(eAh, 8), return_counts=True)
specs["HB_spectrum"] = {float(v): int(c) for v, c in zip(vals, cnt)}
print("H_B alone max diff", specs["HB_only"]); print("H_B spectrum", specs["HB_spectrum"])
out["spectra"] = {str(k): v for k, v in specs.items()}
out["H433_mine_imag_max"] = float(np.abs(H433.imag).max())
out["HB_B_hermitian"] = float(np.abs(HB_B - HB_B.T).max()); out["HB_A_hermitian"] = float(np.abs(HB_A - HB_A.conj().T).max())

# ---------- (4) block structure ----------
outer = [l[0][4:] for l in labs]; Jl = [l[1] for l in labs]
blocks = {}
for i, o in enumerate(outer): blocks.setdefault(o, []).append(i)
oid = np.array([list(blocks).index(o) for o in outer]); Jid = np.array([sorted(set(Jl)).index(J) for J in Jl])
def maxoff(H, ids): return float(np.abs(H)[ids[:, None] != ids[None, :]].max())
bs = {"n_blocks": len(blocks), "dims_hist": {int(d): int(c) for d, c in zip(*np.unique([len(v) for v in blocks.values()], return_counts=True))},
      "offblock_A": maxoff(HB_A, oid), "offblock_B": maxoff(HB_B, oid), "Jviol_A": maxoff(HB_A, Jid), "Jviol_B": maxoff(HB_B, Jid),
      "number_of_distinct_outer_strings_among_256_allowed": len(set(outer))}
ilx = {l: i for i, l in enumerate(il)}
worstabsA = worstgaugeA = worstabsB = worstgaugeB = 0.0
covered = set()
sigdev = 0.0
ratios = {}
for o, sel in blocks.items():
    sub = [ilx[(labs[i][0][:4], labs[i][1])] for i in sel]; covered |= set(sub)
    Ksub = K_b[np.ix_(sub, sub)].astype(complex)
    BA = HB_A[np.ix_(sel, sel)].astype(complex); BB = HB_B[np.ix_(sel, sel)].astype(complex)
    worstabsA = max(worstabsA, float(np.abs(np.abs(BA) - np.abs(Ksub)).max()))
    worstabsB = max(worstabsB, float(np.abs(BB - Ksub).max()))
    _, rA = my_gauge(BA, Ksub); worstgaugeA = max(worstgaugeA, rA)
    # sign ratio matrix A/K per block: is it outer-independent after considering inner label pairs?
    for a in range(len(sel)):
        for b in range(len(sel)):
            if abs(Ksub[a, b]) > 1e-12:
                ratios.setdefault((sub[a], sub[b]), set()).add(round(float((BA[a, b] / Ksub[a, b]).real), 8))
bs.update({"worst_|abs|_diff_A_vs_Ksub": worstabsA, "worst_gauge_resid_A_vs_Ksub": worstgaugeA, "worst_direct_diff_B_vs_Ksub": worstabsB,
           "inner_labels_covered": len(covered), "pairs_with_o_dependent_sign": int(sum(1 for v in ratios.values() if len(v) > 1)),
           "n_pairs": len(ratios)})
print("block structure:", bs)
out["blocks"] = bs
# which inner labels occur in which number of blocks; 16 bright
darkK = [i for i in range(47) if np.abs(K_b[i]).max() < 1e-12]
out["K"] = {"shape": list(K_b.shape), "sym": float(np.abs(K_b - K_b.T).max()), "n_dark": len(darkK), "n_bright": 47 - len(darkK),
            "dark_have_J1": all(1.0 in il[i][1] for i in darkK), "bright_no_J1": all(1.0 not in il[i][1] for i in range(47) if i not in darkK)}
eK = np.linalg.eigvalsh(K_b); v, c = np.unique(np.round(eK, 8), return_counts=True)
out["K"]["spectrum"] = {float(a): int(b) for a, b in zip(v, c)}
out["K"]["nonzero_entries"] = int(np.sum(np.abs(K_b) > 1e-12))
out["K"]["max_abs"] = float(np.abs(K_b).max())
print("K:", out["K"])
# bright sub-blocks
bright = [i for i in range(47) if i not in darkK]
Kb = K_b[np.ix_(bright, bright)]
out["K"]["bright_spectrum"] = {float(a): int(b) for a, b in zip(*np.unique(np.round(np.linalg.eigvalsh(Kb), 8), return_counts=True))}
print("bright K spectrum", out["K"]["bright_spectrum"])

# ---------- (6) gauge_align on random complex gauge ----------
from su2plaq.exact.compare import gauge_align
rng = np.random.default_rng(20261104)
ga = {}
for name, Bm in (("HB_B_433", HB_B.astype(complex)), ("K_47", K_b.astype(complex)), ("HB_A_433", HB_A.astype(complex))):
    th = rng.uniform(0, 2 * np.pi, Bm.shape[0]); Dtrue = np.exp(1j * th)
    A = Dtrue[:, None] * Bm * Dtrue.conj()[None, :]
    D, res = gauge_align(A, Bm)
    # D should equal Dtrue up to a phase per connected component of the pattern of B
    rel = D * Dtrue.conj()
    # connected components
    import scipy.sparse as sp, scipy.sparse.csgraph as cs
    ncomp, lab = cs.connected_components(sp.csr_matrix(np.abs(Bm) > 1e-9), directed=False)
    dev = 0.0
    for k in range(ncomp):
        r = rel[lab == k]; dev = max(dev, float(np.abs(r - r[0]).max()))
    ga[name] = {"residual": float(res), "n_components": int(ncomp), "D_vs_Dtrue_dev_within_component": dev, "|D|-1": float(np.abs(np.abs(D) - 1).max())}
    # negative control: flip sign of one matrix element pair that lies on a cycle (not removable)
    Bn = Bm.copy()
    # pick a nonzero element and flip it symmetrically
    ii, jj = np.nonzero(np.triu(np.abs(Bm) > 1e-9, 1))
    resn = []
    for t in range(min(25, len(ii))):
        An = A.copy(); a, b = ii[t], jj[t]; An[a, b] *= -1; An[b, a] *= -1
        Dn, rn = gauge_align(An, Bm); resn.append(rn)
    ga[name]["flip1_residuals_min_max"] = [float(np.min(resn)), float(np.max(resn))]
    # modulus mismatch
    D2, r2 = gauge_align(2 * A, Bm); ga[name]["modulus_mismatch_returns_None"] = (D2 is None, float(r2))
print("gauge_align:", json.dumps(ga, indent=1))
out["gauge_align_random"] = ga

json.dump(out, open("/tmp/claude-1000/-home-digimonk-Projects-su2qc-encoding/6f24cad7-b2eb-5b02-89d1-34310bbf63e6/scratchpad/out1.json", "w"), indent=1, default=str)
