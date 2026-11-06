"""Three-angle Laurent certificates for rishon circuits (prompts/203 section 3.2).  STUBS (steps 6.L2-6.L4); `SCHEMA` is real."""
from __future__ import annotations

from su2plaq.rishon.compress._pending import pending

SCHEMA = "su2plaq-rishon-cert3-1"


class Laurent3:
    """dict[(m_alpha, m_beta, m_gamma)] -> su2plaq.lean.exact.KNum; arithmetic; evaluate(theta_alpha, theta_beta, theta_gamma); to_json()."""

    def __init__(self, *args, **kwargs):
        raise pending("lean_cert.Laurent3", "6.L2")


def recognise_angle(theta: float, alpha: float, beta: float, max_den: int = 64, tol: float = 1e-12):
    raise pending("lean_cert.recognise_angle", "6.L2")


def export_raw_circuit(qc, out_path, *, alpha: float, beta: float):
    raise pending("lean_cert.export_raw_circuit", "6.L2")


def certify_circuit_kind(qc, kind: str, alpha: float, beta: float, order: int, out_dir=None, timeout: float = 900.0):
    raise pending("lean_cert.certify_circuit_kind", "6.L3")


def check_theorem_file(path, timeout: float = 1800.0) -> dict:
    raise pending("lean_cert.check_theorem_file", "6.L3")


def export_inner_certificate(qc, kind: str, alpha: float, beta: float, order: int, out_path, *, alt_angles=None):
    raise pending("lean_cert.export_inner_certificate", "6.L2")


def check_inner_certificate(path, timeout: float = 900.0):
    raise pending("lean_cert.check_inner_certificate", "6.L2")


def certify_circuit(qc, spec, out_dir=None, timeout: float = 900.0):
    raise pending("lean_cert.certify_circuit", "6.L3")


def checker_eval(cert_path, input_index: int, timeout: float = 900.0) -> list:
    raise pending("lean_cert.checker_eval", "6.L2")


def write_theorem_file(cert_path, theorem_name: str, out_path):
    raise pending("lean_cert.write_theorem_file", "6.L3")
