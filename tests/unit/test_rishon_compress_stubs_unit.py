"""Step 6.0 skeleton for prompts/203 §3: every public name of the rishon compression package exists.  All stubs are built
(6.1-6.4b, 6.L2-6.L4 = step C4 of prompts/204); the stub-raising test is gone with the last stub (`lean_cert`), the module constants are kept."""
import importlib


def test_constants_classes_and_view_attributes():
    P = importlib.import_module("su2plaq.rishon.compress")
    assert P.RISHON_EVALUATOR_FILES[-3:] == ["rishon/compress/spec.py", "rishon/compress/evaluate.py", "rishon/compress/baselines.py"]
    S = importlib.import_module("su2plaq.rishon.compress.spec")
    assert S.RISHON_NOMINAL == importlib.import_module("su2plaq.encodings.rishon").RISHON_NOMINAL == (0.37, 0.61)
    v = S.RishonCompressView
    assert (v.name, v.n_data, v.n_outer, v.is_basis_encoding) == ("rishon", 16, 32, True)
    assert importlib.import_module("su2plaq.rishon.compress.baselines").LADDERS == ("ccx", "rccx", "mcx")
    assert importlib.import_module("su2plaq.rishon.lean_cert").SCHEMA == "su2plaq-rishon-cert3-1"
    assert not importlib.import_module("su2plaq.rishon.lean_cert").Laurent3()          # the empty Laurent polynomial
    assert S.RishonCompressView().target("UE", 0.37, None).shape == (1296, 1296)
