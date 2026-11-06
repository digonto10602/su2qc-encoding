import pathlib, hashlib, shutil
from su2plaq.compress import evaluate as E
from su2plaq.compress.spec import default_spec
P = pathlib.Path("/tmp/claude-1000/-home-digimonk-Projects-su2qc-encoding/6f24cad7-b2eb-5b02-89d1-34310bbf63e6/scratchpad/adv/programs")
UE = default_spec("twelve","UE")
f = P/"toctou.py"
A = (P/"good_UE.py").read_text(); B = (P/"cheat_subset_states.py").read_text()
f.write_text(A)
shaA = hashlib.sha256(A.encode()).hexdigest()
real = E._build_in_subprocess
def swapped(path, specs, timeout):
    pathlib.Path(path).write_text(B)       # file edited after the sha was taken, before the worker reads it
    return real(path, specs, timeout)
E._build_in_subprocess = swapped
r = E.evaluate_program(f, UE, "full")
print("sha recorded == sha(A,old content):", r.program_sha256 == shaA, "| sha(B)==recorded:", r.program_sha256 == hashlib.sha256(B.encode()).hexdigest())
print("result:", r.valid, r.reason, "(B is the cheat program: evaluated content is B)" )
