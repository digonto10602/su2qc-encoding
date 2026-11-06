/-!
# Su2PlaqCert.Structure — structure certificate checker (prompts/006 §4; step 2.L6)

Skeleton: filled in by step 2.L6.  Until then every structure certificate is rejected.
-/
namespace Su2PlaqCert

def checkStructurePath (_path : String) : IO (Option String) :=
  pure (some "structure checker not implemented yet (step 2.L6)")

end Su2PlaqCert
