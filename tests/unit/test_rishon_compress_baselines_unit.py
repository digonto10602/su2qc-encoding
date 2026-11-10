"""Step 6.3 unit tests: rishon seed circuits, ladder programs, windowed Qiskit L3, polish, import reasons (prompts/203 section 3.1)."""
import functools

import numpy as np
import pytest
from qiskit import QuantumCircuit

from su2plaq.compress import baselines as LB
from su2plaq.compress import evaluate as LE
from su2plaq.compress.metrics import key, metrics
from su2plaq.lean.rules import LEAN_RULES
from su2plaq.rishon.compress import baselines as BL
from su2plaq.rishon.compress import evaluate as EV
from su2plaq.rishon.compress import spec as S


@functools.lru_cache(maxsize=None)
def _sp(kind):
    return S.rishon_spec(kind)


def test_general_circuit_per_kind_and_ladder():
    ue, ub = BL.general_circuit(_sp("UE")), BL.general_circuit(_sp("UB"), "rccx")
    assert ue.count_ops().get("cx") == 8 and ue.num_qubits == 48
    assert ub.count_ops().get("rccx") == 1620 and ub.count_ops().get("ccx") == 54
    assert BL.general_circuit(_sp("UB"), "mcx").count_ops().get("rccx") == 1458
    with pytest.raises(ValueError):
        BL.general_circuit(_sp("UE"), "toffoli")
    with pytest.raises(ValueError):
        BL.general_program_path(_sp("UE"), "toffoli")


def test_qiskit_l3_ue_is_exact_and_windowed():
    sp = _sp("UE")
    l3 = BL.qiskit_l3(sp, seed=12345)
    assert EV.evaluate_circuit(l3, sp, mode="trial").valid
    # the same definition as the laptop's window: a window of 1 instruction is the stock level-3 transpile per gate
    assert BL.qiskit_l3(sp, window=1).num_qubits == l3.num_qubits
    whole = BL.qiskit_l3_whole(sp)
    assert isinstance(whole, QuantumCircuit) and set(whole.count_ops()) <= LE.B.BASIS


def test_linear_in_angles_reproduces_and_rejects():
    sp = _sp("UE")
    fn = BL.linear_in_angles(BL.qiskit_l3, sp)
    for a, b in [(sp.alpha, sp.beta), (0.91, 0.23), (1.7, 1.0)]:
        want = LB._gate_list(BL.qiskit_l3(sp.with_angles(a, b)))
        got = LB._gate_list(fn(sp.with_angles(a, b)))
        assert [(n, q) for n, _p, q in want] == [(n, q) for n, _p, q in got]
        assert np.allclose([p[0] for _n, p, _q in want if p], [p[0] for _n, p, _q in got if p], atol=1e-10)
    qc = QuantumCircuit(1)
    qc.rz(0.3, 0)                                   # constant angle: not linear homogeneous
    with pytest.raises(ValueError):
        BL.linear_in_angles(lambda s: qc, sp)
    with pytest.raises(ValueError):                 # skeleton depends on the angle
        BL.linear_in_angles(lambda s: _skel(s), sp)


def _skel(s):
    qc = QuantumCircuit(1)
    qc.rz(s.alpha, 0)
    if s.alpha > 0.5:
        qc.x(0)
    return qc


def test_polish_cancels_and_stays_exact():
    sp = _sp("UE")
    qc = BL.general_circuit(sp)
    padded = QuantumCircuit(*qc.qregs, global_phase=qc.global_phase)
    padded.x(3), padded.x(3), padded.rz(0.1, 5), padded.rz(-0.1, 5)       # identity padding on idle qubits
    padded.compose(qc, inplace=True)
    out, log = BL.polish(padded, sp)
    assert out is not padded and key(metrics(out, sp, measured=False)) < key(metrics(padded, sp, measured=False))
    assert len(out.data) == len(qc.data) + 1 and out.count_ops().get("x", 0) == 0      # x x cancelled; rz(0.1) rz(-0.1) merged (an angle is never tested for zero)
    assert EV.evaluate_circuit(out, sp, mode="trial").valid
    assert all(ln.split(":")[0] in LEAN_RULES for ln in log) and any("accepted" in ln for ln in log)
    same, log2 = BL.polish(qc, sp)
    assert same is qc and any("nothing to do" in ln for ln in log2)
    bad = QuantumCircuit(*qc.qregs)
    bad.append(__import__("qiskit.circuit.library", fromlist=["SXGate"]).SXGate(), [0])
    assert BL.polish(bad, sp)[0] is bad
    assert BL.general_polished(sp)[0].count_ops() == qc.count_ops()


def test_import_seed_reasons():
    sp = _sp("step")
    for s in ("paulo34", "lean22", "lean22_v2", "spinnet15"):
        r = BL.import_seed(sp, s)
        assert isinstance(r, str) and "rishon" in r
    with pytest.raises(ValueError):
        BL.import_seed(sp, "nope")


def test_ladder_program_paths_numbering():
    sp = _sp("step")
    names = [BL.general_program_path(sp, l).name for l in BL.LADDERS]
    assert names == ["000-general.py", "001-general-rccx.py", "002-general-mcx.py"]
    assert BL.general_program_path(_sp("UE")).name == "000-general-ue.py"
