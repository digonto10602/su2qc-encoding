"""Clifford+T synthesis and T-counts (prompts/002 §2.8, docs/METHODS.md §7).

* pygridsynth 1.2.0 (Ross-Selinger gridsynth): `rz(theta) = diag(e^{-i theta/2}, e^{i theta/2})` to operator-norm error eps up
  to a global phase.  Words are operator products (leftmost letter acts last); W = e^{i pi/4} is a global phase.
  Multiples of pi/4 are exact words (no synthesis).  Every word's error is asserted <= eps.
* Qiskit's Clifford+T pass manager with Paulo's settings as an independent second implementation.
"""
from __future__ import annotations

import functools
import math

import mpmath
import numpy as np

from su2plaq.metrics.logical import is_clifford_t_angle, lower

_M = {
    "H": np.array([[1, 1], [1, -1]]) / math.sqrt(2),
    "S": np.diag([1, 1j]),
    "T": np.diag([1, np.exp(1j * math.pi / 4)]),
    "X": np.array([[0, 1], [1, 0]]),
    "W": np.eye(2) * np.exp(1j * math.pi / 4),
}
# rz(k pi/4) = T^k up to a global phase
_EXACT = {0: "", 1: "T", 2: "S", 3: "ST", 4: "SS", 5: "SST", 6: "SSS", 7: "SSST"}


def _word_matrix(word: str) -> np.ndarray:
    U = np.eye(2, dtype=complex)
    for ch in word:
        U = U @ _M[ch]
    return U


def word_error(word, theta) -> float:
    """min_phi ||U_word - e^{i phi} rz(theta)||_2."""
    A = _word_matrix(word)
    B = np.diag([np.exp(-0.5j * theta), np.exp(0.5j * theta)])
    ov = np.trace(B.conj().T @ A)
    ph = ov / abs(ov) if abs(ov) > 1e-300 else 1.0
    return float(np.linalg.norm(A - ph * B, 2))


@functools.lru_cache(maxsize=None)
def _word_cached(theta: float, eps: float) -> str:
    if is_clifford_t_angle(theta):
        return _EXACT[round(theta / (math.pi / 4)) % 8]
    from pygridsynth.gridsynth import gridsynth_gates

    w = str(gridsynth_gates(theta=mpmath.mpf(repr(theta)), epsilon=mpmath.mpf(repr(eps))))
    err = word_error(w, theta)
    if err > eps:
        raise RuntimeError(f"pygridsynth word for theta={theta!r}, eps={eps!r} has error {err:.3e} > eps")
    return w


def pygridsynth_word(theta: float, eps: float) -> str:
    """Clifford+T word (letters H S T X W) for rz(theta) within eps; exact for multiples of pi/4. Cached per (theta, eps)."""
    return _word_cached(float(theta), float(eps))


def pygridsynth_tcount(theta, eps) -> int:
    return pygridsynth_word(theta, eps).count("T")


def t_estimate(n_rot: int, t_fixed: int, eps: float) -> float:
    """t_fixed + n_rot * 3 log2(1/eps)  (Ross-Selinger leading term per rotation)."""
    return t_fixed + n_rot * 3.0 * math.log2(1.0 / eps)


def ct_compile(qc, eps: float, level: int = 3, seed: int = 12345):
    """Qiskit Clifford+T pass manager with Paulo's settings. Returns (circuit, {"cx","t","depth","qubits","gates"})."""
    from qiskit.transpiler import generate_preset_clifford_t_pass_manager

    pm = generate_preset_clifford_t_pass_manager(
        basis_gates=["cx", "h", "s", "sdg", "t", "tdg"], optimization_level=level,
        rz_synthesis_config={"rz_synthesis_error": eps, "rz_cache_error": eps / 10}, seed_transpiler=seed,
        qubits_initially_zero=False)
    out = pm.run(qc)
    ops = dict(out.count_ops())
    return out, {"cx": ops.get("cx", 0), "t": ops.get("t", 0) + ops.get("tdg", 0), "depth": out.depth(),
                 "qubits": out.num_qubits, "gates": ops}


def synthesize(qc, eps: float):
    """Replace every rz of the level-0 lowering by its Clifford+T word (gate order preserved; W dropped, X -> H S S H;
    multiples of pi/4 by exact S/T words).  Global phases of the replaced rotations are not tracked (the evaluator allows
    one global phase).  Returns (circuit, {"n_rot","t_rot","error_bound_sum" = n_rot*eps, "error_measured_sum" = sum of the measured per-word
    errors (<= error_bound_sum), "per_rotation":[...]}).  Rotations at multiples of pi/4 are exact and not counted."""
    from qiskit import QuantumCircuit

    low = lower(qc)
    out = QuantumCircuit(*low.qregs, *low.cregs, global_phase=low.global_phase)
    per, n_rot, t_rot, err_meas = [], 0, 0, 0.0
    for inst in low.data:
        op, qs = inst.operation, [low.find_bit(q).index for q in inst.qubits]
        if op.name != "rz":
            out.append(op, [out.qubits[q] for q in qs])
            continue
        th = float(op.params[0])
        w = pygridsynth_word(th, eps)
        q = out.qubits[qs[0]]
        for ch in reversed(w):  # rightmost letter acts first
            if ch == "H":
                out.h(q)
            elif ch == "S":
                out.s(q)
            elif ch == "T":
                out.t(q)
            elif ch == "X":
                out.h(q), out.s(q), out.s(q), out.h(q)
            elif ch == "W":
                continue
            else:
                raise ValueError(f"unknown letter {ch!r}")
        exact = is_clifford_t_angle(th)
        err = 0.0 if exact else word_error(w, th)
        if not exact:
            n_rot += 1
            t_rot += w.count("T")
            err_meas += err
        per.append({"theta": th, "t": w.count("T"), "exact": exact, "error": err})
    return out, {"n_rot": n_rot, "t_rot": t_rot, "error_bound_sum": n_rot * eps, "error_measured_sum": err_meas,
                  "per_rotation": per}


def t_table(qc, eps_list=(1e-4, 1e-6, 1e-8, 1e-10), qiskit: bool = True) -> list[dict]:
    """Per eps: {"eps","t_fixed","n_rot","t_rot_pygridsynth","t_total","t_est","t_qiskit","cx_qiskit","depth_qiskit"}
    (t_total = t_fixed + sum of pygridsynth T counts; t_est = t_fixed + 3 n_rot log2(1/eps); the t_*qiskit entries are
    None when qiskit=False)."""
    from su2plaq.metrics.logical import logical_metrics

    m = logical_metrics(qc)
    low = lower(qc) if qiskit else None
    rows = []
    for eps in eps_list:
        t_rot = sum(pygridsynth_tcount(th, eps) for th in m["rz_angles"])
        row = {"eps": eps, "t_fixed": m["t_fixed"], "n_rot": m["n_rot"], "t_rot_pygridsynth": t_rot,
               "t_total": m["t_fixed"] + t_rot, "t_est": t_estimate(m["n_rot"], m["t_fixed"], eps),
               "t_qiskit": None, "cx_qiskit": None, "depth_qiskit": None}
        if qiskit:
            _, c = ct_compile(low, eps)
            row.update(t_qiskit=c["t"], cx_qiskit=c["cx"], depth_qiskit=c["depth"])
        rows.append(row)
    return rows
