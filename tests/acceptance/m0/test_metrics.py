"""M0-M1, M2, M3 — logical metrics, pygridsynth T-count band, Qiskit Clifford+T pass manager
(prompts/002 §2.8, METHODS §7)."""
import numpy as np
import pytest
from qiskit import QuantumCircuit
from qiskit.circuit.library import MCXGate

from tests.acceptance._api import api, ross_selinger_band


def test_M0_M1_macro_costs():
    """Level-0 lowering costs (CX, T_fixed, N_rot): ccx (6,7,0), rccx (3,4,0), ccz (6,7,0), swap (3,0,0), ch (1,2,0),
    crz (2,0,2), crx (2,0,2), cp (2,0,3), cz (1,0,0), p (0,0,1), p(pi/4) (0,1,0). Exact: Qiskit's level-0
    decompositions are fixed. Native mcx with >= 3 controls must be rejected by lower()."""
    lm = api("su2plaq.metrics.logical:logical_metrics")
    lower = api("su2plaq.metrics.logical:lower")
    LOGICAL_BASIS = api("su2plaq.metrics.logical:LOGICAL_BASIS")
    assert set(LOGICAL_BASIS) == {"cx", "h", "s", "sdg", "t", "tdg", "x", "z", "rz"}
    th = 0.37
    cases = {}
    qc = QuantumCircuit(3); qc.ccx(0, 1, 2); cases["ccx"] = (qc, (6, 7, 0))
    qc = QuantumCircuit(3); qc.rccx(0, 1, 2); cases["rccx"] = (qc, (3, 4, 0))
    qc = QuantumCircuit(3); qc.ccz(0, 1, 2); cases["ccz"] = (qc, (6, 7, 0))
    qc = QuantumCircuit(2); qc.swap(0, 1); cases["swap"] = (qc, (3, 0, 0))
    qc = QuantumCircuit(2); qc.ch(0, 1); cases["ch"] = (qc, (1, 2, 0))
    qc = QuantumCircuit(2); qc.crz(th, 0, 1); cases["crz"] = (qc, (2, 0, 2))
    qc = QuantumCircuit(2); qc.crx(th, 0, 1); cases["crx"] = (qc, (2, 0, 2))
    qc = QuantumCircuit(2); qc.cp(th, 0, 1); cases["cp"] = (qc, (2, 0, 3))
    qc = QuantumCircuit(2); qc.cz(0, 1); cases["cz"] = (qc, (1, 0, 0))
    qc = QuantumCircuit(1); qc.p(th, 0); cases["p"] = (qc, (0, 0, 1))
    qc = QuantumCircuit(1); qc.p(np.pi / 4, 0); cases["p(pi/4)"] = (qc, (0, 1, 0))
    qc = QuantumCircuit(1); qc.rz(np.pi / 2, 0); cases["rz(pi/2)"] = (qc, (0, 0, 0))
    for name, (qc, expect) in cases.items():
        m = lm(qc)
        assert (m["cx"], m["t_fixed"], m["n_rot"]) == expect, (name, m)
        assert set(lower(qc).count_ops()) <= set(LOGICAL_BASIS)
    m = lm(cases["ccx"][0])
    assert m["qubits"] == 3 and m["depth"] >= 7
    qc = QuantumCircuit(4); qc.append(MCXGate(3), [0, 1, 2, 3])
    with pytest.raises(Exception):
        lower(qc)


@pytest.mark.parametrize("eps", [1e-4, 1e-6, 1e-8])
def test_M0_M2_pygridsynth_band(eps):
    """pygridsynth T-count per rotation within the Ross-Selinger band [3log2(1/eps)-4, 3log2(1/eps)+3log2log2(1/eps)+10]
    for 5 angles; word error <= eps (operator norm after one global phase); the word reproduces rz(theta)."""
    tcount = api("su2plaq.metrics.cliffordt:pygridsynth_tcount")
    word_fn = api("su2plaq.metrics.cliffordt:pygridsynth_word")
    word_error = api("su2plaq.metrics.cliffordt:word_error")
    lo, hi = ross_selinger_band(eps)
    for th in (0.37, 0.61, -0.555, 1.7, -0.2775):
        w = word_fn(th, eps)
        T = tcount(th, eps)
        assert set(w) <= set("HSTXW") and w.count("T") == T
        assert lo <= T <= hi, (th, eps, T, lo, hi)
        assert word_error(w, th) <= eps
    # multiples of pi/4 need no synthesis: T-count of the exact word is 0 or 1
    assert tcount(np.pi / 2, eps) == 0 and tcount(np.pi / 4, eps) == 1


def test_M0_M3_qiskit_ct_pm():
    """Qiskit's Clifford+T pass manager with Paulo's settings on rz(theta): T within +-6 of pygridsynth; deterministic
    under the seed (identical count_ops in two runs); output uses only {cx,h,s,sdg,t,tdg}."""
    ct_compile = api("su2plaq.metrics.cliffordt:ct_compile")
    tcount = api("su2plaq.metrics.cliffordt:pygridsynth_tcount")
    for eps in (1e-6, 1e-10):
        for th in (0.37, 0.61, -0.555):
            qc = QuantumCircuit(1)
            qc.rz(th, 0)
            out1, m1 = ct_compile(qc, eps)
            out2, m2 = ct_compile(qc, eps)
            assert dict(out1.count_ops()) == dict(out2.count_ops()) and m1 == m2
            assert set(out1.count_ops()) <= {"cx", "h", "s", "sdg", "t", "tdg"}
            assert abs(m1["t"] - tcount(th, eps)) <= 6
            assert m1["cx"] == 0 and m1["qubits"] == 1
    t_est = api("su2plaq.metrics.cliffordt:t_estimate")
    assert abs(t_est(10, 296, 1e-6) - (296 + 10 * 3 * np.log2(1e6))) <= 1e-9
