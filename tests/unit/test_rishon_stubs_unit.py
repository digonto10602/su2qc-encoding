"""Step 5.0 skeleton: every not-yet-built public rishon name exists; the unbuilt ones raise NotImplementedError.
Entries move out of PENDING as later steps build them (keep this list in step with the plan)."""
import importlib

import pytest

PENDING: dict = {}      # M5x O1 (outer_electric_certify) is built
ARGS: dict = {}

@pytest.mark.parametrize("mod,name", [(m, n) for m, ns in PENDING.items() for n in ns] or [(None, None)])
def test_pending_names_raise(mod, name):
    if mod is None:
        return      # nothing pending
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
