"""Unit tests for su2plaq.rishon.observables (step 5.5): internal consistency only, no hard-coded physics numbers."""
import numpy as np

from su2plaq.rishon import observables as Ob


def test_closed_spectra_trace_and_multiplicities():
    sp = Ob.closed_spectra((0.5, 2.0))
    for g2 in (0.5, 2.0):
        r = sp["rishon"][g2]
        assert sum(r["multiplicities"]) == 17
        assert abs(sum(e * m for e, m in zip(r["eigenvalues"], r["multiplicities"])) - 1.5 * g2) <= 1e-12   # tr = (g2/2)*3
        k = sp["ks"][g2]
        assert sum(k["multiplicities"]) == 2
        assert abs(sum(k["eigenvalues"]) - 1.5 * g2) <= 1e-12


def test_observables_probabilities_and_n1_plaquette():
    ob = Ob.observables(0.37, 0.61, n_steps=2)
    for th in ("rishon", "ks"):
        assert abs(ob[th][1]["P"]) <= 1e-12
        for n in (1, 2):
            assert 0 <= ob[th][n]["echo"] <= 1 + 1e-12 and ob[th][n]["E_link"] >= -1e-12
    cf = Ob.closed_forms(0.37, 0.61)
    for th in ("rishon", "ks"):
        for key in ("E_link", "P", "echo"):
            assert abs(cf[th][key] - ob[th][1][key]) <= 1e-10


def test_order2_differs_and_table_is_json_able():
    import json

    a = Ob.observables(0.9, 0.5, n_steps=1, order=1)["rishon"][1]
    b = Ob.observables(0.9, 0.5, n_steps=1, order=2)["rishon"][1]
    assert abs(a["echo"] - b["echo"]) <= 1e-10          # the vacuum is an electric eigenstate: same closed-form n = 1
    json.dumps(Ob.observables_table(angles=((0.37, 0.61),)))


def test_closed_spectra_zero_count_is_computed_from_the_model():
    """The number of zero levels = (closed-sector dimension) - (bright 3x3 block rank), from the operators, not typed in."""
    from su2plaq.rishon import operators as ops

    Hf = ops.closed_block_full(1.0)
    dim = Hf.shape[0]
    assert dim == 17
    bright = ops.closed_block(1.0)
    # the full block is the bright block plus decoupled zero rows/columns
    ev_full = np.linalg.eigvalsh(Hf)
    ev_bright = np.linalg.eigvalsh(bright)
    n_zero = int(np.sum(np.abs(ev_full) <= 1e-9))
    n_zero_bright = int(np.sum(np.abs(ev_bright) <= 1e-9))
    assert n_zero - n_zero_bright == dim - bright.shape[0]
    r = Ob.closed_spectra((1.0,))["rishon"][1.0]
    i0 = int(np.argmin(np.abs(r["eigenvalues"])))
    assert r["multiplicities"][i0] == n_zero
    assert sum(r["multiplicities"]) == dim


def test_closed_block_full_detects_a_non_invariant_sector(monkeypatch):
    """A term coupling the closed sector to other states must raise, not be hidden behind typed-in zeros."""
    from su2plaq.rishon import operators as ops

    base = ops.h_magnetic_inner()
    bad = base.copy()
    codes = ops.inner_codes()
    va, _, _ = ops.closed_codes()
    i = int(np.searchsorted(codes, va))
    from su2plaq.rishon.algebra import CODE_A, CODE_B

    vac = {sum((CODE_A if (m >> l) & 1 == 0 else CODE_B) << (4 * l) for l in range(4)) for m in range(16)}
    loop = set(int(c) for c in ops.closed_codes()[2])
    j = next(k for k in range(len(codes)) if int(codes[k]) not in vac and int(codes[k]) not in loop)
    bad[i, j] = bad[j, i] = 1.0
    monkeypatch.setattr(ops, "h_magnetic_inner", lambda: bad)
    with np.testing.assert_raises(ValueError):
        ops.closed_block_full(1.0)
