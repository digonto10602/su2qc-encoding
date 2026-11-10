"""M5-B1 (verifier) — su2plaq.rishon.verify: sensitivity cases and the certified/sampled contract (prompts/200 §2.6;
METHODS-rishon R6).  Discrete separations (as M0-E3); exact-angle tolerances 1e-10."""
import functools

import numpy as np
import pytest
from qiskit import QuantumCircuit, QuantumRegister

from tests.acceptance._api import api


@functools.lru_cache(maxsize=None)
def _enc():
    return api("su2plaq.encodings.rishon:RishonEncoding")()


def _qc(with_outer=True, n_anc=2):
    regs = [QuantumRegister(16, "d")] + ([QuantumRegister(32, "o")] if with_outer else []) + ([QuantumRegister(n_anc, "a")] if n_anc else [])
    return QuantumCircuit(*regs)


def test_M5_B1_verifier_sensitivity():
    """identity = UE(0): ok, certified, method 'inner_block', 273 Gauss states (17 closed + 256 seeded), no outer read;
    X on an ancilla -> dirty_ancilla; Z on a data qubit -> error >= 0.5; X on an outer qubit -> writes_outer;
    CZ(outer, data) -> outer_read_unsupported (the inner view is unsound for outer-reading circuits in M5);
    gauss=False -> NaN residual; synth_tolerances re-exported; physical_cross_check on the closed states."""
    enc = _enc()
    Vf = api("su2plaq.rishon.verify")
    v = Vf.verify(_qc(), enc, "UE", 0.0, None)
    assert v.ok and v.reason == "ok" and v.certified and v.method == "inner_block" and v.engine == "sparse"
    assert v.op_norm_error <= 1e-12 and v.block_error <= 1e-12 and v.leak_amplitude <= 1e-12 and v.dropped_total <= 1e-12
    assert v.gauss_residual <= 1e-12 and v.gauss_states == 273 and v.outer_bits_read == 0
    assert v.tolerances == {"tol_err": 1e-10, "tol_gauss": 1e-10} and v.inner_verdict is not None and v.inner_verdict.ok
    assert abs(abs(v.phase) - 1) <= 1e-12
    qc = _qc()
    qc.x(48)
    v = Vf.verify(qc, enc, "UE", 0.0, None)
    assert not v.ok and v.reason == "dirty_ancilla" and v.leak_amplitude >= 1 - 1e-12
    qc = _qc()
    qc.z(0)
    v = Vf.verify(qc, enc, "UE", 0.0, None)
    assert not v.ok and v.reason == "error" and v.op_norm_error >= 0.5
    qc = _qc()
    qc.x(16)
    v = Vf.verify(qc, enc, "UE", 0.0, None)
    assert not v.ok and v.reason == "writes_outer"
    qc = _qc()
    qc.cz(16, 0)
    v = Vf.verify(qc, enc, "UE", 0.0, None)
    assert not v.ok and v.reason == "outer_read_unsupported" and v.outer_bits_read == 1
    qc = _qc(with_outer=False, n_anc=0)
    v = Vf.verify(qc, enc, "UE", 0.0, None, gauss=False)
    assert v.ok and np.isnan(v.gauss_residual) and v.gauss_states == 0
    # a wrong kind/angle is detected at first order
    v = Vf.verify(_qc(), enc, "UE", 0.37, None)
    assert not v.ok and v.reason == "error" and v.op_norm_error > 0.1
    # explicit target may be passed
    v = Vf.verify(_qc(), enc, "UE", 0.37, None, target=np.eye(1296, dtype=complex))
    assert v.ok
    assert Vf.synth_tolerances(10, 1e-6) == {"tol_err": 10 * 1e-6 + 1e-9, "tol_gauss": 10 * 1e-6 + 1e-9}
    P = api("su2plaq.rishon.physical")
    closed = P.closed_indices(enc.basis)
    x = Vf.physical_cross_check(_qc(), enc, "UE", 0.0, None, states=closed)
    assert x["n_states"] == 17 and x["max_abs_diff"] <= 1e-12
    x = Vf.physical_cross_check(_qc(), enc, "UE", 0.0, None)
    assert x["n_states"] == 273 and x["max_abs_diff"] <= 1e-12
