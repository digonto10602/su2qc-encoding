"""Rishon verification (prompts/200 §2.6; METHODS-rishon R6): the laptop evaluator on the inner view (1296 codes) plus a
sampled rishon Gauss check on 17 closed + 256 seeded physical states.  Outer-reading circuits are not supported in M5."""
from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np
import scipy.sparse as sp

from su2plaq.evaluate import sparse_sim as ss
from su2plaq.evaluate.evaluator import TOL_GAUSS, Verdict, classify_outer_gates, evaluate, synth_tolerances  # noqa: F401
from su2plaq.rishon import operators as _ops
from su2plaq.rishon import physical as _phys

_AMP_DROP = 1e-14          # output amplitudes below this are dropped before the Gauss check (as in the laptop evaluator)
_CACHE: dict = {}


@dataclass
class RishonVerdict:
    ok: bool
    reason: str
    certified: bool
    op_norm_error: float
    block_error: float
    leak_amplitude: float
    dropped_total: float
    max_leak: float
    dirty_ancilla: float
    phase: complex
    gauss_residual: float
    gauss_states: int
    outer_bits_read: int
    method: str
    engine: str
    seconds: float
    tolerances: dict
    failing_inputs: list
    inner_verdict: Verdict | None
    extra: dict = field(default_factory=dict)


def _sample_ids(b, n: int, seed: int) -> list[int]:
    return _phys.closed_indices(b) + _phys.sample_indices(b, n=n, seed=seed)


def _pairs(b, ids: list[int]):
    """Inner components of the physical states `ids` as columns (one per (state, outer pattern)):
    (Z csr [1296, npairs], pair_state (position in ids), pair_outer)."""
    ck = (id(b), tuple(ids))
    if ck in _CACHE:
        return _CACHE[ck][1:]
    codes = _ops.inner_codes()
    sid = np.concatenate([np.full(len(b.keys[k]), j, dtype=np.int64) for j, k in enumerate(ids)])
    keys = np.concatenate([np.asarray(b.keys[k], dtype=np.int64) for k in ids])
    amps = np.concatenate([np.asarray(b.amps[k], dtype=np.complex128) for k in ids])
    inner = keys & 0xFFFF
    rows = np.searchsorted(codes, inner)
    if np.any(rows >= len(codes)) or np.any(codes[np.minimum(rows, len(codes) - 1)] != inner):
        raise ValueError("a physical state has an inner component outside the valid code space")
    pk = (sid << 32) | (keys >> 16)
    upk, col = np.unique(pk, return_inverse=True)
    Z = sp.csr_matrix((amps, (rows, col)), shape=(len(codes), len(upk)))
    out = (Z, upk >> 32, upk & 0xFFFFFFFF)
    if len(_CACHE) > 8:
        _CACHE.clear()
    _CACHE[ck] = (b,) + out          # keeps the basis alive so id() stays unique
    return out


def _code_block(qc, layout, codes: np.ndarray, cap: int) -> np.ndarray:
    """M[a, c] = <code_a| U |code_c> with ancillas (and outer qubits) 0 on input and the data register read through
    `layout.data` (bit i of a code = circuit qubit layout.data[i]); amplitudes outside the code space are not in M."""
    dq = list(layout.data)
    ident = dq == list(range(len(dq)))
    inputs = codes if ident else sum(((codes >> i) & 1) << q for i, q in enumerate(dq))
    batch = ss.run_batch(qc, np.asarray(inputs, dtype=np.int64), cap=cap)
    keys = batch.keys
    dmask = sum(1 << q for q in dq)
    dc = keys if ident else sum(((keys >> q) & 1) << i for i, q in enumerate(dq))
    inside = (keys & ~np.int64(dmask)) == 0
    pos = np.minimum(np.searchsorted(codes, dc), len(codes) - 1)
    is_code = inside & (codes[pos] == dc)
    M = np.zeros((len(codes), len(codes)), dtype=np.complex128)
    np.add.at(M, (pos[is_code], batch.cols[is_code]), batch.amps[is_code])
    return M


def _gauss_sample(qc, enc, gauss_sample: int, seed: int, cap: int) -> tuple[float, int]:
    """Max Gauss residual of U Psi_k over the 17 closed + `gauss_sample` seeded physical states, and their number."""
    b = enc.basis
    ids = _sample_ids(b, gauss_sample, seed)
    Z, pst, pout = _pairs(b, ids)
    codes = _ops.inner_codes()
    M = _code_block(qc, enc.layout_of(qc), codes, cap)
    O = (sp.csr_matrix(M) @ Z).tocoo()
    keep = np.abs(O.data) > _AMP_DROP
    r, c, v = O.row[keep], O.col[keep], O.data[keep]
    key = codes[r] | (pout[c] << 16)
    st = pst[c]
    order = np.argsort(st, kind="stable")
    key, v, st = key[order], v[order], st[order]
    bounds = np.searchsorted(st, np.arange(len(ids) + 1))
    kl = [key[bounds[j]:bounds[j + 1]] for j in range(len(ids))]
    al = [v[bounds[j]:bounds[j + 1]] for j in range(len(ids))]
    res = _phys.gauss_residuals_coo(kl, al)
    return float(res.max()), len(ids)


_CLASSIFY_REASONS = frozenset({"bad_layout", "writes_outer", "disallowed_gate"})


