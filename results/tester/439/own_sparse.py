"""Tester 439: LSH round 2.  Own 24-bit LSH codes, own exact targets (expm of the 6j magnetic block, diagonal U_E), own sparse gate-walk
engine (dict of basis-state amplitudes; any <=3-qubit gate via its Qiskit matrix), run on ALL 433 physical states x 3 angle pairs, for the
five round-2 programs, both on the circuit as built (native rccx/ch) and on the fully lowered circuit (own lowering = qiskit decompose until
{cx,h,s,sdg,t,tdg,x,z,rz,p,u1,u2,u3,u,id}).  Also: outer-register role scan, outer-changed weight, dirty-ancilla weight, leak,
final-state Abelian Gauss-law residual, own CX/T recount (pygridsynth) vs archive.
Run: PYTHONPATH=src taskset -c 0-1 tools/run-capped python results/tester/439/own_sparse.py   -> results/tester/439/own_sparse.json
No RNG is used (all angle pairs fixed); seed recorded as null."""
import json, math, subprocess, sys, time, hashlib, pathlib
from collections import defaultdict
import numpy as np
import scipy.linalg as sla
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator
from su2plaq.exact import spinnet as RB
from su2plaq.compress import evaluate as E
from su2plaq.lsh import loop as LL
import pygridsynth

ROOT = pathlib.Path("/home/digimonk/Projects/su2qc-encoding")
PAIRS = [(0.37, 0.61), (0.91, 0.23), (1.7, 1.0)]
PROGS = {"r02-F1-002": "F1/002-free-end-walk-v.py", "r02-F2-002": "F2/002-tctt-sa-walk18.py",
         "r02-F3-002": "F3/002-seed-carrier-negative.py", "r02-F4-002": "F4/002-fold-mux-merged-end-toggle.py",
         "r02-F5-002": "F5/002-two-flag-walk-table.py", "r00-seed-005": "seed/005-wrap_sn_headline.py"}

# ---------------------------------------------------------------- own codes and targets
labels = RB.labels(jmax=0.5)
assert len(labels) == 433
PN = [(3, 0), (0, 1), (1, 2), (2, 3)]
OUT = [(4, 5), (6, 7), (8, 9), (10, 11)]


def site_bits(j1, j2, J):
    return int(round(j1 + j2 - J)) | (int(round(j2 + J - j1)) << 1) | (int(round(J + j1 - j2)) << 2)


def my_code(label):
    j, J = label
    code = 0
    for c in range(4):
        code |= site_bits(j[PN[c][0]], j[PN[c][1]], J[c]) << (3 * c)
        code |= site_bits(j[OUT[c][0]], j[OUT[c][1]], J[c]) << (12 + 3 * c)
    return code


mine = [my_code(l) for l in labels]
c2i = {c: k for k, c in enumerate(mine)}
assert len(c2i) == 433
HB = RB.h_magnetic_phys_6j(labels)
HE = np.array([sum(x * (x + 1) for x in j[:4]) for j, _ in labels])
assert np.allclose(HB, HB.conj().T)


def target(alpha, beta):
    return sla.expm(-1j * beta * HB) @ np.diag(np.exp(-1j * alpha * HE))


# Abelian Gauss law on the inner links (own, from the bit definitions): per site (l_pn, l_nv, l_vp); N_n = l_pn + l_nv, N_p = l_vp + l_pn;
# link c -> c+1 requires N_n(c) = N_p(c+1); valid site codes = 5 patterns.
VALID_SITE = {(0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1), (0, 1, 1)}


def site(x, c): return ((x >> 3 * c) & 1, (x >> (3 * c + 1)) & 1, (x >> (3 * c + 2)) & 1)


def gauss_viol(x):
    s = [site(x, c) for c in range(4)]
    if any(t not in VALID_SITE for t in s): return True
    return any(s[c][0] + s[c][1] != s[(c + 1) % 4][2] + s[(c + 1) % 4][0] for c in range(4))


assert not any(gauss_viol(c & 0xFFF) for c in mine), "own Gauss law disagrees with the 433 codes"

# ---------------------------------------------------------------- own sparse engine
ISQ = 1 / math.sqrt(2)
_MAT = {}


