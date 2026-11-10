"""Tester-401: own implementation of the METHODS-lsh L6 fallback key; compared with decode_state on all 28 942 AGL-violating
data-valid codes.  Usage: PYTHONPATH=<src> python tester-401-fallback.py"""
import sys
from itertools import product
import numpy as np
from su2plaq.encodings.lsh import LSH
from su2plaq.geometry import plaquette_diagram
from su2plaq.su2.algebra import LinkSpace

enc = LSH(); ls = LinkSpace(0.5); diag = plaquette_diagram()
PN = [(3, 0), (0, 1), (1, 2), (2, 3)]; OUT = [(4, 5), (6, 7), (8, 9), (10, 11)]


def flux(s):
    l12, l23, l31 = s & 1, (s >> 1) & 1, (s >> 2) & 1
    return (l31 + l12, l12 + l23, l23 + l31)       # (N1, N2, N3)


def own_key(code):
    st = {i: None for i in range(12)}            # (j, mL, mR)
    for c in range(4):
        fi, fo = flux((code >> (3 * c)) & 7), flux((code >> (12 + 3 * c)) & 7)
        gin = -0.5 if fi[2] == 2 else 0.5         # inner ends: +1/2 unless J_in = 1
        gout = 0.5 if fo[2] == 2 else -0.5        # outer ends: -1/2 unless J_out = 1
        legs = [(PN[c][0], fi[0], gin), (PN[c][1], fi[1], gin), (OUT[c][0], fo[0], gout), (OUT[c][1], fo[1], gout)]
        for li, N, g in legs:
            if N == 0:
                continue
            role = dict(diag.corners[c].ends)[li]
            mL, mR = (st[li][1], st[li][2]) if st[li] else (0.5, 0.5)
            if role == "out":
                mL = -g                           # G^z = -m_L on an 'out' end
            else:
                mR = g                            # G^z = +m_R on an 'in' end
            st[li] = (0.5, mL, mR)
    return sum((ls.index[st[i]] if st[i] else 0) * 5 ** i for i in range(12))


phys = set(enc._codes.tolist())
outer_valid = [sum(s << (3 * i) for i, s in enumerate(ss)) for ss in product((0, 1, 2, 4, 6), repeat=4)]
bad = [c | (o << 12) for c in enc.inner_codes().tolist() for o in outer_valid if (c | (o << 12)) not in phys]
mism = 0
for c in bad:
    k, a = enc.decode_state(np.array([c]), np.array([1.0 + 0j]))
    if len(k) != 1 or int(k[0]) != own_key(c) or abs(a[0] - 1) > 1e-15:
        mism += 1
print("fallback own-L6 key vs decode_state: mismatches", mism, "of", len(bad))
