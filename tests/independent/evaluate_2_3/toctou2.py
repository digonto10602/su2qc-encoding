import pathlib, hashlib
from su2plaq.compress import evaluate as E
from su2plaq.compress.spec import default_spec
P = pathlib.Path("/tmp/claude-1000/-home-digimonk-Projects-su2qc-encoding/6f24cad7-b2eb-5b02-89d1-34310bbf63e6/scratchpad/adv/programs")
UE = default_spec("twelve","UE")
f = P/"toctou.py"
A = (P/"good_UE.py").read_text(); B = (P/"cheat_subset_states.py").read_text()
shaA = hashlib.sha256(A.encode()).hexdigest(); shaB = hashlib.sha256(B.encode()).hexdigest()
real = E._build_in_subprocess
for label, first, second in (("A=good then swapped to B=cheat", A, B), ("A=cheat then swapped to B=good", B, A)):
    f.write_text(first)
    def swapped(source, specs, timeout):
        f.write_text(second)           # edit after the sha was taken and before/while the worker runs
        return real(source, specs, timeout)
    E._build_in_subprocess = swapped
    r = E.evaluate_program(f, UE, "full")
    sa = hashlib.sha256(first.encode()).hexdigest()
    print(label, "| recorded==sha(first):", r.program_sha256 == sa, "| valid:", r.valid, r.reason, "| expected valid:", first is A)
E._build_in_subprocess = real
