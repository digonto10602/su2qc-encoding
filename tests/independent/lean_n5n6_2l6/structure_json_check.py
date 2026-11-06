import sys, json, pathlib, re
sys.path.insert(0, "/home/digimonk/Projects/su2qc-encoding/src")
from su2plaq.lean import structure as S, certify as C
from su2plaq.lean.certify import LeanCert
out = pathlib.Path(sys.argv[1]); out.mkdir(exist_ok=True, parents=True)
res = {}
# 1. on-disk structure.json
disk = json.loads(pathlib.Path("/home/digimonk/Projects/su2qc-encoding/compress/lean/structure.json").read_text())
print("on-disk provenance.structure_certificate:", disk["provenance"]["structure_certificate"], "checker_sha", disk["provenance"]["checker_sha256"][:12])
import hashlib
exe = pathlib.Path("/home/digimonk/Projects/su2qc-encoding/lean/.lake/build/bin/su2plaq_cert").read_bytes()
print("checker sha now", hashlib.sha256(exe).hexdigest()[:12])
res["disk_checker_sha_matches_current_binary"] = hashlib.sha256(exe).hexdigest() == disk["provenance"]["checker_sha256"]
# 2. schema + values
EXPECT = {"card_physical": 433, "card_link_patterns": 256, "card_two_or_more": 95, "card_closed": 2, "far_end_weighted": 17362,
          "card_supported_outer": 3153, "max_states_per_outer": 17, "dont_care_codes": 3471}
counts = pathlib.Path("/home/digimonk/Projects/su2qc-encoding/lean/Su2Plaq/Structure/Counts.lean").read_text()
errs = []
for f in disk["facts"]:
    for k in ("name", "value", "proved_by", "note"):
        if k not in f: errs.append((f.get("name"), "missing " + k))
    if f["proved_by"] not in ("decide", "native", "numerical"): errs.append((f["name"], "bad proved_by"))
    if f["proved_by"] == "decide":
        if f["value"] != EXPECT[f["name"]]: errs.append((f["name"], "value", f["value"]))
        m = re.search(r"theorem %s\b[^\n]*= (\d+)" % f["name"], counts)
        if not m or int(m.group(1)) != f["value"]: errs.append((f["name"], "Counts.lean statement", m and m.group(1)))
        if f.get("theorem") != "Su2Plaq." + f["name"]: errs.append((f["name"], "theorem ref"))
    if f["proved_by"] == "native" and "certificate" not in f: errs.append((f["name"], "no certificate ref"))
print("schema/value errors:", errs); res["schema_errors"] = errs
names = [f["name"] for f in disk["facts"]]; print("fact names:", names)
res["fact_names"] = names
# 3. forced rejection -> downgrade
S.export_structure_certificate = lambda p: pathlib.Path(p)
for status in ("rejected", "failed"):
    S.check_structure = lambda p, timeout=900.0, st=status: LeanCert(st, "forced", str(p), 0.0, "")
    p = S.write_structure_json(out / f"structure-{status}.json")
    d = json.loads(pathlib.Path(p).read_text())
    kinds = {f["name"]: f["proved_by"] for f in d["facts"]}
    nat = [n for n, k in kinds.items() if k == "native"]
    res[status] = dict(native_left=nat, decide=[n for n, k in kinds.items() if k == "decide"], numerical=[n for n, k in kinds.items() if k == "numerical"],
                       prov=d["provenance"]["structure_certificate"])
    print(status, res[status])
# 4. rendered spec with the downgraded file
import su2plaq.compress.spec as SP
SP.STRUCTURE_JSON = out / "structure-rejected.json"
text = SP.default_spec("twelve", "step").render()
sec = text.split("## Proved structure (Lean)")[1].split("## Tools")[0]
res["spec_rejected_section"] = sec
print("SPEC section when rejected:\n", sec[:900])
SP.STRUCTURE_JSON = pathlib.Path("/home/digimonk/Projects/su2qc-encoding/compress/lean/structure.json")
sec2 = SP.default_spec("twelve", "step").render().split("## Proved structure (Lean)")[1].split("## Tools")[0]
res["spec_disk_section"] = sec2
print("SPEC section (disk):\n", sec2[:2500])
# default structure_facts() claims native without checking?
res["structure_facts_default_proved_by_spectrum"] = [f["proved_by"] for f in S.structure_facts()["facts"] if f["name"] == "spectrum_multiplicities"]
print(res["structure_facts_default_proved_by_spectrum"])
json.dump(res, open(out / "structure_json_check.json", "w"), indent=1, default=str)
