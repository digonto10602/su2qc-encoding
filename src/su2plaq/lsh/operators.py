"""Loop-string-hadron (LSH) operators (prompts/400 section 2, steps 7.1-7.2; docs/METHODS-lsh.md L2-L4).

Model of the point-split plaquette, (inner | outer) pairing, pure gauge, j_max = 1/2.
Built only from loop-number arithmetic (Raychowdhury-Stryker arXiv:1912.06133: loop basis Eq. (lij), factorisation table
Eqs. (loopEffectiveOps), vertex factors Eqs. (RLvertex)-(LLvertex)); never from 6j symbols or the electric basis.

Site code s (3 bits): bit 0 = l_12, bit 1 = l_23, bit 2 = l_31, legs (1, 2, 3) = (p, n, v) at an 'in' site (p/n = previous/next
inner link along the loop b -> r -> t -> l, v = virtual link) and (outer 1, outer 2, v) at an 'out' site.
Fluxes N_1 = l_31 + l_12, N_2 = l_12 + l_23, N_3 = l_23 + l_31; spin of a leg = N / 2.
24-bit code: 'in' site c at bits 3c..3c+2, 'out' site c at bits 12+3c..12+3c+2 (c = corner index 0..3).
"""
from __future__ import annotations

import functools
import itertools
import math

import numpy as np

VALID_SITE = (0b000, 0b001, 0b010, 0b100, 0b110)     # flux cap N_1 <= 1, N_2 <= 1 (physical links at j <= 1/2)
SITE_J1 = 0b110                                     # l_23 = l_31 = 1: virtual flux 2 (J = 1)
CORNER_PN = ((3, 0), (0, 1), (1, 2), (2, 3))        # (p(c), n(c)): inner link indices b r t l = 0 1 2 3
CORNER_OUT = ((4, 5), (6, 7), (8, 9), (10, 11))     # (outer 1, outer 2) link indices of corner c (Diagram.corners order)
LINK_NAMES = ("b", "r", "t", "l")
VERTEX_TYPES = ("LL", "RL", "RR", "LR")             # traversal type of corner c for U_b U_r U_t^dag U_l^dag
# VERTEX[c][i][k] = (sign, sigma_p, sigma_n): entry (i, k) of the vertex-factor matrix of corner c is
# sign * (N_n+1)^(-1/2) L^{sigma_p sigma_n}_{pn} (N_p+1)^(-1/2); row index = matrix index shared with corner c-1, column with c+1
VERTEX = (
    (((+1, -1, +1), (-1, -1, -1)), ((+1, +1, +1), (+1, +1, -1))),      # c0 (l, b): LL = [[ L-+, -L-- ], [ L++,  L+- ]]
    (((+1, +1, +1), (+1, +1, -1)), ((-1, -1, +1), (+1, -1, -1))),      # c1 (b, r): RL = [[ L++,  L+- ], [-L-+,  L-- ]]
    (((+1, +1, -1), (-1, +1, +1)), ((+1, -1, -1), (+1, -1, +1))),      # c2 (r, t): RR = [[ L+-, -L++ ], [ L--,  L-+ ]]
    (((-1, -1, -1), (-1, -1, +1)), ((+1, +1, -1), (-1, +1, +1))),      # c3 (t, l): LR = [[-L--, -L-+ ], [ L+-, -L++ ]]
)


def site_flux(s: int) -> tuple[int, int, int]:
    """(N_1, N_2, N_3) of a 3-bit site code (fluxes = twice the leg spins)."""
    if not 0 <= s < 8:
        raise ValueError(f"site code must be in 0..7, got {s}")
    l12, l23, l31 = s & 1, (s >> 1) & 1, (s >> 2) & 1
    return l31 + l12, l12 + l23, l23 + l31


def site_valid(s: int) -> bool:
    if not 0 <= s < 8:
        return False
    n1, n2, _ = site_flux(s)
    return n1 <= 1 and n2 <= 1


