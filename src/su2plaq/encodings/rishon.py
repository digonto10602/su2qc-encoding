"""Rishon (SU(2) quantum link model) encoding, 48 qubits (prompts/200 §2.4; METHODS-rishon R2, R3, R6).

Link l occupies qubits 4l..4l+3 = (L1, L2, R1, R2); `d` = qubits 0-15 (inner links b, r, t, l), `o` = qubits 16-47
(outer links o0..o7).  Physical states are the sparse COO states of `su2plaq.rishon.physical`; targets are inner
operators (`su2plaq.rishon.operators`) acting as V_in (x) 1_outer.  M5 must not import su2plaq.compress.*.
"""
from __future__ import annotations

import functools
from typing import TYPE_CHECKING

import numpy as np

from su2plaq.encodings.base import EncodedBasis, Encoding, Layout  # noqa: F401
from su2plaq.rishon import operators as _ops
from su2plaq.rishon import physical as _phys
from su2plaq.rishon.algebra import RishonLink

if TYPE_CHECKING:
    from su2plaq.rishon.physical import RishonBasis

RISHON_NOMINAL = (0.37, 0.61)    # NOT in encodings/base.NOMINAL_ANGLES (laptop-owned file)

_LINK_NAMES = ("b", "r", "t", "l")
_N_LINKS = 12
_TYPES = ("A", "B", "Q")


def _registers() -> dict[str, list[int]]:
    regs = {"d": list(range(16)), "o": list(range(16, 48))}
    for l, nm in enumerate(_LINK_NAMES):
        regs[f"link_{nm}"] = list(range(4 * l, 4 * l + 4))
    for k in range(8):
        regs[f"outer_{k}"] = list(range(16 + 4 * k, 20 + 4 * k))
    return regs


def _layout_of(qc, n_data: int, n_outer: int) -> Layout:
    """data = qubits of register 'd' (if absent: the first n_data qubits); outer = qubits of register 'o' (empty if
    absent); ancilla = every other qubit in index order."""
    n = qc.num_qubits
    regs = {reg.name: [qc.find_bit(q).index for q in reg] for reg in qc.qregs}
    if "d" in regs:
        data = regs["d"]
        if len(data) != n_data:
            raise ValueError(f"register 'd' must have {n_data} qubits, has {len(data)}")
    else:
        if n < n_data:
            raise ValueError(f"circuit has {n} qubits, fewer than the {n_data} data qubits")
        data = list(range(n_data))
    outer = regs.get("o", [])
    if outer and len(outer) != n_outer:
        raise ValueError(f"register 'o' must have {n_outer} qubits, has {len(outer)}")
    if set(data) & set(outer):
        raise ValueError("data and outer registers overlap")
    used = set(data) | set(outer)
    return Layout(data=list(data), outer=list(outer), ancilla=[q for q in range(n) if q not in used])


@functools.lru_cache(maxsize=1)
def _codec_tables() -> np.ndarray:
    """(12, 16) int8: link-nibble -> type index (0 A, 1 B, 2 Q) or -1 if invalid at that link.

    Inner links: the six two-rishon nibbles.  Outer links: near end free (empty, full, colour 1, colour 2), far end
    fixed by the type (A/B: empty/full; Q: colour 1), exactly the states produced by `rishon_basis()`."""
    D = _phys._diagram()
    tab = np.full((_N_LINKS, 16), -1, dtype=np.int8)
    rl = RishonLink()
    for nib in range(16):
        t = rl.link_type(nib)
        if t is not None:
            for l in range(4):
                tab[l, nib] = _TYPES.index(t)
    for l in D.outer_links():
        near_role = "out" if D.links[l].near_end == "L" else "in"
        far_role = "in" if near_role == "out" else "out"
        s_near = _phys.near_shift(l) - 4 * l
        s_far = _phys.far_shift(l) - 4 * l
        for ti, t in enumerate(_TYPES):
            far = _phys._end_codes(t, far_role)[0] if t != "Q" else 1
            for near in _phys._end_codes(t, near_role):
                tab[l, (near << s_near) | (far << s_far)] = ti
    return tab


