"""Step 6.0 unit tests: the `ladder=` keyword of build_UB / build_step and operators.electric_coefficient (prompts/203 §1.3, §3)."""
import functools

import numpy as np
import pytest

from su2plaq.circuits import rishon as C
from su2plaq.evaluate.sparse_sim import encoded_block, run_batch
from su2plaq.rishon import operators as O
from su2plaq.rishon.algebra import RishonLink


@functools.lru_cache(maxsize=None)
def _ub(ladder):
    return C.build_UB(0.61, ladder=ladder)


def test_default_ladder_is_ccx_and_identical():
    a, b = C.build_UB(0.61), _ub("ccx")
    assert [(i.operation.name, [a.find_bit(q).index for q in i.qubits], list(i.operation.params)) for i in a.data] == \
           [(i.operation.name, [b.find_bit(q).index for q in i.qubits], list(i.operation.params)) for i in b.data]
    assert a.count_ops().get("rccx", 0) == 0
    s1, s2 = C.build_step(0.37, 0.61, 1), C.build_step(0.37, 0.61, 1, ladder="ccx")
    assert dict(s1.count_ops()) == dict(s2.count_ops()) and s1.num_qubits == s2.num_qubits


def test_ladder_gate_structure():
    base, rc, mc = (dict(_ub(l).count_ops()) for l in ("ccx", "rccx", "mcx"))
    # rccx / mcx swap Toffolis for relative-phase ones, one-for-one (same number of AND gates in the two styles); the ccx
    # ladder has fewer ANDs only because adjacent identical self-inverse ccx pairs cancel, which rccx pairs cannot
    assert rc["ccx"] + rc["rccx"] == mc["ccx"] + mc["rccx"] >= base["ccx"]
    for k in set(base) - {"ccx", "rccx"}:
        assert base[k] == rc[k] == mc[k], k
    # rccx ladder keeps only the ladders of length-1 chains as ccx (they are the same in all variants); mcx keeps the last AND per chain
    assert rc["ccx"] < mc["ccx"] < base["ccx"] and mc["rccx"] < rc["rccx"]
    assert base["crx"] == rc["crx"] == mc["crx"]
    for l in ("rccx", "mcx"):
        st = C.build_step(0.37, 0.61, 1, ladder=l).count_ops()
        assert st.get("ccx", 0) == dict(_ub(l).count_ops())["ccx"] and st.get("rccx", 0) == dict(_ub(l).count_ops())["rccx"]
    o2 = C.build_step(0.37, 0.61, 2, ladder="mcx").count_ops()
    assert o2.get("ccx", 0) == mc["ccx"] and o2.get("rccx", 0) == mc["rccx"]


def test_bad_ladder_raises():
    for fn in (lambda: C.build_UB(0.61, ladder="toffoli"), lambda: C.build_step(0.37, 0.61, ladder="x")):
        with pytest.raises(ValueError):
            fn()


@pytest.mark.parametrize("ladder", ["rccx", "mcx"])
def test_ladder_variants_exact_on_a_few_codes(ladder):
    """Each ladder style implements the same U_B on the inner codes (checked on 12 seeded codes, 1e-10)."""
    codes = O.inner_codes()
    rng = np.random.default_rng(7)
    bright = np.flatnonzero(np.abs(O.inner_target("UB", None, 0.61) - np.eye(1296)).max(axis=0) > 1e-9)
    pick = np.unique(np.concatenate([rng.choice(1296, 6, replace=False), rng.choice(bright, 6, replace=False)]))
    b = run_batch(_ub(ladder), codes[pick])
    assert not np.any(b.keys >> 16)
    M, leak = encoded_block(b, codes, len(pick), (1 << 16) - 1)
    assert leak.max() < 1e-20 and np.abs(M - O.inner_target("UB", None, 0.61)[:, pick]).max() < 1e-10


def test_electric_coefficient_is_quartet_casimir():
    coef = O.electric_coefficient()
    rl = RishonLink()
    for s in rl.sector:
        s = int(s)
        want = 0.5 * (rl.casimir_L[s, s] + rl.casimir_R[s, s]).real
        assert abs(want - (coef if rl.link_type(s) == "Q" else 0.0)) <= 1e-14, s
    assert abs(coef - 0.75) <= 1e-14        # independent value (the Casimir j(j+1) of j = 1/2)
    codes = O.inner_codes()
    nq = sum(np.isin((codes >> (4 * l)) & 15, (5, 6, 9, 10)) for l in range(4))
    assert np.abs(O.h_electric_inner() - coef * nq).max() <= 1e-14
    qc = C.build_UE(0.37)
    ps = [i.operation.params[0] for i in qc.data if i.operation.name == "p"]
    assert len(ps) == 4 and all(abs(p + coef * 0.37) <= 1e-15 for p in ps)
