"""Step 5.0 skeleton: every not-yet-built public rishon name exists; the unbuilt ones raise NotImplementedError.
Entries move out of PENDING as later steps build them (keep this list in step with the plan)."""
import importlib

import pytest

PENDING = {
    "su2plaq.rishon.operators": ["plaquette_W_inner", "h_electric_inner", "h_magnetic_inner", "gauss_inner", "heights",
                                 "dark_codes", "closed_codes", "det_term_inner", "bright_pairs", "inner_target",
                                 "closed_block"],
    "su2plaq.rishon.observables": ["ks_closed_block", "closed_spectra", "closed_forms", "observables_table",
                                   "observables"],
    "su2plaq.rishon.verify": ["verify", "physical_cross_check"],
    "su2plaq.rishon.lean_export": ["export_hb_certificate", "write_hb_lean", "check_hb"],
    "su2plaq.circuits.rishon": ["build_UE", "build_UB", "build_step", "pair_frames"],
}
ARGS = {"gauss_inner": (0, 0), "heights": (0,), "inner_target": ("UE", 0.1, 0.1), "closed_block": (1.0,),
        "ks_closed_block": (1.0,), "closed_forms": (0.1, 0.1), "observables": (0.1, 0.1),
        "verify": (None, None, "UE", 0.1, 0.1), "physical_cross_check": (None, None, "UE", 0.1, 0.1),
        "export_hb_certificate": ("x",), "write_hb_lean": ("x", "y"), "check_hb": ("x",), "build_UE": (0.1,),
        "build_UB": (0.1,), "build_step": (0.1, 0.1), "pair_frames": (0.1,)}

ENCODING_PENDING = {
    "RishonEncoding": {"inner_codes": (), "physical_vectors": (), "decode": (0,), "decode_state": ([], []),
                       "inner_target": ("UE", 0.1, 0.1), "target": ("UE", 0.1, 0.1), "inner_view": (),
                       "layout_of": (None,), "describe": (), "import_map": (None,)},
    "RishonInnerView": {"inner_codes": (), "physical_vectors": (), "layout_of": (None,), "decode_state": ([], [])},
}


@pytest.mark.parametrize("mod,name", [(m, n) for m, ns in PENDING.items() for n in ns])
def test_pending_names_raise(mod, name):
    fn = getattr(importlib.import_module(mod), name)
    with pytest.raises(NotImplementedError):
        fn(*ARGS.get(name, ()))


def test_module_constants_and_classes_exist():
    P = importlib.import_module("su2plaq.rishon.physical")
    assert (P.N_QUBITS, P.N_DATA, P.N_OUTER, P.LINK_TYPES) == (48, 16, 32, ("A", "B", "Q"))
    E = importlib.import_module("su2plaq.encodings.rishon")
    assert E.RISHON_NOMINAL == (0.37, 0.61)
    enc = E.RishonEncoding()
    assert enc.registers["d"] == list(range(16)) and enc.registers["o"] == list(range(16, 48))
    assert enc.registers["link_l"] == [12, 13, 14, 15] and enc.registers["outer_7"] == [44, 45, 46, 47]
    assert (enc.name, enc.n_data, enc.n_outer, enc.is_basis_encoding) == ("rishon", 16, 32, False)
    V = importlib.import_module("su2plaq.rishon.verify")
    assert hasattr(V, "RishonVerdict") and callable(V.synth_tolerances)
    LE = importlib.import_module("su2plaq.rishon.lean_export")
    assert len(LE.RISHON_COUNT_THEOREMS) == 2 and len(LE.RISHON_JW_THEOREMS) == 7


@pytest.mark.parametrize("cls,name", [(c, n) for c, ns in ENCODING_PENDING.items() for n in ns])
def test_encoding_pending_methods_raise(cls, name):
    E = importlib.import_module("su2plaq.encodings.rishon")
    obj = getattr(E, cls)()
    with pytest.raises(NotImplementedError):
        getattr(obj, name)(*ENCODING_PENDING[cls][name])
