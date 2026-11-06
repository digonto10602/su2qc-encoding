"""Step 6.0 skeleton for prompts/203 §3: every public name of the rishon compression package exists; the unbuilt ones raise
NotImplementedError whose message starts with "PENDING:".  Entries move out of PENDING as steps 6.3-6.4 / 6.L2-6.L4 build them (6.1, 6.2 done; `general_circuit` and
`general_program_path` were pulled forward into 6.2 because the evaluator acceptance tests build their programs with them)."""
import importlib

import numpy as np
import pytest

CALLS = {          # module -> {name: args}; built names (6.1: package, spec, oracle; 6.2: evaluate) have their own unit tests
    "su2plaq.rishon.compress.baselines": {"qiskit_l3": (None,), "qiskit_l3_whole": (None,), "polish": (None, None),
                                          "general_polished": (None,), "import_seed": (None, "paulo34")},
    "su2plaq.rishon.compress.round": {"run_round": ("step", 0, False), "certify_best": (), "main": ()},
    "su2plaq.rishon.compress.brief": {"make_ideation_brief": (), "make_brief": ("step", 1, "F"), "main": ()},
    "su2plaq.rishon.compress.run_candidate": {"main": ()},
    "su2plaq.rishon.lean_cert": {"recognise_angle": (1.0, 0.37, 0.61), "export_raw_circuit": (None, "x"),
                                 "certify_circuit_kind": (None, "UE", 0.37, 0.61, 1), "check_theorem_file": ("x",),
                                 "export_inner_certificate": (None, "UE", 0.37, 0.61, 1, "x"), "check_inner_certificate": ("x",),
                                 "certify_circuit": (None, None), "checker_eval": ("x", 0), "write_theorem_file": ("x", "t", "y")},
}


@pytest.mark.parametrize("mod,name", [(m, n) for m, d in CALLS.items() for n in d])
def test_pending_names_raise(mod, name):
    fn = getattr(importlib.import_module(mod), name)
    kwargs = {"alpha": 0.37, "beta": 0.61} if name == "export_raw_circuit" else {}
    with pytest.raises(NotImplementedError, match="PENDING:"):
        fn(*CALLS[mod][name], **kwargs)


def test_constants_classes_and_view_attributes():
    P = importlib.import_module("su2plaq.rishon.compress")
    assert P.RISHON_EVALUATOR_FILES[-3:] == ["rishon/compress/spec.py", "rishon/compress/evaluate.py", "rishon/compress/baselines.py"]
    S = importlib.import_module("su2plaq.rishon.compress.spec")
    assert S.RISHON_NOMINAL == importlib.import_module("su2plaq.encodings.rishon").RISHON_NOMINAL == (0.37, 0.61)
    v = S.RishonCompressView
    assert (v.name, v.n_data, v.n_outer, v.is_basis_encoding) == ("rishon", 16, 32, True)
    assert importlib.import_module("su2plaq.rishon.compress.baselines").LADDERS == ("ccx", "rccx", "mcx")
    assert importlib.import_module("su2plaq.rishon.lean_cert").SCHEMA == "su2plaq-rishon-cert3-1"
    with pytest.raises(NotImplementedError, match="PENDING:"):
        importlib.import_module("su2plaq.rishon.lean_cert").Laurent3()
    assert S.RishonCompressView().target("UE", 0.37, None).shape == (1296, 1296)
