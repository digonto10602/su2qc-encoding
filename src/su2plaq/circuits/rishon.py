"""48-qubit rishon circuits (prompts/200 §2.5; METHODS-rishon R7). `build_UE` (5.6), `build_UB`/`pair_frames` (5.7), `build_step` (5.8)."""
from __future__ import annotations

N_DATA, N_OUTER = 16, 32


def _emit_ue(qc, alpha: float, n_links: int = 4) -> None:
    """CX(L1 -> L2), p(-c alpha) on L2, CX on each of the first `n_links` links, c = operators.electric_coefficient()
    (the quartet Casimir of the link algebra, METHODS-rishon R1)."""
    from su2plaq.rishon.operators import electric_coefficient

    coef = electric_coefficient()
    for link in range(n_links):
        l1, l2 = 4 * link, 4 * link + 1
        qc.cx(l1, l2)
        qc.p(-coef * alpha, l2)
        qc.cx(l1, l2)


def build_UE(alpha: float, with_outer: bool = False, include_outer_electric: bool = False):
    """Electric step U_E(alpha) = exp(-i alpha H_E^inner) on the 1296 inner codes (METHODS-rishon R7).

    On a valid link code the link is a quartet (j = 1/2, H_E = 3/4) iff n_{L1} xor n_{L2} = 1 (A = 1100 and B = 0011 have
    equal L bits, the four Q codes differ).  Per link: CX(L1 -> L2), p(-3 alpha / 4) on L2, CX(L1 -> L2) multiplies a
    quartet by e^{-3 i alpha / 4} and leaves A, B alone (2 CX + 1 rotation).  Registers d[16] (+ o[32] if `with_outer`);
    metadata {"kind": "UE", "alpha": alpha}.

    include_outer_electric (needs with_outer) adds the same three gates on each of the 8 outer links: the quartet test is
    valid there too (near end free, far end fixed by the type), giving exp(-i alpha (H_E^inner + H_E^outer)); the outer
    qubits are used only as CX controls/targets that are restored, so every outer basis state is returned unchanged."""
    from qiskit import QuantumCircuit, QuantumRegister

    if include_outer_electric and not with_outer:
        raise ValueError("include_outer_electric needs with_outer=True")
    regs = [QuantumRegister(N_DATA, "d")] + ([QuantumRegister(N_OUTER, "o")] if with_outer else [])
    qc = QuantumCircuit(*regs, name="UE")
    _emit_ue(qc, alpha, 4 + (8 if include_outer_electric else 0))
    qc.metadata = {"kind": "UE", "alpha": alpha}
    return qc


def _registers(with_outer: bool, n_anc: int, name: str):
    from qiskit import QuantumCircuit, QuantumRegister

    regs = [QuantumRegister(N_DATA, "d")]
    if with_outer:
        regs.append(QuantumRegister(N_OUTER, "o"))
    if n_anc:
        regs.append(QuantumRegister(n_anc, "anc"))
    qc = QuantumCircuit(*regs, name=name)
    anc0 = N_DATA + (N_OUTER if with_outer else 0)
    return qc, list(range(anc0, anc0 + n_anc))


def _n_ancillas() -> int:
    from su2plaq.rishon.frames import designs

    return max(max(len(d["controls"]) - 1, 1) for d in designs())


def pair_frames(beta: float) -> list[dict]:
    """Design data of the 81 bright pairs of U_B(beta) = prod_p exp(i kappa_p beta (|u_p><v_p| + h.c.)) (METHODS-rishon R7).

    Per pair: "kappa" (eigenvalue of the operator, not typed in), "pivot" (target qubit j of the rotation), "controls" (qubits
    that must be 0), "frame_gates" (list of (gate name, qubits) of the frame F_p, applied in this order, undone in reverse
    order), "sign" (+-1: the relative sign of the images of u_p and v_p), "angle" = -2 sign kappa beta (the Rx angle) and
    "angle_over_beta".  Everything is solved from `operators.bright_pairs()` at every call; the frame does not depend on beta.
    """
    from su2plaq.rishon.frames import designs

    out = []
    for d in designs():
        ratio = -2.0 * d["sign"] * d["kappa"]
        out.append({**d, "frame_gates": list(d["frame_gates"]), "controls": list(d["controls"]),
                    "angle_over_beta": ratio, "angle": ratio * float(beta)})
    return out


