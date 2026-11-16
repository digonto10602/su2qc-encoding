"""Unit tests for the encoding registry and its dispatch in the shared compression code (prompts/008 step B1 + prompts/401 step 8.R).

The tests that register a temporary encoding restore the table afterwards; hooks are plain callables of a throw-away module
(`su2plaq_unit_hooks`) so that no real track module is involved.
"""
import dataclasses
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import types

import pytest
from qiskit import QuantumCircuit

from su2plaq.compress import archive as A
from su2plaq.compress import baselines as BL
from su2plaq.compress import brief as BR
from su2plaq.compress import evaluate as E
from su2plaq.compress import provenance as P
from su2plaq.compress import report as RP
from su2plaq.compress import round as RD
from su2plaq.compress import spec as S
from su2plaq.encodings import base, registry
from su2plaq.encodings.registry import EncodingInfo

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "src" / "su2plaq"
LSH_FILES = ["encodings/lsh.py", "lsh/operators.py", "exact/spinnet.py", "exact/compare.py", "lsh/walk.py", "circuits/lsh.py"]


# ---------------------------------------------------------------------------------------------------- helpers
def _hooks():
    m = types.ModuleType("su2plaq_unit_hooks")
    m.calls = []

    def verdict(qc, spec, mode, budget):
        m.calls.append(("verdict", spec.encoding, mode, budget))
        return "VERDICT"

    def general(spec):
        m.calls.append(("general", spec.encoding))
        return QuantumCircuit(3)

    def seeds(spec, root):
        m.calls.append(("seeds", spec.encoding))
        return [("only", None, lambda s: QuantumCircuit(3))]

    def import_seed(spec, source):
        m.calls.append(("import_seed", source))
        return f"hook:{source}"

    def certify(circ, spec, *, timeout, extra_provenance):
        m.calls.append(("certify", timeout, extra_provenance))
        return {"status": "certified", "from_hook": True}

    def render(spec):
        return f"RENDERED {spec.encoding}/{spec.kind}"

    def note(encoding, kind):
        return f"NOTE for {encoding}/{kind}"

    def warm():
        m.calls.append(("warm",))

    for f in (verdict, general, seeds, import_seed, certify, render, note, warm):
        setattr(m, f.__name__, f)
    sys.modules["su2plaq_unit_hooks"] = m
    return m


@pytest.fixture
def temp_encoding():
    """Register encoding `unit_x` (twelve's object, every hook pointing at `su2plaq_unit_hooks`); restore the table afterwards."""
    m = _hooks()
    saved_table, saved_inst, saved_enc = dict(registry._TABLE), dict(registry._INSTANCES), dict(S._ENCODINGS)

    def make(**kw):
        d = dict(name="unit_x", factory="su2plaq.encodings.twelve:TwelveQubit")
        d.update(kw)
        info = EncodingInfo(**d)
        registry.register(info, replace=True)
        return info

    yield make, m
    registry._TABLE.clear()
    registry._TABLE.update(saved_table)
    registry._INSTANCES.clear()
    registry._INSTANCES.update(saved_inst)
    S._ENCODINGS.clear()
    S._ENCODINGS.update(saved_enc)
    sys.modules.pop("su2plaq_unit_hooks", None)


def _fresh(code: str) -> dict:
    env = {k: v for k, v in os.environ.items() if not k.startswith("SU2PLAQ_")}
    env.update({"PYTHONPATH": str(ROOT / "src"), "PYTHONHASHSEED": "0"})
    p = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=300, env=env, cwd=str(ROOT))
    assert p.returncode == 0, p.stderr[-2000:]
    return json.loads(p.stdout.strip().splitlines()[-1])


# ---------------------------------------------------------------------------------------------------- registry
def test_table_content_and_lookups():
    assert registry.names()[:3] == ("twelve", "spinnet", "lsh")
    tw = registry.info("twelve")
    assert tw.name == "twelve" and tw.stamp == "shared" and tw.gauss_in_loop and tw.evaluator_files == ()
    assert tw.kinds == ("step", "UB", "UE") and tw.loop_kind == "step" and tw.prune_fraction is None and tw.verdict is None
    assert registry.lookup("twelve") is tw and registry.lookup("no_such") is None
    with pytest.raises(ValueError, match=r"unknown encoding 'no_such'.*twelve"):
        registry.info("no_such")
    with pytest.raises(ValueError, match="twelve"):
        registry.get("no_such")


