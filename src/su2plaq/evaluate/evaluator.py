"""Circuit evaluator (prompts/002 §2.7, prompts/004; docs/METHODS.md §6): is the circuit, up to ONE global phase, the target on
every physical state, with clean ancillas, no write access to the outer controls, and Gauss-law-respecting outputs?

Algorithm
  1. gates -> SIM_BASIS (level 0, no optimisation, idle qubits not assumed clean); mcx with >= 3 controls is rejected
     (reason `disallowed_gate`).
  2. outer qubits: every gate must be diagonal on them (`classify_outer_gates`), else `writes_outer`; R = outer qubits read.
  3. for every pattern r of R occurring in the physical states: `specialise` the circuit (outer bits resolved classically)
     and simulate the inner codes (625 inputs, ancillas 0): M_r = <inner code|U_r|inner code>, plus the part X of the output
     outside the code space (ancilla bit set / invalid data code).
  4. A[k',k] = sum_o <psi_k'^o| M_{r(o)} |psi_k^o>  (the outer register is a spectator: U is block diagonal in it);
     phase phi = arg tr(V^dag A); block_error = ||A - e^{i phi} V||_2 (method `inner_span`, no outer bit read:
     max(inner-span error, physical error)).
  5. leak_amplitude = ||X||_2 = sqrt(lambda_max(X^dag X)) on the physical inputs (sparse: exact, X^dag X accumulated per outer
     block; aer_mps: certified bound sqrt(max_o W_o) from directly contracted out-of-code weights, W_o the sum of the
     weights of the inner inputs in the support of the outer block).  The verdict criterion is the combined bound
         op_norm_error = block_error + dropped_total + leak_amplitude <= tol_err .
     The weights `max_leak`, `dirty_ancilla` are diagnostics (max_leak <= leak_amplitude^2).  The code-space weight outside
     the physical span (`extra['max_span_leak']`) is controlled by the Gauss check: |s| <= 4 * gauss_residual.
  6. Gauss residual of the decoded outputs U|psi_k>.
Engines: `sparse` (run_batch), `aer_mps` (per-input MPS, accuracy ~2e-10, flagged in `engine_accuracy`/`certified`),
`auto` (sparse; aer_mps on SimCapExceeded).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np
import scipy.sparse as sp
from scipy.linalg import expm

from su2plaq.encodings.base import Layout
from su2plaq.evaluate import sparse_sim as ss

TOL_GAUSS = 1e-10
TOL_PRUNE = 1e-12          # reject when one simulation dropped more than this (L2, one column)
MPS_ACCURACY = 2e-10       # observed accuracy of Aer's MPS (reports/tests/008)
MPS_CERTIFY_MIN = 1e-9     # aer_mps verdicts are certified only at tolerances >= this (combined noise <= 2e-10 + 3.9e-10; prompts/004 §2)

_DIAG_NAMES = {"z", "s", "sdg", "t", "tdg", "rz", "p", "cz", "cp", "ccz"}


class OuterWriteError(ValueError):
    pass


# ------------------------------------------------------------------------------------------------ outer-qubit analysis
def _commutes_with_Z(U: np.ndarray, i: int) -> bool:
    n = U.shape[0]
    idx = np.arange(n)
    differ = ((idx[:, None] >> i) & 1) != ((idx[None, :] >> i) & 1)
    return bool(np.abs(U[differ]).max(initial=0.0) <= 1e-12)


def _outer_reads(ops, outer: set[int]) -> set[int]:
    read: set[int] = set()
    for name, qs, payload in ops:
        touched = [q for q in qs if q in outer]
        if not touched:
            continue
        if name in _DIAG_NAMES:
            written = []
        elif name == "cx":
            written = [qs[1]]
        elif name == "ccx":
            written = [qs[2]]
        elif name in ("x", "swap"):
            written = list(qs)
        else:  # h, sx, u, unitary: numerical check [U, Z_q] = 0
            written = [q for i, q in enumerate(qs) if q in outer and not _commutes_with_Z(payload, i)]
        bad = [q for q in written if q in outer]
        if bad:
            raise OuterWriteError(f"gate {name} on {qs} is not diagonal on outer qubit(s) {bad}")
        read.update(touched)
    return read


def _canonical_perm(layout: Layout, n_data: int, n: int) -> dict[int, int]:
    """qubit of the circuit -> canonical qubit (data i -> i, outer j -> n_data + j, ancillas after the outer register)."""
    if len(layout.data) != n_data:
        raise ValueError(f"layout has {len(layout.data)} data qubits, expected {n_data}")
    perm = {q: i for i, q in enumerate(layout.data)}
    perm.update({q: n_data + j for j, q in enumerate(layout.outer)})
    base = n_data + len(layout.outer)
    perm.update({q: base + k for k, q in enumerate(layout.ancilla)})
    if sorted(perm) != list(range(n)) or sorted(perm.values()) != list(range(n)):
        raise ValueError("layout does not partition the circuit's qubits")
    return perm


def classify_outer_gates(qc, layout: Layout) -> set[int]:
    """Outer qubits touched by diagonal gates; raises OuterWriteError if any gate is non-diagonal on an outer qubit
    (numerical check [U, Z_q] = 0 at 1e-12 for matrix gates)."""
    if not layout.outer:
        return set()
    ops, _ = ss._translate(qc)
    return _outer_reads(ops, set(layout.outer))


def _phase_of(name, p, v):
    if name == "z":
        return np.pi * v
    if name == "s":
        return 0.5 * np.pi * v
    if name == "sdg":
        return -0.5 * np.pi * v
    if name == "t":
        return 0.25 * np.pi * v
    if name == "tdg":
        return -0.25 * np.pi * v
    if name == "rz":
        return p[0] * (0.5 if v else -0.5)
    if name == "p":
        return p[0] * v
    raise ValueError(name)


def _specialise_ops(ops, gphase, values: dict[int, int]):
    """Resolve the qubits in `values` (qubit -> classical bit) in a gate list that is diagonal on them."""
    out = []
    ph = gphase
    for name, qs, payload in ops:
        hit = [q for q in qs if q in values]
        if not hit:
            out.append((name, qs, payload))
            continue
        if name in ("z", "s", "sdg", "t", "tdg", "rz", "p"):
            ph += _phase_of(name, payload, values[qs[0]])
        elif name == "cz" or name == "ccz":
            rest = [q for q in qs if q not in values]
            if any(values[q] == 0 for q in hit):
                continue
            if len(rest) == 0:
                ph += np.pi
            elif len(rest) == 1:
                out.append(("z", (rest[0],), ()))
            elif len(rest) == 2:
                out.append(("cz", tuple(rest), ()))
            else:
                out.append(("ccz", tuple(rest), ()))
        elif name == "cp":
            rest = [q for q in qs if q not in values]
            if any(values[q] == 0 for q in hit):
                continue
            if len(rest) == 0:
                ph += payload[0]
            else:
                out.append(("p", (rest[0],), payload))
        elif name in ("cx", "ccx"):
            t = qs[-1]
            if t in values:
                raise OuterWriteError(f"gate {name} writes qubit {t}")
            ctrls = [q for q in qs[:-1] if q not in values]
            if any(values[q] == 0 for q in qs[:-1] if q in values):
                continue
            nm = {0: "x", 1: "cx", 2: "ccx"}[len(ctrls)]
            out.append((nm, tuple(ctrls) + (t,), ()))
        elif name == "unitary" or name in ("h", "sx", "u"):
            U = payload
            k = len(qs)
            idx = np.arange(2 ** k)
            keep = np.ones(2 ** k, dtype=bool)
            for i, q in enumerate(qs):
                if q in values:
                    keep &= ((idx >> i) & 1) == values[q]
            rest_pos = [i for i, q in enumerate(qs) if q not in values]
            sub = U[np.ix_(keep, keep)]
            if not rest_pos:
                ph += float(np.angle(sub[0, 0]))
            else:
                out.append(("unitary", tuple(qs[i] for i in rest_pos), sub))
        else:
            raise OuterWriteError(f"gate {name} on {qs} cannot be specialised")
    return out, ph


def _ops_to_circuit(ops, gphase, n):
    from qiskit import QuantumCircuit

    qc = QuantumCircuit(n, global_phase=float(gphase))
    for name, qs, payload in ops:
        if name in ("rz", "p", "cp"):
            getattr(qc, name)(payload[0], *qs)
        elif name in ("unitary", "h", "sx", "u"):
            qc.unitary(np.asarray(payload), list(qs))
        else:
            getattr(qc, name)(*qs)
    return qc


def specialise(qc, read_qubits: set[int], pattern: int):
    """Resolve the read outer bits classically: bit i of `pattern` is the value of the i-th smallest qubit of
    `read_qubits`. Returns a circuit on the same number of qubits in which those qubits are idle."""
    ops, ph = ss._translate(qc)
    qs = sorted(read_qubits)
    values = {q: (pattern >> i) & 1 for i, q in enumerate(qs)}
    new, ph = _specialise_ops(ops, ph, values)
    return _ops_to_circuit(new, ph, qc.num_qubits)


# ------------------------------------------------------------------------------------------------ verdict
@dataclass
class Verdict:
    ok: bool
    reason: str
    op_norm_error: float
    max_leak: float
    dirty_ancilla: float
    phase: complex
    outer_bits_read: int
    n_blocks: int
    gauss_residual: float
    method: str
    engine: str
    seconds: float
    failing_inputs: list
    n_inputs: int
    dropped_total: float = 0.0        # certified pruning bound already included in op_norm_error
    engine_accuracy: float = 0.0      # accuracy of the engine itself (aer_mps ~2e-10); 0 for the exact sparse engine
    certified: bool = True            # False if engine_accuracy exceeds the tolerances the verdict was judged by
    tolerances: dict = field(default_factory=dict)  # {"tol_err","tol_gauss"} actually applied
    block_error: float = float("nan")     # ||A - e^{i phi} V||_2 (inner_span: max(inner-span error, physical error))
    leak_amplitude: float = float("nan")  # ||X||_2 (sparse: exact; aer_mps: certified bound sqrt(max_o W_o))
    extra: dict = field(default_factory=dict)


def synth_tolerances(n_rot: int, eps: float) -> dict:
    """Tolerances for a synthesised circuit with n_rot rotations of precision eps (prompts/003 §2, prompts/004): the triangle
    inequality over the rotations bounds the combined error (block error + leak amplitude) by n_rot*eps (+1e-9 float budget)
    and the Gauss residual by n_rot*eps (+1e-9); there is no separate leak tolerance.  The one place this rule lives; pass as evaluate(..., **synth_tolerances(n, eps))."""
    return {"tol_err": n_rot * eps + 1e-9, "tol_gauss": n_rot * eps + 1e-9}


def _early(reason, t0, method, engine, nread=0, msg="", tol=None):
    inf = float("inf")
    return Verdict(False, reason, inf, inf, inf, 1.0 + 0j, nread, 0, float("nan"), method, engine,
                   time.time() - t0, [("message", msg)] if msg else [], 0, tolerances=dict(tol or {}),
                   block_error=inf, leak_amplitude=inf)


# ------------------------------------------------------------------------------------------------ physical data of an encoding
def _phys_data(enc):
    cache = getattr(enc, "_eval_cache", None)
    if cache is not None:
        return cache
    inner = np.asarray(enc.inner_codes(), dtype=np.int64)
    ev = enc.physical_vectors()
    dim = len(ev.codes)
    codes = np.concatenate(ev.codes)
    amps = np.concatenate(ev.amps).astype(np.complex128)
    st = np.concatenate([np.full(len(c), k) for k, c in enumerate(ev.codes)])
    mask = (1 << ev.n_data) - 1
    data = codes & mask
    didx = np.searchsorted(inner, data)
    if np.any(didx >= len(inner)) or np.any(inner[np.minimum(didx, len(inner) - 1)] != data):
        raise ValueError("physical vector has a data code outside inner_codes()")
    outer = codes >> ev.n_data
    order = np.lexsort((st, outer))
    outer, didx, amps, st = outer[order], didx[order], amps[order], st[order]
    bounds = np.flatnonzero(np.r_[True, outer[1:] != outer[:-1], True])
    o_vals, ks_l, Psi_l, supp_l = [], [], [], []
    for a, b in zip(bounds[:-1], bounds[1:]):
        ks, kinv = np.unique(st[a:b], return_inverse=True)
        P = np.zeros((len(inner), len(ks)), dtype=np.complex128)
        np.add.at(P, (didx[a:b], kinv), amps[a:b])
        o_vals.append(int(outer[a]))
        ks_l.append(ks)
        Psi_l.append(P)
        supp_l.append(np.flatnonzero(np.any(np.abs(P) > 0, axis=1)))
    d = {"inner": inner, "dim": dim, "n_data": ev.n_data, "n_outer": ev.n_outer, "mask": mask,
         "o_vals": np.array(o_vals, dtype=np.int64), "ks": ks_l, "Psi": Psi_l, "supp": supp_l}
    try:
        enc._eval_cache = d
    except AttributeError:  # frozen encoding objects: no caching
        pass
    return d


def _span_basis(d):
    """SVD Z = U S W^dagger of all inner-component columns Z (625 x P); U[:, :r] is an orthonormal basis B of the span S.
    Also caches Z and the block structure (columns of Z grouped by outer pattern). Cached on the encoding data."""
    if "svd" not in d:
        Z = np.hstack(d["Psi"])
        sizes = np.array([len(k) for k in d["ks"]])
        offs = np.r_[0, np.cumsum(sizes)]
        ks_flat = np.concatenate(d["ks"])
        rows = np.concatenate([np.repeat(np.arange(a, b), b - a) for a, b in zip(offs[:-1], offs[1:])])
        cols = np.concatenate([np.tile(np.arange(a, b), b - a) for a, b in zip(offs[:-1], offs[1:])])
        U, sv, Wh = np.linalg.svd(Z, full_matrices=False)
        keep = sv > 1e-10 * sv[0]
        d["Z"], d["blk"] = Z, (ks_flat, rows, cols)
        d["svd"] = (U[:, keep], sv[keep], Wh[keep].conj().T)
    return d["svd"]


def _inner_span_error(d, M, V, phi) -> float:
    """||(M - e^{i phi} V_in) P_S||_2 where V_in realises V on S, i.e. V_in Z = Y := Z (block-diagonal V) (the physical
    target acts on the state index inside every outer pattern); with Z = U S W^dagger, V_in U = Y W S^{-1}."""
    B, sv, W = _span_basis(d)
    ks_flat, rows, cols = d["blk"]
    Vbd = sp.csr_matrix((V[ks_flat[rows], ks_flat[cols]], (rows, cols)), shape=(len(ks_flat), len(ks_flat)))
    VB = (d["Z"] @ (Vbd @ W)) / sv[None, :]
    return float(np.linalg.norm(M @ B - np.exp(1j * phi) * VB, 2))


# ------------------------------------------------------------------------------------------------ simulation of one pattern
def _simulate(qcr, d, engine, cap):
    """-> (M, Xanc, Xinv, dropped_total, dropped_max, engine_used, info). X* are sparse (rows, 625) or None."""
    inner, mask = d["inner"], d["mask"]
    nin = len(inner)
    if engine in ("sparse", "auto"):
        try:
            b = ss.run_batch(qcr, inner, cap=cap)
        except ss.SimCapExceeded:
            if engine == "sparse":
                raise
            engine = "aer_mps"
        else:
            M, _ = ss.encoded_block(b, inner, nin, mask)
            inside = (b.keys & ~np.int64(mask)) == 0
            pos = np.minimum(np.searchsorted(inner, b.keys), nin - 1)
            is_code = inside & (inner[pos] == b.keys)

            def xmat(sel):
                if not sel.any():
                    return None
                uk, inv = np.unique(b.keys[sel], return_inverse=True)
                return sp.csr_matrix((b.amps[sel], (inv, b.cols[sel])), shape=(len(uk), nin))

            return M, xmat(~inside), xmat(inside & ~is_code), b.dropped_total, b.dropped_max, "sparse", {}
    from su2plaq.evaluate.aer_check import aer_mps_block

    M, leak_c, info = aer_mps_block(qcr, inner, inner, mask)
    return M, None, None, 0.0, 0.0, "aer_mps", {"leak_cols": leak_c, **info}


def evaluate(qc, enc, target: np.ndarray, *, tol_err: float = 1e-10,
             tol_gauss: float | None = None, gauss: bool = True,
             method: str = "auto", engine: str = "auto", cap: int = 5_000_000) -> Verdict:
    t0 = time.time()
    tg = TOL_GAUSS if tol_gauss is None else float(tol_gauss)
    tols = {"tol_err": tol_err, "tol_gauss": tg}
    if method not in ("auto", "inner_span", "physical"):
        raise ValueError(f"unknown method {method!r}")
    if engine not in ("auto", "sparse", "aer_mps"):
        raise ValueError(f"unknown engine {engine!r}")
    d = _phys_data(enc)
    dim = d["dim"]
    V = np.asarray(target, dtype=np.complex128)
    if V.shape != (dim, dim):
        raise ValueError(f"target must be {dim}x{dim}, got {V.shape}")
    n_data = d["n_data"]
    try:
        layout = enc.layout_of(qc)
        perm = _canonical_perm(layout, n_data, qc.num_qubits)
    except ValueError as e:
        return _early("bad_layout", t0, method, engine, msg=str(e), tol=tols)
    # 1-2: gates and outer access.  All qubits are relabelled to the canonical frame (data 0..n_data-1, then the outer
    # register, then the ancillas) through the layout lists, so any register order of the circuit is handled.
    try:
        ops, gph = ss._translate(qc)
        ops = [(nm, tuple(perm[q] for q in qs), pl) for nm, qs, pl in ops]
        outer_c = set(range(n_data, n_data + len(layout.outer)))
        read = _outer_reads(ops, outer_c)
    except OuterWriteError as e:
        return _early("writes_outer", t0, method, engine, msg=str(e), tol=tols)
    except ValueError as e:
        return _early("disallowed_gate", t0, method, engine, msg=str(e), tol=tols)
    R = sorted(read)
    if method == "inner_span" and R:
        raise ValueError("method 'inner_span' requires that no outer qubit is read")
    use_method = ("physical" if R else "inner_span") if method == "auto" else method
    # groups of outer patterns by the values of the read bits
    o_vals = d["o_vals"]
    r_of_o = np.zeros(len(o_vals), dtype=np.int64)
    for i, q in enumerate(R):
        r_of_o |= ((o_vals >> (q - n_data)) & 1) << i
    A = np.zeros((dim, dim), dtype=np.complex128)
    w_code = np.zeros(dim)
    w_anc = np.zeros(dim)
    w_inv = np.zeros(dim)
    XX = np.zeros((dim, dim), dtype=np.complex128)   # X^dag X, sparse engine (outputs of different outer patterns are orthogonal)
    have_x = False
    maxW, maxW_anc, maxW_inv, w_inputs = 0.0, 0.0, 0.0, np.zeros(len(d["inner"]))   # aer_mps bound bookkeeping
    out_codes: list[list] = [[] for _ in range(dim)]
    out_amps: list[list] = [[] for _ in range(dim)]
    dropped_total, dropped_max, eng_used = 0.0, 0.0, None
    M_first = None
    groups = np.unique(r_of_o)
    for r in groups:
        if R:
            new, ph = _specialise_ops(ops, gph, {q: (int(r) >> i) & 1 for i, q in enumerate(R)})
            qcr = _ops_to_circuit(new, ph, qc.num_qubits)
        else:
            qcr = _ops_to_circuit(ops, gph, qc.num_qubits)
        try:
            M, Xa, Xi, dt, dm, used, info = _simulate(qcr, d, engine if eng_used is None else eng_used, cap)
        except ss.SimCapExceeded as e:
            return _early("unsimulable", t0, use_method, "sparse", len(R), str(e), tol=tols)
        eng_used = used
        dropped_total += dt
        dropped_max = max(dropped_max, dm)
        if used == "aer_mps":
            wa, wi = info["w_anc"], info["w_inv"]
            w_inputs = np.maximum(w_inputs, wa + wi)
        if M_first is None:
            M_first = M
        Ms = sp.csr_matrix(M) if np.count_nonzero(M) < 0.3 * M.size else M
        for oi in np.flatnonzero(r_of_o == r):
            ks, P = d["ks"][oi], d["Psi"][oi]
            Om = Ms @ P
            A[np.ix_(ks, ks)] += P.conj().T @ Om
            w_code[ks] += np.sum(np.abs(Om) ** 2, axis=0)
            for Xm, wv in ((Xa, w_anc), (Xi, w_inv)):
                if Xm is not None:
                    XP = Xm @ P
                    wv[ks] += np.sum(np.abs(XP) ** 2, axis=0)
                    XX[np.ix_(ks, ks)] += XP.conj().T @ XP
                    have_x = True
            if used == "aer_mps":
                sp_ = d["supp"][oi]
                maxW = max(maxW, float(np.sum(wa[sp_] + wi[sp_])))
                maxW_anc = max(maxW_anc, float(np.sum(wa[sp_])))
                maxW_inv = max(maxW_inv, float(np.sum(wi[sp_])))
            if gauss:
                o_code = int(o_vals[oi]) << n_data
                for j, k in enumerate(ks):
                    col = Om[:, j]
                    nz = np.flatnonzero(np.abs(col) > 1e-14)
                    out_codes[k].append(d["inner"][nz] | o_code)
                    out_amps[k].append(col[nz])
    # 4: phase and error
    tr = np.trace(V.conj().T @ A)
    phase = tr / abs(tr) if abs(tr) > 1e-300 else 1.0 + 0j
    phi = float(np.angle(phase))
    Dm = A - phase * V
    err_phys = float(np.linalg.norm(Dm, 2))
    if use_method == "inner_span":
        # the inner-span error is only meaningful for targets that act on the inner links alone, so it bounds but never
        # replaces the physical error
        err_inner = _inner_span_error(d, M_first, V, phi)
        err = max(err_inner, err_phys)
    else:
        err_inner = None
        err = err_phys
    # 5: leak amplitude (prompts/004): sparse = exact ||X||_2, aer_mps = certified bound sqrt(max_o W_o); no subtraction
    A2 = np.sum(np.abs(A) ** 2, axis=0)
    span_leak = np.maximum(0.0, w_code - A2)  # code-space weight outside the physical span (diagnostic; Gauss check bounds it)
    if eng_used == "aer_mps":
        leak_amp = float(np.sqrt(maxW))
        max_leak, dirty, inv_max = maxW, maxW_anc, maxW_inv
        leak = w_inputs
    else:
        leak_amp = float(np.sqrt(max(np.linalg.eigvalsh((XX + XX.conj().T) / 2)[-1], 0.0))) if have_x else 0.0
        leak = w_anc + w_inv                    # per physical state ||X psi_k||^2, summed directly
        max_leak, dirty, inv_max = float(leak.max()), float(w_anc.max()), float(w_inv.max())
    err_total = err + dropped_total + leak_amp
    # 6: Gauss
    gres = float("nan")
    gk, gstates = np.zeros(0), []
    if gauss:
        from su2plaq.exact.physical import gauss_residuals_coo

        kl, al = [], []
        for k in range(dim):
            if out_codes[k]:
                keys, amps = enc.decode_state(np.concatenate(out_codes[k]), np.concatenate(out_amps[k]))
                kl.append(keys)
                al.append(amps)
        gk = gauss_residuals_coo(enc.basis, kl, al) if kl else np.zeros(0)
        gres = float(gk.max()) if kl else 0.0
        gstates = [k for k in range(dim) if out_codes[k]]
    # verdict
    acc = MPS_ACCURACY if eng_used == "aer_mps" else 0.0
    tmin = min(tol_err, tg) if gauss else tol_err
    certified = (acc <= tmin) and (acc == 0.0 or tmin >= MPS_CERTIFY_MIN)
    if dropped_max > TOL_PRUNE:
        reason = "pruning_bound"
    elif leak_amp > tol_err:
        reason = "dirty_ancilla" if dirty >= inv_max else "leak"
    elif err_total > tol_err:
        reason = "error"
    elif gauss and gres > tg:
        reason = "gauss"
    else:
        reason = "ok"
    colerr = np.linalg.norm(Dm, axis=0)
    if reason == "ok":
        failing = []
    elif reason in ("dirty_ancilla", "leak"):
        if eng_used == "aer_mps":
            failing = [(f"inner_code_index {int(c)}", float(np.sqrt(leak[c]))) for c in np.argsort(-leak)[:10]]
        else:
            failing = [(int(k), float(np.sqrt(leak[k]))) for k in np.argsort(-leak)[:10]]
    elif reason == "gauss":
        failing = [(int(gstates[i]), float(gk[i])) for i in np.argsort(-gk)[:10] if gk[i] > tg]
    elif reason == "pruning_bound":
        failing = [("max_dropped_l2", float(dropped_max))]
    else:
        worst = np.argsort(-colerr)[:10]
        failing = [(int(k), float(colerr[k])) for k in worst if colerr[k] > 0]
    return Verdict(ok=reason == "ok", reason=reason, op_norm_error=err_total, max_leak=max_leak, dirty_ancilla=dirty,
                   phase=complex(phase), outer_bits_read=len(R), n_blocks=len(groups), gauss_residual=gres,
                   method=use_method, engine=eng_used or "sparse", seconds=time.time() - t0, failing_inputs=failing,
                   n_inputs=dim, dropped_total=dropped_total, engine_accuracy=acc, certified=certified, tolerances=tols,
                   block_error=err, leak_amplitude=leak_amp,
                   extra={"op_norm_error_physical": err_phys, "max_dropped_l2": dropped_max, "max_span_leak": float(span_leak.max()),
                          "op_norm_error_inner_span": err_inner})


def inner_target(enc, kind, alpha, beta, order=1) -> np.ndarray:
    """625x625 inner operator in the encoding's local basis order (twelve: Paulo local order, link 0 least significant);
    on the span of the inner components of the physical states it equals the physical target."""
    if getattr(enc, "name", None) != "twelve":
        raise NotImplementedError("inner_target is implemented for the twelve-qubit encoding")
    from su2plaq.exact.operators import plaquette_W

    idx = np.arange(625)
    HE = sum(np.where((idx // 5 ** l) % 5 != 0, 0.75, 0.0) for l in range(4))

    def UE(a):
        return np.diag(np.exp(-1j * a * HE))

    def UB(b):
        W = plaquette_W(convention="paulo")
        return expm(1j * b * (W + W.conj().T))

    if kind == "UE":
        return UE(alpha).astype(np.complex128)
    if kind == "UB":
        return UB(beta).astype(np.complex128)
    if kind == "step":
        if order == 1:
            return (UB(beta) @ UE(alpha)).astype(np.complex128)
        if order == 2:
            return (UE(alpha / 2) @ UB(beta) @ UE(alpha / 2)).astype(np.complex128)
        raise ValueError(f"order must be 1 or 2, got {order}")
    raise ValueError(f"unknown kind {kind!r}")