class RishonEncoding(Encoding):
    name = "rishon"
    n_data = 16
    n_outer = 32
    is_basis_encoding = False

    def __init__(self):
        self.registers = _registers()

    @property
    def basis(self) -> "RishonBasis":
        """The 38 432 physical states (built once, cached module-wide); not a KS PhysicalBasis."""
        return _phys.rishon_basis()

    # ------------------------------------------------------------------ codec
    def inner_codes(self) -> np.ndarray:
        return _ops.inner_codes()

    def _type_indices(self, codes: np.ndarray) -> np.ndarray:
        """(n, 12) type indices (-1 invalid) for 48-bit codes; any code outside [0, 2^48) is invalid in every column."""
        codes = np.asarray(codes, dtype=np.int64)
        tab = _codec_tables()
        out = np.empty((len(codes), _N_LINKS), dtype=np.int8)
        for l in range(_N_LINKS):
            out[:, l] = tab[l][(codes >> (4 * l)) & 15]
        out[(codes < 0) | (codes >> 48 != 0), :] = -1
        return out

    def decode(self, code: int):
        """The 12 link types ('A'|'B'|'Q') of a valid 48-bit code, None if it is invalid (wrong weight on a link,
        outer far end not fixed, bits above 47)."""
        ti = self._type_indices(np.array([int(code)], dtype=np.int64))[0]
        if np.any(ti < 0):
            return None
        return tuple(_TYPES[int(i)] for i in ti)

    def decode_state(self, codes, amps):
        """Keys are the codes: identity on valid codes; ValueError on an invalid one."""
        codes = np.asarray(codes, dtype=np.int64)
        if np.any(self._type_indices(codes) < 0):
            raise ValueError("invalid code in decode_state")
        return codes.copy(), np.asarray(amps).copy()

    def physical_vectors(self, which: str = "all", n_sample: int = 256, seed: int = 20261104) -> EncodedBasis:
        """'all' (38 432 states), 'closed' (the 17 closed references), 'sample' (17 closed + n_sample seeded)."""
        b = self.basis
        if which == "all":
            idx = list(range(b.dim))
        elif which == "closed":
            idx = _phys.closed_indices(b)
        elif which == "sample":
            idx = _phys.closed_indices(b) + _phys.sample_indices(b, n=n_sample, seed=seed)
        else:
            raise ValueError(f"which must be 'all', 'closed' or 'sample', got {which!r}")
        return EncodedBasis([b.keys[k] for k in idx], [b.amps[k] for k in idx], self.n_data, self.n_outer)

    # ------------------------------------------------------------------ targets
    def inner_target(self, kind, alpha, beta, order=1) -> np.ndarray:
        return _ops.inner_target(kind, alpha, beta, order)

    def target(self, kind, alpha, beta, order=1, states: list[int] | None = None) -> np.ndarray:
        """<Psi_k'|(V_in (x) 1_outer)|Psi_k> for k, k' in `states` (exact: summed over the common outer patterns)."""
        if states is None:
            raise ValueError("the 38432-dim physical target is never materialised; use inner_target or pass states")
        b = self.basis
        codes = _ops.inner_codes()
        ids, rows, outs, vals = [], [], [], []
        for j, k in enumerate(states):
            keys = np.asarray(b.keys[k], dtype=np.int64)
            r = np.searchsorted(codes, keys & 0xFFFF)
            if np.any(r >= len(codes)) or np.any(codes[np.minimum(r, len(codes) - 1)] != (keys & 0xFFFF)):
                raise ValueError("a physical state has an inner component outside the valid code space")
            ids.append(np.full(len(keys), j, dtype=np.int64))
            rows.append(r)
            outs.append(keys >> 16)
            vals.append(np.asarray(b.amps[k], dtype=np.complex128))
        ids, rows, outs, vals = (np.concatenate(x) for x in (ids, rows, outs, vals))
        V = _ops.inner_target(kind, alpha, beta, order)
        n = len(states)
        out = np.zeros((n, n), dtype=np.complex128)
        # <psi_k'|V (x) 1|psi_k> = sum over outer patterns o of <z_k'^o|V|z_k^o>
        order_ = np.argsort(outs, kind="stable")
        ids, rows, outs, vals = ids[order_], rows[order_], outs[order_], vals[order_]
        starts = np.flatnonzero(np.concatenate(([True], outs[1:] != outs[:-1])))
        bounds = np.unique(np.concatenate((starts, [len(outs)])))
        for lo, hi in zip(bounds[:-1], bounds[1:]):
            sid, sr, sv = ids[lo:hi], rows[lo:hi], vals[lo:hi]
            u_rows, ri = np.unique(sr, return_inverse=True)
            u_ids, ci = np.unique(sid, return_inverse=True)
            Z = np.zeros((len(u_rows), len(u_ids)), dtype=np.complex128)
            np.add.at(Z, (ri, ci), sv)
            out[np.ix_(u_ids, u_ids)] += Z.conj().T @ V[np.ix_(u_rows, u_rows)] @ Z
        return out

    # ------------------------------------------------------------------ views, layout, text
    def inner_view(self) -> "RishonInnerView":
        return RishonInnerView()

    def layout_of(self, qc) -> Layout:
        return _layout_of(qc, self.n_data, self.n_outer)

    def describe(self) -> str:
        D = _phys._diagram()
        links = ", ".join(f"`{n}` = qubits ({4 * l}..{4 * l + 3})" for l, n in enumerate(_LINK_NAMES))
        outs = ", ".join(f"o{k}: ({16 + 4 * k}..{19 + 4 * k}) near end `{D.links[4 + k].near_end}`" for k in range(8))
        return (
            f"### Encoding `{self.name}` ({self.n_data} data + {self.n_outer} outer qubits)\n\n"
            "SU(2) quantum link model, two fermionic rishons per link, Jordan-Wigner with link-contiguous modes. "
            f"Link l occupies qubits (4l, 4l+1, 4l+2, 4l+3) = (L1, L2, R1, R2); occupation bit 1 = mode occupied; "
            f"colour 1 = up. Inner links: {links}.\n\n"
            "| link type | bits L1 L2 R1 R2 | integer |\n|---|---|---|\n"
            "| A (both rishons at the start) | `1100` | 3 |\n| B (both at the end) | `0011` | 12 |\n"
            "| Q (one at each end) | `1010`, `0110`, `1001`, `0101` | 5, 6, 9, 10 |\n\n"
            f"The other 10 of 16 link patterns are unused (don't-care). {len(self.inner_codes())} valid inner codes "
            "(6^4 = 1296).\n\n"
            f"**Outer controls `o[0..{self.n_outer - 1}]`.** Outer link k occupies qubits (16+4k..19+4k); the near end "
            "(at the plaquette corner) is free (empty, full, colour 1, colour 2), the far end is fixed by the link "
            f"type (A/B: empty/full; Q: colour 1). {outs}. The target never changes the outer register; a circuit may "
            "read it (diagonal gates on those qubits only), never write it.\n\n"
            "**Physical states.** 38432 Gauss-law (SU(2)) states: products of corner singlet tensors over the 48-qubit "
            "occupation basis; closed sector 4352; unphysical inputs are don't-care. Ancillas must return to |0>.\n")

    def import_map(self, source):
        """No external circuit acts on rishon codes: every source gets a reason string."""
        known = {
            "paulo34": "Paulo's 34-qubit circuit acts on the 12-qubit Paulo codes (3 qubits per link), not on rishon codes",
            "lean22": "the su2qc-trotter lean circuits act on the 12-qubit Paulo codes, not on rishon codes",
            "lean22_v2": "the su2qc-trotter lean circuits act on the 12-qubit Paulo codes, not on rishon codes",
            "spinnet15": "spinnet15 acts on route-B spin-network labels, a different encoding, not on rishon codes",
        }
        if source in known:
            return known[source] + "; the rishon circuits are built from the inner-operator structure (circuits.rishon)"
        raise ValueError(f"unknown import source {source!r}; known: {sorted(known)}")


class RishonInnerView:
    """Encoding-like object for the laptop evaluator (prompts/002 §2.7 duck typing): the 1296 valid inner codes as
    single-code states with outer bits 0; its target is the inner operator V_in."""

    name = "rishon_inner"
    n_data = 16
    n_outer = 32
    is_basis_encoding = True

    def __init__(self):
        self.registers = _registers()

    def inner_codes(self) -> np.ndarray:
        return _ops.inner_codes()

    def physical_vectors(self) -> EncodedBasis:
        codes = _ops.inner_codes()
        return EncodedBasis([codes[i:i + 1].copy() for i in range(len(codes))],
                            [np.ones(1, dtype=np.complex128) for _ in range(len(codes))], self.n_data, self.n_outer)

    def layout_of(self, qc) -> Layout:
        return _layout_of(qc, self.n_data, self.n_outer)

    def decode_state(self, codes, amps):
        return np.asarray(codes, dtype=np.int64).copy(), np.asarray(amps).copy()
