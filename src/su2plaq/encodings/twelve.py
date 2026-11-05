"""12-qubit encoding (Paulo Eq. 31 inner codes + 2-qubit outer code; prompts/002 §2.5, docs/METHODS.md §3.2).

Built in step 0.8: codec, `inner_codes`, `decode`, `decode_state`, `physical_vectors`, `layout_of`, `target`.
`describe` and `import_map` are M1 step 1.1.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from su2plaq._stub import todo
from su2plaq.encodings.base import ALT_ANGLES, NOMINAL_ANGLES, EncodedBasis, Encoding, Layout  # noqa: F401
from su2plaq.exact.physical import physical_basis, to_convention
from su2plaq.su2.algebra import PAULO_ORDER, paulo_adapter

if TYPE_CHECKING:
    from qiskit import QuantumCircuit

_LINK_NAMES = ("b", "r", "t", "l")


class TwelveQubit(Encoding):
    name = "twelve"
    n_data = 12
    n_outer = 16
    is_basis_encoding = False
    # bits (q_j q_m q_m') with q_m' = bit 0, q_m = bit 1, q_j = bit 2 at qubits (3l, 3l+1, 3l+2); Paulo basis
    LINK_CODE = {"0": 0b000, "++": 0b111, "+-": 0b110, "-+": 0b101, "--": 0b100}
    # Outer link k (0..7) at qubits (12+2k, 12+2k+1) = (q_m_near, q_j) in Paulo's labels (m, m'):
    # j = 0 -> 00; j = 1/2 -> q_j = 1 and q_m = 1 for near label '+', 0 for '-'.  The near label is the first
    # character for near_end 'L' (link starts at its corner) and the second for 'R'; the far label is always '-'
    # (CG far end fixed to +1/2 and Paulo m = -m_CG).

    def __init__(self):
        self.basis = physical_basis(convention="cg")
        self.registers = {"d": list(range(12)), "o": list(range(12, 28))}
        for l, nm in enumerate(_LINK_NAMES):
            self.registers[f"link_{nm}"] = [3 * l, 3 * l + 1, 3 * l + 2]
        for k in range(8):
            self.registers[f"outer_{k}"] = [12 + 2 * k, 13 + 2 * k]
        links = self.basis.diagram.links
        self._near = [links[4 + k].near_end for k in range(8)]
        # tables (paulo index p <-> 3-bit link code / 2-bit outer code)
        self._code3 = np.array([self.LINK_CODE[nm] for nm in PAULO_ORDER], dtype=np.int64)
        self._p_of_code3 = np.full(8, -1, dtype=np.int64)
        self._p_of_code3[self._code3] = np.arange(5)
        self._b_of_p = np.full((8, 5), -1, dtype=np.int64)  # outer link k, paulo index -> 2-bit code (-1: far end not fixed)
        self._p_of_b = np.full((8, 4), -1, dtype=np.int64)
        for k in range(8):
            for p, nm in enumerate(PAULO_ORDER):
                if p == 0:
                    b = 0
                else:
                    near, far = (nm[0], nm[1]) if self._near[k] == "L" else (nm[1], nm[0])
                    if far != "-":
                        continue
                    b = 2 + (1 if near == "+" else 0)
                self._b_of_p[k, p] = b
                self._p_of_b[k, b] = p
        V = paulo_adapter()
        self._cg_of_p = np.array([int(np.nonzero(V[p])[0][0]) for p in range(5)], dtype=np.int64)
        self._sign_of_p = np.array([V[p, self._cg_of_p[p]] for p in range(5)])
        self._inner_codes = None

    # ------------------------------------------------------------------ codec
    def inner_codes(self) -> np.ndarray:
        if self._inner_codes is None:
            idx = np.arange(625)
            codes = np.zeros(625, dtype=np.int64)
            for l in range(4):
                codes |= self._code3[(idx // 5 ** l) % 5] << (3 * l)
            self._inner_codes = np.sort(codes)
        return self._inner_codes.copy()

    def _paulo_indices(self, codes: np.ndarray) -> np.ndarray:
        """(len(codes), 12) paulo local indices; -1 where invalid."""
        codes = np.asarray(codes, dtype=np.int64)
        out = np.empty((len(codes), 12), dtype=np.int64)
        for l in range(4):
            out[:, l] = self._p_of_code3[(codes >> (3 * l)) & 7]
        for k in range(8):
            out[:, 4 + k] = self._p_of_b[k][(codes >> (12 + 2 * k)) & 3]
        if np.any(codes >> 28):
            out[(codes >> 28) != 0, :] = -1
        return out

    def decode_state(self, codes: np.ndarray, amps: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """(data|outer) integers and amplitudes in Paulo's convention -> (electric keys, amplitudes) in
        self.basis.convention ('cg'); amplitudes carry the V_P signs. Raises ValueError on an invalid code."""
        pi = self._paulo_indices(codes)
        if np.any(pi < 0):
            raise ValueError("invalid code in decode_state")
        keys = np.zeros(len(pi), dtype=np.int64)
        sign = np.ones(len(pi))
        for i in range(12):
            keys += self._cg_of_p[pi[:, i]] * 5 ** i
            sign *= self._sign_of_p[pi[:, i]]
        return keys, np.asarray(amps) * sign

    def decode(self, code: int) -> int | None:
        pi = self._paulo_indices(np.array([code], dtype=np.int64))[0]
        if np.any(pi < 0):
            return None
        return int(sum(int(self._cg_of_p[pi[i]]) * 5 ** i for i in range(12)))

    def physical_vectors(self) -> EncodedBasis:
        bp = to_convention(self.basis, "paulo")
        codes_l, amps_l = [], []
        for keys, amps in zip(bp.keys, bp.amps):
            code = np.zeros(len(keys), dtype=np.int64)
            for l in range(4):
                code |= self._code3[(keys // 5 ** l) % 5] << (3 * l)
            for k in range(8):
                p = (keys // 5 ** (4 + k)) % 5
                b = self._b_of_p[k][p]
                if np.any(b < 0):
                    raise ValueError("outer far end is not '-' in Paulo labels")
                code |= b << (12 + 2 * k)
            codes_l.append(code)
            amps_l.append(np.asarray(amps, dtype=np.complex128))
        return EncodedBasis(codes_l, amps_l, self.n_data, self.n_outer)

    def target(self, kind: str, alpha: float, beta: float, order: int = 1) -> np.ndarray:
        from su2plaq.exact.operators import target as _target

        return _target(self.basis, kind, alpha, beta, order)

    def layout_of(self, qc: "QuantumCircuit") -> Layout:
        """data = the qubits of register 'd' in register order (if there is no register 'd': the first n_data qubits);
        outer = the qubits of register 'o' in register order (empty if absent; must have n_outer qubits); ancilla = every
        other qubit in index order.  The evaluator maps qubits through these lists, so any register order is correct."""
        n = qc.num_qubits
        regs = {reg.name: [qc.find_bit(q).index for q in reg] for reg in qc.qregs}
        if "d" in regs:
            data = regs["d"]
            if len(data) != self.n_data:
                raise ValueError(f"register 'd' must have {self.n_data} qubits, has {len(data)}")
        else:
            if n < self.n_data:
                raise ValueError(f"circuit has {n} qubits, fewer than the {self.n_data} data qubits")
            data = list(range(self.n_data))
        outer = regs.get("o", [])
        if outer and len(outer) != self.n_outer:
            raise ValueError(f"register 'o' must have {self.n_outer} qubits, has {len(outer)}")
        if set(data) & set(outer):
            raise ValueError("data and outer registers overlap")
        used = set(data) | set(outer)
        return Layout(data=list(data), outer=list(outer), ancilla=[q for q in range(n) if q not in used])

    def describe(self) -> str:
        todo("TwelveQubit.describe")

    def import_map(self, source: str) -> dict | str:
        todo("TwelveQubit.import_map")