def test_resolve_and_get_cache():
    assert registry.resolve("os.path:join") is os.path.join
    assert registry.resolve("collections:OrderedDict.fromkeys") is not None          # dotted attribute
    for bad in ("nocolon", ":x", "x:"):
        with pytest.raises(ValueError):
            registry.resolve(bad)
    a = registry.get("twelve")
    assert a is registry.get("twelve") and a.name == "twelve" and S.get_encoding("twelve") is a


def test_get_encoding_prefers_hand_inserted_object(temp_encoding):
    sentinel = object()
    S._ENCODINGS["twelve"] = sentinel
    try:
        assert S.get_encoding("twelve") is sentinel
    finally:
        del S._ENCODINGS["twelve"]
    assert S.get_encoding("twelve") is registry.get("twelve")


def test_register_rules(temp_encoding):
    make, _ = temp_encoding
    info = make()
    assert registry.info("unit_x") is info and "unit_x" in registry.names()
    with pytest.raises(ValueError, match="already registered"):
        registry.register(info)
    with pytest.raises(TypeError):
        registry.register("unit_x")
    first = registry.get("unit_x")
    registry.register(dataclasses.replace(info, kinds=("step",)), replace=True)
    assert registry.info("unit_x").kinds == ("step",) and registry.get("unit_x") is not first      # cached instance dropped
    with pytest.raises(dataclasses.FrozenInstanceError):
        info.stamp = "encoding"


def test_importing_registry_imports_no_other_project_module():
    d = _fresh("import sys, json\nfrom su2plaq.encodings import registry\nregistry.names(); registry.info('lsh'); registry.lookup('lsh')\n"
               "print(json.dumps(sorted(m for m in sys.modules if m.startswith('su2plaq'))))")
    assert d == ["su2plaq", "su2plaq.encodings", "su2plaq.encodings.registry"]


# ---------------------------------------------------------------------------------------------------- the lsh entry (prompts/401 §1.4)
def test_lsh_entry_is_pure_data_and_lazy():
    info = registry.info("lsh")
    assert info.factory == "su2plaq.encodings.lsh:LSH" and info.stamp == "encoding" and info.gauss_in_loop is True
    assert info.kinds == ("step", "UB", "UE") and info.loop_kind == "step"
    assert list(info.evaluator_files) == LSH_FILES and all((SRC / f).is_file() for f in LSH_FILES)
    assert info.prune_fraction is None and info.verdict is None and info.worker_warmup is None
    assert info.headline is None and info.tools is None and info.structure_json == "compress/specs/lsh-structure.json"
    for field in ("general_circuit", "seed_candidates", "import_seed", "lean_certify", "render_spec", "brief_note", "angle_linear"):
        assert getattr(info, field).startswith("su2plaq.lsh.loop:"), field
    # every registered name has its literal nominal pair (a process that also imported a track shim has further keys until B3-B5)
    assert base.NOMINAL_ANGLES["lsh"] == (0.37, 0.61) and set(registry.names()) <= set(base.NOMINAL_ANGLES)
    assert all(base.NOMINAL_ANGLES[n] == (0.37, 0.61) for n in registry.names())


def test_lsh_lookups_import_neither_hooks_nor_encoding():
    code = ("import sys, json\nfrom su2plaq.encodings import registry, base\nfrom su2plaq.compress import provenance as P, spec as S\n"
            "registry.info('lsh'); P.code_hash_for('lsh'); P.stamp_hash('lsh'); sp = S.default_spec('lsh', 'step'); sp.sha256()\n"
            "before = {'hooks': 'su2plaq.lsh.loop' in sys.modules, 'encoding': 'su2plaq.encodings.lsh' in sys.modules}\n"
            "enc = S.get_encoding('lsh')\n"
            "print(json.dumps({'before': before, 'after_loop': 'su2plaq.lsh.loop' in sys.modules, 'name': enc.name, 'n': [enc.n_data, enc.n_outer]}))")
    d = _fresh(code)
    assert d["before"] == {"hooks": False, "encoding": False}                  # nothing imported by the table or the hashes
    assert d["after_loop"] is False and d["name"] == "lsh" and d["n"] == [12, 12]


