"""16-qubit spin-network encoding (prompts/100 §1.1-1.4, §2; docs/METHODS-spinnet.md §1-§3).

Data register d[0..7]: qubits 0-3 = inner links b, r, t, l (bit 1 <=> j = 1/2); qubits 4-7 = corner qubits c_0..c_3
(bit 1 <=> J_c = 1, meaningful only when all four links at the corner are 1/2).  Outer register o[0..7] = outer links
o_0..o_7 at qubits 8-15.  The 433 physical states are computational-basis codes; the 47 valid data codes are the inner
labels.  Targets are route B (6j) with the real diagonal gauge D of `gauge_align` to route A (audit 001 N5): the decoded
electric vector of physical code k is gauge[k] * (route-A state k), so <phi_k'|H|phi_k> = (H_B)_{k'k} exactly.

Prototype: scratch/planner/proto_m3_spinnet.py (planner), measured in reports/research/100-*.
"""
from __future__ import annotations

import functools
from typing import TYPE_CHECKING

import numpy as np

from su2plaq.encodings.base import EncodedBasis, Encoding, Layout
from su2plaq.exact.compare import gauge_align
from su2plaq.exact.operators import h_magnetic_phys
from su2plaq.exact.physical import physical_basis
from su2plaq.exact.spinnet import K_inner, h_electric_6j, h_magnetic_phys_6j, inner_labels, labels as route_b_labels
from su2plaq.su2.algebra import LinkSpace

if TYPE_CHECKING:
    from qiskit import QuantumCircuit

FUSE: dict[tuple[float, float], frozenset[float]] = {
    (0.0, 0.0): frozenset({0.0}),
    (0.0, 0.5): frozenset({0.5}),
    (0.5, 0.0): frozenset({0.5}),
    (0.5, 0.5): frozenset({0.0, 1.0}),
}
# (inner a, inner b, outer c, outer d) link indices at corners c0..c3 (= Diagram.corners ends order)
CORNER_LINKS = ((0, 3, 4, 5), (0, 1, 6, 7), (1, 2, 8, 9), (2, 3, 10, 11))
# inner links (b r t l = 0 1 2 3) meeting at corners c0..c3
CORNER_INNER = tuple(c[:2] for c in CORNER_LINKS)

N_DATA, N_OUTER = 8, 8
PAULO_ALPHA_P = 0.1                      # plaquette angle of refs/paulo/spin_network_plaquette3.gates.txt (beta = alpha_P / 2)
GAUGE_TOL = 1e-10
_LINK_NAMES = ("b", "r", "t", "l")
_FLIP = 0b1111


# ------------------------------------------------------------------------------------------------------ codec
def code_of_label(label) -> int:
    """16-bit code of a route-B label ((j_0..j_11), (J_0..J_3)): bits 0-3 inner links, 4-7 corners, 8-15 outer links."""
    j, J = label
    if len(j) != 12 or len(J) != 4:
        raise ValueError("label must be ((j_0..j_11), (J_0..J_3))")
    code = 0
    for l in range(4):
        code |= int(j[l] == 0.5) << l
    for c in range(4):
        code |= int(J[c] == 1.0) << (4 + c)
    for k in range(8):
        code |= int(j[4 + k] == 0.5) << (8 + k)
    return code


@functools.lru_cache(maxsize=1)
def _label_tables():
    labs = route_b_labels(jmax=0.5)
    codes = [code_of_label(lab) for lab in labs]
    if len(set(codes)) != len(codes):
        raise AssertionError("label -> code map is not injective")
    return labs, codes, {c: k for k, c in enumerate(codes)}


def label_of_code(code: int):
    """Inverse of `code_of_label` on the 433 physical codes; None for every other 16-bit pattern."""
    labs, _codes, index = _label_tables()
    k = index.get(int(code))
    return None if k is None else labs[k]


