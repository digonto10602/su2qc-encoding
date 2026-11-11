#!/bin/bash
# Tester 403 (d): mutants run on a COPY of the repo (scratchpad/mut); the real src/ and lean/ are never touched.

S=/tmp/claude-1000/-home-digimonk-Projects-su2qc-encoding/57b28677-d814-4f58-bc95-52ae378eb01f/scratchpad
M=$S/mut; R=/home/digimonk/Projects/su2qc-encoding
source ~/miniforge3/etc/profile.d/conda.sh && conda activate coding
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
restore() { cp $R/src/su2plaq/circuits/lsh.py $M/src/su2plaq/circuits/lsh.py; cp $R/src/su2plaq/lsh/lean_export.py $M/src/su2plaq/lsh/lean_export.py; cp $R/lean/Su2Plaq/LSH/Circuit.lean $M/lean/Su2Plaq/LSH/Circuit.lean; }
run() { # name file old new
  restore
  python - "$M/$2" "$3" "$4" <<'PY'
import sys
p, old, new = sys.argv[1:4]
s = open(p).read()
assert s.count(old) >= 1, ("pattern not found", old)
open(p, "w").write(s.replace(old, new, 1))
PY
  echo "=== MUTANT $1"
  (cd $M && taskset -c 14-19 python -m pytest -x -q -n 4 -p no:cacheprovider tests/unit/test_lsh_circuits_unit.py tests/unit/test_lsh_lean_export_unit.py tests/unit/test_lsh_walk_unit.py 2>&1 | grep -E "^(FAILED|ERROR)|passed|failed" | head -4)
  echo "--- acceptance V1/L2 subset"
  (cd $M && taskset -c 14-19 python -m pytest -q -n 4 -p no:cacheprovider tests/acceptance/m7/test_lsh_external.py "tests/acceptance/m7/test_lsh_lean.py::test_M7_L2_general_circuit_structure_kernel_checked" 2>&1 | grep -E "^(FAILED|ERROR)|passed|failed" | head -5)
}
run "M1 drop inverse transcoder" src/su2plaq/circuits/lsh.py "    emit(W.mirror(W.TRANSCODE))
    qc.metadata" "    qc.metadata"
run "M2 drop forward transcoder" src/su2plaq/circuits/lsh.py "    emit(W.TRANSCODE)
    qc.compose" "    qc.compose"
run "M3 swap two corner-bit wires in wire map" src/su2plaq/circuits/lsh.py "wire.update({4 + c: W.CBIT[c] for c in range(4)})" "wire.update({4 + c: W.CBIT[(c + 1) % 4] for c in range(4)})"
run "M4 ancilla offset ignores outer register" src/su2plaq/circuits/lsh.py "off = N_DATA + N_OUTER if with_outer else N_DATA" "off = N_DATA"
run "M5 swap two lshCoupling entries in Circuit.lean" lean/Su2Plaq/LSH/Circuit.lean "def lshCoupling : List Int := [-4, 2, 2, 2, 0, -4" "def lshCoupling : List Int := [-4, 2, 2, 0, 2, -4"
run "M6 one lshAngles int changed in Circuit.lean" lean/Su2Plaq/LSH/Circuit.lean "[-7, -2, 6, 3]" "[-7, -2, 6, 4]"
run "M7 exporter angle_ints returns wrong int (sign)" src/su2plaq/lsh/lean_export.py "def angle_ints(enc) -> list:" "def angle_ints(enc) -> list:
    return [-7, -2, 6, 3][::-1]
def _angle_ints_orig(enc) -> list:"
run "M8 swap two partner entries in Circuit.lean" lean/Su2Plaq/LSH/Circuit.lean "def lshPartner : List Nat := [585, 596," "def lshPartner : List Nat := [596, 585,"
restore
