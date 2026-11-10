"""24-qubit loop-string-hadron encoding (prompts/400 section 1-2; docs/METHODS-lsh.md L2-L6).

Data register d[0..11] = the four 'in' sites (site c at qubits 3c, 3c+1, 3c+2 = l_pn, l_nv, l_vp); outer register
o[0..11] = the four 'out' sites (site c at 12+3c.. = l_12, l_2v, l_v1).  The 433 physical states are computational-basis
codes (site-valid + Abelian Gauss law); the 47 valid data codes are the inner codes.

Targets are the LSH operator of `su2plaq.lsh.operators` (equal to the 6j route-B operator entry by entry); route A enters
only through `gauge_align` (decode_state), exactly as in the spin-network encoding (docs/METHODS-spinnet.md section 2)."""
from __future__ import annotations

import functools
from typing import TYPE_CHECKING

import numpy as np

from su2plaq.encodings.base import EncodedBasis, Encoding, Layout
from su2plaq.exact.compare import gauge_align
from su2plaq.exact.operators import h_magnetic_phys
from su2plaq.exact.physical import physical_basis
from su2plaq.exact.spinnet import labels as route_b_labels
from su2plaq.lsh import operators as O
from su2plaq.lsh.operators import code_of_label  # noqa: F401  (re-export)
from su2plaq.su2.algebra import LinkSpace

if TYPE_CHECKING:
    from qiskit import QuantumCircuit

N_DATA, N_OUTER = 12, 12
GAUGE_TOL = 1e-10
_DATA_MASK = (1 << N_DATA) - 1


@functools.lru_cache(maxsize=1)
def _code_to_label() -> dict:
    """{24-bit LSH code: route-B label} for the 433 labels of `exact.spinnet.labels(jmax=0.5)` (same order as the
    physical basis).  The map must be injective, otherwise the encoding is broken."""
    labs = route_b_labels(jmax=0.5)
    table = {code_of_label(lab): lab for lab in labs}
    if len(table) != len(labs):
        raise AssertionError("label -> LSH code map is not injective")
    return table


def label_of_code(code: int):
    """Inverse of `code_of_label` on the 433 physical codes; None for every other integer."""
    return _code_to_label().get(int(code))