def site_code(j1: float, j2: float, j3: float) -> int:
    """Site code of leg spins (j1, j2, j3): l_12 = j1 + j2 - j3, l_23 = j2 + j3 - j1, l_31 = j3 + j1 - j2 (each 0 or 1)."""
    ls = (j1 + j2 - j3, j2 + j3 - j1, j3 + j1 - j2)
    out = 0
    for k, l in enumerate(ls):
        r = round(l)
        if abs(l - r) > 1e-12 or r not in (0, 1):
            raise ValueError(f"spins {(j1, j2, j3)} have no loop numbers in {{0, 1}}")
        out |= r << k
    return out


def ladder_amplitude(l: tuple[int, int, int], sigma_p: int, sigma_n: int):
    """<l'| (N_n + 1)^(-1/2) L^{sigma_p sigma_n}_{12} (N_p + 1)^(-1/2) |l> for loop numbers l = (l_12, l_23, l_31) (any
    non-negative integers), legs (1, 2) = (p, n).  Returns (l', amplitude) or None when the amplitude vanishes."""
    l12, l23, l31 = l
    S = l12 + l23 + l31
    if (sigma_p, sigma_n) == (+1, +1):
        new, amp = (l12 + 1, l23, l31), math.sqrt((l12 + 1) * (S + 2))
    elif (sigma_p, sigma_n) == (-1, -1):
        new, amp = (l12 - 1, l23, l31), math.sqrt(l12 * (S + 1))
    elif (sigma_p, sigma_n) == (+1, -1):
        new, amp = (l12, l23 - 1, l31 + 1), -math.sqrt((l31 + 1) * l23)
    elif (sigma_p, sigma_n) == (-1, +1):
        new, amp = (l12, l23 + 1, l31 - 1), -math.sqrt(l31 * (l23 + 1))
    else:
        raise ValueError("sigma must be +1 or -1")
    if min(new) < 0 or amp == 0.0:
        return None
    n_p_old = l31 + l12
    n_n_new = new[0] + new[1]
    return new, amp / math.sqrt((n_n_new + 1) * (n_p_old + 1))


def loop_ladder(s: int, sigma_p: int, sigma_n: int):
    """`ladder_amplitude` on a 3-bit site code; None also when a loop number would leave {0, 1}."""
    r = ladder_amplitude((s & 1, (s >> 1) & 1, (s >> 2) & 1), sigma_p, sigma_n)
    if r is None or max(r[0]) > 1:
        return None
    new, amp = r
    return new[0] | new[1] << 1 | new[2] << 2, amp


def inner_code_of(j4, J) -> int:
    code = 0
    for c, (p, n) in enumerate(CORNER_PN):
        code |= site_code(j4[p], j4[n], J[c]) << (3 * c)
    return code


def code_of_label(label) -> int:
    """24-bit LSH code of a route-B label ((j_0..j_11), (J_0..J_3))."""
    j, J = label
    if len(j) != 12 or len(J) != 4:
        raise ValueError("label must be ((j_0..j_11), (J_0..J_3))")
    code = inner_code_of(j[:4], J)
    for c, (o1, o2) in enumerate(CORNER_OUT):
        code |= site_code(j[o1], j[o2], J[c]) << (12 + 3 * c)
    return code


def _sites(code: int) -> list[int]:
    return [(code >> (3 * k)) & 7 for k in range(8)]


def agl_violations(code: int) -> tuple[str, ...]:
    """Links whose flux read from the two ends disagrees: inner links 'b','r','t','l' (n-leg of one 'in' site vs p-leg of
    the next), virtual links 'v0'..'v3' ('in' vs 'out' site of a corner).  Outer links have one end only."""
    fl = [site_flux(s) for s in _sites(code)]
    bad = []
    for c, (_p, n) in enumerate(CORNER_PN):
        c2 = (c + 1) % 4                       # link n(c) is p(c+1)
        if fl[c][1] != fl[c2][0]:
            bad.append(LINK_NAMES[n])
    for c in range(4):
        if fl[c][2] != fl[4 + c][2]:
            bad.append(f"v{c}")
    return tuple(bad)


def is_physical_code(code: int) -> bool:
    return 0 <= code < 1 << 24 and all(site_valid(s) for s in _sites(code)) and not agl_violations(code)


