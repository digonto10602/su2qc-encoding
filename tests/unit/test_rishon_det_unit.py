"""Unit tests for the det layer operators / targets and the rishon prune cap (prompts/204 steps D1, D2): small, cheap checks."""
import numpy as np
import pytest
from qiskit import QuantumCircuit, QuantumRegister

from su2plaq.encodings.rishon import RISHON_ALT_ETA, RISHON_NOMINAL_ETA, RishonEncoding
from su2plaq.evaluate.evaluator import PRUNE_FRACTION, Verdict
from su2plaq.rishon import operators as O
from su2plaq.rishon import verify as V


def _verdict(reason="pruning_bound", dropped=5e-12, leak=0.0, err=1e-13, dirty=0.0, max_leak=0.0):
    return Verdict(ok=reason == "ok", reason=reason, op_norm_error=err + dropped + leak, max_leak=max_leak, dirty_ancilla=dirty,
                   phase=1 + 0j, outer_bits_read=0, n_blocks=1, gauss_residual=float("nan"), method="inner_block", engine="sparse",
                   seconds=0.0, failing_inputs=[], n_inputs=1296, dropped_total=dropped, block_error=err, leak_amplitude=leak)


# ------------------------------------------------------------------------------------------------ D1: prune cap
def test_constants_and_cap_ordering():
    assert V.RISHON_PRUNE_FRACTION == 0.1 and PRUNE_FRACTION == 1e-2 and V.RISHON_PRUNE_FRACTION >= PRUNE_FRACTION


@pytest.mark.parametrize("kw,reason", [
    (dict(dropped=5e-12), "ok"),                                           # between the two caps, exact otherwise
    (dict(dropped=2e-11), "pruning_bound"),                                # above the rishon cap 1e-11
    (dict(dropped=5e-12, leak=2e-10, dirty=1.0, max_leak=1.0), "dirty_ancilla"),
    (dict(dropped=5e-12, leak=2e-10, dirty=0.1, max_leak=1.0), "leak"),
    (dict(dropped=5e-12, err=2e-10), "error"),
    (dict(dropped=5e-12, err=9.8e-11), "error"),                           # block + pruning together exceed the budget
])
def test_rejudge_cascade(kw, reason):
    got, failing = V._rejudge(_verdict(**kw), V.RISHON_PRUNE_FRACTION * 1e-10, 1e-10)
    assert got == reason
    assert (failing == []) == (reason == "ok")
    if reason == "pruning_bound":
        assert dict(failing) == {"dropped_total": 2e-11, "prune_cap": pytest.approx(1e-11, rel=1e-12)}


def test_rejudge_cap_scales_with_fraction():
    v = _verdict(dropped=5e-12)
    assert V._rejudge(v, 1e-2 * 1e-10, 1e-10)[0] == "pruning_bound"        # the shared cap reproduces the shared verdict
    assert V._rejudge(v, 1e-1 * 1e-10, 1e-10)[0] == "ok"


def test_verify_refuses_fraction_below_shared_and_det_paths_pending():
    enc = RishonEncoding()
    qc = QuantumCircuit(QuantumRegister(16, "d"))
    with pytest.raises(ValueError):
        V.verify(qc, enc, "UE", 0.0, None, prune_fraction=1e-3, gauss=False)
    v = V.verify(qc, enc, "UE", 0.0, None, prune_fraction=0.5, gauss=False)
    assert v.ok and v.extra["prune_fraction"] == 0.5 and v.extra["prune_cap"] == pytest.approx(5e-11) and v.extra["laptop_reason"] == "ok"
    d = V.verify(qc, enc, "UE", 0.0, None, gauss=False)
    assert d.extra["prune_fraction"] == V.RISHON_PRUNE_FRACTION and d.inner_verdict.ok
    with pytest.raises(NotImplementedError, match="PENDING"):
        V.verify(qc, enc, "step", 0.1, 0.1, eta=0.2, gauss=False)


# ------------------------------------------------------------------------------------------------ D2: operators
def test_h_det_inner_and_hamiltonian():
    D = O.h_det_inner()
    assert D.shape == (1296, 1296) and D.dtype == np.float64 and np.array_equal(D, D.T)
    assert np.array_equal(D, O.det_term_inner().real) and set(np.unique(D).tolist()) == {0.0, 2.0}
    HE, HB = O.h_electric_inner(), O.h_magnetic_inner()
    H = O.hamiltonian_inner(1.3, 0.4)
    assert H.dtype == np.complex128 and np.abs(H - (0.65 * np.diag(HE) + HB / 1.3 + 0.4 * D)).max() <= 1e-13
    assert np.abs(O.hamiltonian_inner(1.3) - (0.65 * np.diag(HE) + HB / 1.3)).max() <= 1e-13


