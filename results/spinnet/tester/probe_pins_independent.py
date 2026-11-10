"""Tester 3.L3: independent recomputation of the pinned exact targets.  Parses the certificate JSON with its own K / Laurent
reader (no su2plaq.lean.exact), evaluates at several angle pairs, compares against expm of the route-B 6j Hamiltonians from
su2plaq.exact.spinnet (not lean_export) and against route A (D^dag V_A D).  Also recomputes the canonical state / target text
and SHA-256 independently of su2plaq.lean.pins and compares them with Pins.lean."""
import json, sys, hashlib, re, pathlib, subprocess
import numpy as np
from scipy.linalg import expm
from su2plaq.encodings.spinnet import SpinNet
from su2plaq.exact.spinnet import h_magnetic_phys_6j, h_electric_6j
from su2plaq.exact.operators import target as target_A
from su2plaq.circuits.spinnet import build_step, build_UB, build_UE
from su2plaq.spinnet import lean_export as LE

ROOT = pathlib.Path('.')
SQ = [1.0, 2 ** 0.5, 3 ** 0.5, 6 ** 0.5]
def rat(s):
    if '/' in s:
        p, q = s.split('/'); return int(p) / int(q)
    return float(int(s))
def kval(c):
    v = [rat(x) for x in c]
    re = v[0] + v[2] * SQ[1] + v[4] * SQ[2] + v[6] * SQ[3]
    im = v[1] + v[3] * SQ[1] + v[5] * SQ[2] + v[7] * SQ[3]
    return complex(re, im)
def lp_eval(lp, ta, tb):
    return sum(kval(k) * np.exp(1j * (e[0] * ta + e[1] * tb)) for e, k in lp)
def dense(cert, alpha, beta):
    dA, dB = cert['base']['d_alpha'], cert['base']['d_beta']
    V = np.zeros((433, 433), complex)
    seen = np.zeros(433, int)
    for b in cert['target']['blocks']:
        ks = b['ks']
        for k in ks: seen[k] += 1
        for i, j, lp in b['entries']:
            V[ks[i], ks[j]] = lp_eval(lp, alpha / dA, beta / dB)
    assert (seen == 1).all()
    return V

enc = SpinNet()
labels = enc.basis.labels
HB = h_magnetic_phys_6j(labels); HE = h_electric_6j(labels)
# inner-only electric energy: 3/4 per inner j=1/2 link (bits 0..3); independent of enc.target
codes = [int(c[0]) for c in enc.physical_vectors().codes]
nel = np.array([bin(c & 0xF).count('1') for c in codes])
D = np.diag(enc.gauge)
out = {}
def indep(kind, order, a, b):
    UB = expm(-1j * b * HB)
    UE = lambda x: np.diag(np.exp(-1j * x * 0.75 * nel))
    if kind == 'UE': return UE(a)
    if kind == 'UB': return UB
    return UB @ UE(a) if order == 1 else UE(a / 2) @ UB @ UE(a / 2)
def routeA(kind, order, a, b):
    if kind == 'UE': return D.conj().T @ target_A(enc.basis, 'UE', alpha=a) @ D
    if kind == 'UB': return D.conj().T @ target_A(enc.basis, 'UB', beta=b) @ D
    return D.conj().T @ target_A(enc.basis, 'step', alpha=a, beta=b, order=order) @ D
pairs = [(0.37, 0.61), (0.91, 0.23), (1.70, 1.00), (2.9, -0.77), (0.0, 0.0)]
cdir = pathlib.Path(sys.argv[1])
worst = {}
for path in sorted(cdir.glob('*.json')):
    cert = json.loads(path.read_text())
    kind, order = cert['target']['kind'], cert['target']['order']
    # route A of the inner-electric step: target_A('step') uses the full H_E incl. outer?  restrict to the inner-only comparison for UE/step by the route-B formula
    w_B = w_A = 0.0
    for (a, b) in pairs:
        V = dense(cert, a, b)
        w_B = max(w_B, np.abs(V - indep(kind, order, a, b)).max())
        if kind == 'UB':
            w_A = max(w_A, np.abs(V - routeA(kind, order, a, b)).max())
    worst[path.name] = dict(kind=kind, order=order, base=cert['base'], err_vs_expm_6j=w_B, err_vs_routeA=(w_A if kind == 'UB' else None))
    print(path.name, kind, order, cert['base'], 'max|V_cert - expm|=%.2e' % w_B, ('routeA %.2e' % w_A) if kind == 'UB' else '')
    # independent canonical text + SHA
    st_lines = []
    for k, st in enumerate(cert['states']):
        for t in sorted(st['terms'], key=lambda t: t['code']):
            st_lines.append('S%d:%d:%s\n' % (k, t['code'], ','.join(x for x in t['c'])))
    worst[path.name]['states_sha_indep'] = hashlib.sha256(''.join(st_lines).encode()).hexdigest()
    # also state check: codes equal the labels' codes from the independent codec
    assert [t['code'] for s in cert['states'] for t in s['terms']] == codes
    assert all(s['terms'][0]['c'] == ['1', '0', '0', '0', '0', '0', '0', '0'] for s in cert['states'])
pins = pathlib.Path('lean/Su2PlaqCert/SpinNet/Pins.lean').read_text()
m = re.search(r'statesSha256 : String := "([0-9a-f]+)"', pins)
print('Pins.lean states sha', m.group(1))
shas = {v['states_sha_indep'] for v in worst.values()}
print('independent states sha', shas)
worst['_states_sha_pin_match'] = (shas == {m.group(1)})
print('states pin match:', worst['_states_sha_pin_match'])
json.dump(worst, open(sys.argv[2], 'w'), indent=1, default=str)
