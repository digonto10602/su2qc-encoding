"""Tester mutation harness for lean/Su2Plaq/SpinNet/{Recoupling,Semantics,Spectrum}.lean (report 107).
Concatenates the three Mathlib-free files into ONE scratch file outside the repo, applies a textual mutation, runs bare `lean`
(no Mathlib) and records which theorems the kernel refutes.  Usage: m3x_mutate.py <scratch_dir> <jobs>"""
import json, pathlib, re, subprocess, sys, time, concurrent.futures as cf, resource

REPO = pathlib.Path.home() / "Projects/su2qc-spinnet"
SRC = REPO / "lean/Su2Plaq/SpinNet"
THEOREMS = ["valid_codes_from_codec", "k_matching", "coupling_from_6j", "k_from_6j_full", "ub_h_count", "ub_exact_all_codes",
            "card_states_exact", "blocks_cover", "eig_blocks", "eig_count", "eig_mult"]

def base_text():
    parts = []
    for n in ("Recoupling", "Semantics", "Spectrum"):
        t = (SRC / f"{n}.lean").read_text()
        t = "\n".join(l for l in t.splitlines() if not l.startswith("import Su2Plaq.SpinNet"))
        parts.append(t)
    return "\n".join(parts) + "\n"

# (id, description, [(old, new, expected_count)])
MUT = [
 ("M0_none", "no mutation (control)", []),
 ("B1_rz_sign", "builder: rz sign flipped in applyBasis",
    [("c.unit (-a) 1 0 else c.unit a 1 0", "c.unit a 1 0 else c.unit (-a) 1 0", 1)]),
 ("B2_one_angle", "builder: one ubGates angle .rz 0 (-7) -> (-6)", [(".rz 0 (-7)", ".rz 0 (-6)", 1)]),
 ("B3_eig_signs", "builder: eigenvalue signs swapped in eigsOf",
    [("some (y, 1, k) else some (y, -1, -k)", "some (y, 1, -k) else some (y, -1, k)", 1)]),
 ("T1_racah_sign", "6j: Racah alternating sign removed", [("if z % 2 == 0 then 1 else -1", "1", 1)]),
 ("T2_one_F_value", "one F-symbol value negated: F^{1 1/2 1/2}_{1/2 ...} i.e. fsym with (j1,j2,j12)=(2,1,1) gets -1",
    [("  ⟨⟨ph * s.q.num, s.q.den⟩, s.r.mul", "  let ph : Int := if j1 == 2 && j2 == 1 && j12 == 1 then -ph else ph\n  ⟨⟨ph * s.q.num, s.q.den⟩, s.r.mul", 1)]),
 ("T2b_F_J12_value", "one F-symbol value negated: (J,jp,jn)=(1/2,0,1/2) i.e. fsym (1,0,1,..)",
    [("  ⟨⟨ph * s.q.num, s.q.den⟩, s.r.mul", "  let ph : Int := if j1 == 1 && j2 == 0 && j12 == 1 then -ph else ph\n  ⟨⟨ph * s.q.num, s.q.den⟩, s.r.mul", 1)]),
 ("T2c_F_J0_value", "one F-symbol value negated: J=0 corner with jp=jn=1/2 (fsym (0,1,1,1,J'=?,..))",
    [("  ⟨⟨ph * s.q.num, s.q.den⟩, s.r.mul", "  let ph : Int := if j1 == 0 && j2 == 1 && j12 == 1 then -ph else ph\n  ⟨⟨ph * s.q.num, s.q.den⟩, s.r.mul", 1)]),
 ("T3_F_phase_drops_J", "F phase exponent loses the J term", [("(j1 + j2 + j3 + J) / 2) % 2", "(j1 + j2 + j3) / 2) % 2", 1)]),
 ("T4_dim_factor", "F sqrt((2j12+1)(2j23+1)) -> (2j12+1) only", [("Frac.ofNat ((j12 + 1) * (j23 + 1))", "Frac.ofNat (j12 + 1)", 1)]),
 ("T5_codec_corner", "codec: corner 0 visits (r,b) instead of (l,b)", [("def cornerP : Nat → Nat | 0 => 3", "def cornerP : Nat → Nat | 0 => 1", 1)]),
 ("T6_K_sign", "K = +(P+P^T) instead of -(P+P^T)", [("some (a.add b).neg", "some (a.add b)", 1)]),
 ("G1_qubit_index", "gate qubit index: first .cx 14 0 -> .cx 14 1", [(".cx 14 0, .rz 0 3, .cx 14 0", ".cx 14 1, .rz 0 3, .cx 14 0", 1)]),
 ("G2_rccx_target", "gate qubit index: .rccx 6 7 9 -> .rccx 6 7 10 (first)", [(".rccx 6 7 9, .rccx 8 9 10, .x 2", ".rccx 6 7 10, .rccx 8 9 10, .x 2", 1)]),
 ("G3_drop_gate", "dropped last gate .cx 1 3", [(", .cx 0 1, .cx 1 3]", ", .cx 0 1]", 1)]),
 ("G4_drop_uncompute", "dropped one uncompute gate .rccx 4 5 8 (second occurrence)", [(", .rccx 8 9 10, .rccx 6 7 9, .rccx 4 5 8, .x 7", ", .rccx 8 9 10, .rccx 6 7 9, .x 7", 1)]),
 ("G5_h_sign", "h: sign of the |1> branch dropped", [("[(i0, c), (i1, c.unit 0 (-1) 0)]", "[(i0, c), (i1, c)]", 1)]),
 ("G6_rccx_phase_conj", "RCCX relative phases conjugated (i <-> -i)",
    [("[(i ^^^ (1 <<< t), c.unit 0 0 1)] else [(i ^^^ (1 <<< t), c.unit 0 0 (-1))]", "[(i ^^^ (1 <<< t), c.unit 0 0 (-1))] else [(i ^^^ (1 <<< t), c.unit 0 0 1)]", 1)]),
 ("G7_rccx_toffoli", "RCCX as plain Toffoli (all relative phases 1)",
    [("[(i ^^^ (1 <<< t), c.unit 0 0 1)] else [(i ^^^ (1 <<< t), c.unit 0 0 (-1))]", "[(i ^^^ (1 <<< t), c)] else [(i ^^^ (1 <<< t), c)]", 1),
     ("else if bitOf i a == 1 && bitOf i b == 0 && bitOf i t == 1 then [(i, c.unit 0 (-1) 0)]", "else if false then [(i, c)]", 1)]),
 ("G8_target_sign", "target sign of the off-diagonal flipped", [("Lau.insert (m, -1, 0) (Lau.insert (-m, 1, 0) [])", "Lau.insert (m, 1, 0) (Lau.insert (-m, -1, 0) [])", 1)]),
 ("S1_multiplicity", "eig_mult: 16 -> 15 / 177 -> 178 in expected list", [("[16, 96, 16, 177, 16, 96, 16]", "[15, 96, 16, 178, 16, 96, 16]", 1)]),
 ("S2_all_plus", "eigsOf: both partners get the + vector (duplicate vectors)", [("else if bitOf y 0 == 0 then some (y, 1, k)", "else if true then some (y, 1, k)", 1)]),
 ("S3_fuse", "states: fuse(1/2,1/2) = {0,1/2} instead of {0,1}", [("then [0, 2] else [0]) else [1]", "then [0, 1] else [0]) else [1]", 1)]),
 ("S4_hb2_block", "hb2 ignores the outer block (couples different o)", [("if t.2 == s.2 && t.1 == s.1 ^^^ 15", "if t.1 == s.1 ^^^ 15", 1)]),
]