def gmat(nm, ps):
    key = (nm, tuple(ps))
    if key not in _MAT:
        from qiskit.circuit.library import standard_gates as sg
        cls = {"rccx": sg.RCCXGate, "ch": sg.CHGate, "u": sg.UGate, "u1": sg.U1Gate, "u2": sg.U2Gate, "u3": sg.U3Gate, "cz": sg.CZGate,
               "ccx": sg.CCXGate, "y": sg.YGate, "id": sg.IGate}[nm]
        _MAT[key] = Operator(cls(*ps)).data
    return _MAT[key]


def gates_of(qc):
    g = []
    for inst in qc.data:
        nm = inst.operation.name
        if nm == "barrier": continue
        g.append((nm, [qc.find_bit(q).index for q in inst.qubits], [float(p) for p in inst.operation.params]))
    return g


DIAG = {"rz", "p", "s", "sdg", "t", "tdg", "z"}


def sim(gates, code):
    st = {code: 1.0 + 0j}
    for nm, q, p in gates:
        new = {}
        if nm == "cx":
            c, t = 1 << q[0], 1 << q[1]
            for k, v in st.items(): new[k ^ t if k & c else k] = v
        elif nm == "x":
            t = 1 << q[0]
            for k, v in st.items(): new[k ^ t] = v
        elif nm == "h":
            b = 1 << q[0]; acc = defaultdict(complex)
            for k, v in st.items():
                k0 = k & ~b
                acc[k0] += v * ISQ
                acc[k0 | b] += v * ISQ * (-1 if k & b else 1)
            new = {k: v for k, v in acc.items() if abs(v) > 1e-15}
        elif nm in DIAG:
            for k, v in st.items():
                b = (k >> q[0]) & 1
                ph = {"rz": lambda: np.exp(1j * p[0] * (b - 0.5)), "p": lambda: np.exp(1j * p[0] * b), "z": lambda: -1 if b else 1,
                      "s": lambda: 1j if b else 1, "sdg": lambda: -1j if b else 1,
                      "t": lambda: np.exp(1j * math.pi / 4) if b else 1, "tdg": lambda: np.exp(-1j * math.pi / 4) if b else 1}[nm]()
                new[k] = v * ph
        else:                                   # any <=3-qubit gate by its matrix, little-endian over qargs
            M = gmat(nm, p); n = len(q); acc = defaultdict(complex)
            for k, v in st.items():
                col = sum(((k >> q[i]) & 1) << i for i in range(n))
                k0 = k
                for i in range(n): k0 &= ~(1 << q[i])
                for row in np.flatnonzero(np.abs(M[:, col]) > 1e-14):
                    kk = k0
                    for i in range(n): kk |= ((int(row) >> i) & 1) << q[i]
                    acc[kk] += v * M[row, col]
            new = {k: v for k, v in acc.items() if abs(v) > 1e-15}
        st = new
    return st


def block(gates):
    M = np.zeros((433, 433), dtype=complex); dirty = leak = outer_ch = gauss = 0.0; X = defaultdict(lambda: np.zeros(433, complex))
    max_col = {"dirty": 0.0, "leak": 0.0, "outer": 0.0, "gauss": 0.0}
    for k in range(433):
        d = l = o = g = 0.0
        for key, v in sim(gates, mine[k]).items():
            w = abs(v) ** 2
            if key >> 24: d += w; continue                         # ancilla not returned clean
            if (key >> 12) != (mine[k] >> 12): o += w              # outer register changed
            if key in c2i: M[c2i[key], k] += v
            else: l += w; X[key][k] += v                           # outside the 433 physical codes
            if gauss_viol(key & 0xFFF): g += w                     # Abelian Gauss law on the inner links violated
        for n_, val in (("dirty", d), ("leak", l), ("outer", o), ("gauss", g)): max_col[n_] = max(max_col[n_], val)
    return M, max_col


def dist(M, V):
    ph = np.vdot(V.ravel(), M.ravel()); ph /= abs(ph)
    return float(np.linalg.norm(M - ph * V, 2)), ph


BASIS = {"cx", "h", "s", "sdg", "t", "tdg", "x", "z", "rz", "p", "u1", "u2", "u3", "u", "id", "y"}


def lower(qc):
    q = qc
    for _ in range(12):
        if {i.operation.name for i in q.data} <= BASIS: return q
        q = q.decompose()
    raise RuntimeError("lowering did not terminate")


