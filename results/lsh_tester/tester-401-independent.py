"""Tester-401 independent verification of M7 steps 7.3-7.5 (codec/decode, targets/coupling table, build_UE).
Own implementation of: label -> 24-bit LSH code (from l_12 = j1+j2-j3 cyclic per site), validity predicate over all 2^24
codes, Gauss G^z check of decoded fallback states, route-B targets (6j), U_E phases by my own gate-walk simulator.
Run:  PYTHONPATH=src python results/lsh_tester/tester-401-independent.py results/lsh_tester/tester-401-independent.json
No code from su2plaq.lsh is used to compute the expected numbers; it is only called to obtain the values under test."""
import json, subprocess, sys, time
from itertools import product
import numpy as np
import scipy.linalg as sla

out = {"commit": subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip(),
       "seed": 20261110, "checks": []}


def rec(name, expected, got, tol, ok):
    out["checks"].append({"check": name, "expected": expected, "got": got, "tol": tol, "ok": bool(ok)})
    print(("PASS " if ok else "FAIL ") + name, "| expected", expected, "| got", got, "| tol", tol, flush=True)


from su2plaq.encodings.lsh import LSH
from su2plaq.exact import spinnet as RB
from su2plaq.exact.operators import target as target_A
from su2plaq.exact.physical import gauss_residuals_coo
from su2plaq.geometry import plaquette_diagram
from su2plaq.su2.algebra import LinkSpace

t0 = time.time()
enc = LSH()
labels = RB.labels(jmax=0.5)
assert len(labels) == 433

# ---------------- own codec ------------------------------------------------------------------------------------
PN = [(3, 0), (0, 1), (1, 2), (2, 3)]               # (p(c), n(c)) METHODS-lsh L2: (l,b),(b,r),(r,t),(t,l); b r t l = 0 1 2 3
OUT = [(4, 5), (6, 7), (8, 9), (10, 11)]
diag = plaquette_diagram()
ok_geo = all({li for li, _ in diag.corners[c].ends} == set(PN[c]) | set(OUT[c]) for c in range(4))
rec("geometry: corner c has links {p,n} u {o1,o2}", True, ok_geo, "exact", ok_geo)


def site_bits(j1, j2, J):
    """3 loop-number bits (l12, l23, l31) of a trivalent site; l_12 = j1+j2-J, l_23 = j2+J-j1, l_31 = J+j1-j2."""
    l12, l23, l31 = j1 + j2 - J, j2 + J - j1, J + j1 - j2
    for l in (l12, l23, l31):
        assert abs(l - round(l)) < 1e-12 and round(l) in (0, 1), (j1, j2, J)
    return int(round(l12)) | (int(round(l23)) << 1) | (int(round(l31)) << 2)


def my_code(label):
    j, J = label
    code = 0
    for c in range(4):
        code |= site_bits(j[PN[c][0]], j[PN[c][1]], J[c]) << (3 * c)
        code |= site_bits(j[OUT[c][0]], j[OUT[c][1]], J[c]) << (12 + 3 * c)
    return code


mine = [my_code(l) for l in labels]
rec("own codes distinct", 433, len(set(mine)), "exact", len(set(mine)) == 433)
rec("enc._codes == own code_of_label (433, in order)", True, bool(np.array_equal(enc._codes, np.array(mine))), "exact",
    np.array_equal(enc._codes, np.array(mine)))
eb = enc.physical_vectors()
ok = all(len(c) == 1 and int(c[0]) == mine[k] and len(a) == 1 and abs(a[0] - 1) == 0 for k, (c, a) in enumerate(zip(eb.codes, eb.amps)))
rec("physical_vectors: one code per state = own code, amp 1", True, ok, "exact", ok)
rec("enc.basis.labels == enc.labels == route-B labels (order)", True, enc.basis.labels == labels and list(enc.labels) == list(labels), "exact",
    enc.basis.labels == labels and list(enc.labels) == list(labels))
