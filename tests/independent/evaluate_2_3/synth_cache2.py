import json, pathlib, tempfile, hashlib, numpy as np
from importlib.metadata import version
import importlib.metadata as im
from su2plaq.compress import synth as S
from su2plaq.metrics.cliffordt import pygridsynth_word, word_error
td = pathlib.Path(tempfile.mkdtemp(dir="/tmp/claude-1000/-home-digimonk-Projects-su2qc-encoding/6f24cad7-b2eb-5b02-89d1-34310bbf63e6/scratchpad"))
S.CACHE_DIR = td / "gs"
out = {}
th, eps = 0.4321, 1e-6
w = S.gridsynth_word(th, eps); T = w.count("T")
files = list(S.CACHE_DIR.iterdir()); f = files[0]
out["entry_format"] = sorted(json.loads(f.read_text()).keys()); out["n_files"] = len(files); out["T_good"] = T
ver = version("pygridsynth")
def entry(word, theta=th, e=eps, fixsum=True, v=ver):
    d = {"version": v, "theta": repr(float(theta)), "eps": repr(float(e)), "word": word, "sha256": S._checksum(v, theta, e, word) if fixsum else "0"*64}
    return json.dumps(d)
cases = {
 "garbage_text": "HTHTHTHT",
 "empty_file": "",
 "truncated_json": entry(w)[:60],
 "binary_junk": None,
 "bad_checksum_word_tampered": json.dumps({**json.loads(entry(w)), "word": w[:-3] + "TTT"}),
 "wrong_checksum_literal": entry(w, fixsum=False),
 "alphabet_violation_valid_checksum": entry("HT?SH"),
 "garbage_word_valid_checksum": entry("HTHTHTHTHTHTHTHTHTHTHTHTHTHT"),
 "empty_word_valid_checksum": entry(""),
 "word_for_other_angle_valid_checksum": entry(pygridsynth_word(1.234, eps)),
 "word_for_other_angle_old_checksum": json.dumps({**json.loads(entry(w)), "word": pygridsynth_word(1.234, eps)}),
 "other_version_entry": entry(w, v="0.0.1"),
 "other_eps_field": entry(w, e=1e-4),
 "other_theta_field": entry(w, theta=0.4322),
 "wrong_types": json.dumps({"version": ver, "theta": 1, "eps": 2, "word": 3, "sha256": 4}),
 "json_list": "[1,2,3]",
 "old_txt_style_file_ignored": None,
}
res = {}
for nm, content in cases.items():
    if nm == "binary_junk": f.write_bytes(bytes(range(256)))
    elif nm == "old_txt_style_file_ignored":
        (S.CACHE_DIR/(f.stem + ".txt")).write_text("HTHT"); f.unlink()
    else: f.write_text(content)
    try:
        got = S.gridsynth_word(th, eps)
        res[nm] = dict(returned_equals_good=(got == w), T=got.count("T"), word_err=float(word_error(got, th)), repaired=json.loads(f.read_text())["word"] == got)
    except Exception as e:
        res[nm] = dict(exception=f"{type(e).__name__}: {e}")
    print(nm, res[nm], flush=True)
out["cases"] = res
# keying
before = len(list(S.CACHE_DIR.glob("*.json")))
S.gridsynth_word(float(np.nextafter(th,1)), eps); S.gridsynth_word(th, eps*1.0000001)
orig = im.version; im.version = lambda n: "9.9.9" if n == "pygridsynth" else orig(n)
S.gridsynth_word(th, eps); im.version = orig
out["n_json_before"] = before; out["n_json_after_theta_eps_version_variants"] = len(list(S.CACHE_DIR.glob("*.json")))
out["all_ok"] = all(r.get("returned_equals_good") for r in res.values())
print(out["all_ok"], out["n_json_before"], out["n_json_after_theta_eps_version_variants"])
json.dump(out, open("/tmp/claude-1000/-home-digimonk-Projects-su2qc-encoding/6f24cad7-b2eb-5b02-89d1-34310bbf63e6/scratchpad/adv/synth_cache2.json","w"), indent=1)
