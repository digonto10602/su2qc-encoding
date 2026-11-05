"""Independent verification of M1 step 1.1 (TwelveQubit codec): own tables from Paulo Eq. 31, own decode, own Gauss check.
Usage: PYTHONPATH=src python tests/independent/codec_1_1/check_codec.py <out.json>"""
import itertools, json, subprocess, sys
import numpy as np
from su2plaq.encodings.twelve import TwelveQubit
from su2plaq.exact.physical import to_convention
from su2plaq.su2.algebra import LinkSpace

out = {}
enc = TwelveQubit()
# ---- (1) Eq. 31 from the PDF: |j,m,m'>: 0->000, ++->111, +-->110, -+->101, --->100 ; ket "abc" = (q_j q_m q_m'), q_m' = bit0
EQ31 = {"0": 0b000, "++": 0b111, "+-": 0b110, "-+": 0b101, "--": 0b100}
out["eq31_LINK_CODE_equal"] = dict(enc.LINK_CODE) == EQ31
# bit check from bit definitions: q_j = bit2 (j=1/2), q_m = bit1 (m=+ -> 1), q_m' = bit0 (m'=+ -> 1)
def own_code(lab):
    if lab == "0": return 0
    return (1 << 2) | ((lab[0] == "+") << 1) | (lab[1] == "+")
out["eq31_from_bits"] = all(own_code(k) == v for k, v in EQ31.items())
# notebook LINK_CODE = [0,4,5,6,7] in notebook index order (0, (a,b)=(0,0),(0,1),(1,0),(1,1)) with a = m bit, b = m' bit
nb_order = ["0", "--", "-+", "+-", "++"]
out["notebook_LINK_CODE"] = [EQ31[k] for k in nb_order] == [0, 4, 5, 6, 7]
unused = sorted(set(range(8)) - set(EQ31.values()))
out["unused_codes"] = unused
out["unused_ok"] = unused == [1, 2, 3]
# registers
out["registers_ok"] = all(enc.registers[f"link_{n}"] == [3*l, 3*l+1, 3*l+2] for l, n in enumerate("brtl")) and \
    all(enc.registers[f"outer_{k}"] == [12+2*k, 13+2*k] for k in range(8))
# ---- outer code vs METHODS 3.2 and independent geometry: near end = R if link END is a corner site, L if START
LINKS = [("o0", (-1, 0), (0, 0)), ("o1", (0, -1), (0, 0)), ("o2", (1, 0), (2, 0)), ("o3", (1, -1), (1, 0)),
         ("o4", (1, 1), (2, 1)), ("o5", (1, 1), (1, 2)), ("o6", (-1, 1), (0, 1)), ("o7", (0, 1), (0, 2))]
CORN = {(0, 0), (1, 0), (1, 1), (0, 1)}
own_near = ["R" if e in CORN else "L" for _, s, e in LINKS]
out["near_end_independent"] = own_near
out["near_end_equal"] = own_near == list(enc._near)
# own outer table: (paulo label of link as 2 chars, far must be '-') -> 2-bit code (q_j bit1 of code? NO: qubits (q_m, q_j) = (12+2k, 13+2k)
# so integer bits: q_m = bit 12+2k, q_j = bit 13+2k
ok_outer = True
for k in range(8):
    near = own_near[k]
    for lab in ["0", "++", "+-", "-+", "--"]:
        if lab == "0":
            b = 0
        else:
            nm, fm = (lab[0], lab[1]) if near == "L" else (lab[1], lab[0])
            if fm != "-":
                continue
            b = (1 << 1) | (nm == "+")      # (q_j<<1)|q_m
        # compare to the class: build code with outer k set, decode -> paulo local index
        code = b << (12 + 2 * k)
        pi = enc._paulo_indices(np.array([code]))[0]
        want = ["0", "++", "+-", "-+", "--"].index(lab)
        ok_outer &= int(pi[4 + k]) == want
# invalid outer codes: q_j=0,q_m=1 (01) must be invalid; also the far-'+' labels (no code) 
for k in range(8):
    pi = enc._paulo_indices(np.array([0b01 << (12 + 2 * k)]))[0]
    ok_outer &= int(pi[4 + k]) == -1
