"""Tester 221: independent robust key of archive entries (prompts/203 sec.13 E3).  For every id given: rebuild at the 20 pairs of the locked angle set (my own
generator, seed 20261107), own recount (own lowering + hand macro table + own pygridsynth call, tester-217-recount.py) -> CX, T(1e-6), depth_CT, qubits per pair;
own angle-linearity: every rotation parameter (rz p crz crx cp) of the nominal circuit is fitted by least squares over the 20 pairs to [alpha, beta, sqrt2 beta],
coefficients must be rational with denominator <= 64 (|m| <= 64 d) and the residual <= 1e-9 at all 20 pairs.  usage: tester-221-rank.py id [id...]"""
import sys, os, json, math, subprocess, importlib.util
from fractions import Fraction
import numpy as np
here = os.path.dirname(os.path.abspath(__file__))
def imp(n, f):
    sp = importlib.util.spec_from_file_location(n, os.path.join(here, f)); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m
R = imp("rc217", "tester-217-recount.py"); C = imp("c221", "tester-221-common.py")
R.HAND['cp'] = (2, 3, 0)
from su2plaq.rishon.compress.spec import rishon_spec
rng = np.random.default_rng(20261107)
alpha = rng.uniform(0.05, 2.0, 20); beta = rng.uniform(0.05, 1.2, 20)
pairs = list(zip(alpha.tolist(), beta.tolist()))
s0 = rishon_spec('step')
ROT = ('rz', 'p', 'crz', 'crx', 'cp')
def skel(qc): return [(i.operation.name, tuple(qc.find_bit(q).index for q in i.qubits)) for i in qc.data]
def rot(qc): return [float(i.operation.params[0]) for i in qc.data if i.operation.name in ROT]
M = np.array([[a, b] for a, b in pairs])      # alpha, beta only: sqrt2*beta is collinear with beta over any pair set
for cid in sys.argv[1:]:
    nom = C.build_circuit(cid, s0)
    sk0 = skel(nom)
    rows, angs, sk_eq = [], [], True
    for a, b in pairs:
        qc = C.build_circuit(cid, s0.with_angles(a, b))
        sk_eq &= (skel(qc) == sk0); angs.append(rot(qc))
        r = R.recount(qc)
        rows.append(dict(cx=r['cx'], t_total=r['t_total'], depth_ct=r['depth_ct'], qubits=r['qubits'], n_rot=r['n_rot']))
    # linearity: angle(pair) = ca*alpha + cb*beta exactly (lstsq over 20 pairs); then ca = ma/d, cb = (mb + sqrt2 mg)/d with integers, d <= 64
    fits, linear = [], bool(sk_eq)
    Y = np.array(angs)
    S2 = math.sqrt(2)
    def rationalise(ca, cb):
        for d in range(1, 65):
            ma = ca * d
            if abs(ma - round(ma)) > 1e-9 or abs(round(ma)) > 128: continue
            cands = []
            for mg in range(-128, 129):
                mb = cb * d - mg * S2
                if abs(mb - round(mb)) < 1e-9 and abs(round(mb)) <= 128:
                    cands.append((abs(round(mb)) + abs(mg), int(round(mb)), mg))
            if cands:
                c = min(cands); return (int(round(ma)), c[1], c[2], d)
        return None
    for j in range(Y.shape[1] if sk_eq else 0):
        coef = np.linalg.lstsq(M, Y[:, j], rcond=None)[0]
        res = float(np.abs(M @ coef - Y[:, j]).max())
        fit = rationalise(float(coef[0]), float(coef[1]))
        fits.append(dict(coef=coef.tolist(), resid=res, fit=fit))
        if fit is None or res > 1e-9: linear = False
    out = dict(cid=cid, skeleton_equal=bool(sk_eq), cx=sorted({r['cx'] for r in rows}), qubits=sorted({r['qubits'] for r in rows}),
               t_sum=sum(r['t_total'] for r in rows), depth_sum=sum(r['depth_ct'] for r in rows), t_list=[r['t_total'] for r in rows],
               depth_list=[r['depth_ct'] for r in rows], linear=linear, fits=fits, n_rot=sorted({r['n_rot'] for r in rows}),
               commit=subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).decode().strip())
    json.dump(out, open(os.path.join(here, f'tester-221-rank-{cid}.json'), 'w'), indent=1)
    print(cid, 'cx', out['cx'], 'T_sum', out['t_sum'], 'depth_sum', out['depth_sum'], 'q', out['qubits'], 'linear', linear, 'skel', sk_eq, flush=True)