def count(qc, eps=1e-6):
    q = lower(qc)
    cx = tf = 0; rots = []
    for ins in q.data:
        nm = ins.operation.name; ps = [float(x) for x in ins.operation.params]
        if nm == "cx": cx += 1
        elif nm in ("t", "tdg"): tf += 1
        elif nm in ("rz", "p", "u1"): rots.append(ps[0])
        elif nm == "u":
            th, ph, lam = ps
            if abs(th) < 1e-12: rots.append(ph + lam)
            elif min(abs(th - math.pi / 2), abs(th - math.pi)) < 1e-12 and all(abs(v / (math.pi / 2) - round(v / (math.pi / 2))) < 1e-9 for v in (ph, lam)): pass
            else: raise RuntimeError(f"u{ps}")
        elif nm == "u2":
            if not (abs(ps[0]) < 1e-12 and abs(ps[1] - math.pi) < 1e-12): raise RuntimeError(f"u2{ps}")
        elif nm in ("h", "s", "sdg", "x", "z", "id", "y"): pass
        else: raise RuntimeError(nm)
    tsum = nrot = 0
    for th in rots:
        k = th / (math.pi / 4)
        if abs(k - round(k)) < 1e-9: tf += int(round(k)) % 2
        else: tsum += str(pygridsynth.gridsynth_gates(theta=th, epsilon=eps)).count("T"); nrot += 1
    return {"cx": cx, "t_fixed": tf, "n_rot": nrot, "t_total": tf + tsum, "qubits": qc.num_qubits}


def outer_roles(qc):
    """role of each gate on outer qubits 12..23 in the lowered circuit: 'control' (cx control), 'phase' (diagonal 1q), 'write' (anything else)."""
    q = lower(qc); roles = defaultdict(lambda: defaultdict(int)); data_qubits = set()
    for ins in q.data:
        nm = ins.operation.name; qs = [q.find_bit(b).index for b in ins.qubits]
        for pos, b in enumerate(qs):
            if 12 <= b < 24:
                if nm == "cx" and pos == 0: roles[b]["cx_control"] += 1
                elif nm in DIAG or nm in ("u1",): roles[b]["diag_1q"] += 1
                else: roles[b]["WRITE:" + nm + f"@{pos}"] += 1
    return {int(k): dict(v) for k, v in roles.items()}


if __name__ == "__main__":
    out = {"commit": subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip(),
           "seed": None, "pairs": PAIRS, "engine": "own dict sparse engine, own 24-bit codes, own expm target", "programs": {}}
    t00 = time.time()
    for eid, rel in PROGS.items():
        path = ROOT / "compress/programs/lsh" / rel
        ent = json.load(open(ROOT / f"compress/archive/lsh/entries/{eid}.json"))
        rec = {"sha_file": hashlib.sha256(path.read_bytes()).hexdigest(), "sha_entry": ent["program_sha256"]}
        qc0 = E.load_program(str(path)).build(LL.spec()).circuit()
        rec["count_ops_native"] = dict(qc0.count_ops()); rec["count_ops_lowered"] = dict(lower(qc0).count_ops())
        rec["recount"] = count(qc0); rec["archive_key"] = ent["key"]; rec["archive_metrics"] = {k: ent["metrics_raw"][k] for k in ("cx", "t_fixed", "n_rot", "t_eps", "depth_ct", "qubits")}
        rec["outer_roles"] = outer_roles(qc0)
        rec["by_pair"] = {}
        for (a, b) in PAIRS:
            t0 = time.time()
            qc = E.load_program(str(path)).build(LL.spec().with_angles(a, b)).circuit()
            V = target(a, b)
            Mn, sn = block(gates_of(qc)); en, _ = dist(Mn, V)
            Ml, sl = block(gates_of(lower(qc))); el, _ = dist(Ml, V)
            Mw, _ = block(gates_of(qc)) if False else (None, None)
            Vm = target(a, -b); ewrong, _ = dist(Mn, Vm)
            unit = float(np.linalg.norm(Mn.conj().T @ Mn - np.eye(433), 2))
            rec["by_pair"][f"{a},{b}"] = {"err_native": en, "err_lowered": el, "err_vs_minus_beta": ewrong, "unitarity_defect_433block": unit,
                                         "stats_native": sn, "stats_lowered": sl, "seconds": time.time() - t0}
            print(eid, (a, b), f"native {en:.2e} lowered {el:.2e} wrong-sign {ewrong:.3f} dirty/leak/outer/gauss {sn}", f"{time.time()-t0:.1f}s", flush=True)
        out["programs"][eid] = rec
    out["wall_s"] = time.time() - t00
    json.dump(out, open(ROOT / "results/tester/439/own_sparse.json", "w"), indent=1, default=str)