@functools.lru_cache(maxsize=1)
def _inner_codes() -> tuple:
    out = []
    for ss in itertools.product(VALID_SITE, repeat=4):
        fl = [site_flux(s) for s in ss]
        if all(fl[c][1] == fl[(c + 1) % 4][0] for c in range(4)):
            out.append(sum(s << (3 * c) for c, s in enumerate(ss)))
    return tuple(sorted(out))


def inner_codes() -> np.ndarray:
    """The 47 inner codes: four site-valid 'in' sites obeying the Abelian Gauss law on the four inner links (sorted)."""
    return np.array(_inner_codes(), dtype=np.int64)


@functools.lru_cache(maxsize=1)
def _physical_codes() -> tuple:
    by_nv = {}
    for s in VALID_SITE:
        by_nv.setdefault(site_flux(s)[2], []).append(s)
    out = []
    for x in _inner_codes():
        choices = [by_nv[site_flux((x >> (3 * c)) & 7)[2]] for c in range(4)]
        for oo in itertools.product(*choices):
            out.append(x | sum(s << (12 + 3 * c) for c, s in enumerate(oo)))
    return tuple(sorted(out))


def physical_codes() -> np.ndarray:
    """The 433 site-valid, AGL-valid 24-bit codes (sorted), enumerated in LSH variables only."""
    return np.array(_physical_codes(), dtype=np.int64)


@functools.lru_cache(maxsize=1)
def _plaquette() -> np.ndarray:
    codes = _inner_codes()
    pos = {c: i for i, c in enumerate(codes)}
    P = np.zeros((len(codes), len(codes)))
    for col, code in enumerate(codes):
        sites = [(code >> (3 * c)) & 7 for c in range(4)]
        for idx in itertools.product(range(2), repeat=4):       # matrix indices of the trace
            amp, new = 1.0, 0
            for c in range(4):
                sgn, sp_, sn_ = VERTEX[c][idx[c]][idx[(c + 1) % 4]]
                r = loop_ladder(sites[c], sp_, sn_)
                if r is None:
                    amp = 0.0
                    break
                amp *= sgn * r[1]
                new |= r[0] << (3 * c)
            if amp != 0.0 and new in pos:                        # flux cap = j_max truncation
                P[pos[new], col] += amp
    return P


def plaquette_inner() -> np.ndarray:
    """P[new, old] = <new| Tr(U_b U_r U_t^dag U_l^dag) |old> on the 47 inner codes (order of `inner_codes`)."""
    return _plaquette().copy()


def K_lsh() -> np.ndarray:
    P = _plaquette()
    return -(P + P.T)


def h_magnetic_lsh(codes) -> np.ndarray:
    """H_B = -(Tr U_P + h.c.) on the given 24-bit codes: K_lsh between codes with the same 'out' sites."""
    codes = [int(c) for c in codes]
    pos = {c: i for i, c in enumerate(_inner_codes())}
    K = K_lsh()
    n = len(codes)
    H = np.zeros((n, n))
    by_outer: dict = {}
    for k, c in enumerate(codes):
        by_outer.setdefault(c >> 12, []).append(k)
    for ks in by_outer.values():
        bad = [codes[k] for k in ks if (codes[k] & 0xFFF) not in pos]
        if bad:
            raise ValueError(f"code {bad[0]} has an inner part outside the 47 inner codes")
        ii = [pos[codes[k] & 0xFFF] for k in ks]
        H[np.ix_(ks, ks)] = K[np.ix_(ii, ii)]
    return H


def h_electric_lsh(codes, include_outer: bool = False) -> np.ndarray:
    """Diagonal of H_E = sum_links (N/2)(N/2 + 1): inner links read at the n-leg of their 'in' site; with include_outer
    also the two outer legs of every 'out' site (bits 12..23; absent in a 12-bit inner code, which then adds 0).  Virtual
    links carry no electric energy."""
    out = []
    for code in codes:
        s = _sites(int(code))
        e = sum((site_flux(s[c])[1] / 2) * (site_flux(s[c])[1] / 2 + 1) for c in range(4))
        if include_outer:
            e += sum((f / 2) * (f / 2 + 1) for c in range(4) for f in site_flux(s[4 + c])[:2])
        out.append(e)
    return np.array(out, dtype=np.float64)
