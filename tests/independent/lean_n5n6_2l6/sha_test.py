"""Independent: Lean Sha256 (su2plaq_cert sha256) vs hashlib. seed 20261105."""
import hashlib, os, random, subprocess, sys, json, tempfile, time
BIN = "/home/digimonk/Projects/su2qc-encoding/lean/.lake/build/bin/su2plaq_cert"
rng = random.Random(20261105)
tmp = tempfile.mkdtemp(dir=sys.argv[1])
def lean_sha(b):
    p = os.path.join(tmp, "m.bin"); open(p, "wb").write(b)
    return subprocess.run([BIN, "sha256", p], capture_output=True, text=True, check=True).stdout.strip()
bad = []; n = 0
for L in range(0, 301):
    for rep in range(2):
        b = bytes(rng.getrandbits(8) for _ in range(L)) if rep == 0 else bytes([rng.choice([0, 255, 0x80, 0x61])]) * L
        n += 1
        if lean_sha(b) != hashlib.sha256(b).hexdigest(): bad.append(("len", L, rep))
# boundary lengths around padding multiples, big
for L in [511, 512, 513, 1000, 1023, 1024, 4095, 4096, 65535, 65536, 65537, 1_000_000, 3_000_000, 5_000_001]:
    b = bytes(rng.getrandbits(8) for _ in range(min(L, 4096))) * (L // min(L, 4096) + 1)
    b = b[:L]
    t = time.time(); got = lean_sha(b); dt = time.time() - t
    n += 1
    ok = got == hashlib.sha256(b).hexdigest()
    print("len", L, ok, f"{dt:.2f}s")
    if not ok: bad.append(("big", L))
# known vectors
for m, h in [(b"", "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"), (b"abc", "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")]:
    n += 1
    if lean_sha(m) != h: bad.append(("kat", m))
print(json.dumps({"n_messages": n, "bad": bad}))