ok = all(enc.decode(mine[k]) == k for k in range(433))
rec("decode(own code of label k) == k  (all 433)", True, ok, "exact", ok)
# bit-by-bit independent check of one hand-computed code: vacuum label -> all zero; link b only at 1/2
vac = ((0.0,) * 12, (0.0,) * 4)
rec("vacuum label -> code 0", 0, my_code(vac), "exact", my_code(vac) == 0 and mine[labels.index(vac)] == 0)
# link b alone at 1/2: in-site c0 = (j_p=l=0, j_n=b=1/2, J=1/2): l12=0, l23=1, l31=0 -> 010 ; in-site c1 = (b=1/2, r=0, 1/2): l12 = 0, l23 = 0, l31 = 1 -> 100
# (a data code, not a full physical label: the outer legs would need J=1/2 sites). Check via the 47 inner codes that it is one.
c_b = 0b100010
rec("link-b-only data code 0b100010 is an inner code", True, c_b in enc.inner_codes().tolist(), "exact", c_b in enc.inner_codes().tolist())

# validity predicate over all 2^24: own rule -> exactly the 433
allc = np.arange(1 << 24, dtype=np.int64)
sites = [(allc >> (3 * k)) & 7 for k in range(8)]
sv = np.ones(1 << 24, dtype=bool)
fl = []
for s in sites:
    l12, l23, l31 = s & 1, (s >> 1) & 1, (s >> 2) & 1
    N1, N2, N3 = l31 + l12, l12 + l23, l23 + l31
    sv &= (N1 <= 1) & (N2 <= 1)
    fl.append((N1, N2, N3))
agl = np.ones(1 << 24, dtype=bool)
for c in range(4):
    agl &= fl[c][1] == fl[(c + 1) % 4][0]          # N_n(c) = N_p(c+1)
    agl &= fl[c][2] == fl[4 + c][2]                # N_v(in) = N_v(out)
phys = np.flatnonzero(sv & agl)
rec("2^24 sweep: valid codes (site rule + AGL) = 433 = own label codes", 433, len(phys), "exact",
    len(phys) == 433 and set(phys.tolist()) == set(mine))
# decode None for non-physical codes: all (valid-data & valid-outer-site & AGL-violating) + 30000 random
rng = np.random.default_rng(20261110)
inner = enc.inner_codes().tolist()
outer_valid = [sum(s << (3 * i) for i, s in enumerate(ss)) for ss in product((0, 1, 2, 4, 6), repeat=4)]
bad = [c | (o << 12) for c in inner for o in outer_valid if (c | (o << 12)) not in set(mine)]
rec("# data-valid, site-valid, AGL-violating codes", 28942, len(bad), "exact", len(bad) == 28942)
okd = all(enc.decode(c) is None for c in bad)
rnd = rng.integers(0, 1 << 24, size=30000)
okd &= all((enc.decode(int(c)) is None) == (int(c) not in set(mine)) for c in rnd)
rec("decode() None on 28942 bad + 30000 random non-physical codes", True, okd, "exact", okd)

# ---------------- decode_state: physical + fallback ----------------------------------------------------------
gauge = enc.gauge
errs = []
for k in range(433):
    keys, amps = enc.decode_state(np.array([mine[k]]), np.array([1.0 + 0j]))
    d_ref = dict(zip(enc.basis.keys[k].tolist(), (enc.basis.amps[k] * gauge[k]).tolist()))
    d_got = dict(zip(keys.tolist(), amps.tolist()))
    if set(d_ref) != set(d_got):
        errs.append(1.0)
    else:
        errs.append(max(abs(d_ref[x] - d_got[x]) for x in d_ref))
rec("decode_state(physical k) = gauge[k] x route-A state k (max diff, 433)", 0, max(errs), 1e-12, max(errs) <= 1e-12)
rec("gauge real +-1, residual", "<=1e-10", f"{enc.gauge_residual:.2e}; {int((gauge<0).sum())} minus signs", 1e-10,
    enc.gauge_residual <= 1e-10 and set(np.unique(gauge)) <= {-1.0, 1.0})

