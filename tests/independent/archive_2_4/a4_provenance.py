import hashlib, json, pathlib, subprocess, sys, tempfile, datetime, importlib.metadata as im
sys.path.insert(0, "src")
from su2plaq.compress import evaluate as E, provenance as P, archive as A
from su2plaq.compress.spec import default_spec
SCR = pathlib.Path(sys.argv[1]); G = SCR / "prog" / "001-ue.py"; B = SCR / "prog" / "002-bad.py"
spec = default_spec("twelve", "UE"); OUT = {}
git = lambda *a: subprocess.run(["git", *a], capture_output=True, text=True, cwd=".").stdout.strip()
head = git("rev-parse", "--short", "HEAD"); dirty = bool(git("status", "--porcelain", "--untracked-files=no"))
r = E.evaluate_program(G, spec, "full"); e = A.entry_from_result(r, program_path=str(G), family="F9", round=2, parent="r01-F9-001")
d = e.to_dict()
chk = {}
chk["id"] = (e.id, "r02-F9-001")
chk["program_sha256"] = (e.program_sha256 == hashlib.sha256(G.read_bytes()).hexdigest(), True)
chk["evaluator_sha256"] = (e.evaluator_sha256 == P.code_hash(), True)
chk["spec_sha256"] = (e.spec_sha256 == spec.sha256(), True)
chk["git_commit"] = (e.git_commit, head)
chk["git_dirty"] = (e.git_dirty, dirty)
chk["versions"] = {k: e.versions.get(k) for k in ("qiskit", "qiskit_aer", "numpy", "pygridsynth", "python", "scipy")}
chk["versions_keys"] = sorted(e.versions)
chk["seeds"] = e.seeds
chk["machine"] = e.machine
chk["wall_s"] = e.wall_s
chk["written_utc"] = e.written_utc
chk["parent"] = e.parent; chk["mode"] = e.mode; chk["valid_reason"] = (e.valid, e.reason)
chk["key"] = e.key; chk["cell"] = e.cell; chk["synthesis"] = e.synthesis
chk["verdict_nominal_has"] = {k: e.verdict_nominal.get(k) for k in ("ok", "certified", "engine", "op_norm_error", "tol_err", "tol_gauss", "gauss_residual")}
chk["n_alt"] = len(e.verdicts_alt); chk["skeleton_equal"] = e.skeleton_equal
# do the versions agree with the installed packages?
inst = {}
for pkg in ("qiskit", "qiskit-aer", "numpy", "scipy", "pygridsynth"):
    try: inst[pkg] = im.version(pkg)
    except Exception as ex: inst[pkg] = None
chk["installed"] = inst
OUT["full_entry"] = chk
# cached-result entry: are provenance fields still right (written_utc fresh, evaluator hash current)?
with tempfile.TemporaryDirectory() as td:
    E.evaluate_program(G, spec, "full", cache=True, root=td); rc = E.evaluate_program(G, spec, "full", cache=True, root=td)
    ec = A.entry_from_result(rc, program_path=str(G), family="F9", round=2, parent=None)
    OUT["cached_entry"] = dict(seeds=ec.seeds, spec_sha_ok=ec.spec_sha256 == spec.sha256(), evaluator_ok=ec.evaluator_sha256 == P.code_hash(), wall_s=ec.wall_s, key_equal=ec.key == e.key)
# trial-mode result -> entry -> insert?
rt = E.evaluate_program(G, spec, "trial"); et = A.entry_from_result(rt, program_path=str(G), family="F9", round=2, parent=None)
with tempfile.TemporaryDirectory() as td:
    arch = A.Archive.load("twelve", root=td, n_alt=2)
    OUT["trial_entry"] = dict(mode=et.mode, valid=et.valid, reason=et.reason, inserted=arch.insert(et), rejected=arch.rejected, key=et.key, measured=et.synthesis)
    OUT["full_entry_inserted_n_alt2"] = A.Archive.load("twelve", root=td, n_alt=2).insert(e)
# invalid result -> entry -> refused
rb = E.evaluate_program(B, spec, "full"); eb = A.entry_from_result(rb, program_path=str(B), family="F9", round=2, parent=None)
with tempfile.TemporaryDirectory() as td:
    arch = A.Archive.load("twelve", root=td)
    OUT["invalid_entry"] = dict(valid=eb.valid, reason=eb.reason, key=[str(x) for x in eb.key], cell=eb.cell, inserted=arch.insert(eb))
# provenance of seeds against the code
from su2plaq.metrics.logical import SEED
OUT["seeds_vs_code"] = dict(transpiler_logical=(e.seeds.get("transpiler_logical"), SEED), trial_seed=(e.seeds.get("trial_seed"), spec.trial_seed))
print(json.dumps(OUT, indent=1, default=str))
json.dump(OUT, open("results/tester_m2_step2_4_recheck_provenance.json", "w"), indent=1, default=str)