def test_lsh_hooks_resolve_to_callables():
    info = registry.info("lsh")
    for field in ("general_circuit", "seed_candidates", "import_seed", "lean_certify", "render_spec", "brief_note", "angle_linear"):
        assert callable(registry.resolve(getattr(info, field))), field
    assert "lsh" in registry.resolve(info.brief_note)("lsh", "step").lower()


def test_lsh_hash_and_not_in_shared_list():
    shared = [SRC / f for f in P.EVALUATOR_FILES if (SRC / f).exists()]
    assert P.evaluator_files("lsh") == shared + [SRC / f for f in LSH_FILES]
    assert not any(f in P.EVALUATOR_FILES for f in LSH_FILES)                      # an LSH edit must not stale the other archives
    h = P.code_hash_for("lsh")
    assert len(h) == 64 and h == P.code_hash(files=P.evaluator_files("lsh")) and P.stamp_hash("lsh") == h != P.code_hash()


# ---------------------------------------------------------------------------------------------------- provenance
def test_shared_list_contains_registry_and_hash_formula():
    assert "encodings/registry.py" in P.EVALUATOR_FILES and (SRC / "encodings" / "registry.py").is_file()
    h = hashlib.sha256()
    for f in P.EVALUATOR_FILES:                                                    # the documented formula, written out
        p = SRC / f
        if p.exists():
            h.update(p.name.encode() + b"\0" + p.read_bytes() + b"\0")
    assert P.code_hash() == h.hexdigest()


def test_twelve_and_unregistered_hashes_equal_the_shared_one():
    shared = [SRC / f for f in P.EVALUATOR_FILES if (SRC / f).exists()]
    assert P.evaluator_files("twelve") == shared == P.evaluator_files(None) == P.evaluator_files("not_registered")
    assert P.code_hash_for("twelve") == P.code_hash() == P.code_hash_for("not_registered") == P.code_hash_for()
    assert P.stamp_hash("twelve") == P.stamp_hash("not_registered") == P.stamp_hash() == P.code_hash()


def test_per_encoding_files_and_stamp(temp_encoding):
    make, _ = temp_encoding
    make(evaluator_files=("compress/spec.py",), stamp="shared")
    files = P.evaluator_files("unit_x")
    assert files[-1] == SRC / "compress" / "spec.py" and len(files) == len(P.evaluator_files("twelve")) + 1
    assert P.code_hash_for("unit_x") != P.code_hash() and P.stamp_hash("unit_x") == P.code_hash()        # stamp "shared"
    make(evaluator_files=("compress/spec.py",), stamp="encoding")
    assert P.stamp_hash("unit_x") == P.code_hash_for("unit_x")
    make(evaluator_files=("compress/spec.py", "encodings/base.py"))
    assert P.code_hash_for("unit_x") != files and P.code_hash_for("unit_x") != P.code_hash()


def test_missing_own_file_is_an_error(temp_encoding):
    make, _ = temp_encoding
    make(evaluator_files=("no/such_file.py",))
    with pytest.raises(FileNotFoundError, match="no/such_file.py"):
        P.evaluator_files("unit_x")
    with pytest.raises(FileNotFoundError):
        P.code_hash_for("unit_x")


# ---------------------------------------------------------------------------------------------------- spec dispatch
def test_default_render_is_unchanged_for_twelve(tmp_path):
    sp = S.default_spec("twelve", "step")
    assert sp.render() == sp._render_default()
    text = sp.render()
    assert "`python -m su2plaq.compress.run_candidate <program.py> --encoding twelve --kind step --trial`" in text
    assert "`python -m su2plaq.compress.oracle --encoding twelve --kind step [--column j]" in text
    assert "## Proved structure (Lean)" in text and sp.peak_qubit_cap() == 12 + 16 + 32


