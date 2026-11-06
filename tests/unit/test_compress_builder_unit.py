"""Unit tests for su2plaq.compress.builder (M2 step 2.2)."""
import numpy as np
import pytest
from qiskit import QuantumCircuit
from qiskit.circuit import Gate
from qiskit.circuit.library import MCXGate
from qiskit.quantum_info import Operator

from su2plaq.compress import builder as B
from su2plaq.compress.spec import default_spec

SPEC = default_spec()


def test_alloc_reuses_freed_indices_and_tracks_peak():
    b = B.Builder(SPEC)
    a = b.alloc(3, "w")
    assert a == [28, 29, 30] and b.peak_qubits == 31
    b.free([29])
    assert b.alloc(1) == [29] and b.peak_qubits == 31
    b.free([28, 30])
    assert b.alloc(2) == [28, 30]                 # lowest freed first (29 stays allocated)
    b.free(a)
    with pytest.raises(B.BuilderError):
        b.free([5])                               # a fixed qubit is not an ancilla
    with pytest.raises(B.BuilderError):
        b.alloc(0)
    qc = b.circuit()
    assert qc.num_qubits == 31 and [r.name for r in qc.qregs] == ["d", "o", "anc"]


def test_gate_validation():
    b = B.Builder(SPEC)
    for bad in (lambda: b.x(99), lambda: b.cx(0, 0), lambda: b.rz(float("nan"), 0), lambda: b.rz(True, 0), lambda: b.h(-1),
                lambda: b.ccx(0, 1, 28), lambda: b.cx(0, 1.5)):
        with pytest.raises(B.BuilderError):
            bad()
    b.rz(np.float64(0.3), np.int64(2))            # numpy scalars are accepted
    q = b.alloc(1)[0]
    b.free(q)
    with pytest.raises(B.BuilderError):
        b.x(q)                                    # freed ancilla cannot be used
    assert b.n_gates == 1
    with pytest.raises(B.BuilderError):
        B.Builder()
    with pytest.raises(B.BuilderError):
        B.Builder(n_qubits=3).reg("d")
    assert B.Builder(SPEC).reg("d") == list(range(12))


@pytest.mark.parametrize("k", [0, 1, 2, 3, 4, 5])
def test_mcx_is_an_exact_toffoli_with_clean_ancillas(k):
    b = B.Builder(n_qubits=k + 1)
    b.mcx(list(range(k)), k)
    qc = b.circuit()
    n = qc.num_qubits
    assert n == k + 1 + max(0, k - 2) and b.peak_qubits == n
    ref = QuantumCircuit(k + 1)
    ref.append(MCXGate(k), range(k + 1)) if k else ref.x(0)
    U, R = Operator(qc).data, Operator(ref).data
    idx = [i for i in range(2 ** n) if i >> (k + 1) == 0]       # ancillas (above the fixed qubits) in |0>
    assert np.abs(U[np.ix_(idx, idx)] - R).max() < 1e-12
    other = [i for i in range(2 ** n) if i >> (k + 1) != 0]
    assert not other or np.abs(U[np.ix_(other, idx)]).max() < 1e-12
    assert {i.operation.name for i in qc.data} <= B.BASIS | B.MACROS


def test_append_qiskit_is_all_or_nothing_and_uses_class_identity():
    b = B.Builder(SPEC)
    good = QuantumCircuit(3, global_phase=0.25)
    good.ccx(0, 1, 2)
    good.rz(0.3, 2)
    good.barrier()
    b.append_qiskit(good, [3, 4, 5])
    assert b.n_gates == 2 and abs(b.circuit().global_phase - 0.25) < 1e-15
    disguised_inner = QuantumCircuit(3, name="ccx")        # custom gate named like an allowed macro
    disguised_inner.cz(0, 1)
    for bad in (_circ_with(disguised_inner.to_gate(), 3), _circ_with(Gate("h", 1, []), 1), _circ_with(MCXGate(3), 4)):
        before = b.n_gates
        with pytest.raises(B.BuilderError):
            b.append_qiskit(bad, list(range(bad.num_qubits)))
        assert b.n_gates == before
    mixed = QuantumCircuit(2)
    mixed.h(0)
    mixed.cx(0, 1)
    mixed.sx(0)                                             # not allowed: nothing of `mixed` may be appended
    with pytest.raises(B.BuilderError):
        b.append_qiskit(mixed, [0, 1])
    assert b.n_gates == 2
    with pytest.raises(B.BuilderError):
        b.append_qiskit(good, [0, 1])                       # wrong map length
    with pytest.raises(B.BuilderError):
        b.append_qiskit(good, [3, 4, 99])                   # unallocated qubit


def _circ_with(gate, n):
    qc = QuantumCircuit(n)
    qc.append(gate, list(range(n)))
    return qc


def test_discoveries_limit():
    b = B.Builder(n_qubits=1)
    for i in range(3):
        b.discover(f"DISCOVERY: {i}")
    with pytest.raises(B.BuilderError):
        b.discover("one too many")
    assert b.circuit().metadata["discoveries"] == b.discoveries and len(b.discoveries) == 3


GOOD = '''"""SUMMARY: a test program.

DISCOVERY: first idea
DISCOVERY: second idea
"""
FAMILY = "F1"
PARENT = None


def build(spec):
    return None
'''


def test_program_header_contract(tmp_path):
    h = B.parse_program_header(GOOD)
    assert h == {"summary": "a test program.", "discoveries": ["DISCOVERY: first idea", "DISCOVERY: second idea"],
                 "family": "F1", "parent": None}
    assert B.parse_program_header(GOOD.replace("PARENT = None", 'PARENT = "r0-seed-000"'))["parent"] == "r0-seed-000"
    for bad in (GOOD.replace("SUMMARY: a test program.", "just text"), GOOD.replace('FAMILY = "F1"\n', ""),
                GOOD.replace("PARENT = None\n", ""), GOOD.replace("def build(spec)", "def make(spec)"),
                GOOD.replace('"""\nFAMILY', 'DISCOVERY: third\nDISCOVERY: fourth\n"""\nFAMILY'), "def (:"):
        with pytest.raises(B.BuilderError):
            B.parse_program_header(bad)
    p = tmp_path / "001-x.py"
    p.write_text(GOOD)
    h1 = B.program_sha256(p)
    assert len(h1) == 64 and B.program_sha256(p) == h1
    p.write_text(GOOD + "\n# edit\n")
    assert B.program_sha256(p) != h1


def test_rendered_spec_states_the_synthesised_rule_and_prune_cap():
    from su2plaq.evaluate.evaluator import PRUNE_FRACTION

    t = SPEC.render()
    assert "N_{\\rm rot}\\varepsilon+1e-09" in t and f"{PRUNE_FRACTION:g} times the error tolerance" in t and "pruning_bound" in t


def test_numpy_scalars_are_accepted_for_angles_and_qubits():
    b = B.Builder(n_qubits=3)
    b.rz(np.float32(0.25), np.int64(1))
    b.p(np.float16(0.5), np.int32(2))
    b.crx(np.int64(1), np.int64(0), np.int8(2))
    assert b.n_gates == 3
    with pytest.raises(B.BuilderError):
        b.rz(np.bool_(True), 0) if False else b.rz(True, 0)
