"""24-qubit loop-string-hadron encoding (prompts/400 section 1-2; docs/METHODS-lsh.md L2-L6).

Data register d[0..11] = the four 'in' sites (site c at qubits 3c, 3c+1, 3c+2 = l_pn, l_nv, l_vp); outer register
o[0..11] = the four 'out' sites (site c at 12+3c.. = l_12, l_2v, l_v1).  The 433 physical states are computational-basis
codes (site-valid + Abelian Gauss law); the 47 valid data codes are the inner codes.

Step 7.1: `label_of_code`.  The class `LSH` is a STUB until step 7.3 (codec) / 7.4 (targets)."""
from __future__ import annotations

import functools

from su2plaq.encodings.base import Encoding
from su2plaq.exact.spinnet import labels as route_b_labels
from su2plaq.lsh.operators import code_of_label  # noqa: F401  (re-export)

N_DATA, N_OUTER = 12, 12


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


def _pending(name: str, step: str):
    raise NotImplementedError(f"PENDING: su2plaq.encodings.lsh.LSH.{name} is not built yet (prompts/400 step {step})")


class LSH(Encoding):
    name = "lsh"
    n_data = N_DATA
    n_outer = N_OUTER
    is_basis_encoding = True

    def __init__(self):
        _pending("__init__", "7.3")

    def inner_codes(self):
        _pending("inner_codes", "7.3")

    def physical_vectors(self):
        _pending("physical_vectors", "7.3")

    def decode(self, code: int):
        _pending("decode", "7.3")

    def decode_state(self, codes, amps):
        _pending("decode_state", "7.3")

    def target(self, kind, alpha, beta, order=1, include_outer_electric=False):
        _pending("target", "7.4")

    def inner_target(self, kind, alpha, beta, order=1):
        _pending("inner_target", "7.4")

    def h_magnetic(self):
        _pending("h_magnetic", "7.4")

    def h_electric(self, include_outer=False):
        _pending("h_electric", "7.4")

    def layout_of(self, qc):
        _pending("layout_of", "7.3")

    def describe(self) -> str:
        _pending("describe", "7.3")

    def import_map(self, source: str):
        _pending("import_map", "7.3")
