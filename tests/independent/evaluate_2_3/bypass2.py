import sys, pathlib
sys.path.insert(0, "/tmp/claude-1000/-home-digimonk-Projects-su2qc-encoding/6f24cad7-b2eb-5b02-89d1-34310bbf63e6/scratchpad/adv")
from cases import prog, UE_CORE, SP
M = lambda n: str(SP / f"MARKER_{n}.bin")
PRE = "import su2plaq.compress.builder as BB\nimport numpy as np\n"
X = {}
def mk(name, body):
    X[name] = prog(f'''{PRE}
def build(spec):
    bi = BB.__builtins__
{body}
{UE_CORE}    return b
''')
mk("h_io_open", f'    f = bi["open"]("{M("io_open")}", "w"); f.write("x"); f.close()')
mk("h_io_open_append_rplus", f'    f = bi["open"]("{M("io_open2")}", "a"); f.write("x"); f.close()')
mk("h_os_open_wronly", f'    os_ = BB.pathlib.os; fd = os_.open("{M("os_open")}", os_.O_WRONLY | os_.O_CREAT); os_.write(fd, b"x"); os_.close(fd)')
mk("h_pathlib_io_open", f'    BB.pathlib.io.open("{M("pathlib_io")}", "wb").write(b"x")')
mk("h_tempfile", '    tf = bi["__import__"]("tempfile"); fd, p = tf.mkstemp(); f = tf.NamedTemporaryFile()')
mk("h_pickle_dump", f'    pk = bi["__import__"]("pickle"); pk.dump([1], bi["open"]("{M("pickle")}", "wb"))')
mk("h_marshal_dump", f'    mm = bi["__import__"]("marshal"); mm.dump([1], bi["open"]("{M("marshal")}", "wb"))')
mk("h_numpy_memmap", f'    m = np.memmap("{M("memmap")}", dtype="float64", mode="w+", shape=(4,)); m[:] = 1; m.flush()')
mk("h_numpy_open_memmap", f'    np.lib.format.open_memmap("{M("open_memmap")}", mode="w+", dtype="float64", shape=(4,))')
mk("h_sqlite3_c_level", f'    sq = bi["__import__"]("sqlite3"); c = sq.connect("{M("sqlite")}"); c.execute("create table t(x)"); c.commit(); c.close()')
mk("h_os_system", '    BB.pathlib.os.system("touch ' + M("os_system") + '")')
mk("h_subprocess", '    sp = bi["__import__"]("subprocess"); sp.run(["touch", "' + M("subprocess") + '"])')
mk("h_os_remove_existing", f'    BB.pathlib.os.remove("{SP}/programs/good_UE.py.copy")')
mk("h_os_mkdir", f'    BB.pathlib.os.mkdir("{SP}/MARKER_dir")')
mk("h_socket", '    s = bi["__import__"]("socket"); s.socket().connect(("127.0.0.1", 9))')
mk("h_ctypes_loaded_by_numpy", '    ct = bi["__import__"]("ctypes"); lib = ct.CDLL(None); lib.puts(b"hi")')
mk("h_ctypes_pythonapi", f'    ct = bi["__import__"]("ctypes"); ct.pythonapi.PyRun_SimpleString(b"open(\'{M("ctypes_pyapi")}\',\'w\').write(\'x\')")')
mk("h_reading_etc_passwd_allowed", '    t = bi["open"]("/etc/hostname").read()')
# attacks on the hook itself
mk("h_patch_realpath", f'''    os_ = BB.pathlib.os; out = BB.pathlib.sys.argv[4]
    os_.path.realpath = lambda p: out
    bi["open"]("{M("patch_realpath")}", "w").write("x")''')
mk("h_patch_isinstance", f'''    bi["isinstance"] = lambda *a, **k: False
    import builtins
    bi["open"]("{M("patch_isinstance")}", "w").write("x")''')
mk("h_gc_mutate_hook_closure", f'''    gc = bi["__import__"]("gc")
    for o in gc.get_objects():
        if getattr(o, "__name__", "") == "hook" and getattr(o, "__closure__", None):
            o.__closure__[0].cell_contents.add(BB.pathlib.os.path.realpath("{M("gc_hook")}"))
    bi["open"]("{M("gc_hook")}", "w").write("x")''')
mk("h_sys_modules_tamper", f'''    sysm = BB.pathlib.sys.modules
    sysm.pop("os", None); sysm["os"] = None
    BB.pathlib.sys.addaudithook(lambda e, a: None)
    bi["open"]("{M("sysmod")}", "w").write("x")''')
mk("h_overwrite_result_files_then_exit", f'''    out = BB.pathlib.sys.argv[4]; meta = BB.pathlib.sys.argv[5]
    bi["open"](meta, "w").write('{{"discoveries": [[]]}}')
    BB.pathlib.os._exit(0)''')
for k, v in X.items(): (SP/"programs"/f"{k}.py").write_text(v)
(SP/"programs"/"good_UE.py.copy").write_text("x")
print(len(X), list(X))
