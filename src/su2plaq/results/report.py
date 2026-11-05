"""Markdown report rendered from results JSON only (prompts/002 §2.9): deterministic, idempotent."""
from __future__ import annotations

from su2plaq.results.store import load_result


def _fmt(x) -> str:
    if x is None:
        return "-"
    if isinstance(x, bool):
        return "yes" if x else "no"
    if isinstance(x, float):
        return f"{x:.6g}"
    if isinstance(x, (list, tuple)):
        return ", ".join(_fmt(v) for v in x)
    if isinstance(x, dict):
        return ", ".join(f"{k}={_fmt(v)}" for k, v in x.items())
    return str(x)


def _table(header: list[str], rows: list[list]) -> str:
    out = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    out += ["| " + " | ".join(_fmt(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def render(paths: list) -> str:
    """Markdown tables (verification, logical metrics, T-count table) from the JSON files in `paths` (given order)."""
    docs = [load_result(p) for p in paths]
    ver_rows, log_rows, t_rows = [], [], []
    for d in docs:
        v, m, pr, par = d["verification"], d["metrics"], d["provenance"], d["params"]
        ver_rows.append([d["encoding"], d["circuit_id"], d["kind"], par.get("alpha"), par.get("beta"), par.get("order"),
                         v.get("ok"), v.get("reason"), v.get("op_norm_error"), v.get("leak_amplitude"), v.get("max_leak"), v.get("gauss_residual"),
                         v.get("method"), v.get("engine"), v.get("certified"), pr["git_commit"] + ("*" if pr.get("git_dirty") else "")])
        lg = m.get("logical", {})
        log_rows.append([d["circuit_id"], lg.get("cx"), lg.get("depth"), lg.get("n_rot"), lg.get("t_fixed"), lg.get("qubits"), lg.get("ancilla")])
        for row in m.get("t_table", []):
            t_rows.append([d["circuit_id"], row.get("eps"), row.get("t_fixed"), row.get("n_rot"), row.get("t_rot_pygridsynth"),
                           row.get("t_total"), row.get("t_est"), row.get("t_qiskit"), row.get("cx_qiskit"), row.get("depth_qiskit")])
    parts = ["### Verification", _table(["encoding", "circuit", "kind", "alpha", "beta", "order", "ok", "reason", "op-norm error",
                                         "leak amp", "max leak", "Gauss residual", "method", "engine", "certified", "commit"], ver_rows),
             "", "### Logical metrics", _table(["circuit", "CX", "depth", "N_rot", "T_fixed", "qubits", "ancilla"], log_rows)]
    if t_rows:
        parts += ["", "### T-count table", _table(["circuit", "eps", "T_fixed", "N_rot", "T_rot (pygridsynth)", "T_total",
                                                   "T_est", "T (Qiskit)", "CX (Qiskit)", "depth (Qiskit)"], t_rows)]
    return "\n".join(parts) + "\n"
