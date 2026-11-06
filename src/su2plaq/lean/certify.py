"""Certificate export / check / theorem files for circuits (prompts/006 §4, §5).  Skeleton: step 2.L4/2.L5."""
from __future__ import annotations

import pathlib
from dataclasses import dataclass, field

from su2plaq._stub import todo


@dataclass
class LeanCert:
    status: str          # "certified" | "rejected" | "n_a" | "failed" | "not_run"
    reason: str
    cert_path: str | None
    seconds: float
    checker_sha256: str
    theorem_path: str | None = None
    axioms: list = field(default_factory=list)


def export_certificate(qc, enc, kind: str, alpha: float, beta: float, order: int, out_path, *,
                       verdict_phases: list[complex] | None = None) -> pathlib.Path | str:
    todo("lean.certify.export_certificate")


def export_raw_circuit(qc, out_path, *, alpha: float, beta: float) -> pathlib.Path | str:
    todo("lean.certify.export_raw_circuit")


def check_certificate(path, timeout: float = 900.0) -> LeanCert:
    todo("lean.certify.check_certificate")


def certify_circuit(qc, spec, out_dir=None, timeout: float = 900.0) -> LeanCert:
    todo("lean.certify.certify_circuit")


def certify_circuit_kind(qc, enc, kind: str, alpha: float, beta: float, order: int, out_dir=None,
                         timeout: float = 900.0) -> LeanCert:
    todo("lean.certify.certify_circuit_kind")


def write_theorem_file(cert_path, theorem_name: str, out_path) -> pathlib.Path:
    todo("lean.certify.write_theorem_file")


def checker_eval(cert_path, input_index: int, timeout: float = 900.0) -> list:
    todo("lean.certify.checker_eval")
