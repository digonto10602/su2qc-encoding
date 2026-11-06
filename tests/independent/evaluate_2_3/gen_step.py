import numpy as np, pathlib
from su2plaq.circuits import twelve as C
from su2plaq.compress.spec import default_spec
spec = default_spec("twelve","step")
pairs = [(spec.alpha, spec.beta)] + list(spec.alt_angles)
cs = [C.build_step(a, b, 1, with_outer=True) for a, b in pairs]
print("num qubits", cs[0].num_qubits, "ops", len(cs[0].data))
def ops(c): return [(i.operation.name, [float(p) for p in i.operation.params], tuple(c.find_bit(q).index for q in i.qubits)) for i in c.data]
O = [ops(c) for c in cs]
assert all([(n, q) for n, p, q in o] == [(n, q) for n, p, q in O[0]] for o in O)
lines = []
M = np.array([[a, b] for a, b in pairs] + [[1, 0]])
for k, (n, p, q) in enumerate(O[0]):
    if p:
        ang = [o[k][1][0] for o in O]
        # fit angle = ca*alpha + cb*beta on first two, check on the third
        sol = np.linalg.solve(np.array(pairs[:2]), ang[:2])
        res = abs(np.dot(sol, pairs[2]) - ang[2])
        assert res < 1e-12, (n, k, res)
        lines.append((n, tuple(sol), q))
    else:
        lines.append((n, None, q))
src = ['"""SUMMARY: build_step(0.37, 0.61) wrapped as a program (timing test)\n"""', 'FAMILY = "T"', 'PARENT = None', '',
       'from su2plaq.compress.builder import Builder', '', 'OPS = [']
for n, sol, q in lines:
    src.append(f"    ({n!r}, {None if sol is None else tuple(float(x) for x in sol)!r}, {q!r}),")
src += [']', '', 'def build(spec):', '    b = Builder(spec)', '    for name, c, qs in OPS:',
        '        if c is None:', '            getattr(b, name)(*qs)', '        else:', '            getattr(b, name)(c[0] * spec.alpha + c[1] * spec.beta, *qs)', '    return b', '']
pathlib.Path("/tmp/claude-1000/-home-digimonk-Projects-su2qc-encoding/6f24cad7-b2eb-5b02-89d1-34310bbf63e6/scratchpad/adv/programs/step_program.py").write_text("\n".join(src))
print("written", len(lines))
