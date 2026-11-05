"""12-qubit circuits (prompts/002 §2.6; docs/METHODS.md §2). Register order: d (12), then o (16) if present, then ancillas."""
from __future__ import annotations

from su2plaq._stub import todo

N_DATA, N_OUTER = 12, 16
INNER_J_QUBITS = (2, 5, 8, 11)          # q_j of the inner links b, r, t, l (qubits 3l + 2)
OUTER_J_QUBITS = tuple(12 + 2 * k + 1 for k in range(8))   # q_j of outer link k (qubits 12 + 2k + 1)


def build_UE(alpha: float, with_outer: bool = False, include_outer_electric: bool = False):
    """Electric step U_E(alpha) = exp(-i alpha H_E^inner): one p(-3 alpha / 4) on the j-qubit of each inner link (the code
    of a j = 1/2 link has q_j = 1 and j(j+1) = 3/4; Qiskit p(l) = diag(1, e^{il})).  Registers d[12] (+ o[16] if
    `with_outer`); metadata {"kind": "UE", "alpha": alpha}.

    include_outer_electric (needs with_outer) adds the same p(-3 alpha / 4) on the j-qubit of each of the 8 outer links,
    i.e. exp(-i alpha (H_E^inner + H_E^outer)) = operators.target(..., "UE", include_outer_electric=True)."""
    from qiskit import QuantumCircuit, QuantumRegister

    if include_outer_electric and not with_outer:
        raise ValueError("include_outer_electric needs with_outer=True")
    regs = [QuantumRegister(N_DATA, "d")] + ([QuantumRegister(N_OUTER, "o")] if with_outer else [])
    qc = QuantumCircuit(*regs, name="UE")
    lam = -0.75 * alpha
    for q in INNER_J_QUBITS:
        qc.p(lam, q)
    if include_outer_electric:
        for q in OUTER_J_QUBITS:
            qc.p(lam, q)
    qc.metadata = {"kind": "UE", "alpha": alpha}
    return qc


# ---------------------------------------------------------------------------------------------------------------------
# Magnetic step: port of Paulo's notebook refs/paulo/optimized_plaquette_dontcare_lowT.ipynb (cells 3-23), alpha_P = 2 beta.
# Registers d12 p4 e4 w7 g3 tmp3 h1 (22 ancillas, all returned to |0>).  `native_mcrx=True` keeps the notebook's two
# two-control rotations as qiskit `mcrx` (used only for paulo_logical); `False` replaces each by
# rccx(active, g, h) - crx(theta, h, side) - rccx(active, g, h) on the scratch qubit h (macros only).
# ---------------------------------------------------------------------------------------------------------------------
def _qm_p(link):
    return 3 * link


def _qm(link):
    return 3 * link + 1


def _qj(link):
    return 3 * link + 2


_JIDX = [_qj(l) for l in range(4)]
# vertices a, b, c, d: (x endpoint bit, y endpoint bit, incident jx, incident jy)
_VERTEX_SPEC = [(_qm(3), _qm(0), _qj(3), _qj(0)), (_qm_p(0), _qm(1), _qj(0), _qj(1)),
                (_qm_p(1), _qm_p(2), _qj(1), _qj(2)), (_qm(2), _qm_p(3), _qj(2), _qj(3))]


def _registers(with_outer: bool):
    from qiskit import QuantumCircuit, QuantumRegister

    d = QuantumRegister(N_DATA, "d")
    regs = {"d": d}
    order = [d]
    if with_outer:
        regs["o"] = QuantumRegister(N_OUTER, "o")
        order.append(regs["o"])
    for nm, n in (("p", 4), ("e", 4), ("w", 7), ("g", 3), ("tmp", 3), ("h", 1)):
        regs[nm] = QuantumRegister(n, nm)
        order.append(regs[nm])
    return QuantumCircuit(*order, name="UB"), regs