def test_render_spec_tools_structure_and_cap_hooks(temp_encoding):
    make, m = temp_encoding
    make(render_spec="su2plaq_unit_hooks:render")
    sp = S.TaskSpec(encoding="unit_x", kind="UB", alpha=0.37, beta=0.61)
    assert sp.render() == "RENDERED unit_x/UB"
    make(tools=("python cand.py", "python orc.py"), structure_json="compress/specs/does-not-exist.json")
    text = sp.render()
    assert "`python cand.py <program.py> --encoding unit_x --kind UB --trial`" in text and "`python orc.py --encoding unit_x" in text
    assert "pending: `compress/specs/does-not-exist.json` has not been generated yet." in text
    make()
    assert sp.peak_qubit_cap() == 12 + 16 + 32 and dataclasses.replace(sp, max_qubits=7).peak_qubit_cap() == 7


def test_peak_qubit_cap_uses_encoding_method(temp_encoding):
    class Enc:
        n_data, n_outer = 1, 1

        def peak_qubit_cap(self, spec):
            return 41

    S._ENCODINGS["unit_cap"] = Enc()
    try:
        sp = S.TaskSpec(encoding="unit_cap", kind="step", alpha=0.1, beta=0.2)
        assert sp.peak_qubit_cap() == 41 and dataclasses.replace(sp, max_qubits=9).peak_qubit_cap() == 9
    finally:
        del S._ENCODINGS["unit_cap"]


def test_default_spec_still_needs_a_nominal_pair():
    assert S.default_spec("lsh", "step").alpha == 0.37
    with pytest.raises(ValueError, match="unknown encoding"):
        S.default_spec("no_such_encoding", "step")


# ---------------------------------------------------------------------------------------------------- evaluate dispatch
def test_one_verdict_uses_the_registered_verdict_function(temp_encoding):
    make, m = temp_encoding
    make(verdict="su2plaq_unit_hooks:verdict")
    sp = S.TaskSpec(encoding="unit_x", kind="step", alpha=0.37, beta=0.61)
    assert E._one_verdict(QuantumCircuit(1), sp, "trial", 3.0) == "VERDICT"
    assert m.calls == [("verdict", "unit_x", "trial", 3.0)]


def test_one_verdict_passes_gauss_and_prune_fraction_from_the_entry(temp_encoding, monkeypatch):
    make, m = temp_encoding
    seen = {}

    def fake_eval(qc, enc, V, **kw):
        seen.update(kw)
        return "V"

    import su2plaq.evaluate.evaluator as EV

    monkeypatch.setattr(EV, "evaluate", fake_eval)
    sp = S.default_spec("twelve", "UE")
    assert E._one_verdict(QuantumCircuit(1), sp, "full", 60.0) == "V"
    assert seen["gauss"] is True and "prune_fraction" not in seen and seen["engine"] == "auto" and seen["states"] is None
    make(gauss_in_loop=False, prune_fraction=0.25)
    sp = S.TaskSpec(encoding="unit_x", kind="UE", alpha=0.37, beta=0.61)
    seen.clear()
    E._one_verdict(QuantumCircuit(1), sp, "trial", 60.0)
    assert seen["gauss"] is False and seen["prune_fraction"] == 0.25 and seen["engine"] == "sparse" and len(seen["states"]) == sp.trial_inputs
    sp = S.TaskSpec(encoding="not_registered", kind="UE", alpha=0.37, beta=0.61)
    S._ENCODINGS["not_registered"] = registry.get("twelve")
    try:
        seen.clear()
        E._one_verdict(QuantumCircuit(1), sp, "full", 60.0)
        assert seen["gauss"] is True and "prune_fraction" not in seen        # no entry: the old defaults
    finally:
        del S._ENCODINGS["not_registered"]


def test_engine_qubit_limit_is_checked_before_any_simulation():
    sp = dataclasses.replace(S.default_spec("twelve", "step"), max_qubits=100)
    r = E.evaluate_circuit(QuantumCircuit(E.ENGINE_QUBIT_LIMIT + 1), sp, "trial")
    assert not r.valid and r.reason == "engine_qubit_limit" and "63 qubits" in r.message and r.verdict is None
    r = E.evaluate_circuit(QuantumCircuit(61), S.default_spec("twelve", "step"), "trial")           # cap 60: the older check comes first
    assert r.reason == "max_qubits"