_SELF_INVERSE = {"x": 1, "z": 1, "h": 1, "cx": 1, "cz": 1, "ch": 1, "ccx": 2, "ccz": 3}   # name -> number of symmetric leading qubits
_SYMMETRIC = {"z", "cz", "ccz"}


def _cancel_adjacent(ops: list) -> list:
    """Remove pairs of identical self-inverse gates (x, z, h, cx, cz, ch, ccx, ccz) with nothing in between on their qubits
    (exact; parameterised gates are never touched)."""
    alive = [True] * len(ops)
    stacks: dict[int, list[int]] = {}
    for idx, (name, qs, params) in enumerate(ops):
        key = (name, frozenset(qs) if name in _SYMMETRIC else qs)
        if name in _SELF_INVERSE and not params:
            tops = {stacks[q][-1] if stacks.get(q) else None for q in qs}
            if len(tops) == 1 and None not in tops:
                k = next(iter(tops))
                n2, q2, p2 = ops[k]
                if (n2, frozenset(q2) if n2 in _SYMMETRIC else q2) == key and not p2:
                    for q in qs:
                        stacks[q].pop()
                    alive[k] = alive[idx] = False
                    continue
        for q in qs:
            stacks.setdefault(q, []).append(idx)
    return [op for op, a in zip(ops, alive) if a]


LADDERS = ("ccx", "rccx", "mcx")


def _ladder_names(ladder: str, n: int) -> list[str]:
    """Gate name of each of the n AND gates of a control ladder: "ccx" = all Toffolis (default, M5); "rccx" = all
    relative-phase Toffolis (self-uncomputing mirror, exact); "mcx" = `Builder.mcx` style, rccx everywhere except the last
    AND (which feeds the controlled rotation) as a true ccx (research 202 section 3)."""
    if ladder == "ccx":
        return ["ccx"] * n
    if ladder == "rccx":
        return ["rccx"] * n
    if ladder == "mcx":
        return ["rccx"] * (n - 1) + ["ccx"]
    raise ValueError(f"ladder must be one of {LADDERS}, got {ladder!r}")


def _pair_ops(f: dict, anc: list[int], ladder: str = "ccx") -> list:
    j, ctrl, theta = f["pivot"], f["controls"], f["angle"]
    ops = [(n, tuple(q), ()) for n, q in f["frame_gates"]]
    ops += [("x", (c,), ()) for c in ctrl]
    if len(ctrl) == 1:
        ops.append(("crx", (ctrl[0], j), (theta,)))
    else:
        chain = [(ctrl[0], ctrl[1], anc[0])] + [(anc[i - 2], ctrl[i], anc[i - 1]) for i in range(2, len(ctrl))]
        names = _ladder_names(ladder, len(chain))
        ops += [(nm, c, ()) for nm, c in zip(names, chain)]
        ops.append(("crx", (anc[len(ctrl) - 2], j), (theta,)))
        ops += [(nm, c, ()) for nm, c in reversed(list(zip(names, chain)))]
    ops += [("x", (c,), ()) for c in ctrl]
    ops += [(n, tuple(q), ()) for n, q in reversed(f["frame_gates"])]
    return ops


def _emit_ub(qc, beta: float, anc: list[int], ladder: str = "ccx") -> dict:
    """Append U_B(beta) to `qc` (data qubits 0..15, ancillas `anc`, all clean before and after); returns metadata.
    The 81 pair blocks commute; consecutive blocks share Hadamard/CX/X structure and adjacent identical self-inverse gates
    are cancelled (exact, angle-independent)."""
    frames = pair_frames(beta)
    ops = []
    for f in sorted(frames, key=lambda f: (tuple(f["controls"]), f["pivot"], tuple(f["frame_gates"]))):   # blocks commute
        ops += _pair_ops(f, anc, ladder)
    n_before = len(ops)
    ops = _cancel_adjacent(ops)
    for name, qs, params in ops:
        getattr(qc, name)(*params, *qs)
    hist: dict[str, int] = {}
    for f in frames:
        key = f"{abs(f['angle_over_beta']):.12g}"
        hist[key] = hist.get(key, 0) + 1
    return {"n_pairs": len(frames), "angle_over_beta_abs_counts": hist, "pivots": sorted({f["pivot"] for f in frames}),
            "n_controls": sorted({len(f["controls"]) for f in frames}), "gates_before_cancel": n_before,
            "gates_after_cancel": len(ops)}


