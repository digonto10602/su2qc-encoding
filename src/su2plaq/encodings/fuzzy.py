"""Fuzzy-sphere encoding: 4 qubits per link, 12 links, 48 qubits (plan 300 §2, docs/METHODS-fuzzy.md F1).

A link carries a 4x4 matrix Psi; its 16 matrix units |row, col> are the 16 computational states of four qubits (no
don't-cares).  Index 8 q1 + 4 q2 + 2 q3 + q4 with row = 2 q1 + q2, col = 2 q3 + q4; link l = 0..11 (order b, r, t, l,
o_0..o_7) sits at qubits 4l..4l+3 with q1 -> 4l+3, q2 -> 4l+2, q3 -> 4l+1, q4 -> 4l (little-endian).
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from su2plaq.encodings.base import EncodedBasis, Layout

if TYPE_CHECKING:
    from qiskit import QuantumCircuit

_LINK_NAMES = ("b", "r", "t", "l")
_SEED = 20261104


class FuzzyEncoding:
    name = "fuzzy"
    n_data = 16
    n_outer = 32
    is_basis_encoding = True
    basis = None

    def __init__(self):
        self.registers = {"d": list(range(16)), "o": list(range(16, 48))}
        for l, nm in enumerate(_LINK_NAMES):
            self.registers[f"link_{nm}"] = [4 * l, 4 * l + 1, 4 * l + 2, 4 * l + 3]
            self.registers[f"row_{nm}"] = [4 * l + 3, 4 * l + 2]   # (q1, q2)
            self.registers[f"col_{nm}"] = [4 * l + 1, 4 * l]       # (q3, q4)
        for k in range(8):
            self.registers[f"outer_{k}"] = [16 + 4 * k + i for i in range(4)]
        self._cache: dict[tuple[int, int], EncodedBasis] = {}

    # ------------------------------------------------------------------ codec
    def inner_codes(self) -> np.ndarray:
        """All 2^16 codes are valid inner link configurations."""
        return np.arange(1 << 16, dtype=np.int64)

    def decode(self, code: int) -> int | None:
        """Identity on 16-bit codes (the code is the basis-state index of the four matrix units); None if out of range."""
        code = int(code)
        return code if 0 <= code < (1 << 16) else None

    def physical_vectors(self, n_sample: int = 64, seed: int = _SEED) -> EncodedBasis:
        """A seeded SAMPLE of Gauss-law states as 48-bit COO vectors (data = low 16 bits, outer = high 32).  The full physical
        set (about 10^8 vectors) is never enumerated; verification is block-wise (METHODS-fuzzy F6)."""
        key = (int(n_sample), int(seed))
        if key not in self._cache:
            from su2plaq.fuzzy.gauss import sample_physical_states

            states = sample_physical_states(n_sample, seed)
            self._cache[key] = EncodedBasis([np.asarray(k, dtype=np.int64) for k, _ in states],
                                            [np.asarray(a, dtype=np.complex128) for _, a in states],
                                            self.n_data, self.n_outer)
        return self._cache[key]

    def target(self, kind: str, alpha: float, beta: float, order: int = 1, r: float = 1.0) -> np.ndarray:
        """Exact targets: 'UE' (16x16, exp(-i alpha/2 K1)), 'UK' (16x16, exp(-i kappa2 K2), kappa2 = r alpha/2), 'UEK' (their
        product) and 'UB' (256x256 on the row qubits, exp(+2 i beta square)).  There is no 48-qubit dense 'step' target."""
        from su2plaq.fuzzy import targets as tg

        if kind == "UE":
            return tg.UE_link(alpha)
        if kind == "UK":
            return tg.UK_link(tg.kappa2_of(alpha, r))
        if kind == "UEK":
            return tg.UEK_link(alpha, tg.kappa2_of(alpha, r))
        if kind == "UB":
            return tg.UB_row(beta)
        if kind == "step":
            raise ValueError("no dense 'step' target for the fuzzy encoding (2^48 dimensional); use "
                             "su2plaq.fuzzy.targets.apply_step on sampled states")
        raise ValueError(f"unknown target kind {kind!r}")

    def layout_of(self, qc: "QuantumCircuit") -> Layout:
        """data = qubits of register 'd' (else the first 16), outer = qubits of register 'o' (empty if absent; 32 if present),
        ancilla = every other qubit in index order."""
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
        links = ", ".join(f"`{n}` = qubits ({4 * l}..{4 * l + 3})" for l, n in enumerate(_LINK_NAMES))
        outs = ", ".join(f"o{k}: ({16 + 4 * k}..{19 + 4 * k})" for k in range(8))
        return (
            f"### Encoding `{self.name}` ({self.n_data} data + {self.n_outer} outer = 48 qubits)\n\n"
            "**Link space.** A fuzzy link carries a 4x4 complex matrix Psi; the 16 matrix units |row, col> are the 16 "
            "computational states of four qubits (q_1, q_2, q_3, q_4), index 8 q_1 + 4 q_2 + 2 q_3 + q_4, row = 2 q_1 + q_2, "
            "col = 2 q_3 + q_4. There are no don't-care codes: every 16-bit inner code is valid (65536). q_1 and q_3 are the "
            "block bits (0 = upper block, T_R; 1 = lower block, T_L), q_2 and q_4 the spin bits. Left multiplication "
            "Psi -> M Psi is M (x) 1 on (q_1, q_2); right multiplication Psi -> Psi M is 1 (x) M^T on (q_3, q_4). "
            "The flavour F: Psi -> Psi Gamma_5 is Z on q_3.\n\n"
            f"**Data register `d[0..15]`.** Inner link l in (b, r, t, l) occupies qubits (4l, 4l+1, 4l+2, 4l+3) = "
            f"(q_4, q_3, q_2, q_1) ({links}). Row qubits of link l: (4l+3, 4l+2); the plaquette operator acts on the row "
            "qubits only.\n\n"
            f"**Outer register `o[0..31]`.** Outer link k = 0..7 occupies qubits 16+4k..19+4k in the same layout ({outs}). The "
            "kinetic blocks act on the outer links too; the plaquette reads none of them.\n\n"
            "**Physical states.** The kernel of the four corner Gauss generators G^A_c (T_L on outgoing, T_R on incoming links), "
            "far ends of the outer links free; about 10^8 states (6.77e9 with far-end weights), never enumerated: "
            "`physical_vectors` returns a seeded sample. Ancillas must return to |0>.\n")

    def import_map(self, source: str) -> dict | str:
        """No circuit for another encoding applies to the fuzzy qubit map; returns the reason (str) for the known sources."""
        known = ("paulo34", "lean22", "lean22_v2", "spinnet15")
        if source not in known:
            raise ValueError(f"unknown import source {source!r}; known: {list(known)}")
        return (f"{source} is a circuit for another encoding (SU(2) electric/spin-network codes of 12 or 15 qubits); it does not "
                "apply to the fuzzy link space (4 qubits per link, 48 qubits): no import map")
