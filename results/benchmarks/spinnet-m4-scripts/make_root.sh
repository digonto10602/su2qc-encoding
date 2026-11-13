#!/bin/bash
# usage: make_root.sh <dst> <encoding> <round> [keep_gridsynth(0/1)] : scratch copy of compress/ + results/compress/<enc> with round <round> entries removed
set -e
SRC=/home/digimonk/Projects/su2qc-encoding
DST=$1; ENC=$2; RND=$3; KEEPGS=${4:-1}
rm -rf "$DST"; mkdir -p "$DST/compress" "$DST/results/compress"
for d in archive attempts briefs discoveries ideation lean programs specs; do cp -r $SRC/compress/$d "$DST/compress/$d"; done
mkdir -p "$DST/compress/cache"
if [ "$KEEPGS" = 1 ]; then cp -r $SRC/compress/cache/gridsynth "$DST/compress/cache/gridsynth"; fi
cp -r $SRC/results/compress/$ENC "$DST/results/compress/$ENC"
rm -f "$DST"/compress/archive/$ENC/entries/r$(printf %02d $RND)-*.json
python - "$DST" "$ENC" "$RND" <<'PY'
import sys, json, pathlib
dst, enc, rnd = pathlib.Path(sys.argv[1]), sys.argv[2], int(sys.argv[3])
f = dst/"compress"/"attempts"/f"{enc}.jsonl"
keep = [l for l in f.read_text().splitlines() if l.strip() and json.loads(l).get("round") != rnd]
f.write_text("\n".join(keep) + "\n")
print("attempts kept", len(keep))
PY
