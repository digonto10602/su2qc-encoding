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
        """Markdown description of registers, codec and controls (used in the task specification)."""
        inv = {v: k for k, v in self.LINK_CODE.items()}
        rows = "\n".join(f"| `{nm}` | {self.LINK_CODE[nm]:03b} | {nm if nm != '0' else '(j=0)'} |"
                         for nm in PAULO_ORDER)
        links = ", ".join(f"`{n}` = qubits ({3 * l}, {3 * l + 1}, {3 * l + 2})" for l, n in enumerate(_LINK_NAMES))
        outs = ", ".join(f"o{k}: ({12 + 2 * k}, {13 + 2 * k}) near end `{self._near[k]}`" for k in range(8))
        n_phys = len(self.basis.labels)
        return (
            f"### Encoding `{self.name}` ({self.n_data} data + {self.n_outer} outer qubits)\n\n"
            f"**Data register `d[0..{self.n_data - 1}]`.** Inner link l in {{b, r, t, l}} occupies qubits (3l, 3l+1, 3l+2) = "
            f"(q_m', q_m, q_j) ({links}). Codes are written as bits q_j q_m q_m' (q_m' is bit 0 of the link code):\n\n"
            "| Paulo state | q_j q_m q_m' | meaning |\n|---|---|---|\n" + rows + "\n\n"
            f"The codes 001, 010, 011 are unused (don't-care). {len(self.inner_codes())} valid inner codes "
            f"(5^4 = {5 ** 4}); the inner register is the Paulo basis |m m'> = s(m)s(m')|1/2,-m,-m'>_CG.\n\n"
            f"**Outer controls `o[0..{self.n_outer - 1}]`.** Outer link k (0..7) occupies qubits (12+2k, 13+2k) = "
            "(q_m, q_j): j = 0 -> 00; j = 1/2 -> q_j = 1 and q_m = 1 for m_near = +, 0 for m_near = - "
            f"(m_near is the first Paulo label for a link that starts at its corner, the second for one that ends there; "
            f"the far-end label is fixed to -). {outs}. The target never changes the outer register; a circuit may read "
            "it (diagonal gates on those qubits only), never write it.\n\n"
            f"**Physical states.** {n_phys} Gauss-law (gauge-invariant) states, superpositions of inner codes entangled "
            "with the outer register; unphysical inputs are don't-care. Ancillas must return to |0> on physical inputs.\n")

    def import_map(self, source: str) -> dict | str:
        """How an external circuit maps onto this encoding's qubits (frame: data 0..11, outer 12..27, ancillas from 28).

        Returns {"qubit_map": source qubit -> our qubit, "angles": callable(alpha, beta) -> dict of the angles the source
        needs, "fixed_angle": bool, plus "n_source_qubits", "kind", "note"}, or a reason string if the source does not
        apply.  Sources: "paulo34" (Paulo's compiled 34-qubit Clifford+T circuit, `refs/paulo/*.qpy`: fixed angle beta = 1,
        kind UB), "lean22" / "lean22_v2" (su2qc-trotter lean 22-qubit and structurally compressed 19-qubit plaquette
        circuits: same data layout, plaquette angle alpha_P = 2 beta in exp(+i alpha_P Re Tr W), electric phase p(-3 alpha/4)
        on each q_j), "spinnet15" (different encoding: reason string).

        TODO(M2, audit 003 N4): su2qc-trotter's step appends the electric phases AFTER the plaquette circuit (U = U_E U_B),
        the opposite of our U_1 = U_B U_E.  Before the lean22 seeds are used as `step` seeds, import only the plaquette part
        (kind "UB") and prepend our build_UE, or record the source order and reverse it; check it against target("UB", beta)."""
        n_anc = {"paulo34": 22, "lean22": 10, "lean22_v2": 7}
        if source == "spinnet15":
            return ("spinnet15 is Paulo's 15-qubit spin-network circuit: it acts on route-B labels (a different encoding), "
                    "not on the 12-qubit electric-basis codes; it is handled by the spin-network encoding (M3)")
        if source not in n_anc:
            raise ValueError(f"unknown import source {source!r}; known: {sorted(n_anc) + ['spinnet15']}")
        n_src = self.n_data + n_anc[source]
        qubit_map = list(range(self.n_data)) + [self.n_data + self.n_outer + i for i in range(n_anc[source])]
        if source == "paulo34":
            def angles(alpha, beta):  # fixed: the compiled circuit is exp(+i*2*Re Tr W), i.e. beta = 1
                return {"kind": "UB", "beta": 1.0, "alpha_P": 2.0}
            return {"qubit_map": qubit_map, "angles": angles, "fixed_angle": True, "n_source_qubits": n_src, "kind": "UB",
                    "note": "34 qubits = 12 data + 22 ancillas (registers p e w g tmp h); Clifford+T, 294 CX, 1162 T"}

        def angles(alpha, beta):
            return {"alpha_P": 2.0 * beta, "electric_p": -0.75 * alpha}
        return {"qubit_map": qubit_map, "angles": angles, "fixed_angle": False, "n_source_qubits": n_src, "kind": "step",
                "note": f"{source}: {n_anc[source]} ancillas; angles solved from the operator, skeleton independent of alpha"}
