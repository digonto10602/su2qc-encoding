"""Before / after table of a compression run, from the results JSON only (prompts/002 §5 row 2.6).

  python -m su2plaq.compress.report --encoding twelve --kind step [--out path]

`report_table` reads `results/compress/<encoding>/round-*.json` (never the archive or the programs), writes the markdown table and
`results/compress/<encoding>/summary.json` (rows, the lineage of the valid entries in the (CX, T) plane as data, counts).
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

from su2plaq.compress.spec import ROOT

HEADER = ["row", "qubits", "CX", "T_fixed", "N_rot", "T(1e-6)", "T_est(1e-6)", "T(1e-10)", "depth_CT", "verdict", "Lean", "entry / commit"]


def _f(x) -> str:
    if x is None:
        return "-"
    if isinstance(x, float):
        return f"{x:.6g}"
    return str(x)


def _lean(rec) -> str:
    lean = rec.get("lean")
    if not lean:
        return "not_run"
    st = lean.get("status")
    return "certified" if st in ("certified", "accepted") else ("failed" if st in ("failed", "rejected") else "n_a")


def _verdict(rec) -> str:
    if not rec.get("valid"):
        return f"invalid: {rec.get('reason', '?')}"
    v = rec.get("verdict") or {}
    err = v.get("op_norm_error")
    leak = v.get("leak_amplitude")
    return "valid (err " + _f(err) + ", leak " + _f(leak) + ")" if err is not None else "valid"


def _row_from_record(name, rec) -> list:
    m = rec.get("metrics") or {}
    tm = m.get("t_measured") or {}
    est = m.get("t_estimate") or {}
    return [name, m.get("qubits"), m.get("cx"), m.get("t_fixed"), m.get("n_rot"), m.get("t_eps"), est.get("1e-06"),
            tm.get("1e-10", est.get("1e-10")), m.get("depth_ct"), _verdict(rec), _lean(rec),
            f"{rec.get('id', '-')} @ {rec.get('git_commit', '-')}"]


def _row_external(x) -> list:
    m = x.get("metrics") or {}
    est = m.get("t_estimate") or {}
    if "metrics" not in x:
        return [f"{x['source']} (not applicable)", "-", "-", "-", "-", "-", "-", "-", "-", x.get("reason", ""), "n_a", "-"]
    verdict = ("valid at its own angle (beta = 1, kind " + str(x.get("kind")) + "), err " + _f(x.get("op_norm_error"))
               if x.get("valid") else f"not verified: {x.get('reason')}")
    return [x["source"] + (" (fixed angle; Clifford+T up to a global phase)" if x.get("fixed_angle") else ""), m.get("qubits"),
            m.get("cx"), m.get("t_fixed"), m.get("n_rot"), m.get("t_eps"), est.get("1e-06"), est.get("1e-10"), m.get("depth_ct"),
            verdict, "n_a", "-"]


def report_table(encoding, kind, root=None) -> str:
    root = pathlib.Path(root) if root is not None else ROOT
    rdir = root / "results" / "compress" / encoding
    rounds = [json.loads(f.read_text()) for f in sorted(rdir.glob("round-*.json"))]
    records = [dict(rec, round=r["round"]) for r in rounds for rec in r.get("candidates", [])]
    externals = [x for r in rounds if r["round"] == 0 for x in r.get("external", [])]
    archived = {i for r in rounds for i in r.get("entries", [])}                     # what was actually archived
    valid = [r for r in records if r.get("valid") and r.get("key") and r["id"] in archived]
    rows, names = [], {"general": "general", "general+polish": "general + polish", "qiskit_l3": "Qiskit L3 (windows of 32)"}
    seen = set()
    for r in records:
        if r["round"] == 0 and r["label"] in names:
            rows.append(_row_from_record(names[r["label"]], r))
            seen.add(r["id"])
    for r in records:
        if r["round"] == 0 and r["label"] not in names:
            rows.append(_row_from_record(f"seed {r['label']}", r))
            seen.add(r["id"])
    for x in externals:
        if x["source"] == "qiskit_l3_whole":
            m = x.get("metrics")
            na = "n/a (unverifiable)"
            rows.append(["Qiskit L3 (whole circuit; counts only)", *([m.get("qubits"), m.get("cx"), m.get("t_fixed"), m.get("n_rot"), na,
                         (m.get("t_estimate") or {}).get("1e-06"), na, na] if m else ["-"] * 8), x.get("reason", ""), "n_a", "-"])
        else:
            rows.append(_row_external(x))
    best_by_family = {}
    for r in valid:
        if r["family"] not in best_by_family or tuple(r["key"]) < tuple(best_by_family[r["family"]]["key"]):
            best_by_family[r["family"]] = r
    for fam in sorted(best_by_family):
        rows.append(_row_from_record(f"best of family {fam}", best_by_family[fam]))
    gbest = min(valid, key=lambda r: (tuple(r["key"]), r["id"]), default=None)
    if gbest is not None:
        rows.append(_row_from_record("GLOBAL BEST", gbest))
    lines = [f"### Compression result: `{encoding}` / `{kind}`", "", "| " + " | ".join(HEADER) + " |", "|" + "|".join("---" for _ in HEADER) + "|"]
    lines += ["| " + " | ".join(_f(c) for c in row) + " |" for row in rows]
    lines += ["", "Every exact-angle circuit is the target up to ONE global phase; Clifford+T circuits (synthesised) are equal to their "
              "exact-angle design up to the synthesis error and one global phase. T(1e-6), T(1e-10): T_fixed + pygridsynth T of every "
              "rotation (measured); T_est: T_fixed + 3 N_rot log2(1/eps). Key = (CX, T(1e-6), depth_CT, qubits), lexicographic."]
    synth = [(r["round"], r["synthesis_verification"]) for r in rounds if r.get("synthesis_verification")]
    for rnd, s in synth:
        lines.append(f"Round {rnd}: Clifford+T re-verification of `{s['entry']}`: " + (
            f"{'ok' if s['ok'] else 'FAILED'} (eps {s['eps']:g}, {s['n_rot']} rotations, T {s['t_total']}, error {_f(s['op_norm_error'])} <= "
            f"{_f(s['tolerances']['tol_err'])})" if s.get("n_rot") is not None else f"not run ({s.get('error')})"))
    text = "\n".join(lines) + "\n"
    lineage = [{"id": r["id"], "parent": r.get("parent"), "family": r["family"], "round": r["round"], "cx": r["key"][0], "t_eps": r["key"][1], "parent_known": r.get("parent_known", True)}
               for r in valid]
    summary = {"encoding": encoding, "kind": kind, "n_rounds": len(rounds), "n_candidates": len(records), "n_valid": len(valid),
               "global_best": gbest["id"] if gbest else None, "global_best_key": gbest["key"] if gbest else None,
               "best_by_family": {k: v["id"] for k, v in best_by_family.items()}, "rows": [[_f(c) for c in row] for row in rows],
               "lineage": lineage}
    rdir.mkdir(parents=True, exist_ok=True)
    (rdir / "summary.json").write_text(json.dumps(summary, indent=1))
    return text


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m su2plaq.compress.report")
    ap.add_argument("--encoding", default="twelve")
    ap.add_argument("--kind", default="step")
    ap.add_argument("--out")
    ap.add_argument("--root")
    a = ap.parse_args(argv)
    text = report_table(a.encoding, a.kind, root=a.root)
    if a.out:
        pathlib.Path(a.out).write_text(text)
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
