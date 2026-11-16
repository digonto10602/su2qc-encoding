"""Rishon compression loop (prompts/203 section 3.1; facade since prompts/008 step B5).  The encoding "rishon" is an entry of the shared
registry (`su2plaq.encodings.registry`); importing this package registers nothing and patches nothing.  Modules: spec, oracle, evaluate
(verdict function, worker alias), baselines, brief, round, run_candidate, robust, replay, three_layer."""
from __future__ import annotations

# provenance.EVALUATOR_FILES + the rishon files that decide a verdict (prompts/203 section 3.1): the registry entry's `evaluator_files`
from su2plaq.compress import provenance as _provenance
from su2plaq.encodings import registry as _registry
from su2plaq.rishon.compress.spec import register  # noqa: F401  (no-op, kept for callers)

RISHON_EVALUATOR_FILES: list[str] = list(_provenance.EVALUATOR_FILES) + list(_registry.info("rishon").evaluator_files)

# prompts/203 section 13 E3: the spec carries the headline-rule section.  Wrapped here, not edited in spec.py, because spec.py is hashed
# into `code_hash()` and the archive best's evaluator sha (test_M6_G1) must keep matching; see robust.py.
from su2plaq.rishon.compress import robust as _robust  # noqa: E402
from su2plaq.rishon.compress import spec as _spec  # noqa: E402

render_spec = _robust.with_headline_section(_spec.render_spec)      # registry hook `render_spec` (the spec text + the headline section)
_spec.render_spec = render_spec                                      # `spec.write_spec` renders through it


def code_hash() -> str:
    """`provenance.code_hash_for("rishon")`: the shared files followed by the ten rishon files of the registry entry."""
    return _provenance.code_hash_for("rishon")
