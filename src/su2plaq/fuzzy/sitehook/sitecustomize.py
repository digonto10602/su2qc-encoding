"""Interpreter start-up hook for the M10 compression loop (plan 302 §2).

`su2plaq.fuzzy.compress_hook.install()` exports ``SU2PLAQ_FUZZY_HOOK=1`` and appends this directory to ``PYTHONPATH``; the sandboxed
build worker of the laptop evaluator (``python -m su2plaq.compress.evaluate --worker``) inherits both, imports this module at start-up
and thereby registers the fuzzy units, so that ``Builder(spec)`` resolves ``fuzzy_ub`` / ``fuzzy_link`` inside the sandbox.
Without the variable this module does nothing."""
import os
import sys

if os.environ.get("SU2PLAQ_FUZZY_HOOK") == "1":
    _src = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))      # <repo>/src
    if _src not in sys.path:
        sys.path.insert(0, _src)
    from su2plaq.fuzzy import compress_hook as _hook

    _hook.install()