def test_worker_warmup_runs_for_registered_encodings_only(temp_encoding):
    make, m = temp_encoding
    make(worker_warmup="su2plaq_unit_hooks:warm")
    E._warm_up(["twelve", "unit_x", "not_registered"])
    assert m.calls == [("warm",)]


def test_evaluate_program_cache_key_is_per_encoding(tmp_path, monkeypatch):
    seen = {}
    def fake_path(ev, *a, **k):
        seen["ev"] = ev
        return tmp_path / "x.json"

    monkeypatch.setattr(P, "cache_path", fake_path)
    monkeypatch.setattr(E, "_evaluate_program_bytes", lambda *a, **k: E.ProgramResult(False, "contract", None, [], True, None, "", 0.0, [], "", "full"))
    f = tmp_path / "p.py"
    f.write_text("x = 1\n")
    E.evaluate_program(f, S.default_spec("twelve", "step"), "full", cache=True, root=tmp_path)
    assert seen["ev"] == P.code_hash_for("twelve") == P.code_hash()


# ---------------------------------------------------------------------------------------------------- archive / round / baselines / brief / report
def _result(valid=True):
    return E.ProgramResult(valid, "ok" if valid else "error", None, [], True, {"cx": 3, "t_eps": 5, "depth_ct": 7, "qubits": 9} if valid else None,
                           "a" * 64, 0.5, [], "s", "full", spec_sha256="b" * 64, seeds={})


def test_entry_from_result_stamps_both_hashes(temp_encoding):
    make, _ = temp_encoding
    e = A.entry_from_result(_result(), program_path="x/001-a.py", family="F", round=1, parent=None, encoding="twelve")
    assert e.evaluator_sha256 == P.stamp_hash("twelve") == P.code_hash() and e.encoding_sha256 == P.code_hash_for("twelve")
    assert json.loads(json.dumps(e.to_dict()))["encoding_sha256"] == e.encoding_sha256
    assert A.Entry.from_dict(e.to_dict()).encoding_sha256 == e.encoding_sha256
    make(evaluator_files=("compress/spec.py",), stamp="encoding")
    e2 = A.entry_from_result(_result(), program_path="x/001-a.py", family="F", round=1, parent=None, encoding="unit_x")
    assert e2.evaluator_sha256 == e2.encoding_sha256 == P.code_hash_for("unit_x") != P.code_hash()
    e0 = A.entry_from_result(_result(), program_path="x/001-a.py", family="F", round=1, parent=None)     # old call: unchanged
    assert e0.evaluator_sha256 == P.code_hash() and e0.encoding_sha256 is None and "encoding_sha256" not in e0.to_dict()
    legacy = e0.to_dict()
    assert A.Entry.from_dict(legacy).encoding_sha256 is None                                              # old entry files load


def test_certify_dispatch(temp_encoding, monkeypatch):
    make, m = temp_encoding
    make()                                                                  # lean_certify None -> n_a with the entry's reason
    sp = S.TaskSpec(encoding="unit_x", kind="step", alpha=0.37, beta=0.61)
    d, sec = RD._certify(QuantumCircuit(1), sp, program_file_sha256="f" * 64)
    assert d == {"status": "n_a", "reason": ""} and sec >= 0.0
    make(lean_na_reason="no exporter", lean_certify=None)
    assert RD._certify(QuantumCircuit(1), sp)[0] == {"status": "n_a", "reason": "no exporter"}
    make(lean_certify="su2plaq_unit_hooks:certify")
    d, _ = RD._certify(QuantumCircuit(1), sp, program_file_sha256="f" * 64)
    assert d == {"status": "certified", "from_hook": True, "program_file_sha256": "f" * 64}
    assert m.calls[-1] == ("certify", 1200.0, {"program_file_sha256": "f" * 64})
    # twelve (and an unregistered name) go through the twelve exporter, which may return a dataclass
    import su2plaq.lean.certify as LC

    @dataclasses.dataclass
    class Fake:
        status: str = "certified"
        cert_path: str | None = None

    monkeypatch.setattr(LC, "certify_circuit", lambda circ, spec, timeout=0, extra_provenance=None: Fake())
    d, _ = RD._certify(QuantumCircuit(1), S.default_spec("twelve", "step"))
    assert d == {"status": "certified", "cert_path": None}


