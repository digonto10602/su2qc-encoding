"""M1-O1 — the outer-control don't-care table: dim S_o for every outer pattern and the inner-span rank
(prompts/002 §4 step 1.8; settles plan-001 claim (i)). Exact integers; the rank is recomputed independently here."""
import numpy as np
import pytest

import functools

from tests.acceptance._api import api


@functools.lru_cache(maxsize=None)
def _enc():
    return api("su2plaq.encodings.twelve:TwelveQubit")()


def test_M1_O1_outer_dont_care_table():
    """s_o_dims has 3^8 = 6561 entries (one per outer electric pattern with the far end fixed), 3153 of them non-zero
    (the patterns carrying physical support); the closed pattern has dim 2; max dim 17; inner_span() is orthonormal with
    rank equal to the rank of the stacked inner components computed here from physical_vectors(). All 625 inner codes
    occur. Consequence: an outer-blind circuit must be exact on the inner span; outer-reading circuits only on each S_o."""
    enc = _enc()
    basis = enc.basis
    dims = api("su2plaq.exact.physical:s_o_dims")(basis)
    assert len(dims) == 6561 and all(isinstance(v, (int, np.integer)) and v >= 0 for v in dims.values())
    nonzero = {o: v for o, v in dims.items() if v > 0}
    assert len(nonzero) == 3153 and dims[0] == 2 and max(dims.values()) == 17
    supp = api("su2plaq.exact.physical:s_o_support")(basis)
    assert set(supp) == set(nonzero) and all(1 <= len(s) <= 17 for s in supp.values())
    assert len(set().union(*[set(s.tolist()) for s in supp.values()])) == 625
    S = api("su2plaq.exact.physical:inner_span")(basis)
    assert S.shape[0] == 625 and np.abs(S.conj().T @ S - np.eye(S.shape[1])).max() <= 1e-10
    # independent rank: stack the inner components of every (state, outer code) pair from the encoding's vectors
    eb = enc.physical_vectors()
    cols = []
    for codes, amps in zip(eb.codes, eb.amps):
        outer = codes >> 12
        inner = codes & 0xFFF
        for o in np.unique(outer):
            sel = outer == o
            v = np.zeros(4096, complex)
            v[inner[sel]] = amps[sel]
            cols.append(v)
    Mstack = np.array(cols).T
    rank = np.linalg.matrix_rank(Mstack, tol=1e-10)
    assert S.shape[1] == rank
    # the span is the same space: every column lies in it (projector residual 1e-10) — map codes to the 625-index order
    codes625 = enc.inner_codes()
    sub = Mstack[codes625, :]
    assert np.abs(Mstack).sum() - np.abs(sub).sum() <= 1e-12   # no weight outside valid codes
    resid = sub - S @ (S.conj().T @ sub)
    assert np.abs(resid).max() <= 1e-10
