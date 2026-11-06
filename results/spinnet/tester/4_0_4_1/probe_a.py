import sys, importlib, pkgutil, json, copy
import su2plaq, su2plaq.compress, su2plaq.lean, su2plaq.encodings
mods = {}
for pkg in (su2plaq.compress, su2plaq.lean, su2plaq.encodings):
    for m in pkgutil.iter_modules(pkg.__path__, pkg.__name__ + "."):
        try: mods[m.name] = importlib.import_module(m.name)
        except Exception as e: print("skip", m.name, e)
def snap():
    out = {}
    for n, m in mods.items():
        for k, v in vars(m).items():
            out[(n, k)] = (id(v), repr(v)[:200] if isinstance(v, (set, frozenset, tuple, list, str, int, float, dict)) and k not in ("_ENCODINGS","NOMINAL_ANGLES") else None)
    return out
from su2plaq.compress import evaluate as E
from su2plaq.encodings import base
from su2plaq.compress import spec as S
before = snap()
wl0 = (sorted(E.ALLOWED_PROJECT_IMPORTS), sorted(E.FORBIDDEN_NAMES))
enc0 = sorted(S._ENCODINGS); nom0 = dict(base.NOMINAL_ANGLES)
for n in dir(E):
    if "ALLOW" in n.upper() or "FORBID" in n.upper(): print("evaluate const", n)
from su2plaq.spinnet import loop
loop.install(); loop.install()
after = snap()
changed = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
print("CHANGED attributes in compress/lean/encodings modules:")
for k in changed: print("  ", k)
print("whitelist unchanged:", wl0 == (sorted(E.ALLOWED_PROJECT_IMPORTS), sorted(E.FORBIDDEN_NAMES)), wl0)
print("encodings before/after:", enc0, sorted(S._ENCODINGS)); print("nominal diff:", {k:v for k,v in base.NOMINAL_ANGLES.items() if nom0.get(k)!=v})
print("INSTALLED keys:", sorted(loop.INSTALLED))
# worker-time view
seen = {}
def fake(*a):
    seen["wl"] = (sorted(E.ALLOWED_PROJECT_IMPORTS), sorted(E.FORBIDDEN_NAMES)); seen["args"] = a
E._worker = fake
loop.main(["--worker", "p", "s", "o", "m"])
print("worker-time whitelist equal to parent-before:", seen["wl"] == wl0, seen["args"])