def test_certify_failure_is_recorded_not_raised(temp_encoding):
    make, m = temp_encoding
    m.certify = lambda *a, **k: (_ for _ in ()).throw(NotImplementedError("later"))
    make(lean_certify="su2plaq_unit_hooks:certify")
    sp = S.TaskSpec(encoding="unit_x", kind="step", alpha=0.37, beta=0.61)
    d, _ = RD._certify(QuantumCircuit(1), sp)
    assert d["status"] == "not_run" and "later" in d["reason"]


def test_baselines_dispatch(temp_encoding):
    make, m = temp_encoding
    sp = S.default_spec("twelve", "UE")
    assert BL.general_circuit(sp).num_qubits > 12                         # default: the twelve-qubit reference
    make(general_circuit="su2plaq_unit_hooks:general", import_seed="su2plaq_unit_hooks:import_seed")
    spx = S.TaskSpec(encoding="unit_x", kind="step", alpha=0.37, beta=0.61)
    assert BL.general_circuit(spx).num_qubits == 3 and BL.import_seed(spx, "lean22") == "hook:lean22"
    assert m.calls == [("general", "unit_x"), ("import_seed", "lean22")]
    assert isinstance(BL.import_seed(sp, "spinnet15"), (str, dict))      # default path untouched


def test_seed_candidates_dispatch(temp_encoding, tmp_path):
    make, m = temp_encoding
    make(seed_candidates="su2plaq_unit_hooks:seeds")
    spx = S.TaskSpec(encoding="unit_x", kind="step", alpha=0.37, beta=0.61)
    out = RD._seed_candidates(spx, tmp_path)
    assert [x[0] for x in out] == ["only"] and m.calls == [("seeds", "unit_x")]
    assert RD._seed_candidates.__code__ is not RD._seed_candidates_default.__code__


def test_brief_registry_hooks(temp_encoding, tmp_path, monkeypatch):
    make, _ = temp_encoding
    assert BR._commands("twelve") == ("python -m su2plaq.compress.run_candidate", "python -m su2plaq.compress.oracle")
    assert BR._note("twelve", "step") == [] and "compress/lean/structure.json" in BR._structure_pointer(tmp_path)
    make(tools=("py cand", "py orc"), structure_json="compress/specs/x.json", brief_note="su2plaq_unit_hooks:note",
         render_spec="su2plaq_unit_hooks:render")
    f = tmp_path / "compress" / "specs" / "x.json"
    f.parent.mkdir(parents=True)
    f.write_text("{}")
    assert "`compress/specs/x.json`" in BR._structure_pointer(tmp_path, "unit_x")
    f.unlink()
    assert BR._structure_pointer(tmp_path, "unit_x").startswith("pending: `compress/specs/x.json`")
    assert BR._note("unit_x", "UB") == ["", "NOTE for unit_x/UB"]
    monkeypatch.setitem(base.NOMINAL_ANGLES, "unit_x", (0.37, 0.61))
    text = BR.make_ideation_brief("unit_x", "step", root=tmp_path).read_text()
    assert "`py orc --encoding unit_x --kind step ...`" in text and text.rstrip().endswith("NOTE for unit_x/step")
    text = BR.make_brief("unit_x", "step", 1, "F1", root=tmp_path).read_text()
    assert "`py cand <program.py> --encoding unit_x --kind step --trial`" in text and "`py orc ...`" in text
    assert text.rstrip().endswith("NOTE for unit_x/step")
    assert (tmp_path / "compress" / "specs" / "unit_x-step.md").read_text() == "RENDERED unit_x/step"


def test_report_external_row_prints_own_beta():
    paulo = {"source": "paulo34", "fixed_angle": True, "kind": "UB", "valid": True, "op_norm_error": 1e-6, "metrics": {"qubits": 34, "cx": 294}}
    assert "beta = 1, kind UB" in RP._row_external(paulo)[10]
    assert "beta = 0.05, kind UB" in RP._row_external({**paulo, "beta": 0.05})[10]
