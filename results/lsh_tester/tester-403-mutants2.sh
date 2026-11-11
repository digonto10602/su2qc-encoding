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
run "M9 swap two link wires in wire map" src/su2plaq/circuits/lsh.py "wire = {i: W.LINK[i] for i in range(4)}" "wire = {i: W.LINK[(i + 1) % 4] for i in range(4)}"
run "M10 uncompute with forward transcoder instead of inverse" src/su2plaq/circuits/lsh.py "    emit(W.mirror(W.TRANSCODE))" "    emit(W.TRANSCODE)"
run "M11 corner bits: mapped to w wires (2,5,8,11) instead of 1,4,7,10" src/su2plaq/circuits/lsh.py "wire.update({4 + c: W.CBIT[c] for c in range(4)})" "wire.update({4 + c: W.WBIT[c] for c in range(4)})"
run "M12 drop metadata/with_outer: with_outer ignored (no o register)" src/su2plaq/circuits/lsh.py "([QuantumRegister(N_OUTER, \"o\")] if with_outer else [])" "([])"
restore