class LSH(Encoding):
    name = "lsh"
    n_data = N_DATA
    n_outer = N_OUTER
    is_basis_encoding = True

    def __init__(self):
        self.basis = physical_basis(convention="cg")
        labs = self.basis.labels
        if list(labs) != list(route_b_labels(jmax=0.5)):
            raise AssertionError("route-A basis labels differ from the route-B enumeration (exact.spinnet.labels)")
        codes = [code_of_label(lab) for lab in labs]
        if len(set(codes)) != len(codes) or sorted(codes) != O.physical_codes().tolist():
            raise AssertionError("label codes differ from the LSH enumeration (site-valid + Abelian Gauss law)")
        self.labels = labs
        self.registers = {"d": list(range(12)), "o": list(range(12, 24)),
                          "l_pn": [0, 3, 6, 9], "l_nv": [1, 4, 7, 10], "l_vp": [2, 5, 8, 11]}
        for c in range(4):
            self.registers[f"site_in_{c}"] = [3 * c, 3 * c + 1, 3 * c + 2]
            self.registers[f"site_out_{c}"] = [12 + 3 * c, 12 + 3 * c + 1, 12 + 3 * c + 2]
        self._codes = np.array(codes, dtype=np.int64)
        self._index = {c: k for k, c in enumerate(codes)}
        self._inner = O.inner_codes()
        self._valid_data = np.zeros(1 << N_DATA, dtype=bool)
        self._valid_data[self._inner] = True
        self.K_codes = O.K_lsh()
        self._HB = O.h_magnetic_lsh(codes)
        self._HE_inner = O.h_electric_lsh(codes)
        self._HE_all = O.h_electric_lsh(codes, include_outer=True)
        HA, _ = h_magnetic_phys(self.basis)
        D, res = gauge_align(HA, self._HB)
        if D is None or res > GAUGE_TOL:
            raise RuntimeError(f"route A / LSH gauge alignment failed (residual {res})")
        gauge = np.sign(D.real)
        if np.abs(D - gauge).max() > GAUGE_TOL:
            raise RuntimeError("gauge from gauge_align is not real +-1")
        self.gauge = gauge.astype(np.float64)
        self.gauge_residual = float(res)
        self._eig_B = None
        self._eig_K = None
        self._ls = LinkSpace(0.5)
        self._dec_cache: dict = {}

    # ---- codec
    def inner_codes(self) -> np.ndarray:
        return self._inner.copy()

    def physical_vectors(self) -> EncodedBasis:
        return EncodedBasis([np.array([c], dtype=np.int64) for c in self._codes],
                            [np.array([1.0 + 0j]) for _ in self._codes], self.n_data, self.n_outer)

    def decode(self, code: int):
        return self._index.get(int(code))

    def _fallback(self, code: int):
        """Product state of an AGL-violating code (valid data part, site-valid outer part): every spin-1/2 end at corner c
        is a G^z eigenstate; inner ends +1/2 (J_in != 1) or -1/2 (J_in = 1); outer ends -1/2 (J_out != 1) or +1/2
        (J_out = 1).  A corner whose two sites disagree on the virtual flux then has total G^z != 0 (|G^z| >= 1/2), the map
        code -> electric key is injective, and the state is orthogonal to every physical state.  Far ends at m = +1/2.
        cg convention: G^z = -m_L on an 'out' end, +m_R on an 'in' end."""
        fl = [O.site_flux((code >> (3 * k)) & 7) for k in range(8)]
        key = 0
        for i in range(12):
            mL = mR = 0.5
            half = False
            for c, corner in enumerate(self.basis.diagram.corners):
                for li, role in corner.ends:
                    if li != i:
                        continue
                    if i < 4:
                        N = fl[c][0] if i == O.CORNER_PN[c][0] else fl[c][1]
                        g = -0.5 if fl[c][2] == 2 else 0.5
                    else:
                        N = fl[4 + c][0] if i == O.CORNER_OUT[c][0] else fl[4 + c][1]
                        g = 0.5 if fl[4 + c][2] == 2 else -0.5
                    if N:
                        half = True
                        if role == "out":
                            mL = -g
                        else:
                            mR = g
            if half:
                key += self._ls.index[(0.5, mL, mR)] * 5 ** i
        return np.array([key], dtype=np.int64), np.array([1.0 + 0j])

    def _decoded(self, code: int):
        hit = self._dec_cache.get(code)
        if hit is None:
            if code < 0 or code >> 24 or not self._valid_data[code & _DATA_MASK]:
                raise ValueError(f"code {code:#x}: data part is not one of the 47 inner codes")
            if not all(O.site_valid((code >> (12 + 3 * c)) & 7) for c in range(4)):
                raise ValueError(f"code {code:#x}: an 'out' site violates the flux cap")
            k = self._index.get(code)
            hit = self._fallback(code) if k is None else (self.basis.keys[k], self.basis.amps[k] * self.gauge[k])
            self._dec_cache[code] = hit
        return hit

    def decode_state(self, codes, amps):
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

    # ---- targets
    def h_magnetic(self) -> np.ndarray:
        return self._HB.copy()

    def h_electric(self, include_outer: bool = False) -> np.ndarray:
        return (self._HE_all if include_outer else self._HE_inner).copy()

    @staticmethod
    def _expm_herm(eig, t):
        w, v = eig
        return (v * np.exp(-1j * t * w)) @ v.conj().T

    def _compose(self, kind, UE, UB, alpha, order):
        if kind == "UE":
            return UE(alpha)
        if kind not in ("UB", "step"):
            raise ValueError(f"unknown target kind {kind!r}")
        U = UB()
        if kind == "UB":
            return U
        if order == 1:
            return U @ UE(alpha)
        if order == 2:
            return UE(alpha / 2) @ U @ UE(alpha / 2)
        raise ValueError(f"unknown Trotter order {order!r}")

    def target(self, kind, alpha, beta, order: int = 1, include_outer_electric: bool = False) -> np.ndarray:
        HE = self._HE_all if include_outer_electric else self._HE_inner

        def UB():
            if self._eig_B is None:
                self._eig_B = np.linalg.eigh(self._HB)
            return self._expm_herm(self._eig_B, beta)

        return self._compose(kind, lambda a: np.diag(np.exp(-1j * a * HE)), UB, alpha, order)

    def inner_target(self, kind, alpha, beta, order: int = 1) -> np.ndarray:
        hE = O.h_electric_lsh(self._inner)

        def UB():
            if self._eig_K is None:
                self._eig_K = np.linalg.eigh(self.K_codes)
            return self._expm_herm(self._eig_K, beta)

        return self._compose(kind, lambda a: np.diag(np.exp(-1j * a * hE)), UB, alpha, order)

    # ---- layout / description / imports
    def layout_of(self, qc: "QuantumCircuit") -> Layout:
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
        codes = self._inner.tolist()
        bright = [c for c in codes if all(((c >> (3 * s)) & 7) != O.SITE_J1 for s in range(4))]
        rows = "\n".join(f"| `{c:012b}` | " + " ".join(f"{(c >> (3 * s)) & 7:03b}" for s in range(4))
                         + f" | {'bright' if c in bright else 'dark'} |" for c in codes)
        return (
            f"### Encoding `{self.name}` ({self.n_data} data + {self.n_outer} outer qubits, basis encoding)\n\n"
            "Loop-string-hadron (LSH) loop numbers on the point-split plaquette (8 trivalent sites, (inner | outer) pairing). "
            "**Data register `d[0..11]`**: 'in' site of corner c at qubits 3c, 3c+1, 3c+2 = (l_pn, l_nv, l_vp), loop numbers "
            "between the previous inner link p, the next inner link n (loop order b, r, t, l) and the virtual link v. "
            "**Outer controls `o[0..11]`**: 'out' site of corner c at qubits 12+3c.. = (l_12, l_2v, l_v1) for its two outer "
            "links; read-only.  Fluxes: N_p = l_vp + l_pn, N_n = l_pn + l_nv, N_v = l_nv + l_vp; spin = N/2.\n\n"
            "**Validity.** Site codes 000, 001, 010, 100, 110 (bits l_31 l_23 l_12; flux at most 1 on physical links); "
            "Abelian Gauss law: the flux of every inner link and every virtual link read from its two ends agrees.  "
            f"{len(self._codes)} physical states, each one computational-basis code; {len(codes)} valid data codes "
            f"({len(bright)} bright, {len(codes) - len(bright)} dark = a site in 110, i.e. J = 1).  The plaquette moves every "
            "bright site 000 <-> 001 or 010 <-> 100 and never reads the outer register.  Other data patterns are "
            "don't-care; data-valid codes that break the Abelian Gauss law on a virtual link are decoded to an orthogonal "
            "product state with Gauss residual >= 1/2.\n\n"
            "**Gauge.** Target = the LSH operator (equal to the 6j route-B operator entry by entry); route A differs by the "
            f"real diagonal gauge of `gauge_align` ({int(np.sum(self.gauge < 0))} minus signs, residual "
            f"{self.gauge_residual:.1e}).\n\n"
            "| data code (bits 11..0) | sites c0 c1 c2 c3 (each l_vp l_nv l_pn) | class |\n|---|---|---|\n" + rows + "\n")

    def import_map(self, source: str):
        if source == "spinnet":
            return {"wrap": "su2plaq.circuits.lsh:wrap_spinnet", "kind": "UB", "fixed_angle": False,
                    "skeletons": ["general7", "pairs9", "flags4", "flags5", "flags6"], "extra_cx": 40, "extra_t": 32,
                    "note": "any spin-network U_B circuit (register d[8] + ancillas) between the LSH transcoder and its inverse"}
        if source == "paulo15":
            return {"wrap": "su2plaq.circuits.lsh:wrap_spinnet", "kind": "UB", "fixed_angle": True, "beta": -0.05,
                    "note": "Paulo's 15-qubit file wrapped by the transcoder equals U_B(-0.05) in the LSH sign gauge "
                            "(gauge-equivalent to U_B(+0.05), METHODS-spinnet section 2)"}
        if source in ("paulo34", "lean22", "lean22_v2"):
            return f"{source} is a 12-qubit electric-basis circuit: it does not act on LSH loop-number codes"
        raise ValueError(f"unknown import source {source!r}; known: ['spinnet', 'paulo15', 'paulo34', 'lean22', 'lean22_v2']")