def _early(inner: Verdict | None, reason: str, t0: float, tols: dict, nread: int = 0, msg: str = "") -> RishonVerdict:
    inf = float("inf")
    return RishonVerdict(False, reason, False, inf, inf, inf, inf, inf, inf, 1.0 + 0j, float("nan"), 0, nread,
                         "inner_block", "sparse", time.time() - t0, dict(tols), [("message", msg)] if msg else [], inner)


def verify(qc, enc, kind: str, alpha: float | None, beta: float | None, order: int = 1, *, tol_err: float = 1e-10,
           tol_gauss: float | None = None, gauss: bool = True, gauss_sample: int = 256, seed: int = 20261104,
           engine: str = "auto", cap: int = 5_000_000, target: np.ndarray | None = None,
           states=None) -> RishonVerdict:
    """Verify `qc` against the rishon inner target (kind, alpha, beta, order) or an explicit 1296x1296 `target`.

    1. outer qubits read by diagonal gates -> reason 'outer_read_unsupported' (the inner view is unsound, METHODS-rishon R6);
       an outer write / bad layout / disallowed gate is reported by the laptop `evaluate` ('writes_outer', ...).
    2. inner-block verdict = laptop `evaluate` on `enc.inner_view()` (all 38 432 physical states for outer-blind circuits).
    3. sampled Gauss residual of the circuit outputs on 17 closed + `gauss_sample` seeded physical states (sparse engine).

    `states` (M6 trial mode, prompts/203 section 2): optional subset of inner-code positions; only those columns are formed
    (laptop `evaluate(states=...)`, phase / errors refer to them); use with `gauss=False`."""
    t0 = time.time()
    tg = TOL_GAUSS if tol_gauss is None else float(tol_gauss)
    tols = {"tol_err": tol_err, "tol_gauss": tg}
    classify_error = ""
    try:
        read = classify_outer_gates(qc, enc.layout_of(qc))
    except ValueError as e:     # incl. OuterWriteError: bad layout / outer write / disallowed gate
        read, classify_error = set(), f"{type(e).__name__}: {e}"    # recorded; `evaluate` below must reject (asserted)
    if read:
        return _early(None, "outer_read_unsupported", t0, tols, len(read),
                      f"outer qubits {sorted(read)} are read by the circuit; the block-wise path is M6")
    view = enc.inner_view()
    V = enc.inner_target(kind, alpha, beta, order) if target is None else np.asarray(target, dtype=np.complex128)
    iv = evaluate(qc, view, V, tol_err=tol_err, tol_gauss=tg, gauss=False, engine=engine, cap=cap, states=states)
    if classify_error and (iv.ok or iv.reason not in _CLASSIFY_REASONS):
        raise RuntimeError(f"classify_outer_gates raised ({classify_error}) but evaluate returned reason "
                           f"{iv.reason!r} (ok={iv.ok}); expected one of {sorted(_CLASSIFY_REASONS)}")
    gres, gstates, reason = float("nan"), 0, iv.reason
    simulated = np.isfinite(iv.op_norm_error)
    if gauss and simulated:
        try:
            gres, gstates = _gauss_sample(qc, enc, gauss_sample, seed, cap)
        except ss.SimCapExceeded:
            if iv.ok:
                reason = "unsimulable_gauss"
        else:
            if iv.ok and gres > tg:
                reason = "gauss"
    failing = list(iv.failing_inputs)
    if reason == "gauss":
        failing = [("gauss_residual", gres), ("tol_gauss", tg)]
    return RishonVerdict(ok=reason == "ok", reason=reason, certified=iv.certified, op_norm_error=iv.op_norm_error,
                         block_error=iv.block_error, leak_amplitude=iv.leak_amplitude, dropped_total=iv.dropped_total,
                         max_leak=iv.max_leak, dirty_ancilla=iv.dirty_ancilla, phase=iv.phase, gauss_residual=gres,
                         gauss_states=gstates, outer_bits_read=iv.outer_bits_read, method="inner_block",
                         engine=iv.engine, seconds=time.time() - t0, tolerances=dict(iv.tolerances),
                         failing_inputs=failing, inner_verdict=iv,
                         extra={"inner_method": iv.method, "gauss_sample": gauss_sample, "seed": seed,
                                **({"classify_error": classify_error} if classify_error else {})})


def physical_cross_check(qc, enc, kind, alpha, beta, order=1, states: list[int] | None = None) -> dict:
    """Explicit A_{k'k} = <Psi_k'|U|Psi_k> on `states` (default: 17 closed + 256 seeded) against
    <Psi_k'|V_in (x) 1|Psi_k> = enc.target(..., states); -> {"max_abs_diff", "n_states", "phase"} (one global phase fitted).
    Sampled tester tool, not a verdict input."""
    b = enc.basis
    ids = _sample_ids(b, 256, 20261104) if states is None else list(states)
    Z, pst, pout = _pairs(b, ids)
    codes = _ops.inner_codes()
    M = _code_block(qc, enc.layout_of(qc), codes, 5_000_000)
    O = sp.csr_matrix(M) @ Z
    G = (Z.conj().T @ O).tocoo()
    same = pout[G.row] == pout[G.col]
    A = np.zeros((len(ids), len(ids)), dtype=np.complex128)
    np.add.at(A, (pst[G.row[same]], pst[G.col[same]]), G.data[same])
    T = enc.target(kind, alpha, beta, order, states=ids)
    tr = np.trace(T.conj().T @ A)
    phase = tr / abs(tr) if abs(tr) > 1e-300 else 1.0 + 0j
    return {"max_abs_diff": float(np.abs(A - phase * T).max()), "n_states": len(ids), "phase": complex(phase)}
