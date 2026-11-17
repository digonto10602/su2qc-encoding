"""Unit tests of su2plaq.crosscheck.ks (prompts/009 §5.1): operators, signs, transported targets, step circuits, cross-verdict."""
from __future__ import annotations

import numpy as np
import pytest

from su2plaq.compress.spec import get_encoding
from su2plaq.crosscheck import ks as K


def test_ks_operators_shapes_and_electric_values():
    from su2plaq.exact.physical import physical_basis

    j = np.array([lab[0] for lab in physical_basis(convention="cg").labels], dtype=float)
    for enc in K.KS_ENCODINGS:
        hi, ha, HB = K.ks_operators(enc)
        assert hi.shape == (433,) and ha.shape == (433,) and HB.shape == (433, 433)
        assert np.abs(hi - 0.75 * (j[:, :4] == 0.5).sum(1)).max() <= 1e-12
        assert np.abs(ha - 0.75 * (j == 0.5).sum(1)).max() <= 1e-12
        assert np.abs(HB - HB.conj().T).max() <= 1e-12


def test_ks_operators_return_copies():
    hi, _, _ = K.ks_operators("spinnet")
    hi[:] = 99.0
    assert K.ks_operators("spinnet")[0].max() < 99.0


def test_ks_hamiltonian_composition_and_spectra():
    g2 = 1.7
    hi, ha, HB = K.ks_operators("lsh")
    assert np.abs(K.ks_hamiltonian("lsh", g2) - (0.5 * g2 * np.diag(ha) + HB / g2)).max() <= 1e-12
    assert np.abs(K.ks_hamiltonian("lsh", g2, include_outer_electric=False) - (0.5 * g2 * np.diag(hi) + HB / g2)).max() <= 1e-12
    ev = {e: np.linalg.eigvalsh(K.ks_hamiltonian(e, g2)) for e in K.KS_ENCODINGS}
    assert np.abs(ev["twelve"] - ev["spinnet"]).max() <= 1e-10 and np.abs(ev["twelve"] - ev["lsh"]).max() <= 1e-10


def test_gauge_signs():
    for e in K.KS_ENCODINGS:
        D = K.gauge_signs(e)
        assert D.shape == (433,) and set(np.unique(D).tolist()) <= {-1.0, 1.0}
    assert np.all(K.gauge_signs("twelve") == 1.0)


def test_transported_target_is_destination_target_and_unitary():
    for src, dst in (("lsh", "spinnet"), ("twelve", "lsh")):
        T = K.transported_target(src, dst, "step", 0.37, 0.61, 1)
        assert np.linalg.norm(T - get_encoding(dst).target("step", 0.37, 0.61, 1), 2) <= 1e-10
        assert np.linalg.norm(T.conj().T @ T - np.eye(433), 2) <= 1e-10
    # identity for src == dst
    assert np.abs(K.transported_target("spinnet", "spinnet", "UE", 0.37, 0.61) - get_encoding("spinnet").target("UE", 0.37, 0.61)).max() <= 1e-14


def test_bad_encoding_names_rejected():
    with pytest.raises(ValueError):
        K.ks_operators("rishon")
    with pytest.raises(ValueError):
        K.gauge_signs("fuzzy_ub")


def test_step_circuit_general_and_argument_checks():
    qc, info = K.step_circuit("lsh", "general", 0.37, 0.61, 1)
    assert info == {"which": "general", "entry": None} and qc.num_qubits > 0
    with pytest.raises(ValueError):
        K.step_circuit("lsh", "bogus")
    with pytest.raises(ValueError):
        K.step_circuit("lsh", "headline", order=2)


def test_cross_verdict_general_lsh_against_spinnet_target():
    v = K.cross_verdict("lsh", "spinnet", "general", 0.37, 0.61, 1)
    assert v.ok and v.certified and v.n_inputs == 433 and v.total_error <= 1e-10