def run(args):
    scratch, (mid, desc, edits) = args
    d = pathlib.Path(scratch) / mid
    d.mkdir(parents=True, exist_ok=True)
    text = base_text()
    for old, new, cnt in edits:
        c = text.count(old)
        if c != cnt:
            return dict(id=mid, desc=desc, error=f"pattern count {c} != {cnt}: {old!r}")
        text = text.replace(old, new)
    f = d / "Mut.lean"
    f.write_text(text)
    t0 = time.time()
    r = subprocess.run(["taskset", "-c", "0-9", "/usr/bin/time", "-f", "%M", "lean", str(f)], capture_output=True, text=True, timeout=900, cwd=str(REPO / "lean"))
    dt = time.time() - t0
    rss_kb = int(r.stderr.strip().splitlines()[-1]) if r.stderr.strip() else -1
    lines = text.splitlines()
    thm_at = [(i + 1, re.match(r"theorem (\w+)", l).group(1)) for i, l in enumerate(lines) if re.match(r"theorem (\w+)", l)]
    failed, other = [], []
    for m in re.finditer(r"Mut\.lean:(\d+):(\d+): error: (.*)", r.stdout):
        ln = int(m.group(1))
        prev = [n for (k, n) in thm_at if k <= ln]
        if prev and (ln - [k for (k, n) in thm_at if k <= ln][-1]) <= 12:
            failed.append(prev[-1])
        else:
            other.append((ln, m.group(3)[:120]))
    failed = sorted(set(failed))
    passed = [t for t in THEOREMS if t not in failed]
    return dict(id=mid, desc=desc, wall_s=round(dt, 1), peak_rss_gb=round(rss_kb / 1e6, 2), returncode=r.returncode,
                failed=failed, passed=passed, other_errors=other, tail=r.stdout[-600:], stderr_tail=r.stderr[-300:])

if __name__ == "__main__":
    scratch, jobs = sys.argv[1], int(sys.argv[2])
    only = set(sys.argv[3:])
    muts = [m for m in MUT if not only or m[0] in only]
    with cf.ThreadPoolExecutor(jobs) as ex:
        res = list(ex.map(run, [(scratch, m) for m in muts]))
    out = pathlib.Path(scratch) / "mutation_results.json"
    out.write_text(json.dumps(res, indent=1))
    for r in res:
        print(r["id"], "|", r.get("error") or ("FAILED: " + ",".join(r["failed"]) if r["failed"] else "none failed"), "|", r.get("wall_s"), "s", r.get("peak_rss_gb"), "GB", r.get("other_errors") or "")
