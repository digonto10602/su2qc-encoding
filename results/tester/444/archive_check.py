"""Tester 444: archive / round file / index consistency, hashes, attempts, discoveries, provenance, lean block, tree side effects.  No RNG."""
import json, glob, pathlib, hashlib, subprocess
ROOT = pathlib.Path("/home/digimonk/Projects/su2qc-encoding"); J = lambda p: json.load(open(ROOT / p))
out = {"commit": subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip(), "seed": None}
rnd = J("results/compress/lsh/round-006.json"); idx = J("compress/archive/lsh/index.json")
out["round_keys"] = list(rnd.keys()); out["round"] = {k: rnd.get(k) for k in ("round", "n_valid", "n_invalid", "best_key", "best_id", "evaluator_sha256", "spec_sha256", "external")}
out["round_git"] = rnd.get("provenance")
ents = {pathlib.Path(p).stem: json.load(open(p)) for p in glob.glob(str(ROOT / "compress/archive/lsh/entries/*.json"))}
out["n_entry_files"] = len(ents); out["index_n_entries"] = idx.get("n_entries"); out["index_best"] = idx.get("best")
out["index_keys"] = list(idx.keys())
# per-family best and cells recomputed
fam = {}
for i, e in ents.items():
    if e["valid"]:
        fam.setdefault(e["family"], []).append((tuple(e["key"]), i))
out["family_best_own"] = {f: min(v)[1] for f, v in sorted(fam.items())}
cells = {}
for i, e in ents.items():
    if e["valid"] and e.get("cell"):
        c = tuple(e["cell"]); 
        if c not in cells or (tuple(e["key"]), i) < cells[c][0]: cells[c] = ((tuple(e["key"])), i), 
out["n_cells_own"] = len(cells)
out["cells_own"] = {f"{c[0]},{c[1]}": v[0][1] for c, v in sorted(cells.items())} if False else None
out["global_min_key_own"] = min((tuple(e["key"]), i) for i, e in ents.items() if e["valid"])
out["candidates_in_round"] = [(c["id"], c["valid"], c["key"]) for c in rnd["candidates"]]
for eid in ("r06-F3-006",):
    e = ents[eid]; c = next(c for c in rnd["candidates"] if c["id"] == eid)
    f = ROOT / e["program_path"]
    out[eid] = {"sha_file_eq_entry": hashlib.sha256(f.read_bytes()).hexdigest() == e["program_sha256"], "sha_round_eq_entry": c["program_sha256"] == e["program_sha256"],
                "key_entry_eq_round": c["key"] == e["key"], "hashes_ok": e["evaluator_sha256"] == e["encoding_sha256"] == rnd["evaluator_sha256"], "spec_ok": e["spec_sha256"] == rnd["spec_sha256"],
                "parent": e["parent"], "parent_in_archive": e["parent"] in ents, "family": e["family"], "round": e["round"], "cell": e["cell"], "git_commit": e["git_commit"], "git_dirty": e["git_dirty"],
                "lean": None if e["lean"] is None else {k: e["lean"].get(k) for k in ("status", "axioms", "program_file_sha256", "gates_sha256", "cert_path")},
                "feedback_exists": (ROOT / f"results/compress/lsh/feedback/{eid}.json").exists()}
att = [json.loads(l) for l in open(ROOT / "compress/attempts/lsh.jsonl") if l.strip()]
out["attempts_total"] = len(att); out["attempts_r6"] = [a for a in att if a["round"] == 6]
out["index_best_equals_global_min"] = idx.get("best") == out["global_min_key_own"][1] if isinstance(idx.get("best"), str) else idx.get("best")
cert = J("results/lsh/certs/lsh-step-o1-dd63c8bf6fad.json")
out["cert"] = {"gates_sha256": cert["gates_sha256"], "provenance_commit": cert["provenance"].get("git_commit"), "git_dirty": cert["provenance"].get("git_dirty"), "n_gates": len(cert["gates"]), "n_states": len(cert["states"]), "n_qubits": cert["n_qubits"]}
d = open(ROOT / "compress/discoveries/lsh.md").read()
out["discoveries_mentions"] = {k: d.count(k) for k in ("r05-F3-005", "r06-F3-006")}
print(json.dumps(out, indent=1, default=str))
json.dump(out, open(ROOT / "results/tester/444/archive_check.json", "w"), indent=1, default=str)
