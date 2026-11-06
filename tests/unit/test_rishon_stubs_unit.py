"""Step 5.0 skeleton: every not-yet-built public rishon name exists; the unbuilt ones raise NotImplementedError.
Entries move out of PENDING as later steps build them (keep this list in step with the plan)."""
import importlib

import pytest

PENDING = {
    "su2plaq.rishon.observables": ["closed_spectra", "closed_forms", "observables_table", "observables"],
    "su2plaq.rishon.verify": ["verify", "physical_cross_check"],
    "su2plaq.rishon.lean_export": ["export_hb_certificate", "write_hb_lean", "check_hb"],
    "su2plaq.circuits.rishon": ["build_UE", "build_UB", "build_step", "pair_frames"],
}
ARGS = {"closed_forms": (0.1, 0.1), "observables": (0.1, 0.1),
        "verify": (None, None, "UE", 0.1, 0.1), "physical_cross_check": (None, None, "UE", 0.1, 0.1),
        "export_hb_certificate": ("x",), "write_hb_lean": ("x", "y"), "check_hb": ("x",), "build_UE": (0.1,),
        "build_UB": (0.1,), "build_step": (0.1, 0.1), "pair_frames": (0.1,)}

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
