# Tester report 002 — M0 step 0.2 (geometry)

- Date: 2026-11-04
- Git commit: 5bda416 (+ uncommitted step files: `src/su2plaq/geometry.py`, `tests/unit/test_geometry.py`, `tests/unit/test_import.py`)
- Prompt in force: `prompts/002-m0-m2-foundation-twelve-qubit-compression.md` (§2.1, §3 row 0.2)
- Mode: step
- Related: `reports/tests/001-m0-step-0-1-scaffold.md`
- Raw numbers: `results/m0_step02_geometry_indep.json`

## Commands
```
source ~/anaconda3/etc/profile.d/conda.sh && conda activate coding
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
graphify update . ; graphify affected "point_split" ; graphify query "geometry plaquette_diagram usage"
pytest -n auto tests/unit
pytest tests/acceptance/m0/test_geometry.py -v
pytest -n auto tests/acceptance -q --junitxml=<scratch>/acc.xml     # classified PENDING vs other from the XML
pytest --collect-only -q tests/acceptance
python tools/check_lock.py && ~/.claude/bin/acceptance-check
python <scratch>/indep_geom.py      # independent re-derivation of the geometry from note s1
```
`graphify affected point_split`: only `tests/unit/test_geometry.py`; `Diagram` is imported by `src/su2plaq/exact/physical.py` (still a stub), so no other code is affected yet.

## Results
| check | expected | got | tolerance | verdict |
|---|---|---|---|---|
| `m0/test_geometry.py::test_M0_G1_diagram` | pass | pass | exact | PASS |
| `m0/test_geometry.py::test_M0_G2_point_split` | pass | pass | exact | PASS |
| unit tests `tests/unit` | all pass | 46 passed | — | PASS |
| acceptance suite, other tests | PENDING or the 3 known R1 AssertionErrors | 79 PENDING (NotImplementedError), 3 AssertionError = `test_M1_R1_results_files[step/UE/UB]` (missing `results/twelve/*.json`), 2 passed (G1, G2) | — | PASS (no new failures) |
| `--collect-only` | 84 tests, clean | 84 collected | — | PASS |
| `tools/check_lock.py` | LOCK OK | LOCK OK | — | PASS |
| `acceptance-check` | PASS | PASS, matches acceptance-v2 | — | PASS |
| independent geometry check (34 sub-checks, below) | 34/34 | 34/34 | exact | PASS |

### Independent geometry check (all against `refs/su2_plaquette_truncations_encodings.md` §1, not against the builder's tests)
- Each link $U_\mu(x)$ is re-derived as start $x$, end $x+\hat\mu$ ($\hat1=(1,0)$, $\hat2=(0,1)$): all 12 links match (start, end, hence direction).
- Each outer link has exactly one end on a corner. `near_end` = 'L' for o2, o4, o5, o7 (start at corner), 'R' for o0, o1, o3, o6 (end at corner): matches.
- Corner ends re-derived from the endpoints: set equality for all 4 corners; each has 2 inner + 2 outer ends, ordered inner-then-outer and by increasing link index. The 16 (link, role) pairs each occur in exactly one corner.
- Loop: the list `[(b,+),(r,+),(t,-),(l,-)]` is a closed path $(0,0)\to(1,0)\to(1,1)\to(0,1)\to(0,0)$, which is $U_P=U_bU_rU_t^\dagger U_l^\dagger$.
- Point-split graph: 8 sites, edge ids exactly 0..15, every one of the 8 sites has degree 3. At each corner $c$ the `('in',c)` site carries exactly the corner's two inner ends and `('out',c)` exactly its two outer ends (the (inner|outer) pairing). Virtual edge $12+c$ runs `('in',c)` to `('out',c)`. Real edges follow link direction (start site, end site). Inner pairs per corner are $c_0:\{b,l\}$, $c_1:\{b,r\}$, $c_2:\{r,t\}$, $c_3:\{t,l\}$, as in METHODS §5.
- `corner_of_end` is consistent with all 16 ends and raises `ValueError` on a non-corner end.

Note on one apparent discrepancy (not a code defect): the note's §1 text lists the last four outer links as $U_1(-1,1),U_2(0,1),U_1(1,1),U_2(1,1)$; prompts/002 §2.1 and METHODS §1 (and the locked test) index them in corner order as $o_4=U_1(1,1)$, $o_5=U_2(1,1)$, $o_6=U_1(-1,1)$, $o_7=U_2(0,1)$. The builder follows the plan. The set of 8 outer links is identical to the note's.

## The `('ext', i)` pseudo-sites
- prompts/002 §2.1 only fixes `SplitGraph.edges: dict[int, tuple[tuple[str,int], tuple[str,int]]]`, 16 edges, and that the 8 sites are `('in',c)`/`('out',c)`. It says nothing about the far end of an outer link.
- No other locked test touches `point_split`, `SplitGraph` or `geometry` (grep over `tests/acceptance/m0, m1, m2`: only G1 and G2). G2 only reads `a[0]`/`b[0]`, tests membership `a in deg`, and asserts `g.sites` has 8 entries; `('ext', i)` is compatible with all of that (it is a `(str,int)` tuple not in `g.sites`, and sites keep degree 3). So the choice is allowed but not constrained.
- Caveat for later steps: edges of outer links reference names that are not in `g.sites`; any consumer that indexes `sites` by every edge endpoint must filter `site[0] != 'ext'`. The docstring says so. `src/su2plaq/spinnet/` consumers (step 0.8) should be told.

## Problems
None. No new failures against report 001.