def build_UB(beta: float, with_outer: bool = False, ladder: str = "ccx"):
    """Magnetic step U_B(beta) = exp(-i beta H_B^inner) as 81 commuting two-level rotations (METHODS-rishon R7).

    Pair p: F_p (Clifford-type frame, X/CX/Z/CZ/H and j-controlled versions) maps the bright vectors u_p, v_p of
    H_B^in = -sum_p kappa_p (|u_p><v_p| + h.c.) to two computational codes that differ in the pivot bit j only; then
    Rx(-2 s_p kappa_p beta) on j controlled on the (zero) bits that separate that pair from the images of every other valid
    code (`ladder` selects the control-ladder style on clean ancillas, mirrored uncompute: "ccx" Toffolis (default; the M5 circuit), "rccx" relative-phase Toffolis, "mcx" = rccx..ccx..rccx as `Builder.mcx`; the uncompressed rccx/mcx variants are rejected by the prune cap, reports/tests/204 N1, research 202 section 3), then F_p^dagger.  The angles are 2 beta (x32), 4 beta (x48) and
    8 sqrt(2) beta (x1) (kappa = 1, 2, 4 sqrt 2), signs from the operator.  Registers d (+ o), then ancillas `anc`;
    metadata {"kind": "UB", "beta": beta, "n_pairs": 81, ...}."""
    _ladder_names(ladder, 1)
    n_anc = _n_ancillas()
    qc, anc = _registers(with_outer, n_anc, "UB")
    meta = _emit_ub(qc, float(beta), anc, ladder)
    qc.metadata = {"kind": "UB", "beta": float(beta), **meta}
    return qc


def build_UD(eta: float, with_outer: bool = False, include_outer_det: bool = False):
    """Det layer U_D(eta) = exp(-i eta H_D^in) on d (+ o): the general 8-CX gadget per link (prompts/204 section 4).
    include_outer_det (needs with_outer) adds the gadget on the 8 outer links.  metadata {"kind": "UD", "eta": eta}.
    STUB (prompts/204 step D3)."""
    raise NotImplementedError("PENDING: circuits.rishon.build_UD (prompts/204 step D3)")


def prepend_det_layer(unit, eta: float):
    """New circuit on `unit`'s registers (first register must be d[16], else ValueError): the det gadgets on d, then all of
    `unit`'s instructions unchanged and in order (prompts/204 sections 5, 6.1).  STUB (prompts/204 step D3)."""
    raise NotImplementedError("PENDING: circuits.rishon.prepend_det_layer (prompts/204 step D3)")


def build_step(alpha: float, beta: float, order: int = 1, with_outer: bool = False, ladder: str = "ccx", eta: float | None = None):
    """One Trotter step on d (+ o) and the U_B ancillas: order 1 = U_B(beta) U_E(alpha) (electric layer applied first),
    order 2 = U_E(alpha/2) U_B(beta) U_E(alpha/2)  (prompts/200 METHODS §2).  `ladder` as in `build_UB`.  metadata {"kind": "step", ...}.
    `eta` (prompts/204): angle of the det layer; with it the step is U_B U_D(eta) U_E (order 2: half-angle det gadgets), not built yet;
    `eta=None` is the two-layer circuit above."""
    if order not in (1, 2):
        raise ValueError(f"step order must be 1 or 2, got {order}")
    if eta is not None:
        raise NotImplementedError("PENDING: build_step(eta=...) three-layer step (prompts/204 step D3)")
    _ladder_names(ladder, 1)
    n_anc = _n_ancillas()
    qc, anc = _registers(with_outer, n_anc, f"step{order}")

    def electric(a):
        _emit_ue(qc, a)

    if order == 1:
        electric(float(alpha))
        meta = _emit_ub(qc, float(beta), anc, ladder)
    else:
        electric(float(alpha) / 2)
        meta = _emit_ub(qc, float(beta), anc, ladder)
        electric(float(alpha) / 2)
    qc.metadata = {"kind": "step", "alpha": float(alpha), "beta": float(beta), "order": order, **meta}
    return qc
