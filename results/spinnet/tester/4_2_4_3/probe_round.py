"""Probe (a)+(b): dry seed round under a tmp root, no Lean; consistency of archive / attempts / feedback / round JSON; briefs."""
import sys, json, time, pathlib, resource
from su2plaq.spinnet import loop as L
root = pathlib.Path(sys.argv[1]); root.mkdir(parents=True, exist_ok=True)
out = {}
t0 = time.time()
info = L.seed_round(root=root, lean=False, dry_run=True)
out["wall_seed_round_s"] = time.time() - t0
out["info"] = info
d = json.loads((root / "results/compress/spinnet/round-000.json").read_text())
out["round_keys"] = sorted(d)
out["cand_keys"] = sorted(d["candidates"][0])
out["cands"] = [{k: c[k] for k in ("label", "id", "family", "valid", "key", "cell", "parent", "round", "mode", "skeleton_equal", "alt_ok", "program_path", "lean")} for c in d["candidates"]]
out["external"] = [{k: v for k, v in x.items() if k != "metrics"} | ({"metrics": {m: x["metrics"].get(m) for m in ("cx", "t_fixed", "n_rot", "t_eps", "depth_ct", "qubits")}} if x.get("metrics") else {}) for x in d["external"]]
out["synth"] = d["synthesis_verification"]
out["spinnet_key"] = d["spinnet"]
out["lean_seconds"] = d["lean_seconds"]
att = [json.loads(x) for x in (root / "compress/attempts/spinnet.jsonl").read_text().splitlines() if x.strip()]
out["attempts"] = [(a["id"], a["round"], a["family"], a["valid"], a["key"]) for a in att]
out["feedback"] = sorted(p.name for p in (root / "results/compress/spinnet/feedback").glob("*.json"))
out["archive_files"] = sorted(str(p.relative_to(root)) for p in (root / "compress/archive").rglob("*") if p.is_file())
from su2plaq.compress import archive as A
ar = A.Archive.load("spinnet", root=root, n_alt=2, strict=True)
out["archive_entries"] = [(e.id, e.family, e.valid, list(e.key), e.program_path, e.round) for e in ar.entries()]
out["archive_best"] = (ar.best().id, list(ar.best().key))
L.make_brief(1, "F1", root=root)
L.make_brief(3, "F2", root=root)
L.make_ideation_brief(root=root)
out["maxrss_gb"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6
print(json.dumps(out, indent=1, default=str))