def _paulo_ub(beta: float, with_outer: bool, native_mcrx: bool):
    qc, R = _registers(with_outer)
    d, p, e, w, g, tmp, h = R["d"], R["p"], R["e"], R["w"], R["g"], R["tmp"], R["h"][0]
    alpha = 2.0 * beta                                    # alpha_P = 2 beta
    verts = [(d[x], d[y], d[jx], d[jy]) for x, y, jx, jy in _VERTEX_SPEC]
    j = [d[q] for q in _JIDX]
    ys = [v[1] for v in verts]
    xs = [v[0] for v in verts]
    side = j[3]
    pairs = [(j[3], j[0]), (j[0], j[1]), (j[1], j[2]), (j[2], j[3])]

    def cond_h(jx, jy, target):                           # exact controlled-H on j_x j_y = 11 (scratch h)
        qc.rccx(jx, jy, h)
        qc.sdg(target), qc.h(target), qc.tdg(target)
        qc.cx(h, target)
        qc.t(target), qc.h(target), qc.s(target)
        qc.rccx(jx, jy, h)

    def forward_color():
        for link in (2, 3):
            qc.cx(d[_qj(link)], d[_qm(link)])
            qc.cx(d[_qj(link)], d[_qm_p(link)])
        for x, y, jx, jy in verts:
            qc.cx(x, y)
            qc.ccx(jx, y, x)
        qc.z(verts[0][0])
        qc.z(verts[2][0])
        for x, y, jx, jy in verts:
            cond_h(jx, jy, x)

    def inverse_color():
        for x, y, jx, jy in reversed(verts):
            cond_h(jx, jy, x)
        qc.z(verts[2][0])
        qc.z(verts[0][0])
        for x, y, jx, jy in reversed(verts):
            qc.ccx(jx, y, x)
            qc.cx(x, y)
        for link in (3, 2):
            qc.cx(d[_qj(link)], d[_qm_p(link)])
            qc.cx(d[_qj(link)], d[_qm(link)])

    def domain_walls(inverse=False):
        seq = list(zip(p, pairs))
        for pi, (a, b) in (reversed(seq) if inverse else seq):
            if inverse:
                qc.cx(b, pi), qc.cx(a, pi)
            else:
                qc.cx(a, pi), qc.cx(b, pi)

    def errors(inverse=False):
        seq = list(zip(p, ys, e))
        for pi, yi, ei in (reversed(seq) if inverse else seq):
            qc.x(pi), qc.rccx(pi, yi, ei), qc.x(pi)

    conds = xs + list(e)

    def active_flag(inverse=False):
        if not inverse:
            for q in conds:
                qc.x(q)
            qc.rccx(conds[0], conds[1], w[0])
            for i in range(2, 8):
                qc.rccx(w[i - 2], conds[i], w[i - 1])
        else:
            for i in reversed(range(2, 8)):
                qc.rccx(w[i - 2], conds[i], w[i - 1])
            qc.rccx(conds[0], conds[1], w[0])
            for q in reversed(conds):
                qc.x(q)

    def pair_basis(inverse=False):
        for k in ((2, 1, 0) if inverse else (0, 1, 2)):
            qc.cx(side, j[k])

    r0, r1, r2 = j[0], j[1], j[2]
    g1, gq, gh = g[0], g[1], g[2]
    t0, t1 = tmp[0], tmp[1]

    def g_class(inverse=False):
        if not inverse:
            qc.x(r0), qc.x(r1), qc.x(r2)
            qc.rccx(r0, r1, t0), qc.rccx(t0, r2, g1)
            qc.x(r2), qc.x(r1), qc.x(r0)
            qc.x(r1)
            qc.rccx(r0, r1, t1), qc.rccx(t1, r2, gq)
            qc.x(r1)
            qc.x(gh), qc.cx(g1, gh), qc.cx(gq, gh)
        else:
            qc.cx(gq, gh), qc.cx(g1, gh), qc.x(gh)
            qc.x(r1)
            qc.rccx(t1, r2, gq), qc.rccx(r0, r1, t1)
            qc.x(r1)
            qc.x(r0), qc.x(r1), qc.x(r2)
            qc.rccx(t0, r2, g1), qc.rccx(r0, r1, t0)
            qc.x(r2), qc.x(r1), qc.x(r0)

    def domain_colors(inverse=False):
        seq = list(zip(p, ys))
        for pi, yi in (reversed(seq) if inverse else seq):
            qc.rccx(pi, side, yi)

    def sign_conjugation():
        qc.cz(ys[1], side), qc.cz(ys[3], side), qc.cz(p[1], side), qc.cz(tmp[2], side)
        qc.cz(gh, side)

    def rotations():
        active = w[6]
        for theta, ctl in ((-2.0 * alpha, g1), (-1.0 * alpha, gh)):
            if native_mcrx:
                qc.mcrx(theta, [active, ctl], side)
            else:
                qc.rccx(active, ctl, h)
                qc.crx(theta, h, side)
                qc.rccx(active, ctl, h)
        qc.crx(-0.5 * alpha, gq, side)

    forward_color()
    domain_walls(), errors(), active_flag()
    pair_basis()
    g_class()
    domain_colors()
    qc.rccx(p[2], p[3], tmp[2])
    sign_conjugation()
    rotations()
    sign_conjugation()
    qc.rccx(p[2], p[3], tmp[2])
    domain_colors(True)
    g_class(True)
    pair_basis(True)
    active_flag(True), errors(True), domain_walls(True)
    inverse_color()
    qc.metadata = {"kind": "UB", "beta": beta}
    return qc


def build_UB(beta: float, with_outer: bool = False):
    """Magnetic step U_B(beta) = exp(+i beta (Tr U_P + h.c.)) (alpha_P = 2 beta in Paulo's notation), exact on the 625 inner
    codes (Paulo basis); a port of Paulo's notebook with its two two-control rotations replaced by rccx / crx / rccx on the
    scratch qubit h, so only BASIS and MACROS gates occur.  Registers d[12] (+ o[16]), p4 e4 w7 g3 tmp3 h1 (22 ancillas,
    clean at the end).  The outer register is never touched.  Same gate skeleton for every beta."""
    return _paulo_ub(beta, with_outer, native_mcrx=False)


def build_step(alpha: float, beta: float, order: int = 1, with_outer: bool = False):
    todo("build_step")


def paulo_logical(beta: float = 1.0):
    """Faithful reconstruction of the notebook circuit (registers d p e w g tmp h, native mcrx / crx; alpha_P = 2 beta) for
    cross-checks only: NOT an allowed-gate circuit."""
    return _paulo_ub(beta, False, native_mcrx=True)


def paulo_circuit():
    todo("paulo_circuit")
