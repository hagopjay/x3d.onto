# DSPy records found in the Mac Google Drive sync folder (read-only, 27 Oct 2026)
Folder: Drive `1PhP_95V7n5UIRbyewnflJUzRCOyevnJY` (owner: the Mac account), subfolder `bundle/dspy/`, 6 files, all created 24 Oct 2026. Nothing was changed or deleted on Drive. Grades: C confirmed from the files read, L likely, S suspected.

| file | what it is |
|---|---|
| EVAL_PLAN.md | DSPy-style eval design for the Shroud radiation-event hypothesis lab (spike of 21 Oct): three signatures, planted tasks, splits, optimiser order, Goodhart guard, stopping rules |
| sim.py, constraints.py, constraints.json, baselines.json, propose_eval.py | forward simulator, 10 ledger-derived constraints (5 TRAIN, 3 HELD-OUT, 2 unscored), random-search baselines, planted-task proposer eval |
Only EVAL_PLAN.md was read in full. The other five were listed, not opened.

## How it fits our DSPy records
1. **Same method, new domain.** The plan's ProposeMechanism metric (simulator fit on TRAIN, report HELD-OUT separately) is the pattern we use for the validator: optimise on one split, select on another. Its Goodhart guard cites our `profile='Full'` finding (a gamed validator metric) directly. (C)
2. **Its lesson matches ours.** "TRAIN is not discriminating": 14 of 16 mechanism families reach 0.98 to 1.00 by random search. Same shape as our E-G result (optimising for the ladder's output gave no gain over seed plus ladder) and as the 0.8% yield of the placement and USE-type terms in `RESULTS.md`: a term that cannot separate candidates adds feedback, not signal. (L)
3. **Open item it states and we can fill.** "The DSPy library is not installed" and L3 (BootstrapFewShot, then MIPROv2, ledger-capped at about $5-10) is not run. DSPy 3.4.1 with GEPA and a ledger-capped Gemini wrapper (`vertex_lm.py`, research/dspy-2026-10-17/code) already exist and ran for $4.83 on the scene-writing prompt here. Reusable pieces: GEPA feedback-as-text from failed test ids, per-run cap, the A/B on held-out items, and the check that a candidate prompt does not smuggle the held-out answer in (our prompt audit idea).
4. **Gaps, not done.** (a) No DSPy run has touched the radiation lab; the planted-task proposer eval is only a baseline. (b) The B32 transcription issue (0.4 J/cm2 / 33 ns = 12.1 MW/cm2, row says 16) is the lab's, not ours; not adjudicated. (c) The plan's "agreement with human labels on a seed set" for CritiqueRender is the same calibration gap as the picture-judge spec (Claude Doc f484ec0f-df8f-4ece-9a03-ce26605a5568).

Added only; no existing record was replaced.

## Added after a sibling thread's Drive listing (27 Oct ~21:15Z)
- Same six `bundle/dspy/` files confirmed; also staged on the Mac but not uploaded: DOC.md (79,404 B) and README (27)-(30). The Shared Drive Shroud export folder holds older copies (DOC.md 46,933 B vs rev 70 here: compare by hash before trusting either).
- The Mac catalog's open items P1-6 (BootstrapFewShot/MIPROv2 on planted tasks; a writer prompt with a lawful metric and closed escape hatches, on the 1,200 Polys trials, vs few-shot 6%) are already measured here: Full-barred prompt 30% vs few-shot 6% on Polys prompts 5-9, repair ladder v4 83.7 to 86.9% on the test half. The Mac agent likely lacks the later ladder and rung results (S). Full sibling list: /mnt/project-files/ontology-extraction/DRIVE-DSPY-RECORDS-2026-10-27.md.
