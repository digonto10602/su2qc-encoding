"""Gate-set-restricted circuit Builder (prompts/002 §2.10). Stubs (step 0.1)."""
from __future__ import annotations

from su2plaq._stub import todo

BASIS = {"x", "z", "h", "s", "sdg", "t", "tdg", "rz", "p", "cx", "cz"}
MACROS = {"ccx", "rccx", "ccz", "swap", "ch", "crz", "crx", "cp"}
# (CX, T_fixed, N_rot) after level-0 lowering (measured, METHODS §7)
MACRO_COST = {"ccx": (6, 7, 0), "rccx": (3, 4, 0), "ccz": (6, 7, 0), "swap": (3, 0, 0), "ch": (1, 2, 0),
              "crz": (2, 0, 2), "crx": (2, 0, 2), "cp": (2, 0, 3), "cz": (1, 0, 0)}


class BuilderError(Exception):
    pass


class Builder:
    peak_qubits: int
    discoveries: list[str]

    def __init__(self, spec=None, n_qubits: int | None = None):
        todo("Builder")

    def reg(self, name) -> list[int]:
        todo("Builder.reg")

    def alloc(self, n: int = 1, name=None) -> list[int]:
        todo("Builder.alloc")

    def free(self, qubits):
        todo("Builder.free")

    def x(self, q):
        todo("Builder.x")

    def z(self, q):
        todo("Builder.z")

    def h(self, q):
        todo("Builder.h")

    def s(self, q):
        todo("Builder.s")

    def sdg(self, q):
        todo("Builder.sdg")

    def t(self, q):
        todo("Builder.t")

    def tdg(self, q):
        todo("Builder.tdg")

    def rz(self, theta, q):
        todo("Builder.rz")

    def p(self, lam, q):
        todo("Builder.p")

    def cx(self, c, t):
        todo("Builder.cx")

    def cz(self, a, b):
        todo("Builder.cz")

    def ccx(self, a, b, t):
        todo("Builder.ccx")

    def rccx(self, a, b, t):
        todo("Builder.rccx")

    def ccz(self, a, b, t):
        todo("Builder.ccz")

    def ch(self, c, t):
        todo("Builder.ch")

    def swap(self, a, b):
        todo("Builder.swap")

    def crz(self, theta, c, t):
        todo("Builder.crz")

    def crx(self, theta, c, t):
        todo("Builder.crx")

    def cp(self, theta, c, t):
        todo("Builder.cp")

    def mcx(self, controls: list[int], target: int):
        todo("Builder.mcx")

    def append_qiskit(self, qc, qubit_map: list[int]):
        todo("Builder.append_qiskit")

    def discover(self, line: str):
        todo("Builder.discover")

    def circuit(self):
        todo("Builder.circuit")