def align_inner_block(M: np.ndarray, V: np.ndarray):
    """Compare a circuit's 47x47 inner block M with the target V up to a global phase and a real diagonal gauge.

    phase = arg tr(V^dag M) is removed first, then gauge_align(M / phase, V).  Returns (D over the 47 inner codes,
    residual max|M/phase - D V D^dag|, phase); (None, modulus mismatch, phase) if |M| != |V|."""
    M = np.asarray(M)
    V = np.asarray(V)
    ov = np.trace(V.conj().T @ M)
    phase = complex(ov / abs(ov)) if abs(ov) > 1e-300 else 1.0 + 0j
    D, res = gauge_align(M / phase, V)
    return D, float(res), phase


# ------------------------------------------------------------------------------------------------------ encoding
class SpinNet(Encoding):
    name = "spinnet"
    n_data = N_DATA
    n_outer = N_OUTER
    is_basis_encoding = True

    def __init__(self):
        self.basis = physical_basis(convention="cg")
        labs, codes, index = _label_tables()
        if self.basis.labels != labs:
            raise AssertionError("route-A basis labels differ from route-B labels")
        diagram = self.basis.diagram
        if tuple(tuple(i for i, _ in c.ends) for c in diagram.corners) != CORNER_LINKS:
            raise AssertionError("CORNER_LINKS does not match Diagram.corners")
        self.labels = labs
        self.registers = {"d": list(range(8)), "o": list(range(8, 16)), "links": [0, 1, 2, 3], "corners": [4, 5, 6, 7]}
        for l, nm in enumerate(_LINK_NAMES):
            self.registers[f"link_{nm}"] = [l]
        for c in range(4):
            self.registers[f"corner_{c}"] = [4 + c]
        for k in range(8):
            self.registers[f"outer_{k}"] = [8 + k]
        self._codes = np.array(codes, dtype=np.int64)
        self._index = index
        # inner labels (route-B order) <-> sorted inner codes
        il = inner_labels(0.5)
        il_code = np.array([code_of_label((j + (0.0,) * 8, J)) & 0xFF for j, J in il], dtype=np.int64)
        if len(set(il_code.tolist())) != 47:
            raise AssertionError("inner labels do not map to 47 distinct data codes")
        self._inner = np.sort(il_code)
        perm = np.array([int(np.flatnonzero(il_code == c)[0]) for c in self._inner], dtype=np.int64)
        self.K = K_inner(0.5)                                  # inner_labels order
        self.K_codes = self.K[np.ix_(perm, perm)]              # inner_codes order
        self._inner_pos = {int(c): i for i, c in enumerate(self._inner)}
        self._valid_data = np.zeros(256, dtype=bool)
        self._valid_data[self._inner] = True
        self._pos_of_k = np.array([self._inner_pos[int(c) & 0xFF] for c in self._codes], dtype=np.int64)
        # operators and gauge
        self._HB = h_magnetic_phys_6j(labs)
        self._HE_inner = np.diag(h_electric_6j(labs)).copy()
        self._HE_all = np.diag(h_electric_6j(labs, inner_only=False)).copy()
        HA, _ = h_magnetic_phys(self.basis)
        D, res = gauge_align(HA, self._HB)
        if D is None or res > GAUGE_TOL:
            raise RuntimeError(f"route A / route B gauge alignment failed (residual {res})")
        gauge = np.sign(D.real)
        if np.abs(D - gauge).max() > GAUGE_TOL:
            raise RuntimeError("gauge from gauge_align is not real +-1")
        self.gauge = gauge.astype(np.float64)
        self.gauge_residual = float(res)
        self._eig_B = None
        self._eig_K = None
        self._ls = LinkSpace(0.5)
        self._dec_cache: dict[int, tuple[np.ndarray, np.ndarray]] = {}

    # ---- codec
    def inner_codes(self) -> np.ndarray:
        return self._inner.copy()

    def physical_vectors(self) -> EncodedBasis:
        return EncodedBasis([np.array([c], dtype=np.int64) for c in self._codes],
                            [np.array([1.0 + 0j]) for _ in self._codes], self.n_data, self.n_outer)

    def decode(self, code: int) -> int | None:
        """Label index k (0..432) of a physical code, None otherwise."""
        return self._index.get(int(code))

    def _fallback(self, code: int) -> tuple[np.ndarray, np.ndarray]:
        """Product state of an inadmissible code (METHODS-spinnet §3): every spin-1/2 end at corner c is an eigenstate of
        its Gauss generator G^z with eigenvalue +1/2 (corner bit 0) or -1/2 (corner bit 1); far ends of outer links at
        m = +1/2 (CG first m).  In the cg convention L^z = -m_L on an 'out' end and R^z = +m_R on an 'in' end, so the
        eigenvalue g is realised by m_L = -g ('out') and m_R = +g ('in'); all ends of a corner then have the same G^z sign,
        |G^z_c| = k/2 >= 1/2 (a naive 'm = g on every end' would let an out and an in end cancel and break orthogonality
        to the corner singlet)."""
        j = [(code >> l) & 1 for l in range(4)] + [(code >> (8 + k)) & 1 for k in range(8)]
        bit = [(code >> (4 + c)) & 1 for c in range(4)]
        key = 0
        for i in range(12):
            if not j[i]:
                continue                       # j = 0 link: key digit 0 (state (0, 0, 0))
            mL = mR = 0.5
            for c, corner in enumerate(self.basis.diagram.corners):
                for li, role in corner.ends:
                    if li == i:
                        g = -0.5 if bit[c] else 0.5          # G^z eigenvalue of this end
                        if role == "out":
                            mL = -g
                        else:
                            mR = g
            key += self._ls.index[(0.5, mL, mR)] * 5 ** i
        return np.array([key], dtype=np.int64), np.array([1.0 + 0j])

    def _decoded(self, code: int) -> tuple[np.ndarray, np.ndarray]:
        hit = self._dec_cache.get(code)
        if hit is None:
            if code < 0 or code >> 16 or not self._valid_data[code & 0xFF]:
                raise ValueError(f"code {code:#x} is not a valid spin-network code (data part outside the 47 inner codes)")
            k = self._index.get(code)
            if k is None:
                hit = self._fallback(code)
            else:
                hit = (self.basis.keys[k], self.basis.amps[k] * self.gauge[k])
            self._dec_cache[code] = hit
        return hit

    def decode_state(self, codes, amps) -> tuple[np.ndarray, np.ndarray]:
        """sum_k a_k phi_k as coalesced COO over electric keys (cg): physical code -> gauge[k] x route-A state; code with
        a valid inner data part but inadmissible label -> product-state fallback (METHODS-spinnet §3, an isometry on the
        whole code space); ValueError if the data part is not one of the 47 inner codes."""
        codes = np.asarray(codes, dtype=np.int64)
        amps = np.asarray(amps)
        if len(codes) == 0:
            return np.zeros(0, dtype=np.int64), np.zeros(0, dtype=np.complex128)
        ks, vs = [], []
        for code, a in zip(codes.tolist(), amps):
            k, v = self._decoded(code)
            ks.append(k)
            vs.append(v * a)
        keys = np.concatenate(ks)
        vals = np.concatenate(vs).astype(np.complex128)
        uk, inv = np.unique(keys, return_inverse=True)
        out = np.bincount(inv, weights=vals.real, minlength=len(uk)) + 1j * np.bincount(inv, weights=vals.imag, minlength=len(uk))
        return uk.astype(np.int64), out

    # ---- targets (route B)
    def h_magnetic(self) -> np.ndarray:
        return self._HB.copy()

    def h_electric(self, include_outer: bool = False) -> np.ndarray:
        return (self._HE_all if include_outer else self._HE_inner).copy()

    def _eigB(self):
        if self._eig_B is None:
            self._eig_B = np.linalg.eigh(self._HB)
        return self._eig_B

    def _eigK(self):
        if self._eig_K is None:
            self._eig_K = np.linalg.eigh(self.K_codes)
        return self._eig_K

    @staticmethod
    def _expm_herm(eig, t: float) -> np.ndarray:
        w, v = eig
        return (v * np.exp(-1j * t * w)) @ v.conj().T

    def target(self, kind: str, alpha, beta, order: int = 1, include_outer_electric: bool = False) -> np.ndarray:
        """433x433 route-B target: 'UE' = diag exp(-i alpha H_E), 'UB' = exp(-i beta H_B^B), 'step' = U_B U_E (order 1) or
        U_E(alpha/2) U_B U_E(alpha/2) (order 2).  include_outer_electric adds the 8 outer j(j+1) to H_E."""
        HE = self._HE_all if include_outer_electric else self._HE_inner

        def UE(a):
            return np.diag(np.exp(-1j * a * HE))

        if kind == "UE":
            return UE(alpha)
        UB = self._expm_herm(self._eigB(), beta) if kind in ("UB", "step") else None
        if kind == "UB":
            return UB
        if kind != "step":
            raise ValueError(f"unknown target kind {kind!r}")
        if order == 1:
            return UB @ UE(alpha)
        if order == 2:
            return UE(alpha / 2) @ UB @ UE(alpha / 2)
        raise ValueError(f"unknown Trotter order {order!r}")

    def inner_target(self, kind: str, alpha, beta, order: int = 1) -> np.ndarray:
        """47x47 target on the inner codes (sorted): exp(-i beta K), diag exp(-i alpha sum_inner j(j+1)), or the step."""
        hE = 0.75 * np.array([bin(int(c) & 0xF).count("1") for c in self._inner])   # sum_inner j(j+1) on each code

        def UE(a):
            return np.diag(np.exp(-1j * a * hE))

        if kind == "UE":
            return UE(alpha)
        if kind not in ("UB", "step"):
            raise ValueError(f"unknown target kind {kind!r}")
        UB = self._expm_herm(self._eigK(), beta)
        if kind == "UB":
            return UB
        if order == 1:
            return UB @ UE(alpha)
        if order == 2:
            return UE(alpha / 2) @ UB @ UE(alpha / 2)
        raise ValueError(f"unknown Trotter order {order!r}")

    def regauge(self, V: np.ndarray, D_inner: np.ndarray) -> np.ndarray:
        """D V D^dag with D over the 47 inner codes extended to the 433 states by the data part of each state's code."""
        D = np.asarray(D_inner)[self._pos_of_k]
        return D[:, None] * np.asarray(V) * np.conj(D)[None, :]

    # ---- layout / description / imports
    def layout_of(self, qc: "QuantumCircuit") -> Layout:
        """data = qubits of register 'd' (else the first 8), outer = qubits of register 'o' (empty if absent), ancilla = rest."""
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
        """Markdown description: registers, codec table, the 47 inner codes, the 433 states, corner rule, gauge statement."""
        codes = self._inner.tolist()
        bright = [c for c in codes if c >> 4 == 0]
        rows = "\n".join(
            f"| `{c:08b}` | {c & 15:04b} | {c >> 4:04b} | {'bright' if c >> 4 == 0 else 'dark'} |" for c in codes)
        outs = ", ".join(f"o{k} = qubit {8 + k}" for k in range(8))
        return (
            f"### Encoding `{self.name}` ({self.n_data} data + {self.n_outer} outer qubits, basis encoding)\n\n"
            "**Data register `d[0..7]`.** Qubits 0-3 = inner links b, r, t, l (bit 1 <=> j = 1/2, bit 0 <=> j = 0); qubits "
            "4-7 = corner qubits c_0..c_3 (bit 1 <=> J_c = 1, bit 0 <=> J_c in {0, 1/2}).  Code of a label = "
            "sum_l [j_l = 1/2] 2^l + sum_c [J_c = 1] 2^(4+c) + sum_k [j_(o_k) = 1/2] 2^(8+k).\n\n"
            f"**Outer controls `o[0..7]`.** Outer link o_k (METHODS section 1 order) at qubit 8 + k: {outs}.  A circuit may "
            "read them (controls), never write them.\n\n"
            "**Corner rule.** A corner qubit is meaningful only when all four links at the corner are 1/2: J_c = 1 needs "
            "T(1/2, 1/2) = {0, 1} on both the inner and the outer side.  Every corner therefore has a corner bit 1 only "
            "with its four links 1/2, the label -> code map is injective, and the admissible J's of a corner never contain "
            "both 0 and 1/2.\n\n"
            f"**Physical states.** {len(self._codes)} gauge-invariant states, each a distinct computational-basis code "
            f"(unit vectors).  The valid data codes are the {len(codes)} inner labels ({len(bright)} bright: no corner bit; "
            f"{len(codes) - len(bright)} dark); the bright codes are paired by the four-link flip (code ^ 0b1111).  Other "
            "data patterns are don't-care; valid-data codes whose outer pattern does not fuse (11 599) are decoded to an "
            "orthogonal product state with Gauss residual >= 1/2 so the Gauss check sees any leak.\n\n"
            "**Gauge.** The target is route B (6j); route A differs by the real diagonal gauge D = +-1 of `gauge_align` "
            f"({int(np.sum(self.gauge < 0))} minus signs, residual {self.gauge_residual:.1e}); the decoded vector of "
            "code k is D_k times the route-A state, so decoded outputs are compared with the route-B target directly.  "
            "The sign of beta is a basis-sign convention at j_max = 1/2.\n\n"
            "| data code (bits 7..0) | links (b r t l = bits 3..0) | corners (bits 7..4) | class |\n|---|---|---|---|\n" + rows + "\n")

    def import_map(self, source: str) -> dict | str:
        """Mapping of an external circuit onto this encoding's frame (data 0..7, outer 8..15, ancillas from 16)."""
        if source == "paulo15":
            qubit_map = {**{q: q for q in range(4)}, **{12 + c: 4 + c for c in range(4)}, **{16 + a: 16 + a for a in range(7)}}
            qubit_map_open = {**{q: q for q in range(4)}, **{12 + c: 4 + c for c in range(4)}, **{16 + a: 8 + a for a in range(7)}}

            def angles(alpha, beta):          # fixed: the file is exp(+i alpha_P Re Tr U_P) at alpha_P = 0.1
                return {"kind": "UB", "beta": PAULO_ALPHA_P / 2, "alpha_P": PAULO_ALPHA_P}
            return {"qubit_map": qubit_map, "qubit_map_open": qubit_map_open, "angles": angles, "fixed_angle": True,
                    "n_source_qubits": 15, "kind": "UB", "gauge": "one -1 per bright pair (align_inner_block)",
                    "note": "refs/paulo/spin_network_plaquette3.gates.txt: file q0-3 links, q12-15 corners, q16-22 ancillas "
                            "(q4-11 untouched); qubit_map is for the frame with the outer register, qubit_map_open without it; "
                            "equals exp(-i beta K) up to a real diagonal gauge, beta = alpha_P / 2"}
        if source == "spinnet_v2":
            skeletons = ["pairs9", "flags4", "flags5", "flags6"]
            qubit_map = {**{q: q for q in range(8)}, **{8 + a: 16 + a for a in range(3)}}
            qubit_map_open = {q: q for q in range(11)}

            def angles(alpha, beta):
                return {"kind": "UB", "beta": beta}
            return {"qubit_map": qubit_map, "qubit_map_open": qubit_map_open, "angles": angles, "fixed_angle": False,
                    "n_source_qubits": 11, "kind": "UB", "skeletons": skeletons,
                    "note": "su2qc-trotter spinnet_v2 skeletons (3 ancillas); angles re-solved from K, skeleton independent of beta"}
        if source in ("paulo34", "lean22", "lean22_v2"):
            return (f"{source} is a 12-qubit electric-basis circuit (3 qubits per inner link): it does not act on the "
                    "spin-network codes (16-qubit encoding)")
        raise ValueError(f"unknown import source {source!r}; known: ['paulo15', 'spinnet_v2', 'paulo34', 'lean22', 'lean22_v2']")
