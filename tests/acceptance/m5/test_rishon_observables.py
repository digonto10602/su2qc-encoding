"""M5-O1 — shared observables of the rishon model and Kogut-Susskind (prompts/200 §2.7; METHODS-rishon R5; research 200
§7-§8).  Closed forms vs exact 2x2 / 3x3 exponentials 1e-12; production values (from the 1296-dim inner target and the
laptop's 433-dim KS target) vs the independent closed blocks 1e-10."""
import numpy as np
import pytest

from tests.acceptance._api import CLOSED_ALLHALF, CLOSED_VACUUM, api
from tests.acceptance.m5 import _ref


def test_M5_O1_closed_spectra():
    """Closed-sector spectra at g^2 in {0.5, 1, 2}: rishon (per outer singlet choice) eigenvalue 0 with multiplicity 15
    and 3g^2/4 ± sqrt(9g^4/16 + 32/g^4); KS: 3g^2/4 ± sqrt(9g^4/16 + 4/g^4).  The KS values also equal the laptop's
    hamiltonian_phys on the two closed states."""
    Ob = api("su2plaq.rishon.observables")
    sp = Ob.closed_spectra((0.5, 1.0, 2.0))
    for g2 in (0.5, 1.0, 2.0):
        r, k = _ref.closed_eigs(g2)
        R = sp["rishon"][g2]
        ev, mult = np.array(R["eigenvalues"], float), np.array(R["multiplicities"], int)
        order = np.argsort(ev)
        ev, mult = ev[order], mult[order]
        assert len(ev) == 3 and np.abs(ev - r).max() <= 1e-10 and mult.tolist() == [1, 15, 1]
        K = sp["ks"][g2]
        evk = np.sort(np.array(K["eigenvalues"], float))
        assert len(evk) == 2 and np.abs(evk - k).max() <= 1e-10 and list(K["multiplicities"]) == [1, 1]
        assert np.abs(np.sort(np.linalg.eigvalsh(Ob.ks_closed_block(g2))) - k).max() <= 1e-12
        basis = api("su2plaq.exact.physical:physical_basis")(convention="cg")
        H = api("su2plaq.exact.operators:hamiltonian_phys")(basis, g2)
        idx = [basis.index(CLOSED_VACUUM), basis.index(CLOSED_ALLHALF)]
        assert np.abs(np.sort(np.linalg.eigvalsh(H[np.ix_(idx, idx)])) - k).max() <= 1e-10


@pytest.mark.parametrize("alpha,beta", list(_ref.ANGLES))
def test_M5_O1_observables_after_steps(alpha, beta):
    """E_link(n), P(n) = <Re Tr U_P>, Loschmidt echo after n = 1, 2 first-order steps from the vacuum: production (inner
    target on the closed codes; laptop target on the KS closed states) vs the independent closed blocks (1e-10); P(1) = 0
    in both theories (1e-12); the n = 1 closed forms (theta_KS = 2 beta, theta_R = 4 sqrt2 beta) hold (1e-12)."""
    Ob = api("su2plaq.rishon.observables")
    got = Ob.observables(alpha, beta, n_steps=2)
    for n in (1, 2):
        ref = _ref.observables_closed(alpha, beta, n)
        for th in ("rishon", "ks"):
            for key in ("E_link", "P", "echo"):
                assert abs(got[th][n][key] - ref[th][key]) <= 1e-10, (th, n, key, got[th][n][key], ref[th][key])
        if n == 1:
            assert abs(got["rishon"][1]["P"]) <= 1e-12 and abs(got["ks"][1]["P"]) <= 1e-12
    cf = Ob.closed_forms(alpha, beta)
    rf = _ref.closed_forms(alpha, beta)
    for th in ("rishon", "ks"):
        for key in ("E_link", "P", "echo"):
            assert abs(cf[th][key] - rf[th][key]) <= 1e-12 and abs(cf[th][key] - got[th][1][key]) <= 1e-10
    # KS values independently from the laptop's physical target restricted to the closed sector
    basis = api("su2plaq.exact.physical:physical_basis")(convention="cg")
    T = api("su2plaq.exact.operators:target")(basis, "step", alpha, beta, 1)
    i0, i1 = basis.index(CLOSED_VACUUM), basis.index(CLOSED_ALLHALF)
    psi = T[:, i0]
    assert abs(np.linalg.norm(psi[[i0, i1]]) - 1) <= 1e-10
    assert abs(abs(psi[i0]) ** 2 - got["ks"][1]["echo"]) <= 1e-10
    assert abs(0.75 * abs(psi[i1]) ** 2 - got["ks"][1]["E_link"]) <= 1e-10
    tab = Ob.observables_table()
    assert set(tab) >= {"angles", "rishon", "ks", "definitions"} and len(tab["angles"]) == 3
