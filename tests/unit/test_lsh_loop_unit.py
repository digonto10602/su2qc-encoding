"""Unit tests of su2plaq.lsh.loop phase 0 (prompts/401 steps 8.0, 8.1) and su2plaq.lsh.rs_split (step 8.U).
The registry-dependent hooks are stubs until step 8.R; they must say so (NotImplementedError), not return garbage."""
import json
import pathlib
import shutil

import numpy as np
import pytest
from qiskit import QuantumCircuit, QuantumRegister

from su2plaq.lsh import loop as L
from su2plaq.lsh import rs_split as RS
from su2plaq.metrics.logical import logical_metrics

ROOT = pathlib.Path(__file__).resolve().parents[2]


def test_constants():
    assert L.SEED_LABELS == ("general", "wrap_pairs9", "wrap_flags4", "wrap_flags5", "wrap_flags6", "wrap_sn_headline",
                             "wrap_sn_r05F3", "wrap_sn_r02F5", "general+polish", "qiskit_l3")
    assert [f for _, f in L.SEED_FILES][:3] == ["000-general.py", "001-wrap_pairs9.py", "002-wrap_flags4.py"]
    assert len(L.LSH_EVALUATOR_FILES) == 6 and all((ROOT / "src" / "su2plaq" / f).exists() for f in L.LSH_EVALUATOR_FILES)
    assert (L.STOP_MAX_ROUNDS, L.STOP_NO_GAIN_ROUNDS, L.STOP_MAX_SESSIONS, L.N_ANGLE_PAIRS) == (8, 3, 20, 20)
    assert set(L.WRAP_SOURCES) == {"wrap_sn_headline", "wrap_sn_r05F3", "wrap_sn_r02F5"}
    assert "native" in L.BRIEF_NOTE and L.brief_note("lsh", "step") == L.BRIEF_NOTE


def test_stubs_are_pending():
    for fn, args in ((L.spec, ()), (L.general_circuit, (None,)), (L.seed_candidates, (None, None)), (L.stop_state, ()),
                     (L.main, ()), (L.certify_headline, ())):
        with pytest.raises(NotImplementedError, match="prompts/401"):
            fn(*args)


def test_wrap_spinnet_step_registers_and_refusals():
    sn = QuantumCircuit(QuantumRegister(8, "d"), QuantumRegister(1, "a"))
    sn.ccx(0, 1, 8)
    qc = L.wrap_spinnet_step(sn)
    assert [r.name for r in qc.qregs] == ["d", "o", "a"] and [r.size for r in qc.qregs] == [12, 12, 1]
    lm = logical_metrics(L.wrap_spinnet_step(QuantumCircuit(QuantumRegister(8, "d"))))
    assert (lm["cx"], lm["t_fixed"]) == (40, 32)                            # the transcoder pair alone (M7-V1)
    with_o = QuantumCircuit(QuantumRegister(8, "d"), QuantumRegister(8, "o"))
    with_o.cx(0, 1)
    assert L.wrap_spinnet_step(with_o).num_qubits == 24                      # untouched outer register is dropped onto o[12]
    with_o.cx(8, 1)
    with pytest.raises(ValueError):
        L.wrap_spinnet_step(with_o)
    with pytest.raises(ValueError):
        L.wrap_spinnet_step(QuantumCircuit(QuantumRegister(7, "d")))
    with pytest.raises(ValueError):
        L.wrap_spinnet_step(QuantumCircuit(QuantumRegister(8, "x")))


@pytest.mark.parametrize("label,cx", [("general", 94), ("wrap_flags4", 84), ("wrap_sn_headline", 71)])
def test_seed_circuit_counts(label, cx):
    qc = L.seed_circuit(label, 0.37, 0.61)
    assert [r.name for r in qc.qregs][:2] == ["d", "o"] and logical_metrics(qc)["cx"] == cx


def test_seed_circuit_errors_and_pin(tmp_path):
    for bad in ("nope", "general+polish", "qiskit_l3"):
        with pytest.raises(ValueError):
            L.seed_circuit(bad, 0.37, 0.61)
    rel = pathlib.Path(L.WRAP_SOURCES["wrap_sn_headline"][0])
    (tmp_path / rel).parent.mkdir(parents=True)
    shutil.copy(ROOT / rel, tmp_path / rel)
    assert L.seed_circuit("wrap_sn_headline", 0.37, 0.61, root=tmp_path).num_qubits == 25      # intact copy: the pin accepts it
    with open(tmp_path / rel, "a") as fh:
        fh.write("\n# edited\n")
    with pytest.raises(ValueError, match="pinned"):
        L.seed_circuit("wrap_sn_headline", 0.37, 0.61, root=tmp_path)


