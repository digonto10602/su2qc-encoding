"""Tester 204: independent check of build_UB / build_step against own JW reference + own sparse simulator."""
import sys, json, time, subprocess, importlib.util
sys.path.insert(0, 'src')
import numpy as np
from scipy.linalg import expm
spec = importlib.util.spec_from_file_location('mysim', 'results/rishon/tester-204-mysim.py'); ms = importlib.util.module_from_spec(spec); spec.loader.exec_module(ms)
import su2plaq.circuits.rishon as C
t0 = time.time()
out = {'commit': subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).decode().strip() + '+uncommitted', 'seed': None}
codes, HB, HE = ms.own_reference()
out['n_codes'] = len(codes)
ev = np.linalg.eigvalsh(HB)
out['HB_spectrum_extremes'] = [float(ev[0]), float(ev[-1]), 4 * np.sqrt(2)]
I = np.eye(1296)

def opnorm_phase(M, V):
    tr = np.trace(V.conj().T @ M); ph = tr / abs(tr)
    return float(np.linalg.norm(M - ph * V, 2)), ph, float(np.linalg.norm(M - V, 2))

def run(qc):
    nq = qc.num_qubits
    assert nq == 26, nq
    s = ms.Sim(codes, nq).run(qc)
    M, w_anc, w_out = s.block(codes, 0xFFFF)
    return M, w_anc, w_out, s

# ---- structure of the circuit
qcs = {}
res = {}
for beta in (0.23, 0.61, 1.0, 2.0):
    tt = time.time()
    qc = C.build_UB(beta)
    M, w_anc, w_out, s = run(qc)
    V = expm(-1j * beta * HB)
    e, ph, e_nophase = opnorm_phase(M, V)
    unit = float(np.linalg.norm(M.conj().T @ M - I, 2))
    res[str(beta)] = {'opnorm_after_phase': e, 'phase': [ph.real, ph.imag], 'opnorm_no_phase': e_nophase,
                      'max_anc_dirty_weight': float(w_anc.max()), 'max_leak_out_of_codes_weight': float(w_out.max()),
                      'M_unitarity': unit, 'my_dropped_l2_total': float(np.sqrt((s.dw ** 2).sum())), 'my_max_support': int(s.maxsize),
                      'wall_s': time.time() - tt}
    print('UB', beta, res[str(beta)], flush=True)
out['UB'] = res

# ---- angles vs kappa (from OWN H_B components) and factor convention
from scipy.sparse.csgraph import connected_components
import scipy.sparse as sp
from collections import Counter
nc, lab = connected_components(sp.csr_matrix(np.abs(HB) > 1e-12), directed=False)
cnt = np.bincount(lab)
kap = Counter()
for ci in range(nc):
    if cnt[ci] == 1: continue
    idx = np.flatnonzero(lab == ci)
    w = np.linalg.eigvalsh(HB[np.ix_(idx, idx)]); kap[round(float(w[-1]), 9)] += 1
out['own_kappa_counts'] = {str(k): v for k, v in sorted(kap.items())}
ang = {}
for beta in (0.23, 0.61, 1.0, 2.0):
    qc = C.build_UB(beta)
    ops = Counter()
    for inst in qc.data:
        if inst.operation.params:
            ops[(inst.operation.name, round(abs(float(inst.operation.params[0])) / beta, 9))] += 1
    ang[str(beta)] = {f'{k[0]}:{k[1]}': v for k, v in sorted(ops.items())}
out['angle_over_beta'] = ang
out['expected_2kappa'] = {str(round(2 * k, 9)): v for k, v in sorted(kap.items())}
out['8sqrt2'] = 8 * np.sqrt(2)
# sign: angle(beta)/beta identical for all betas (linear, no offset)
def angs(beta): return np.array([float(i.operation.params[0]) for i in C.build_UB(beta).data if i.operation.params])
a1, a2 = angs(0.23), angs(2.0)
out['angles_linear_in_beta_max_dev'] = float(np.abs(a1 / 0.23 - a2 / 2.0).max())
out['n_param_gates'] = int(len(a1))
# skeleton across angles
def skel(qc): return [(i.operation.name, tuple(qc.find_bit(q).index for q in i.qubits)) for i in qc.data]
out['skeleton_equal_all_betas'] = bool(all(skel(C.build_UB(b)) == skel(C.build_UB(0.61)) for b in (0.23, 1.0, 2.0)))
out['skeleton_equal_step_across_angles'] = bool(skel(C.build_step(0.37, 0.61, 1)) == skel(C.build_step(1.7, 1.0, 1)) and skel(C.build_step(0.37, 0.61, 2)) == skel(C.build_step(1.7, 1.0, 2)))
# beta -> 0: gate param -> 0 (only the crx angles change); beta=0 gives identity?
M0, wa, wo, s0 = run(C.build_UB(0.0))
out['UB_beta0_minus_identity'] = float(np.linalg.norm(M0 - I, 2))

# ---- steps
st = {}
for order in (1, 2):
    for al, be in ((0.37, 0.61), (1.70, 1.0)):
        qc = C.build_step(al, be, order)
        M, w_anc, w_out, s = run(qc)
        UB = expm(-1j * be * HB)
        D = lambda a: np.diag(np.exp(-1j * a * HE))
        if order == 1: ref = UB @ D(al); wrong = D(al) @ UB; other = None
        else: ref = D(al / 2) @ UB @ D(al / 2); wrong = UB @ D(al); other = D(al) @ UB
        e, ph, e0 = opnorm_phase(M, ref)
        ew = opnorm_phase(M, wrong)[0]
        # order 1 vs order 2 target distinguishing
        ref_other = (D(al / 2) @ UB @ D(al / 2)) if order == 1 else UB @ D(al)
        eo = opnorm_phase(M, ref_other)[0]
        st[f'order{order},a{al},b{be}'] = {'opnorm_after_phase': e, 'phase': [ph.real, ph.imag], 'vs_wrong_order_UEUB_or_UBUE': ew,
                                           'vs_other_trotter_order': eo, 'dirty': float(w_anc.max()), 'leak': float(w_out.max()), 'dropped_l2': float(np.sqrt((s.dw ** 2).sum()))}
        print('step', order, al, be, st[f'order{order},a{al},b{be}'], flush=True)
out['step'] = st
out['wall_s'] = time.time() - t0
json.dump(out, open('results/rishon/tester-204-ub-independent.json', 'w'), indent=1, default=str)
