"""M1-P1, M1-P2 — cross-checks against Paulo's circuit files (prompts/002 §4 step 1.6, research 001 §3.6, §6).
Second evaluator engine: qiskit-aer matrix_product_state (truncation threshold 0, Aer's memory estimate overridden
with max_memory_mb, amplitudes by contracting save_matrix_product_state — never save_amplitudes, which returns
zeros with MPS in Aer 0.17.2). Measured by the planner: 625 inputs in 139 s, max bond dimension 16, error 2.9e-6."""
import json

import pytest

import functools

from tests.acceptance._api import api, op_norm_after_phase

META = "refs/paulo/SU2_plaquette_jmax_half_CT_metadata.json"


@functools.lru_cache(maxsize=None)
def _enc():
    return api("su2plaq.encodings.twelve:TwelveQubit")()


@pytest.mark.slow
def test_M1_P1_paulo_qpy_verifies(root):
    """Paulo's compiled 34-qubit Clifford+T circuit (dt = g = 1, i.e. beta = 1, alpha_P = 2) loads with the metadata
    counts (34 qubits, 294 CX, 1162 T) and verifies against target 'UB' at beta = 1 through the evaluator:
    op-norm error <= 2e-5 where op_norm_error = block error + leak amplitude (prompts/004; the leak is no longer a
    separate weight check). Justification: 866 rotation-T at >= 54 T per rotation (3 log2 1e6 - 6) means at most 16
    synthesised rotations, each within 1e-6 -> triangle-inequality bound ||U - U_ex||_2 <= 1.6e-5 on the whole register,
    which bounds block error and leak amplitude jointly (root-sum-square); the sum of the two is <= sqrt(2) x that, i.e.
    <= 2.3e-5 in the worst case, and the aer_mps leak amplitude is a certified upper bound (Cauchy-Schwarz over the <= 16
    inner components of a physical state, reports/research/003 §3) that can exceed the true value by up to 4x. Measured
    (research/003): block error 2.905e-6, leak-amplitude bound 7.85e-6 (per-input weight max 4.1e-12, max_o W_o = 6.2e-11) -> combined 1.08e-5, budget 2e-5. Engine 'auto': the sparse simulator if its amplitude cap is not exceeded (Qiskit's
    level-3 schedule opens up to 21 Hadamards at once, 2^21 amplitudes per input), else aer_mps.
    Gauss tolerance 2e-5 = the error tolerance (prompts/003 §2, Digonto 2026-11-04): the Gauss residual of an output
    is <= ||G^a_c|| ||U - U_exact|| with ||U - U_exact|| <= N_rot eps by the same triangle inequality, so the rounding
    of the synthesised rotations is allowed to show up in the Gauss residual with the same budget (measured 1.2e-10,
    reports/tests/009); exact-angle circuits keep 1e-10. The verdict must be certified (aer_mps accuracy 2e-10 is
    below every tolerance used here)."""
    enc = _enc()
    paulo_circuit = api("su2plaq.circuits.twelve:paulo_circuit")
    evaluate = api("su2plaq.evaluate.evaluator:evaluate")
    meta = json.loads((root / META).read_text())
    qc = paulo_circuit()
    ops = qc.count_ops()
    assert qc.num_qubits == meta["resources"]["num_qubits"] == 34
    assert ops["cx"] == meta["resources"]["CX_count"] == 294
    assert ops.get("t", 0) + ops.get("tdg", 0) == meta["resources"]["T_count"] == 1162
    assert qc.qregs[0].name == "d" and qc.qregs[0].size == 12
    V = enc.target("UB", None, 1.0)
    tol = dict(tol_err=2e-5, tol_gauss=2e-5)  # prompts/004: no tol_leak; the leak amplitude is inside op_norm_error
    v = evaluate(qc, enc, V, engine="auto", **tol)
    assert v.ok, (v.reason, v.op_norm_error, v.block_error, v.leak_amplitude, v.gauss_residual, v.method, v.engine)
    assert v.op_norm_error <= 2e-5 and v.block_error <= 1.6e-5 and v.leak_amplitude <= 2e-5 and v.gauss_residual <= 2e-5
    assert v.max_leak <= v.leak_amplitude ** 2 + 1e-30 and v.dirty_ancilla <= v.max_leak + 1e-30
    assert v.engine in ("sparse", "aer_mps") and v.certified and v.engine_accuracy <= 1e-9
    assert v.tolerances == tol
    # the sign of beta matters: the inverse is not accepted
    v2 = evaluate(qc, enc, V.conj().T, engine=v.engine, **tol)
    assert not v2.ok and v2.op_norm_error > 0.1


def test_M1_P2_port_reproduces_counts(root):
    """The faithful reconstruction of the notebook circuit, paulo_logical(beta = 1) (keeps the notebook's mcrx/crx and
    registers d p e w g tmp h), is exact on the 625 inner codes (1e-10), has logical T_fixed = 296 (56 rccx x 4 +
    8 ccx x 7 + 16 explicit T), 294 CX and 14 rotations after level-0 lowering, and compiled with Paulo's settings
    (Clifford+T PM level 3, eps 1e-6, seed 12345) reproduces his resources within 5 % (T 1162, CX 294, 34 qubits).
    Same Qiskit version/seed/settings: equality expected, 5 % absorbs pass-manager drift."""
    enc = _enc()
    paulo_logical = api("su2plaq.circuits.twelve:paulo_logical")
    ct_compile = api("su2plaq.metrics.cliffordt:ct_compile")
    logical_metrics = api("su2plaq.metrics.logical:logical_metrics")
    run_batch = api("su2plaq.evaluate.sparse_sim:run_batch")
    encoded_block = api("su2plaq.evaluate.sparse_sim:encoded_block")
    inner_target = api("su2plaq.evaluate.evaluator:inner_target")
    meta = json.loads((root / META).read_text())
    qc = paulo_logical(1.0)
    assert qc.num_qubits == 34 and [r.name for r in qc.qregs] == ["d", "p", "e", "w", "g", "tmp", "h"]
    lm = logical_metrics(qc)
    assert lm["t_fixed"] == 296 and lm["cx"] == 294 and lm["n_rot"] == 14
    codes = enc.inner_codes()
    M, leak = encoded_block(run_batch(qc, codes), codes, len(codes), code_mask=(1 << 12) - 1)
    assert leak.max() <= 1e-12 and op_norm_after_phase(M, inner_target(enc, "UB", None, 1.0)) <= 1e-10
    out, m = ct_compile(qc, 1e-6, level=3, seed=12345)
    for key, ref in (("t", meta["resources"]["T_count"]), ("cx", meta["resources"]["CX_count"]), ("qubits", meta["resources"]["num_qubits"])):
        assert abs(m[key] - ref) <= 0.05 * ref, (key, m[key], ref)
