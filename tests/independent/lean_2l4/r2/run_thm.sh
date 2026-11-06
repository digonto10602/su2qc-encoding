#!/bin/bash
export PATH=$HOME/.elan/bin:$PATH
cd /home/digimonk/Projects/su2qc-encoding/lean
S=/tmp/claude-1000/-home-digimonk-Projects-su2qc-encoding/6f24cad7-b2eb-5b02-89d1-34310bbf63e6/scratchpad/r2
for n in angle extraZ swap phase dirty subset dupidx coef term_deleted signflip_block2 signflip_block1 target stateterm; do
  t0=$(date +%s.%N)
  out=$(timeout 1200 lake env lean $S/thm/$n.lean 2>&1 | cut -c1-260 | head -4 | tr '\n' ' ')
  t1=$(date +%s.%N)
  echo "$n | $(printf '%.0f' $(echo "$t1 - $t0" | bc)) s | $out" >> $S/thm_results.txt
done
echo DONE >> $S/thm_results.txt