def test_ud_is_exp_of_h_det_and_unitary_group():
    D = O.h_det_inner()
    w, v = np.linalg.eigh(D)
    for eta in (0.29, 0.53):
        U = O.inner_target("UD", None, None, eta=eta)
        assert U.dtype == np.complex128 and np.abs(U - (v * np.exp(-1j * eta * w)) @ v.T).max() <= 1e-12
        assert np.abs(U.conj().T @ U - np.eye(1296)).max() <= 1e-12
    assert np.abs(O.inner_target("UD", None, None, eta=0.0) - np.eye(1296)).max() == 0.0
    a, b = O.inner_target("UD", None, None, eta=0.1), O.inner_target("UD", None, None, eta=0.19)
    assert np.abs(a @ b - O.inner_target("UD", None, None, eta=0.29)).max() <= 1e-12


def test_step_with_and_without_eta():
    a, b, e = 0.37, 0.61, 0.29
    UE, UB, UD = O.inner_target("UE", a, None), O.inner_target("UB", None, b), O.inner_target("UD", None, None, eta=e)
    two = O.inner_target("step", a, b)
    assert np.array_equal(two, O.inner_target("step", a, b, 1, eta=None)) and np.abs(two - UB @ UE).max() <= 1e-13
    assert np.abs(O.inner_target("step", a, b, 1, eta=e) - UB @ UD @ UE).max() <= 1e-12
    h = lambda x: O.inner_target("UD", None, None, eta=x)
    S2 = O.inner_target("step", a, b, 2, eta=e)
    assert np.abs(S2 - O.inner_target("UE", a / 2, None) @ h(e / 2) @ UB @ h(e / 2) @ O.inner_target("UE", a / 2, None)).max() <= 1e-12
    assert np.abs(O.inner_target("step", a, b, 2, eta=0.0) - O.inner_target("step", a, b, 2)).max() <= 1e-12
    assert np.linalg.norm(O.inner_target("step", a, b, 1, eta=e) - two, 2) > 1e-2


def test_target_errors():
    with pytest.raises(ValueError):
        O.inner_target("UD", None, None)
    with pytest.raises(ValueError):
        O.inner_target("UE", 0.3, None, eta=0.1)
    with pytest.raises(ValueError):
        O.inner_target("UB", None, 0.3, eta=0.1)
    with pytest.raises(ValueError):
        O.inner_target("step", 0.3, 0.3, 3, eta=0.1)


def test_closed_block_full_with_lam_d():
    B0 = O.closed_block_full(1.1)
    assert np.array_equal(B0, O.closed_block_full(1.1, 0.0)) and B0.shape == (17, 17)
    B = O.closed_block_full(1.1, 0.2)
    assert np.abs(B - B.conj().T).max() <= 1e-13
    X = np.zeros((17, 17))
    for k in range(16):
        for l in range(4):
            X[k, k ^ (1 << l)] = 1.0           # "link l is type B" bit, as in the acceptance model
    assert np.abs(B - B0 - 0.4 * X).max() <= 1e-12            # det acts as 2 lam_d X_l on the 16 vacua, loop untouched


def test_encoding_pass_through_and_constants():
    enc = RishonEncoding()
    assert (RISHON_NOMINAL_ETA, RISHON_ALT_ETA) == (0.29, (0.53, 1.07))
    assert np.array_equal(enc.inner_target("step", 0.37, 0.61), O.inner_target("step", 0.37, 0.61))
    assert np.array_equal(enc.inner_target("step", 0.37, 0.61, 1, eta=0.29), O.inner_target("step", 0.37, 0.61, 1, eta=0.29))
    ids = [0, 1, 5]
    T = enc.target("step", 0.37, 0.61, 1, states=ids)
    assert np.array_equal(T, enc.target("step", 0.37, 0.61, 1, states=ids, eta=None))
    T3 = enc.target("step", 0.37, 0.61, 1, states=ids, eta=0.29)
    assert T3.shape == (3, 3) and np.linalg.norm(T3, 2) <= 1.0 + 1e-9
    U = enc.target("UD", None, None, states=list(range(5)), eta=0.29)
    assert U.shape == (5, 5) and np.linalg.norm(U, 2) <= 1.0 + 1e-9
