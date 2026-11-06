# Ideation brief: `spinnet` / `step`

Read the task specification `compress/specs/spinnet-step.md` and nothing else about previous solutions (no seeds, no archive).
Proved structure (Lean): the section 'Proved structure (Lean)' of the specification (kernel-checked facts about the spin-network problem; there is no separate structure file).

Write `compress/ideation/spinnet.md`: at most 5 families, one datapath idea each (what the registers hold, which gates carry the weight, why it should beat a generic circuit), most promising first. Use the oracle (`python -m su2plaq.spinnet.loop oracle ...`) to look at the target; write scratch files only under `scratch/proposer/`. Do not write programs in this session.