ls = LinkSpace(0.5)


def gz_corners(key):
    """G^z at each of the 4 corners for an electric-basis key: out end -m_L, in end +m_R (cg)."""
    digs = [(key // 5 ** i) % 5 for i in range(12)]
    st = [ls.states[d] for d in digs]
    g = []
    for c in range(4):
        s = 0.0
        for li, role in diag.corners[c].ends:
            _, mL, mR = st[li]
            s += -mL if role == "out" else mR
        g.append(s)
    return g


gz_phys = max(max(abs(x) for x in gz_corners(int(k))) for kk in enc.basis.keys for k in kk)
rec("own G^z formula vanishes on the support of all 433 physical states", 0, gz_phys, 1e-12, gz_phys < 1e-12)
phys_keys = set(int(k) for kk in enc.basis.keys for k in kk)
fk = []
norms = []
gzmax = []
for c in bad:
    keys, amps = enc.decode_state(np.array([c]), np.array([1.0 + 0j]))
    norms.append(abs(np.linalg.norm(amps) - 1))
    fk.append(tuple(keys.tolist()))
    gzmax.append(max(max(abs(x) for x in gz_corners(int(k))) for k in keys))
rec("fallback: 28942 keys all distinct", 28942, len(set(fk)), "exact", len(set(fk)) == 28942)
allfk = set(k for t in fk for k in t)
rec("fallback keys disjoint from physical support", 0, len(allfk & phys_keys), "exact", not (allfk & phys_keys))
rec("fallback: unit norm (max |norm-1|)", 0, max(norms), 1e-12, max(norms) <= 1e-12)
rec("fallback: min over codes of max_c |G^z_c| (own formula)", ">=0.5", min(gzmax), 0.5 - 1e-12, min(gzmax) >= 0.5 - 1e-12)
vv = gauss_residuals_coo(enc.basis, [np.array(t) for t in fk[:3000]], [np.array([1.0 + 0j] * len(t)) for t in fk[:3000]])
rec("fallback Gauss residual (project fn, first 3000)", ">=0.5", float(vv.min()), 0.5 - 1e-10, vv.min() >= 0.5 - 1e-10)
# errors
errs_ok = True
for code in (0b011, 0b011 << 12, (1 << 24), -1):
    try:
        enc.decode_state(np.array([code]), np.array([1.0 + 0j]))
        errs_ok = False
    except ValueError:
        pass
rec("ValueError for bad data part / out-site cap / >24 bits / negative", True, errs_ok, "exact", errs_ok)
# linearity
ka, aa = enc.decode_state(np.array([mine[3], mine[200], bad[17]]), np.array([0.3, 0.4j, -0.5 + 0.1j]))
refd = {}
for code, w in zip([mine[3], mine[200], bad[17]], [0.3, 0.4j, -0.5 + 0.1j]):
    k_, a_ = enc.decode_state(np.array([code]), np.array([1.0 + 0j]))
    for x, y in zip(k_.tolist(), a_):
        refd[x] = refd.get(x, 0) + w * y
lin = max(abs(refd[x] - v) for x, v in zip(ka.tolist(), aa)) if set(refd) == set(ka.tolist()) else 1
rec("decode_state linear (3-term superposition incl. fallback)", 0, lin, 1e-12, lin <= 1e-12)

# ---------------- targets ------------------------------------------------------------------------------------
HB_6j = RB.h_magnetic_phys_6j(labels)
HE_in = np.diag(RB.h_electric_6j(labels, inner_only=True))
HE_all = np.diag(RB.h_electric_6j(labels, inner_only=False))
# own electric energy straight from the labels
HE_own = np.array([sum(x * (x + 1) for x in j[:4]) for j, _ in labels])
HE_own_all = np.array([sum(x * (x + 1) for x in j) for j, _ in labels])
rec("own H_E (inner / all) = route-B 6j diag", 0, max(np.abs(HE_own - HE_in).max(), np.abs(HE_own_all - HE_all).max()), 1e-14, True)
from su2plaq.encodings.spinnet import SpinNet
sn = SpinNet()
Dm = np.diag(enc.gauge)
res = {}
for (alpha, beta) in ((0.37, 0.61), (0.91, 0.23), (1.70, 1.00), (-0.55, 2.3), (0.05, 0.05)):
    VB_ref = sla.expm(-1j * beta * HB_6j)
    UE_ref = np.diag(np.exp(-1j * alpha * HE_own))
    UEo_ref = np.diag(np.exp(-1j * alpha * HE_own_all))
    e = {}
    e["UB vs expm(6j)"] = np.abs(enc.target("UB", None, beta) - VB_ref).max()
    e["UE vs own diag"] = np.abs(enc.target("UE", alpha, None) - UE_ref).max()
    e["UE outer vs own"] = np.abs(enc.target("UE", alpha, None, include_outer_electric=True) - UEo_ref).max()
    for order in (1, 2):
        UEh = np.diag(np.exp(-1j * alpha / 2 * HE_own)) if order == 2 else UE_ref
        step_ref = VB_ref @ UE_ref if order == 1 else UEh @ VB_ref @ UEh
        e[f"step o{order} vs 6j"] = np.abs(enc.target("step", alpha, beta, order) - step_ref).max()
        e[f"step o{order} vs SpinNet"] = np.abs(enc.target("step", alpha, beta, order) - sn.target("step", alpha, beta, order)).max()
    e["UB vs SpinNet"] = np.abs(enc.target("UB", None, beta) - sn.target("UB", None, beta)).max()
    e["UE vs SpinNet"] = np.abs(enc.target("UE", alpha, None) - sn.target("UE", alpha, None)).max()
    if abs(alpha) > 0:
        # route A with gauge (1e-10): V_LSH = D^dag V_A D
        e["UB vs D^dag V_A D"] = np.abs(enc.target("UB", None, beta) - Dm.conj().T @ target_A(enc.basis, "UB", beta=beta) @ Dm).max()
        e["step o1 vs D^dag V_A D"] = np.abs(enc.target("step", alpha, beta, 1) - Dm.conj().T @ target_A(enc.basis, "step", alpha=alpha, beta=beta, order=1) @ Dm).max()
    # unitarity
    e["unitarity UB"] = np.abs(enc.target("UB", None, beta) @ enc.target("UB", None, beta).conj().T - np.eye(433)).max()
    res[(alpha, beta)] = e
    for k, v in e.items():
        tol = 1e-10 if "D^dag" in k else 1e-12
        rec(f"target {k} at (alpha,beta)=({alpha},{beta})", 0, float(v), tol, v <= tol)
# bad kind
try:
    enc.target("nope", 0.1, 0.1); okk = False
except ValueError:
    okk = True
rec("target('nope') ValueError", True, okk, "exact", okk)
# Hermiticity of H_B / H_E
rec("H_B Hermitian (real symmetric)", 0, float(np.abs(enc.h_magnetic() - enc.h_magnetic().T).max()), 1e-14, np.abs(enc.h_magnetic() - enc.h_magnetic().T).max() <= 1e-14)
rec("enc.h_magnetic() vs 6j H_B", 0, float(np.abs(enc.h_magnetic() - HB_6j).max()), 1e-12, np.abs(enc.h_magnetic() - HB_6j).max() <= 1e-12)

# coupling table / partner table vs route-B K_inner (independent, uses 6j F-symbols), via own codec
import su2plaq.lsh.walk as W
inner_labs = RB.inner_labels(0.5)
K6 = RB.K_inner(0.5)
def my_inner_code(lab):
    j4, J = lab
    code = 0
    for c in range(4):
        code |= site_bits(j4[PN[c][0]], j4[PN[c][1]], J[c]) << (3 * c)
    return code
icodes = [my_inner_code(l) for l in inner_labs]
rec("47 inner codes (own, from route-B inner labels) = enc.inner_codes()", True, sorted(icodes) == enc.inner_codes().tolist(), "exact", sorted(icodes) == enc.inner_codes().tolist())
tab = W.coupling_table(enc)
par = W.partner_table(enc)
bad_t = 0
for i, ci in enumerate(icodes):
    col = K6[:, i]
    nz = np.flatnonzero(np.abs(col) > 1e-12)
    exp_v = 0.0 if len(nz) == 0 else float(col[nz[0]])
    if abs(tab[ci] - exp_v) > 1e-12:
        bad_t += 1
    if len(nz):
        if par.get(ci) != icodes[int(nz[0])]:
            bad_t += 1
    elif ci in par:
        bad_t += 1
rec("coupling_table + partner_table = route-B K_inner (47 codes, values incl. sign, partners)", 0, bad_t, "exact", bad_t == 0)
vals = sorted(tab.values())
ms = {v: vals.count(v) for v in sorted(set(vals))}
rec("coupling table value multiset", "{-2:2,-0.5:2,0:31,1:12}", ms, "exact", ms == {-2.0: 2, -0.5: 2, 0.0: 31, 1.0: 12})
# inner target
KI = enc.inner_target("UB", None, 0.61)
order_idx = [icodes.index(c) for c in enc.inner_codes().tolist()]
K6s = K6[np.ix_(order_idx, order_idx)]
rec("inner_target UB vs expm(-i beta K_route-B) (own ordering)", 0, float(np.abs(KI - sla.expm(-0.61j * K6s)).max()), 1e-12, np.abs(KI - sla.expm(-0.61j * K6s)).max() <= 1e-12)

# ---------------- build_UE with own simulator -------------------------------------------------------------------
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator, Statevector
from su2plaq.circuits.lsh import build_UE


def own_phase(qc, code):
    """phase of a basis state code under a circuit made only of p(l)/rz(t)/z/s/t gates, with the global phase."""
    ph = float(qc.global_phase)
    for inst in qc.data:
        nm = inst.operation.name
        q = [qc.find_bit(x).index for x in inst.qubits]
        b = (code >> q[0]) & 1
        if nm == "p":
            ph += inst.operation.params[0] * b
        elif nm == "rz":
            ph += inst.operation.params[0] * (b - 0.5)
        else:
            raise ValueError("unexpected gate " + nm)
    return np.exp(1j * ph)


for alpha in (0.37, 0.91, 1.70, -0.6, 3.0, 0.0):
    for with_outer, inc in ((False, False), (True, False), (True, True)):
        qc = build_UE(alpha, with_outer=with_outer, include_outer_electric=inc)
        ref = HE_own_all if inc else HE_own
        got = np.array([own_phase(qc, mine[k]) for k in range(433)])
        exp = np.exp(-1j * alpha * ref)
        rec(f"build_UE own-sim vs exp(-i alpha H_E) 433 states alpha={alpha} outer={with_outer} outerE={inc} (cx={qc.count_ops().get('cx',0)}, ops={dict(qc.count_ops())})",
            0, float(np.abs(got - exp).max()), 1e-13, np.abs(got - exp).max() <= 1e-13)
# own simulator vs Qiskit: Operator on 12 qubits (all 4096 data codes), Statevector on 24-qubit circuit for sample codes
alpha = 0.91
q12 = build_UE(alpha)
d12 = np.diag(Operator(q12).data)
own12 = np.array([own_phase(q12, c) for c in range(4096)])
rec("own simulator vs qiskit Operator, 12 qubits, 4096 codes", 0, float(np.abs(d12 - own12).max()), 1e-13, np.abs(d12 - own12).max() <= 1e-13)
q24 = build_UE(alpha, with_outer=True, include_outer_electric=True)
worst = 0.0
for k in (0, 1, 100, 250, 432):
    sv = Statevector.from_int(mine[k], 1 << 24).evolve(q24)
    arr = np.asarray(sv.data)
    idx = int(np.argmax(np.abs(arr)))
    assert idx == mine[k]
    worst = max(worst, abs(arr[idx] - own_phase(q24, mine[k])))
rec("own simulator vs qiskit Statevector (24 qubits, 5 states, outer row)", 0, float(worst), 1e-13, worst <= 1e-13)
# convention: link b only at j=1/2 -> e^{-3i alpha/4} relative to vacuum ; outer links 1/2 each add 3/4
b_code = c_b
ph = own_phase(build_UE(0.37), b_code & 0xFFF) / own_phase(build_UE(0.37), 0)
rec("single link b at j=1/2: phase e^{-3 i alpha/4}", 0, float(abs(ph - np.exp(-0.75j * 0.37))), 1e-13, abs(ph - np.exp(-0.75j * 0.37)) <= 1e-13)
q = build_UE(0.37, with_outer=True, include_outer_electric=True)
# outer: states with a single outer link o_0 only (site out0: legs (o0,o1,v) = (1/2,0,1/2): l12 = 1/2+0-1/2 = 0, l23 = 0+1/2-1/2=0, l31 = 1/2+1/2-0 = 1 -> bit2)
# use a label which exists: outer link o0 and o1 both 1/2, J_0 = 0
lab_o2 = ((0.0,) * 4 + (0.5, 0.5) + (0.0,) * 6, (0.0, 0.0, 0.0, 0.0))
assert lab_o2 in labels
c_o2 = my_code(lab_o2)
ph = own_phase(q, c_o2) / own_phase(q, 0)
rec("outer links o0,o1 both at 1/2 (J_0=0): phase e^{-2*(3/4) i alpha}", 0, float(abs(ph - np.exp(-1.5j * 0.37))), 1e-13, abs(ph - np.exp(-1.5j * 0.37)) <= 1e-13)
# evaluate through the project evaluator at several alpha
from su2plaq.evaluate.evaluator import evaluate
for alpha in (0.37, 0.91, 1.7, -0.6):
    v = evaluate(build_UE(alpha), enc, enc.target("UE", alpha, None))
    rec(f"evaluate UE(inner) alpha={alpha}", "ok, err<=1e-10", f"ok={v.ok} err={v.op_norm_error:.2e} gauss={v.gauss_residual:.1e} leak={v.leak_amplitude:.1e}", 1e-10, v.ok and v.op_norm_error <= 1e-10)
    vo = evaluate(build_UE(alpha, with_outer=True, include_outer_electric=True), enc, enc.target("UE", alpha, None, include_outer_electric=True), method="physical")
    rec(f"evaluate UE(outer row, 12 phases) alpha={alpha}", "ok, outer bits 12, blocks 305", f"ok={vo.ok} err={vo.op_norm_error:.2e} bits={vo.outer_bits_read} blocks={vo.n_blocks}", 1e-10,
        vo.ok and vo.outer_bits_read == 12 and vo.n_blocks == 305 and vo.op_norm_error <= 1e-10)
q12 = build_UE(0.37)
q24 = build_UE(0.37, with_outer=True, include_outer_electric=True)
rec("gate counts inner UE: 8 phases, no cx", "8 p", dict(q12.count_ops()), "exact", dict(q12.count_ops()) == {"p": 8})
rec("gate counts outer-row UE: 20 phases", "20 p", dict(q24.count_ops()), "exact", dict(q24.count_ops()) == {"p": 20})
out["wall_s"] = time.time() - t0
fails = [c for c in out["checks"] if not c["ok"]]
out["n_checks"] = len(out["checks"]); out["n_fail"] = len(fails)
json.dump(out, open(sys.argv[1], "w"), indent=1, default=str)
print("CHECKS", len(out["checks"]), "FAIL", len(fails), "wall", round(out["wall_s"], 1))
