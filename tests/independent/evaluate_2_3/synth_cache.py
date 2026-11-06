import json, pathlib, tempfile, hashlib, numpy as np, sys
from importlib.metadata import version
from su2plaq.compress import synth as S
from su2plaq.metrics.cliffordt import pygridsynth_word, word_error
out = {}
td = pathlib.Path(tempfile.mkdtemp(dir="/tmp/claude-1000/-home-digimonk-Projects-su2qc-encoding/6f24cad7-b2eb-5b02-89d1-34310bbf63e6/scratchpad"))
S.CACHE_DIR = td / "gs"
th, eps = 0.4321, 1e-6
w = S.gridsynth_word(th, eps)
files = list(S.CACHE_DIR.iterdir()); out["n_files_after_first"] = len(files)
# key = version|theta|eps
key = f"{version('pygridsynth')}|{float(th)!r}|{float(eps)!r}"
out["file_name_matches_key"] = files[0].name == hashlib.sha256(key.encode()).hexdigest() + ".txt"
# exact theta: nextafter / other eps -> different entries
S.gridsynth_word(float(np.nextafter(th, 1)), eps); S.gridsynth_word(th, eps*1.0000001)
out["n_files_after_theta_eps_variants"] = len(list(S.CACHE_DIR.iterdir()))
# version in key: fake version
import importlib.metadata as im
real = S.__dict__.get("version")
orig = im.version
im.version = lambda n: "9.9.9" if n == "pygridsynth" else orig(n)
S.gridsynth_word(th, eps)
out["n_files_after_fake_version"] = len(list(S.CACHE_DIR.iterdir()))
im.version = orig
# corruption 1: garbage
f = files[0]
good_T = w.count("T")
f.write_text("HTHTHTHTHTHTHTHTHTHTHTHTHTHT")
got = S.gridsynth_word(th, eps)
out["corrupt_garbage_word_returned"] = got[:20]; out["corrupt_garbage_trusted"] = (got != w); out["T_good"] = good_T; out["T_after_corrupt"] = S.gridsynth_T(th, eps)
# corruption 2: empty file / non-word text
f.write_text("")
out["corrupt_empty_returned_repr"] = repr(S.gridsynth_word(th, eps)); out["corrupt_empty_trusted"] = (S.gridsynth_word(th, eps) != w)
f.write_text("not a word ###")
out["corrupt_text_returned_repr"] = repr(S.gridsynth_word(th, eps))
# a valid-looking word for another angle (word_error check)
w2 = pygridsynth_word(1.234, eps); f.write_text(w2)
got = S.gridsynth_word(th, eps)
out["wrong_angle_word_trusted"] = (got == w2); out["word_error_of_returned_vs_theta"] = float(word_error(got, th))
# metrics path with corrupted cache gives wrong T_eps
out["pygridsynth_version"] = version("pygridsynth")
print(json.dumps(out, indent=1))
json.dump(out, open("/tmp/claude-1000/-home-digimonk-Projects-su2qc-encoding/6f24cad7-b2eb-5b02-89d1-34310bbf63e6/scratchpad/adv/synth_cache.json","w"), indent=1)
