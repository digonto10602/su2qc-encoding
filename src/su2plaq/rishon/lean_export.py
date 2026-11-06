"""Lean export for the rishon track (prompts/200 §2.9). Stubs (step 5.0); built in 5.L1-5.L3."""
from __future__ import annotations

import pathlib

from su2plaq._stub import todo

RISHON_COUNT_THEOREMS = ("Su2Plaq.card_rishon_physical", "Su2Plaq.card_rishon_closed")
RISHON_JW_THEOREMS = (
    "Su2Plaq.Rishon.car_4", "Su2Plaq.Rishon.car_8", "Su2Plaq.Rishon.bilinear_string_free_8",
    "Su2Plaq.Rishon.sector_card", "Su2Plaq.Rishon.u_ladder", "Su2Plaq.Rishon.det_u_sector",
    "Su2Plaq.Rishon.end_bilinear_local",
)


def export_hb_certificate(out_path) -> pathlib.Path:
    todo("rishon.lean_export.export_hb_certificate")


def write_hb_lean(cert_path, out_path) -> pathlib.Path:
    todo("rishon.lean_export.write_hb_lean")


def check_hb(lean_file, timeout=900) -> dict:
    todo("rishon.lean_export.check_hb")
