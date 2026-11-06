"""Exploratory projection check: rishon one-Trotter-step circuit vs Kogut-Susskind (KS, j_max = 1/2) step circuit.

Question: if every spin-0 rishon link is restricted to ONE singlet combination, does the rishon step reproduce the KS step?

Definitions (basis-free, per link l; A = code 3, B = code 12, Q = codes 5, 6, 9, 10):
    |+-> = (|A> +- |B>)/sqrt2,   P_sigma = prod_l (P_Q,l + |sigma><sigma|_l)  (the same sigma on every link),
    control  P_A = prod_l (P_Q,l + |A><A|_l).
The projector acts on the 48-qubit computational basis link by link (4 qubits per link).  The rishon physical space
(38 432 states, `su2plaq.rishon.physical.rishon_basis`) is a direct sum over the 433 KS labels (j-pattern, J-tuple) of groups of
2^{n0} states (n0 = number of spin-0 links), the members of a group differing only in A/B on the spin-0 links.  P preserves every
group; its matrix G_g on a group is verified numerically from the 48-bit vectors (Hermitian, idempotent, trace = rank,
closure P Psi_k in span(group)); the range vector of each group gives the 433 columns of V_sigma (38 432 x 433 isometry).

    PYTHONPATH=src taskset -c 10-19 python scripts/m5_ks_projection.py [--out results/rishon/ks_projection.json] [--quick]

Everything is computed here (no expected number typed in).  --quick is for the unit tests only (no circuit simulation).
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import platform
import resource
import time

import numpy as np
import scipy.linalg as sla
from scipy.optimize import linear_sum_assignment

from su2plaq.rishon import operators as rops
from su2plaq.rishon import physical as rphys
from su2plaq.rishon.algebra import CODE_A, CODE_B, CODES_Q, RishonLink

ROOT = pathlib.Path(__file__).resolve().parents[1]
ALPHA, BETA = 0.37, 0.61
BETAS = (0.61, 0.3, 0.1, 0.03)
G2_LIST = (0.5, 1.0, 2.0)
TOL_ZERO = 1e-12


# ------------------------------------------------------------------------------------------ link projectors
def link_projector16(variant: str) -> np.ndarray:
    """16x16 single-link projector in the computational basis: P_Q + |sigma><sigma| ('plus', 'minus') or P_Q + |A><A| ('A')."""
    P = np.zeros((16, 16), dtype=np.complex128)
    for q in CODES_Q:
        P[q, q] = 1.0
    if variant in ("plus", "minus"):
        s = 1.0 if variant == "plus" else -1.0
        v = np.zeros(16, dtype=np.complex128)
        v[CODE_A] = 1.0 / np.sqrt(2.0)
        v[CODE_B] = s / np.sqrt(2.0)
        P += np.outer(v, v.conj())
    elif variant == "A":
        P[CODE_A, CODE_A] += 1.0
    else:
        raise ValueError(f"variant must be 'plus', 'minus' or 'A', got {variant!r}")
    return P


def _ab_weights(variant: str) -> tuple[complex, complex, complex, complex]:
    """(AA, BA, AB, BB) = matrix elements <out|P|in> for in/out in {A, B}: P|A> = AA|A> + BA|B>, P|B> = AB|A> + BB|B>."""
    P = link_projector16(variant)
    return P[CODE_A, CODE_A], P[CODE_B, CODE_A], P[CODE_A, CODE_B], P[CODE_B, CODE_B]


def coalesce(col: np.ndarray, key: np.ndarray, amp: np.ndarray, drop: float = 0.0):
    """Sum amplitudes with equal (col, key); returns sorted (col, key, amp)."""
    if len(amp) == 0:
        return col.astype(np.int64), key.astype(np.int64), amp
    comp = (col.astype(np.int64) << 48) | key.astype(np.int64)
    order = np.argsort(comp, kind="stable")
    comp, amp = comp[order], amp[order]
    start = np.flatnonzero(np.concatenate(([True], comp[1:] != comp[:-1])))
    tot = np.add.reduceat(amp, start)
    keep = np.abs(tot) > drop
    cs = comp[start][keep]
    return (cs >> 48).astype(np.int64), cs & ((np.int64(1) << 48) - 1), tot[keep]


def apply_projector(col: np.ndarray, key: np.ndarray, amp: np.ndarray, variant: str, links=range(12)):
    """Apply prod_{l in links} (P_Q + |sigma><sigma|) (or the A control) to a COO family (col, 48-bit key, amp).
    Q nibbles are untouched; A/B nibbles are mixed with the 2x2 matrix of `link_projector16`; any other nibble raises."""
    AA, BA, AB, BB = _ab_weights(variant)
    q_codes = np.array(CODES_Q, dtype=np.int64)
    for l in links:
        sh = 4 * l
        nib = (key >> sh) & 15
        isA, isB = nib == CODE_A, nib == CODE_B
        isQ = np.isin(nib, q_codes)
        if not np.all(isA | isB | isQ):
            raise ValueError(f"invalid link nibble on link {l}")
        base = key & ~(np.int64(15) << sh)
        cols = [col[isQ]]
        keys = [key[isQ]]
        amps = [amp[isQ]]
        for mask, to_a, to_b in ((isA, AA, BA), (isB, AB, BB)):
            for code, w in ((CODE_A, to_a), (CODE_B, to_b)):
                if w != 0:
                    cols.append(col[mask])
                    keys.append(base[mask] | (np.int64(code) << sh))
                    amps.append(amp[mask] * w)
        col, key, amp = coalesce(np.concatenate(cols), np.concatenate(keys), np.concatenate(amps))
    return col, key, amp


# ------------------------------------------------------------------------------------------ groups (the 433 KS labels)
def label_j(types) -> tuple:
    return tuple(0.5 if t == "Q" else 0.0 for t in types)


def rishon_groups(b) -> dict:
    """KS label (j tuple, J tuple) -> list of rishon basis indices (types differ only by A/B on spin-0 links)."""
    grp = collections.defaultdict(list)
    for i, (types, Js) in enumerate(b.labels):
        grp[(label_j(types), tuple(float(x) for x in Js))].append(i)
    return dict(grp)


def group_coo(b, idx: list[int]):
    """COO family (col = position in idx, key, amp) of the basis states idx."""
    col = np.concatenate([np.full(len(b.keys[k]), j, dtype=np.int64) for j, k in enumerate(idx)])
    key = np.concatenate([np.asarray(b.keys[k], dtype=np.int64) for k in idx])
    amp = np.concatenate([np.asarray(b.amps[k], dtype=np.complex128) for k in idx])
    return col, key, amp


def _sparse_pair(n: int, A, B):
    """Sparse (keys x n) matrices of two COO families on a common key axis."""
    import scipy.sparse as sp

    keys = np.unique(np.concatenate([A[1], B[1]]))
    ra, rb = np.searchsorted(keys, A[1]), np.searchsorted(keys, B[1])
    return (sp.csr_matrix((A[2], (ra, A[0])), shape=(len(keys), n)), sp.csr_matrix((B[2], (rb, B[0])), shape=(len(keys), n)))


def group_projector(b, idx: list[int], variant: str, chunk: int = 256) -> dict:
    """Matrix G of P on the group `idx` and the verification numbers (all from the 48-bit vectors, nothing assumed):
    G_ij = <Psi_i|P Psi_j>, closure = max_j ||P Psi_j - sum_i G_ij Psi_i|| (computed as a vector residual, not from norms)."""
    n = len(idx)
    fam = group_coo(b, idx)
    pfam = apply_projector(*fam, variant)
    SA, SB = _sparse_pair(n, fam, pfam)
    S = (SA.conj().T @ SA).toarray()
    G = (SA.conj().T @ SB).toarray()                    # G[i, j] = <Psi_i | P Psi_j>
    closure = 0.0
    for lo in range(0, n, chunk):
        R = SB[:, lo:lo + chunk].toarray() - SA @ G[:, lo:lo + chunk]
        closure = max(closure, float(np.linalg.norm(R, axis=0).max()))
    return {
        "G": G,
        "orthonormality": float(np.abs(S - np.eye(n)).max()),
        "closure": closure,
        "hermitian": float(np.abs(G - G.conj().T).max()),
        "idempotent": float(np.abs(G @ G - G).max()),
        "trace": float(np.trace(G).real),
        "n": n,
    }


def analytic_vector(b, idx: list[int], variant: str) -> np.ndarray:
    """w over the group states: product over spin-0 links of the link vector (|A> + s|B>)/sqrt2 or |A>; (checked by G w = w)."""
    w = np.ones(len(idx), dtype=np.complex128)
    for pos, k in enumerate(idx):
        types = b.labels[k][0]
        for t in types:
            if t == "Q":
                continue
            if variant == "A":
                w[pos] *= 1.0 if t == "A" else 0.0
            else:
                s = 1.0 if variant == "plus" else -1.0
                w[pos] *= (1.0 if t == "A" else s) / np.sqrt(2.0)
    return w


def build_V(b, ks_labels, variant: str, *, check: bool = True, max_group: int | None = None) -> dict:
    """The isometry V (38 432 x 433, as a COO family: col = KS label position, 48-bit key, amp) onto range(P) in the physical
    space, with the per-group verification summarised.  max_group (unit tests): only groups of at most that size."""
    grp = rishon_groups(b)
    cols, keys, amps = [], [], []
    stats = {"hermitian": 0.0, "idempotent": 0.0, "closure": 0.0, "orthonormality": 0.0, "range_residual": 0.0,
             "rank": 0.0, "n_groups": 0, "n_states": 0, "trace_per_group_min": 1e9, "trace_per_group_max": -1e9}
    index = {}
    for pos, lab in enumerate(ks_labels):
        key = (tuple(float(x) for x in lab[0]), tuple(float(x) for x in lab[1]))
        index[key] = pos
    done = []
    for lab, idx in grp.items():
        if max_group is not None and len(idx) > max_group:
            continue
        pos = index[lab]
        w = analytic_vector(b, idx, variant)
        nrm = np.linalg.norm(w)
        w = w / nrm
        if check:
            r = group_projector(b, idx, variant)
            G = r["G"]
            stats["hermitian"] = max(stats["hermitian"], r["hermitian"])
            stats["idempotent"] = max(stats["idempotent"], r["idempotent"])
            stats["closure"] = max(stats["closure"], r["closure"])
            stats["orthonormality"] = max(stats["orthonormality"], r["orthonormality"])
            stats["range_residual"] = max(stats["range_residual"], float(np.linalg.norm(G @ w - w)))
            stats["rank"] += r["trace"]
            stats["trace_per_group_min"] = min(stats["trace_per_group_min"], r["trace"])
            stats["trace_per_group_max"] = max(stats["trace_per_group_max"], r["trace"])
            # G is a rank-1 projector w w^dagger: ||G - w w^dagger|| (so the range of P on the group is span(w))
            stats["rank1_residual"] = max(stats.get("rank1_residual", 0.0), float(np.abs(G - np.outer(w, w.conj())).max()))
            del G, r
        stats["n_groups"] += 1
        stats["n_states"] += len(idx)
        c0, k0, a0 = group_coo(b, idx)
        nz = np.abs(w[c0]) > 0
        c1, k1, a1 = coalesce(np.full(nz.sum(), pos, dtype=np.int64), k0[nz], a0[nz] * w[c0][nz], drop=1e-15)
        cols.append(c1)
        keys.append(k1)
        amps.append(a1)
        done.append(pos)
    stats["trace_per_group_min"] = stats["trace_per_group_min"] if check else float("nan")
    stats["trace_per_group_max"] = stats["trace_per_group_max"] if check else float("nan")
    return {"col": np.concatenate(cols), "key": np.concatenate(keys), "amp": np.concatenate(amps), "positions": done,
            "stats": stats, "n_cols": len(ks_labels)}


def V_overlap(V: dict) -> np.ndarray:
    """V^dagger V (433 x 433) from the 48-bit vectors."""
    import scipy.sparse as sp

    keys = np.unique(V["key"])
    S = sp.csr_matrix((V["amp"], (np.searchsorted(keys, V["key"]), V["col"])), shape=(len(keys), V["n_cols"]))
    return (S.conj().T @ S).toarray()


def V_gauss_residual(V: dict) -> float:
    """max over the columns of the Gauss residual max_{c,a} ||G^a_c v||, from the 48-bit COO vectors."""
    order = np.argsort(V["col"], kind="stable")
    col, key, amp = V["col"][order], V["key"][order], V["amp"][order]
    pos = np.unique(col)
    bounds = np.searchsorted(col, np.append(pos, pos[-1] + 1))
    kl = [key[bounds[i]:bounds[i + 1]] for i in range(len(pos))]
    al = [amp[bounds[i]:bounds[i + 1]] for i in range(len(pos))]
    return float(rphys.gauss_residuals_coo(kl, al).max())


# ------------------------------------------------------------------------------------------ reduction of inner operators
class Reducer:
    """States as COO families (col, key, amp) with key = inner code | outer << n_data.  reduce(ops) = [V^dagger (O (x) 1) V] for
    inner operators O (dense, rows/columns indexed by the sorted inner codes), summed exactly over the outer patterns."""

    def __init__(self, col, key, amp, n_cols: int, n_data: int, codes: np.ndarray):
        mask = (np.int64(1) << n_data) - 1
        inner = key & mask
        outer = key >> n_data
        rows = np.searchsorted(codes, inner)
        if np.any(rows >= len(codes)) or np.any(codes[np.minimum(rows, len(codes) - 1)] != inner):
            raise ValueError("a state has an inner component outside the valid code space")
        order = np.lexsort((col, outer))
        self.col, self.rows, self.amp = col[order], rows[order], amp[order]
        outer = outer[order]
        self.bounds = np.flatnonzero(np.concatenate(([True], outer[1:] != outer[:-1], [True])))
        self.n_cols = n_cols
        self.n_in = len(codes)

    def reduce(self, ops: list[np.ndarray]) -> list[np.ndarray]:
        out = [np.zeros((self.n_cols, self.n_cols), dtype=np.complex128) for _ in ops]
        for a, bnd in zip(self.bounds[:-1], self.bounds[1:]):
            cs, ci = np.unique(self.col[a:bnd], return_inverse=True)
            rs, ri = np.unique(self.rows[a:bnd], return_inverse=True)
            Z = np.zeros((len(rs), len(cs)), dtype=np.complex128)
            np.add.at(Z, (ri, ci), self.amp[a:bnd])
            ix = np.ix_(cs, cs)
            for k, O in enumerate(ops):
                out[k][ix] += Z.conj().T @ (O[np.ix_(rs, rs)] @ Z)
        return out


# ------------------------------------------------------------------------------------------ small helpers
def op_norm(A: np.ndarray) -> float:
    return float(np.linalg.norm(A, 2))


def herm_eigs(A: np.ndarray) -> np.ndarray:
    return np.linalg.eigvalsh((A + A.conj().T) / 2)


def fit_scale(HR: np.ndarray, HK: np.ndarray) -> dict:
    """Best c in |HR| ~ c |HK| (entrywise moduli, least squares over all matrix elements) and the worst entrywise misfit."""
    aR, aK = np.abs(HR), np.abs(HK)
    c_mod = float((aR * aK).sum() / (aK * aK).sum())
    return {"c_modulus": c_mod, "modulus_residual": float(np.abs(aR - c_mod * aK).max())}


def eigenphase_distance(U1: np.ndarray, U2: np.ndarray) -> float:
    """Max chordal distance |e^{i t1} - e^{i t2}| between the optimally matched eigenphase multisets of two (near-)unitary matrices."""
    t1 = np.angle(np.linalg.eigvals(U1))
    t2 = np.angle(np.linalg.eigvals(U2))
    C = np.abs(np.exp(1j * t1)[:, None] - np.exp(1j * t2)[None, :])
    r, c = linear_sum_assignment(C)
    return float(C[r, c].max())


def polar_unitary(W: np.ndarray) -> np.ndarray:
    u, _, vh = np.linalg.svd(W)
    return u @ vh


def leakage_from(W: np.ndarray, Gout: np.ndarray | None = None) -> dict:
    """Singular values of W = V^dagger C V and the operator norm of (1 - P) C V = sqrt(lambda_max(V^dagger C^dagger C V - W^dagger W))
    (exact for an operator whose output stays in the physical space; Gout = V^dagger C^dagger C V, identity for a unitary C)."""
    sv = np.linalg.svd(W, compute_uv=False)
    n = W.shape[0]
    Gm = np.eye(n) if Gout is None else Gout
    lam = herm_eigs(Gm - W.conj().T @ W)
    colnorm = np.linalg.norm(W, axis=0)
    return {"n_states": int(n), "n_sv_below_1_minus_1e-9": int((sv < 1 - 1e-9).sum()),
            "n_basis_columns_with_unit_norm_1e-9": int((colnorm > 1 - 1e-9).sum()),
            "sv_min": float(sv.min()), "sv_max": float(sv.max()), "leak_op_norm": float(np.sqrt(max(lam.max(), 0.0))),
            "one_minus_sv_min": float(1.0 - sv.min())}


def phase_corrected_diff(A: np.ndarray, B: np.ndarray) -> tuple[float, float]:
    """(op norm of A - e^{i phi} B, phi) with phi fitted from tr(B^dagger A)."""
    tr = np.trace(B.conj().T @ A)
    ph = tr / abs(tr) if abs(tr) > 0 else 1.0
    return op_norm(A - ph * B), float(np.angle(ph))


def gauge_vector(HR: np.ndarray, HK: np.ndarray, c: float) -> tuple[np.ndarray | None, float]:
    from su2plaq.exact.compare import gauge_align

    return gauge_align(HR / c, HK, tol=1e-9)


def apply_gauge(M: np.ndarray, D: np.ndarray) -> np.ndarray:
    """D M D^dagger for a diagonal unitary D given as a vector."""
    return D[:, None] * M * np.conj(D)[None, :]


def peak_rss_mb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


# ------------------------------------------------------------------------------------------ KS side
def ks_exact(ksb, alpha: float, beta: float) -> np.ndarray:
    from su2plaq.exact.operators import target

    return target(ksb, "step", alpha, beta, 1)


def ks_circuit_block(cap: int = 5_000_000):
    """(M_KS 433 x 433 in the physical basis, step.json params, the 625x625 code block) of results/twelve/step.qpy."""
    from qiskit import qpy

    from su2plaq.encodings.twelve import TwelveQubit
    from su2plaq.rishon.verify import _code_block

    enc = TwelveQubit()
    with open(ROOT / "results/twelve/step.qpy", "rb") as fh:
        qc = qpy.load(fh)[0]
    codes = enc.inner_codes()
    M = _code_block(qc, enc.layout_of(qc), codes, cap)
    ev = enc.physical_vectors()
    col = np.concatenate([np.full(len(c), k, dtype=np.int64) for k, c in enumerate(ev.codes)])
    key = np.concatenate(ev.codes).astype(np.int64)
    amp = np.concatenate(ev.amps).astype(np.complex128)
    red = Reducer(col, key, amp, len(ev.codes), enc.n_data, codes)
    (Mp, MM) = red.reduce([M, M.conj().T @ M])
    return Mp, MM, enc


def rishon_circuit_block(cap: int = 5_000_000) -> np.ndarray:
    """1296 x 1296 code block of results/rishon/step.qpy (outer-blind circuit: acts as M (x) 1 on the physical space)."""
    from qiskit import qpy

    from su2plaq.encodings.rishon import RishonEncoding
    from su2plaq.rishon.verify import _code_block

    enc = RishonEncoding()
    with open(ROOT / "results/rishon/step.qpy", "rb") as fh:
        qc = qpy.load(fh)[0]
    return _code_block(qc, enc.layout_of(qc), rops.inner_codes(), cap)


# ------------------------------------------------------------------------------------------ main analysis
def analyse_variant(variant: str, b, ksb, ks_labels, ks_ref: dict, M_R: np.ndarray | None, log) -> dict:
    t0 = time.time()
    res: dict = {"variant": variant}
    V = build_V(b, ks_labels, variant)
    st = V["stats"]
    S = V_overlap(V)
    sv = np.linalg.svd(S, compute_uv=False)
    res["projector"] = {
        "rank_of_P_on_physical_space": st["rank"], "n_groups": st["n_groups"], "n_physical_states": st["n_states"],
        "group_trace_min": st["trace_per_group_min"], "group_trace_max": st["trace_per_group_max"],
        "hermitian_residual": st["hermitian"], "idempotent_residual": st["idempotent"],
        "closure_residual_P_Psi_in_span_group": st["closure"], "group_orthonormality_residual": st["orthonormality"],
        "range_vector_residual_Gw_minus_w": st["range_residual"], "rank1_residual": st["rank1_residual"],
        "V_overlap_minus_identity": float(np.abs(S - np.eye(len(S))).max()), "V_overlap_sv_min": float(sv.min()),
        "gauss_residual_of_range_vectors": V_gauss_residual(V),
    }
    log(f"[{variant}] projector verified ({time.time() - t0:.0f}s): rank={st['rank']}")

    codes = rops.inner_codes()
    red = Reducer(V["col"], V["key"], V["amp"], V["n_cols"], 16, codes)
    HB = rops.h_magnetic_inner()
    HEd = np.diag(rops.h_electric_inner()).astype(np.complex128)
    ops = [HB, HB @ HB, HEd]
    names = ["HB", "HB2", "HE_inner"]
    exact_ops = {}
    for beta in BETAS:
        exact_ops[beta] = rops.inner_target("step", ALPHA, beta, 1)
    ops += [exact_ops[bt] for bt in BETAS]
    names += [f"U_{bt}" for bt in BETAS]
    if M_R is not None:
        ops += [M_R, M_R.conj().T @ M_R]
        names += ["circuit", "circuit_MM"]
    out = dict(zip(names, red.reduce(ops)))
    log(f"[{variant}] reductions done ({time.time() - t0:.0f}s)")

    HB_R, HB2_R, HE_R = out["HB"], out["HB2"], out["HE_inner"]
    HB_K, HE_K = ks_ref["HB"], ks_ref["HE"]
    # ---------------------------------------------------------- check 1: Hamiltonian level
    he = {"max_offdiag": float(np.abs(HE_R - np.diag(np.diag(HE_R))).max()),
          "inner_diag_minus_KS": float(np.abs(HE_R - HE_K).max())}
    # all-12-link H_E from the 48-bit vectors (3/4 per Q link, outer included) vs KS inner + outer
    he["all12_diag_minus_KS"] = float(np.abs(all12_HE_diag(V) - ks_ref["HE_all12"]).max())
    res["check1_HE"] = he
    fit = fit_scale(HB_R, HB_K)
    c = fit["c_modulus"]
    D, gres = gauge_vector(HB_R, HB_K, c) if c > 1e-9 else (None, float("nan"))
    herm = float(np.abs(HB_R - HB_R.conj().T).max())
    spec = {}
    for g2 in G2_LIST:
        eR = herm_eigs(0.5 * g2 * HE_R + HB_R / g2)
        eK = herm_eigs(0.5 * g2 * HE_K + HB_K / g2)
        eKc = herm_eigs(0.5 * g2 * HE_K + c * HB_K / g2)
        spec[str(g2)] = {"max_abs_diff_R_vs_KS": float(np.abs(eR - eK).max()),
                         "max_abs_diff_R_vs_KS_with_cHB": float(np.abs(eR - eKc).max())}
    res["check1_HB"] = {"hermitian_residual": herm, **fit, "c": c, "gauge_align_found": D is not None,
                        "gauge_align_residual": gres, "gauge_is_pm1_real": bool(D is not None and np.abs(D.imag).max() < 1e-12),
                        "spectra_vs_KS_by_g2": spec,
                        "spectra_match_helper_max": float(max(v["max_abs_diff_R_vs_KS"] for v in spec.values())),
                        "norm_HB_R": op_norm(HB_R), "norm_HB_KS": op_norm(HB_K),
                        "frobenius_ratio_R_over_KS": float(np.linalg.norm(HB_R) / np.linalg.norm(HB_K))}
    if D is not None:
        res["check1_HB"]["matrix_residual_after_gauge_of_HB_R_minus_c_HB_KS"] = float(
            np.abs(HB_R - c * apply_gauge(HB_K, D)).max())
    # ---------------------------------------------------------- check 2: leakage of H_B
    R2 = HB2_R - HB_R @ HB_R
    lam = herm_eigs(R2)
    leak_hb = float(np.sqrt(max(lam.max(), 0.0)))
    res["check2_HB_leakage"] = {"op_norm_(1-P)HB_P": leak_hb,
                                "predicted_second_order_mismatch_coefficient_leak2_over_2": 0.5 * leak_hb ** 2,
                                "HB_P_op_norm": op_norm(HB_R), "min_eig_of_V*HB2V-(V*HBV)^2": float(lam.min())}
    log(f"[{variant}] HB leak {res['check2_HB_leakage']['op_norm_(1-P)HB_P']:.6g}, c={c:.12g}")

    # ---------------------------------------------------------- check 3: step circuit
    def vs_ks(W: np.ndarray, Mk: np.ndarray) -> dict:
        d = {"op_norm_ungauged_D_identity_phase_fitted": phase_corrected_diff(W, Mk)[0]}
        if D is not None:
            Wd = apply_gauge(Mk, D)
            d["op_norm_after_gauge"] = op_norm(W - Wd)
            d["op_norm_after_gauge_phase_fitted"] = phase_corrected_diff(W, Wd)[0]
            d["max_abs_after_gauge"] = float(np.abs(W - Wd).max())
        d["eigenphase_matching_max_chord_polar_unitary"] = eigenphase_distance(polar_unitary(W), Mk)
        return d

    from scipy.sparse import csr_matrix
    from scipy.sparse.csgraph import connected_components

    ncomp, comp = connected_components(csr_matrix(np.abs(HB_K) > 1e-9), directed=False)
    other = comp[:, None] != comp[None, :]
    c3 = {"c_used_for_rescaled_KS": c, "n_components_of_KS_HB_graph": int(ncomp)}
    KS_nom = ks_ref["M_exact_nominal"]
    KS_resc = ks_exact_cached(ksb, ALPHA, c * BETA)
    if "circuit" in out:
        W = out["circuit"]
        lk = leakage_from(W, out["circuit_MM"])
        lk["V*C*CV_minus_I_max"] = float(np.abs(out["circuit_MM"] - np.eye(len(W))).max())
        c3["circuit_rishon"] = {**lk, "vs_KS_exact_nominal": vs_ks(W, KS_nom), "vs_KS_exact_rescaled_beta_c_beta": vs_ks(W, KS_resc)}
        if ks_ref.get("M_circuit") is not None:
            c3["circuit_rishon"]["vs_KS_circuit"] = vs_ks(W, ks_ref["M_circuit"])
        eigs = np.linalg.eigvals(W)
        c3["circuit_rishon"]["max_abs_element_between_KS_HB_components"] = float(np.abs(W)[other].max())
        c3["circuit_rishon"]["eig_modulus_min"] = float(np.abs(eigs).min())
        c3["circuit_rishon"]["eig_modulus_max"] = float(np.abs(eigs).max())
        exact = out["U_0.61"]
        c3["circuit_minus_exact_rishon_projected_op_norm"] = op_norm(W - exact)
    Wn = out["U_0.61"]
    c3["exact_rishon_nominal"] = {**leakage_from(Wn), "vs_KS_exact_nominal": vs_ks(Wn, KS_nom),
                                  "vs_KS_exact_rescaled_beta_c_beta": vs_ks(Wn, KS_resc)}
    res["check3_step"] = c3
    # ---------------------------------------------------------- check 4: small-angle scaling
    rows = []
    for beta in BETAS:
        W = out[f"U_{beta}"]
        lk = leakage_from(W)
        Mk = ks_exact_cached(ksb, ALPHA, c * beta)
        Mk1 = ks_exact_cached(ksb, ALPHA, beta)
        row = {"beta": beta, "leak": lk["leak_op_norm"], "sv_min": lk["sv_min"],
               "diff_vs_KS_rescaled": vs_ks(W, Mk), "diff_vs_KS_beta_unrescaled": vs_ks(W, Mk1)}
        row["leak_over_beta"] = lk["leak_op_norm"] / beta
        key_m = "op_norm_after_gauge" if "op_norm_after_gauge" in row["diff_vs_KS_rescaled"] else "op_norm_ungauged_D_identity_phase_fitted"
        row["mismatch_rescaled_over_beta2"] = row["diff_vs_KS_rescaled"][key_m] / beta ** 2
        rows.append(row)
    res["check4_small_angle"] = {"alpha": ALPHA, "rows": rows, "slopes": scaling_slopes(rows)}
    res["seconds"] = time.time() - t0
    return res


_KS_CACHE: dict = {}


def ks_exact_cached(ksb, alpha: float, beta: float) -> np.ndarray:
    key = (round(alpha, 14), round(beta, 14))
    if key not in _KS_CACHE:
        _KS_CACHE[key] = ks_exact(ksb, alpha, beta)
    return _KS_CACHE[key]


def scaling_slopes(rows: list[dict]) -> dict:
    """Local log-log slopes d log y / d log beta between consecutive beta values for the leak and the gauge-fixed mismatch."""
    out = {"leak": [], "mismatch_vs_KS_rescaled": [], "betas_pairs": []}
    for r0, r1 in zip(rows[:-1], rows[1:]):
        lb = np.log(r1["beta"] / r0["beta"])
        out["betas_pairs"].append([r0["beta"], r1["beta"]])
        out["leak"].append(float(np.log(r1["leak"] / r0["leak"]) / lb) if r0["leak"] > 0 and r1["leak"] > 0 else float("nan"))
        k = ("op_norm_after_gauge" if "op_norm_after_gauge" in r0["diff_vs_KS_rescaled"]
             else "op_norm_ungauged_D_identity_phase_fitted")
        y0, y1 = r0["diff_vs_KS_rescaled"][k], r1["diff_vs_KS_rescaled"][k]
        out["mismatch_vs_KS_rescaled"].append(float(np.log(y1 / y0) / lb) if y0 > 0 and y1 > 0 else float("nan"))
    return out


def all12_HE_diag(V: dict) -> np.ndarray:
    """V^dagger H_E^{all 12 links} V from the 48-bit vectors: H_E = 3/4 per quartet link (inner and outer), diagonal in the codes."""
    import scipy.sparse as sp

    key = V["key"]
    q = np.zeros(len(key))
    for l in range(12):
        q += np.isin((key >> (4 * l)) & 15, np.array(CODES_Q))
    keys = np.unique(key)
    S = sp.csr_matrix((V["amp"], (np.searchsorted(keys, key), V["col"])), shape=(len(keys), V["n_cols"]))
    Sd = sp.csr_matrix((V["amp"] * 0.75 * q, (np.searchsorted(keys, key), V["col"])), shape=(len(keys), V["n_cols"]))
    return (S.conj().T @ Sd).toarray()


def ks_reference(ksb, ks_labels) -> dict:
    from su2plaq.exact import operators as kop
    from su2plaq.exact import spinnet

    HB, leak = kop.h_magnetic_phys(ksb)
    HB6 = spinnet.h_magnetic_phys_6j(ks_labels)
    HE = np.diag(kop.h_electric_inner(ksb)).astype(np.complex128)
    HEo = np.diag(kop.h_electric_outer(ksb))
    return {"HB": HB, "HB6j": HB6, "HE": HE, "HE_all12": HE + HEo, "M_exact_nominal": ks_exact(ksb, ALPHA, BETA),
            "HB_phys_leak": leak}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "results/rishon/ks_projection.json"))
    ap.add_argument("--quick", action="store_true", help="skip the circuit simulations (tests only)")
    ap.add_argument("--variants", default="plus,minus,A")
    args = ap.parse_args(argv)
    t_start = time.time()
    from su2plaq.exact.physical import physical_basis
    from su2plaq.metrics.provenance import provenance

    def log(msg):
        print(f"[{time.time() - t_start:7.1f}s rss={peak_rss_mb():7.0f}MB] {msg}", flush=True)

    b = rphys.rishon_basis()
    ksb = physical_basis()
    ks_labels = ksb.labels
    ks_ref = ks_reference(ksb, ks_labels)
    log("bases built")
    # same KS labels as 6j route (ordering) -> HB (route A) vs HB (route B) equal up to gauge: recorded
    meta = {}
    from su2plaq.exact.compare import gauge_align

    _, r_ab = gauge_align(ks_ref["HB"], ks_ref["HB6j"])
    meta["KS_routeA_vs_routeB_HB_gauge_residual"] = float(r_ab)
    meta["KS_HB_phys_leak"] = float(ks_ref["HB_phys_leak"])
    M_R = None
    ks_ref["M_circuit"] = None
    if not args.quick:
        M_R = rishon_circuit_block()
        log("rishon circuit block simulated")
        Mk, MkMM, _ = ks_circuit_block()
        ks_ref["M_circuit"] = Mk
        d, ph = phase_corrected_diff(Mk, ks_ref["M_exact_nominal"])
        meta["KS_circuit_minus_exact_op_norm_phase_fitted"] = d
        meta["KS_circuit_unitarity_dev"] = op_norm(Mk.conj().T @ Mk - np.eye(Mk.shape[0]))
        log("KS circuit block simulated")
    steps = {}
    for name in ("results/rishon/step.json", "results/twelve/step.json"):
        j = json.loads((ROOT / name).read_text())
        steps[name] = {"params": j["params"], "op_norm_error": j["verification"]["op_norm_error"],
                       "certified": j["verification"].get("certified"), "git_commit": j["provenance"]["git_commit"],
                       "git_dirty": j["provenance"]["git_dirty"]}
    rl = RishonLink()
    meta["det_U_B_A_element"] = [float(rl.det_U[CODE_B, CODE_A].real), float(rl.det_U[CODE_B, CODE_A].imag)]
    meta["det_U_A_B_element"] = [float(rl.det_U[CODE_A, CODE_B].real), float(rl.det_U[CODE_A, CODE_B].imag)]
    meta["link_projector_commutes_with_L_R"] = {
        v: float(max(np.abs(link_projector16(v) @ m - m @ link_projector16(v)).max() for m in list(rl.L) + list(rl.R)))
        for v in ("plus", "minus", "A")}
    variants = {}
    for v in args.variants.split(","):
        variants[v] = analyse_variant(v, b, ksb, ks_labels, ks_ref, M_R, log)
    prov = provenance({"none_random": 0})
    prov["host"] = platform.node()
    prov["wall_seconds"] = time.time() - t_start
    prov["peak_rss_mb"] = peak_rss_mb()
    prov["command"] = "PYTHONPATH=src taskset -c 10-19 python scripts/m5_ks_projection.py"
    doc = {"description": __doc__.split("\n")[0], "parameters": {"alpha": ALPHA, "beta": BETA, "betas_small_angle": list(BETAS),
                                                                    "g2_list": list(G2_LIST), "order": 1},
           "step_circuits": steps, "meta": meta, "variants": variants, "provenance": prov}
    from su2plaq.rishon.results import _jsonable

    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(_jsonable(doc), indent=2, allow_nan=True) + "\n")
    log(f"wrote {out}")
    return doc


if __name__ == "__main__":
    main()
