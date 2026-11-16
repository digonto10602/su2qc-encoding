"""The two fuzzy compression units as encodings (prompts/302; METHODS-fuzzy F9): `FuzzyUBTask` (`fuzzy_ub`, kind UB) and
`FuzzyLinkTask` (`fuzzy_link`, kind UE), the factories of their registry entries (prompts/008 step B5).  Kept apart from
`compress_hook` (hooks, step composition) so that the shared code can instantiate the units without importing the hook module."""
from __future__ import annotations

from su2plaq.fuzzy import targets as tg
from su2plaq.fuzzy.verify import FuzzyBlockEncoding


class _Basis:
    """All 2^n computational codes are physical: labels code0 .. code{2^n-1}."""

    def __init__(self, n: int):
        self.labels = [f"code{k}" for k in range(n)]

    def index(self, key):
        return self.labels.index(key)


_PROPOSER_NOTE = (
    "Proposer commands (the fuzzy hook is installed by these wrappers; the plain `python -m su2plaq.compress.*` modules do not know "
    "the fuzzy units, so use the script): `python scripts/m10_round.py candidate <program.py> --encoding {enc} --kind {kind} --trial|--full` "
    "(wraps `su2plaq.compress.run_candidate`), `python scripts/m10_round.py oracle --encoding {enc} --kind {kind} [--column j] [--element i j]`. "
    "Programs import only `su2plaq.compress.{{builder,oracle,spec}}` and numpy. Background: docs/METHODS-fuzzy.md F5, F9.\n")


class FuzzyUBTask(FuzzyBlockEncoding):
    name = "fuzzy_ub"

    def __init__(self):
        super().__init__(8, data_qubits=list(range(8)))
        self.registers = {"d": list(range(8)), "row_b": [1, 0], "row_r": [3, 2], "row_t": [5, 4], "row_l": [7, 6]}
        self.basis = _Basis(256)

    def target(self, kind, alpha, beta, order=1):
        if kind != "UB":
            raise ValueError("fuzzy_ub only has the kind 'UB'")
        return tg.UB_row(beta)

    def peak_qubit_cap(self, spec):
        return self.n_data + 32

    def task_text(self, spec) -> str:
        return (f"Implement $U_B(\\beta)=\\exp(+2i\\beta\\,\\square)$ of the fuzzy-gauge-theory plaquette (arXiv:2308.05253; "
                f"METHODS-fuzzy F5) exactly (up to one global phase) on the 8 row qubits, i.e. a $256\\times256$ unitary on all {len(self.basis.labels)} "
                f"computational codes (all are physical), at $\\beta={spec.beta:g}$ and, with the same gate skeleton, at the alternate "
                f"pairs. Every ancilla must return to $|0\\rangle$.")

    def describe(self) -> str:
        return (
            "FUZZY unit `fuzzy_ub` (fuzzy gauge theory, arXiv:2308.05253, METHODS-fuzzy F1-F5): the row block of the plaquette "
            "operator of the 4-link plaquette. Data register `d` = 8 row qubits; frame qubit 2l = q2 and 2l+1 = q1 of link l "
            "(l = 0,1,2,3 = b, r, t, l), registers `row_b=[1,0]`, `row_r=[3,2]`, `row_t=[5,4]`, `row_l=[7,6]` "
            "(most significant first). Row index of a code is sum_l (2 q1^l + q2^l) 4^l. The target is the exact 256 x 256 unitary "
            "exp(+2 i beta square) with `spec.beta` = beta (`spec.alpha` is unused). Only the row qubits carry data: the column "
            "qubits (q3, q4) are not touched by the plaquette. The known structure: parity frame (3 CNOTs q1^b -> q1^{r,t,l}); the "
            "operator splits into 8 parity sectors, each Clifford-conjugate to a rotation R_x(-4 beta sigma) with singular values "
            "{16, 0^12}, {4, 0^15} or {1^16}; the baseline spends ~1700 CX on one 3-controlled AND and Clifford frames per sector. "
            "Ancillas: up to 32 clean ancillas, `Builder.alloc/free`.\n"
            + _PROPOSER_NOTE.format(enc="fuzzy_ub", kind="UB"))


class FuzzyLinkTask(FuzzyBlockEncoding):
    name = "fuzzy_link"

    def __init__(self):
        super().__init__(4, data_qubits=[0, 1, 2, 3])
        self.registers = {"d": [0, 1, 2, 3]}
        self.basis = _Basis(16)

    def target(self, kind, alpha, beta, order=1):
        if kind != "UE":
            raise ValueError("fuzzy_link only has the kind 'UE'")
        return tg.UEK_link(alpha, beta)             # spec.beta plays kappa2

    def peak_qubit_cap(self, spec):
        return self.n_data                           # no ancilla: the composed step keeps link-local kinetic layers

    def task_text(self, spec) -> str:
        return (f"Implement the one-link kinetic block $U_{{EK}}(\\alpha,\\kappa_2)=\\exp[-i(\\tfrac\\alpha2\\mathcal K_1+\\kappa_2\\mathcal K_2)]$ "
                f"of the fuzzy gauge theory (arXiv:2308.05253; METHODS-fuzzy F2, F9) exactly (up to one global phase) as a $16\\times16$ "
                f"unitary on the 4 link qubits, at $(\\alpha,\\kappa_2)=({spec.alpha:g},{spec.beta:g})$ and, with the same gate skeleton, at the "
                f"alternate pairs. **`spec.beta` is $\\kappa_2$** (the Trotter step uses $\\kappa_2=r\\alpha/2$; the three angle pairs are "
                f"three independent $(\\alpha,\\kappa_2)$ points). No ancilla: do not call `alloc` (more than 4 qubits is rejected).")

    def describe(self) -> str:
        return (
            "FUZZY unit `fuzzy_link` (fuzzy gauge theory, arXiv:2308.05253, METHODS-fuzzy F1-F2, F9): one link. Data register `d` = "
            "frame qubits (0,1,2,3) = (q4, q3, q2, q1) of the link. Target exp(-i(alpha/2 K1 + kappa2 K2)) with `spec.alpha` = alpha and "
            "**`spec.beta` = kappa2** (the Trotter step applies it to 12 links with kappa2 = r alpha/2). K1 = 3/2 - 1/4 (X2X4 - Y2Y4 + Z2Z4)"
            "(1 + Z1Z3), K2 = -X1X3 + Y1X2Y3X4 - Y1Y2Y3Y4 + Y1Z2Y3Z4 (qubit k = q_k), [K1, K2] = 0. In the Clifford frame cx(q1,q3) cx(q2,q4) "
            "h(q1) h(q2) both are diagonal sums of Z-strings (10 strings in total; see F9), so the block is one frame plus a phase "
            "polynomial; the baseline uses two CNOT ladders (36 CX). No ancilla.\n"
            + _PROPOSER_NOTE.format(enc="fuzzy_link", kind="UE"))
