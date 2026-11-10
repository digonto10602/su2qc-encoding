"""Step 6.2 unit tests: the rishon evaluator (trial mode on the U_E circuit, verdict conversion, contract failures, worker usage,
synthesised re-verification).  Full-mode / cache behaviour is covered by the acceptance tests M6-E3 / E4."""
import functools
import time

import numpy as np
import pytest
from qiskit import QuantumCircuit, QuantumRegister

from su2plaq.circuits import rishon as C
from su2plaq.evaluate.evaluator import Verdict
from su2plaq.rishon.compress import baselines as BL
from su2plaq.rishon.compress import evaluate as EV
from su2plaq.rishon.compress import spec as S


@functools.lru_cache(maxsize=None)
def _ue():
    return S.rishon_spec("UE"), C.build_UE(0.37, with_outer=True)


def test_trial_states_seeded_sorted_and_distinct():
    sp, _ = _ue()
    st = EV.trial_states(sp)
    assert st.shape == (64,) and len(set(st.tolist())) == 64 and (np.diff(st) > 0).all() and 0 <= st.min() and st.max() < 1296
    assert np.array_equal(st, EV.trial_states(sp))
    assert not np.array_equal(st, EV.trial_states(S.rishon_spec("UE").__class__(**{**sp.to_dict(), "trial_seed": 1})))


def test_trial_valid_verdict_fields():
    sp, qc = _ue()
    r = EV.evaluate_circuit(qc, sp, "trial")
    v = r.verdict
    assert r.valid and r.mode == "trial" and isinstance(v, Verdict) and v.method == "rishon_inner_block" and v.certified
    assert v.n_inputs == 64 and v.outer_bits_read == 0 and v.extra["rishon"] is True and v.extra["gauss_states"] == 0
    assert r.metrics["measured"] is False and r.metrics["qubits"] == 48 and r.spec_sha256 == sp.sha256() and not r.verdicts_alt


def test_full_mode_gauss_sample_fields():
    sp, qc = _ue()
    r = EV.evaluate_circuit(qc, sp, "full")
    v = r.verdict
    assert r.valid and v.n_inputs == 1296 and v.extra["gauss_states"] == 273 and v.gauss_residual <= 1e-10 and v.extra["inner_method"]
    assert r.metrics["measured"] is True


def test_rejections_reasons():
    sp, qc = _ue()
    o = qc.copy(); o.cz(16, 0)
    r = EV.evaluate_circuit(o, sp, "trial")
    assert (r.valid, r.reason, r.verdict.outer_bits_read) == (False, "outer_read_unsupported", 1) and r.verdict.n_blocks == 0
    w = qc.copy(); w.x(40)
    assert EV.evaluate_circuit(w, sp, "trial").reason == "writes_outer"
    d = qc.copy(); d.unitary(np.eye(2), [0])
    assert not EV.evaluate_circuit(d, sp, "trial").valid
    big = QuantumCircuit(QuantumRegister(16, "d"), QuantumRegister(32, "o"), QuantumRegister(33, "anc"))
    assert EV.evaluate_circuit(big, sp, "trial").reason == "max_qubits"
    with pytest.raises(ValueError):
        EV.evaluate_circuit(qc, sp, "nope")
    r = EV.evaluate_circuit(qc, S.rishon_spec("UB"), "trial")          # the wrong operator
    assert not r.valid and r.verdict.op_norm_error > 0.1


def test_program_contract_failure_needs_no_subprocess(tmp_path):
    sp, _ = _ue()
    bad = tmp_path / "bad.py"
    bad.write_text('"""SUMMARY: imports os."""\nimport os\nFAMILY = "x"\nPARENT = None\n\ndef build(spec):\n    return None\n')
    r = EV.evaluate_program(bad, sp, "trial")
    assert not r.valid and r.reason == "contract" and "os" in r.message
    nob = tmp_path / "nobuild.py"
    nob.write_text('"""SUMMARY: no build."""\nFAMILY = "x"\nPARENT = None\n')
    assert EV.evaluate_program(nob, sp, "trial").reason == "contract"
    bad_open = tmp_path / "bo.py"
    bad_open.write_text('"""SUMMARY: open."""\nFAMILY = "x"\nPARENT = None\n\ndef build(spec):\n    open("f", "w")\n')
    assert EV.evaluate_program(bad_open, sp, "trial").reason == "contract"


def test_program_trial_end_to_end_and_worker_registration(tmp_path):
    """The seed program built in the subprocess worker (registers "rishon" there) equals the in-process circuit."""
    sp, qc = _ue()
    path = BL.general_program_path(sp)
    t0 = time.time()
    r = EV.evaluate_program(path, sp, "trial")
    assert r.valid and r.reason == "ok" and r.program_sha256 and r.summary.startswith("the reference circuit") and time.time() - t0 < 120
    assert r.metrics["cx"] == 8 and r.metrics["qubits"] == 48
    # a program that runs arbitrary rishon emission-time code through get_encoding, in the sandboxed worker
    prog = tmp_path / "p.py"
    prog.write_text('"""SUMMARY: reads the registered view.\n\nDISCOVERY: the view is registered in the worker."""\nFAMILY = "t"\nPARENT = None\n\n'
                    'from su2plaq.compress.builder import Builder\nfrom su2plaq.compress.spec import get_encoding\n\n\n'
                    'def build(spec):\n    b = Builder(spec)\n    enc = get_encoding("rishon")\n    assert len(enc.bright_pairs()) == 81\n'
                    '    for l in range(4):\n        b.cx(4 * l, 4 * l + 1)\n        b.p(-0.75 * spec.alpha, 4 * l + 1)\n        b.cx(4 * l, 4 * l + 1)\n    return b\n')
    r2 = EV.evaluate_program(prog, sp, "trial")
    assert r2.valid and r2.discoveries == ["DISCOVERY: the view is registered in the worker."]


def test_worker_usage_error():
    with pytest.raises(SystemExit):
        EV.main([])
    with pytest.raises(SystemExit):
        EV.main(["--worker", "only-one"])


def test_verify_synthesised_on_ue():
    sp, qc = _ue()
    sv = EV.verify_synthesised(qc, sp, eps=1e-3)
    assert sv["ok"] and sv["n_rot"] == 4 and sv["tolerances"]["tol_err"] == pytest.approx(4e-3 + 1e-9)
    assert sv["verdict"].op_norm_error <= sv["tolerances"]["tol_err"] and sv["verdict"].method == "rishon_inner_block" and sv["t_total"] > 0