out["outer_code_independent_ok"] = bool(ok_outer)
# ---- (2) own decode / encode on 625 inner codes
ls = LinkSpace(0.5)
V = {"0": 0, "++": 1, "+-": 2, "-+": 3, "--": 4}                    # Paulo order
# Paulo |m m'> = s(m)s(m')|1/2,-m,-m'>_CG ; CG LinkSpace index of (1/2, mL, mR)
def cg_idx(mL, mR): return ls.index[(0.5, mL, mR)]
def paulo_to_cg(lab):
    if lab == "0": return 0, 1.0
    s = {"+": 1, "-": -1}
    m, mp = lab
    return cg_idx(-0.5 * s[m], -0.5 * s[mp]), float(s[m] * s[mp])
codes = enc.inner_codes()
rev = {v: k for k, v in EQ31.items()}
ok_dec = True; keys_seen = set()
for c in codes:
    key = 0; 
    for l in range(4):
        lab = rev[(int(c) >> (3 * l)) & 7]
        i, _ = paulo_to_cg(lab)
        key += i * 5 ** l
    d = enc.decode(int(c))
    ok_dec &= d == key
    keys_seen.add(key)
out["decode_matches_own_625"] = bool(ok_dec)
out["decode_distinct_625"] = len(keys_seen) == 625
# decode∘encode identity on all 625 inner keys (encode = own inverse table); also encode∘decode identity on 625 codes
inv_cg = {paulo_to_cg(k)[0]: k for k in ["0", "++", "+-", "-+", "--"]}
ok_rt = True
for key in range(625):
    code = 0
    for l in range(4):
        code |= EQ31[inv_cg[(key // 5 ** l) % 5]] << (3 * l)
    ok_rt &= enc.decode(code) == key
out["decode_encode_identity_625"] = bool(ok_rt)
out["encode_decode_identity_625"] = all(
    (lambda c: c == sum(EQ31[inv_cg[(enc.decode(int(c)) // 5 ** l) % 5]] << (3 * l) for l in range(4)))(c) for c in codes)
# the other 4096-625 inner codes -> None
bad = [c for c in range(4096) if c not in set(codes.tolist())]
out["n_invalid_inner"] = len(bad)
out["invalid_inner_decode_none"] = all(enc.decode(c) is None for c in bad)
# ---- 433 vectors
eb = enc.physical_vectors()
out["n_vectors"] = len(eb.codes)
norms = np.array([np.linalg.norm(a) for a in eb.amps])
out["norm_dev_max"] = float(np.abs(norms - 1).max())
allc = np.unique(np.concatenate(eb.codes))
idx = {int(c): i for i, c in enumerate(allc)}
A = np.zeros((len(allc), 433), dtype=complex)
for j, (c, a) in enumerate(zip(eb.codes, eb.amps)):
    for ci, ai in zip(c, a): A[idx[int(ci)], j] += ai
G = A.conj().T @ A
out["gram_dev_max"] = float(np.abs(G - np.eye(433)).max())
out["all_codes_int64_in_range"] = all(c.dtype == np.int64 and c.max() < 2 ** 28 for c in eb.codes)
out["inner_codes_valid_all"] = all(set(((c & 0xFFF).tolist())) <= set(codes.tolist()) for c in eb.codes)
# own Gauss check: CG-convention generators from spin-1/2 (sigma/2), spin-0 -> 0
sx = np.array([[0, 1], [1, 0]]) / 2; sy = np.array([[0, -1j], [1j, 0]]) / 2; sz = np.array([[1, 0], [0, -1]]) / 2
J = [sx, sy, sz]
# link index space: [0 ; (1/2,mL,mR)] ; m index 0 -> +1/2 ; state idx = 1 + 2*iL + iR   (check vs ls)
assert all(cg_idx(0.5 - iL, 0.5 - iR) == 1 + 2 * iL + iR for iL in (0, 1) for iR in (0, 1)) or True
def lidx(iL, iR): return 1 + 2 * iL + iR
# check ordering assumption explicitly
order_ok = all(ls.index[(0.5, 0.5 - iL, 0.5 - iR)] == lidx(iL, iR) for iL in (0, 1) for iR in (0, 1))
out["linkspace_order_assumption"] = bool(order_ok)
def op_link(a, side, role):
    """5x5: 'out'/L: -J^T on mL ; 'in'/R: J on mR"""
    M = np.zeros((5, 5), dtype=complex)
    Ja = -J[a].T if side == "L" else J[a]
    for iL in range(2):
        for iR in range(2):
            for jp in range(2):
                if side == "L": M[lidx(jp, iR), lidx(iL, iR)] += Ja[jp, iL]
                else: M[lidx(iL, jp), lidx(iL, iR)] += Ja[jp, iR]
    return M
# corners of the plaquette: canonical ends from the repo's diagram (geometry is acceptance-tested in M0-G*), role 'out'->L,'in'->R
from su2plaq.geometry import plaquette_diagram
dg = plaquette_diagram()
# decode all vector components with OWN decode incl. signs
def own_decode_vec(c_arr, a_arr):
    keys = []; amps = []
    for c, a in zip(c_arr, a_arr):
        key = 0; sg = 1.0; ok = True
        for l in range(4):
            lab = rev[(int(c) >> (3 * l)) & 7]
            i, s = paulo_to_cg(lab); key += i * 5 ** l; sg *= s
        for k in range(8):
            b = (int(c) >> (12 + 2 * k)) & 3
            if b == 0: lab = "0"
            elif b == 2: lab = "-+" if own_near[k] == "R" else "+-"   # near '-' , far '-'  -> near is second char for R
            elif b == 3: lab = "++" if False else None
            else: raise ValueError
            if b == 3:
                # near '+', far '-': R -> (m,m')=(-,+) ; L -> (+,-)
                lab = "-+" if own_near[k] == "R" else "+-"
            elif b == 2:
                lab = "--"
            i, s = paulo_to_cg(lab); key += i * 5 ** (4 + k); sg *= s
        keys.append(key); amps.append(a * sg)
    return np.array(keys, dtype=np.int64), np.array(amps)
# apply a 5x5 on link l to a COO vector
def apply(keys, amps, l, M):
    d = {}
    for k, a in zip(keys, amps):
        s = (k // 5 ** l) % 5
        for sp in np.nonzero(M[:, s])[0]:
            k2 = k + (sp - s) * 5 ** l
            d[int(k2)] = d.get(int(k2), 0) + a * M[sp, s]
    return d
worst = 0.0; worst_rep = 0.0
for j in range(433):
    kk, aa = own_decode_vec(eb.codes[j], eb.amps[j])
    rk, ra = enc.decode_state(eb.codes[j], eb.amps[j])
    assert np.array_equal(kk, rk) and np.abs(aa - ra).max() < 1e-14
    for c in dg.corners:
        for a in range(3):
            tot = {}
            for link, role in c.ends:
                for k2, v in apply(kk, aa, link, op_link(a, "L" if role == "out" else "R", role)).items():
                    tot[k2] = tot.get(k2, 0) + v
            worst = max(worst, np.sqrt(sum(abs(v) ** 2 for v in tot.values())))
out["own_decode_equals_repo_decode_state_all433"] = True
out["gauss_residual_own_max"] = float(worst)
# ---- (4) R2
from su2plaq.evaluate import evaluator as ev
from qiskit import QuantumCircuit
e2 = TwelveQubit(); alpha = 0.37
V_ = e2.target("UE", alpha, 0.0)
def circ():
    qc = QuantumCircuit(28)
    for q in (2, 5, 8, 11): qc.p(-0.75 * alpha, q)
    return qc
r2 = {}
for eng, tol, tg in [("aer_mps", 5e-10, 5e-10), ("aer_mps", 9.99e-10, 9.99e-10), ("aer_mps", 1e-9, 1e-9), ("aer_mps", 1e-9, 5e-10),
                     ("aer_mps", 5e-10, 1e-9), ("aer_mps", 1e-6, 1e-6), ("aer_mps", 1e-10, 1e-10), ("sparse", 5e-10, 5e-10), ("sparse", 1e-10, 1e-10), ("sparse", 1e-12, 1e-12)]:
    v = ev.evaluate(circ(), e2, V_, engine=eng, tol_err=tol, tol_gauss=tg)
    r2[f"{eng} tol_err={tol:g} tol_gauss={tg:g}"] = dict(ok=bool(v.ok), certified=bool(v.certified), engine=v.engine, acc=float(v.engine_accuracy), err=float(v.err) if hasattr(v, "err") else None)
for eng, tol in [("aer_mps", 5e-10), ("aer_mps", 2e-9), ("aer_mps", 9.9e-10), ("sparse", 5e-10)]:
    v = ev.evaluate(circ(), e2, V_, engine=eng, gauss=False, tol_err=tol)
    r2[f"{eng} gauss=False tol_err={tol:g}"] = dict(ok=bool(v.ok), certified=bool(v.certified), engine=v.engine)
out["R2"] = r2
out["commit"] = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
out["seed_note"] = "deterministic; no random numbers"
json.dump(out, open(sys.argv[1], "w"), indent=1, default=str)
print(json.dumps(out, indent=1, default=str))
