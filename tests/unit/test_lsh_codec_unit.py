"""Unit tests for su2plaq.encodings.lsh (prompts/400 step 7.1: `label_of_code`) and the interface surface of the LSH
modules (step 7.0: every name of prompts/400 section 2 exists, whatever its build status)."""
import importlib

import pytest

from su2plaq.encodings.lsh import LSH, code_of_label, label_of_code
from su2plaq.exact.spinnet import labels
from su2plaq.lsh import operators as O

SURFACE = {
    "su2plaq.lsh.operators": ["VALID_SITE", "SITE_J1", "CORNER_PN", "CORNER_OUT", "LINK_NAMES", "VERTEX_TYPES", "VERTEX",
                              "site_flux", "site_valid", "site_code", "ladder_amplitude", "loop_ladder", "inner_code_of",
                              "code_of_label", "agl_violations", "is_physical_code", "inner_codes", "physical_codes",
                              "plaquette_inner", "K_lsh", "h_magnetic_lsh", "h_electric_lsh"],
    "su2plaq.lsh.walk": ["LINK", "CBIT", "WBIT", "TARGET", "J_HALF_PHASE", "TRANSCODE", "FRAME", "transcode_steps", "mirror",
                         "skeleton", "classical_run", "classical_slots", "coupling_table", "partner_table", "solve_angles",
                         "angle_fractions", "build"],
    "su2plaq.lsh.lean_export": ["coupling_ints", "partner_ints", "angle_ints", "lean_literals", "write_lean_tables",
                                "export_certificate", "certify", "write_pins"],
    "su2plaq.circuits.lsh": ["build_UE", "build_UB", "build_step", "wrap_spinnet"],
    "su2plaq.encodings.lsh": ["N_DATA", "N_OUTER", "code_of_label", "label_of_code", "LSH"],
}


@pytest.mark.parametrize("mod", sorted(SURFACE))
def test_interface_surface(mod):
    m = importlib.import_module(mod)
    missing = [n for n in SURFACE[mod] if not hasattr(m, n)]
    assert missing == []


def test_class_attributes():
    assert (LSH.name, LSH.n_data, LSH.n_outer, LSH.is_basis_encoding) == ("lsh", 12, 12, True)
    for meth in ("inner_codes", "physical_vectors", "decode", "decode_state", "target", "inner_target", "h_magnetic",
                 "h_electric", "layout_of", "describe", "import_map"):
        assert callable(getattr(LSH, meth))


def test_label_of_code_inverse_and_none():
    labs = labels(jmax=0.5)
    for lab in labs:
        code = code_of_label(lab)
        assert code == O.code_of_label(lab) and label_of_code(code) == lab
        assert label_of_code(int(code)) == lab
    physical = set(O.physical_codes().tolist())
    assert {code_of_label(lab) for lab in labs} == physical
    for code in (0b010, 1 << 1, 1 << 23, (1 << 24) - 1, 0b001):
        assert code not in physical and label_of_code(code) is None