def test_seed_program_source_text(monkeypatch):
    from su2plaq.compress import baselines
    from su2plaq.encodings.lsh import LSH

    monkeypatch.setattr(baselines, "get_encoding", lambda name: LSH())          # the registry of step 8.R does this in production
    for label in ("general", "wrap_flags4"):
        text = L.seed_program_source(label)
        compile(text, label, "exec")
        for forbidden in ("su2plaq.circuits", "su2plaq.spinnet", "su2plaq.lsh"):
            assert forbidden not in text
        assert "from su2plaq.compress.builder import Builder" in text and "def build(spec):" in text
    assert "r02-F1-002" in L.seed_program_source("wrap_sn_headline") and L.WRAP_SOURCES["wrap_sn_headline"][1] in L.seed_program_source("wrap_sn_headline")
    with pytest.raises(ValueError):
        L.seed_program_source("qiskit_l3")


def _rec(cx=71, t_sum=22480, rho=0, qubits=25, n_rot=17, t_fixed=48):
    return {"id": "x", "cx": cx, "t_sum": t_sum, "rho": rho, "qubits": qubits, "n_rot": n_rot, "t_fixed": t_fixed}


def test_improves_rule():
    old = _rec()
    assert L.improves(old, None) and not L.improves(None, old) and not L.improves(_rec(), old)
    assert L.improves(_rec(cx=70, t_sum=99999), old) and not L.improves(_rec(cx=72, t_sum=1), old)
    band = 20 * 17
    assert not L.improves(_rec(t_sum=22480 - band), old) and L.improves(_rec(t_sum=22480 - band - 1), old)
    assert L.improves(_rec(t_sum=22480 + 5, rho=0), _rec(rho=1)) and L.improves(_rec(t_sum=22480 + 5, qubits=24), old)
    assert L.improves(_rec(n_rot=16, t_sum=22480 - 100), old) and not L.improves(_rec(n_rot=16, t_sum=22480 + 100), old)
    assert L.stop_key(old) == (71, 22480, 0, 25)


def test_structure_facts_read_from_lean_and_file_is_current(tmp_path):
    facts = L.structure_facts()
    by = {f["name"]: f for f in facts["facts"]}
    assert by["card_inner_codes"]["value"] == 47 and by["coupling_by_y_weight"]["value"] == {"0": -4, "1": 2, "2": -1}
    assert by["transcoder_overhead"]["proved_by"] == "numerical" and by["eight_differences"]["proved_by"] == "decide"
    p = pathlib.Path(L.write_structure(path=tmp_path / "s.json"))
    assert json.loads(p.read_text())["facts"] == json.loads(json.dumps(facts["facts"]))
    mtime = p.stat().st_mtime_ns
    L.write_structure(path=p)
    assert p.stat().st_mtime_ns == mtime                                      # unchanged content: not rewritten
    committed = ROOT / "compress" / "specs" / "lsh-structure.json"
    assert committed.exists() and json.loads(committed.read_text()) == json.loads(p.read_text())


def test_structure_facts_refuse_changed_lean_source(tmp_path):
    d = tmp_path / "lean" / "Su2Plaq" / "LSH"
    d.mkdir(parents=True)
    for n in ("Counts", "Facts", "Circuit"):
        shutil.copy(ROOT / "lean" / "Su2Plaq" / "LSH" / f"{n}.lean", d / f"{n}.lean")
    assert L.structure_facts(root=tmp_path)["facts"]
    t = (d / "Counts.lean").read_text().replace("innerCodes = 47", "innerCodes = 48")
    (d / "Counts.lean").write_text(t)
    with pytest.raises(RuntimeError, match="card_inner_codes"):
        L.structure_facts(root=tmp_path)
    (d / "Counts.lean").write_text(t.replace("innerCodes = 48", "innerCodes = 47") + "\n-- native_decide\n")
    with pytest.raises(RuntimeError, match="native_decide"):
        L.structure_facts(root=tmp_path)


def test_rs_split_row():
    R = RS.recoupling()
    assert R.shape == (433, 433) and np.abs(R.T @ R - np.eye(433)).max() <= 1e-12
    s = RS.structure()
    assert (s["nnz"], s["max_per_row"], s["sites_touched"], s["qubits_touched"]) == (400, 4, 6, 18)
    assert (s["ours"]["nnz"], s["ours"]["max_per_row"]) == (256, 1) and s["spectrum_diff"] <= 1e-10
