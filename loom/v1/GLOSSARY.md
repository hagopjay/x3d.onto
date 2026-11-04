# Glossary

Terms as Loom v1 uses them. Source IDs are in [SOURCES.md](SOURCES.md).

| Term | Meaning | Source |
|---|---|---|
| **Loom** | Makes one thing right: generator, witnesses, receipt. Scope: one artifact | DEF, LEC 6 |
| **Flywheel** | Turns a failure anywhere into a rule everywhere: incident → fact → rule → fork check → upstream on "send" | DEF, LEC 6 |
| **Knowledge graph** | The flywheel's mass: facts, rules, ontology, ledgers and memories that keep it turning when no agent runs | DEF, LEC 6 |
| **Loom heuristic** | The thesis that X3D's machine-readable rules (XSD, X3DUOM) make generate → validate → repair the natural way for AI to build in 3D | SITE |
| **Tether line** | "X3D is the 3D format an AI can be held accountable to for structure and behaviour…" (grade L) | DEF |
| **Card** | A declared input the generator weaves from: data, score, spec, recipe, style board | DEF, LEC 2 |
| **Generator** | Code that emits the artifact; the only place a fix may go (law 1) | DEF |
| **Candidate** | The exact set of files under test: runtime, generators, test code, sources, docs, vendored runtime. Identified by the sha256 of its inventory | LS2, core.py |
| **Witness** | An independent instrument that checks one kind of thing and is blind to others; it observes | DEF, LEC 3 |
| **Gate** | A predicate that decides whether work may proceed; it uses witness records | LS1 §7 |
| **Witness record** | One immutable JSON (`loom.witness/1`) per witness run: status, grade, subject_sha256, instrument, measurements, coverage, evidence hashes | LS1 §14, core.py |
| **Acceptance profile** | A named list of the witnesses a kind of delivery requires, with allowed deferrals (`loom.profile/1`) | LS1 §1, §11 |
| **Acceptance** | The check that every required witness record is present, current, green and C-graded; "a closed set of current-candidate witnesses, not a score" | IFC, accept.py |
| **Stale witness** | A record whose subject digest no longer matches the candidate | LS2 |
| **Status** | What happened: pass, fail, error (the instrument could not complete), not_run, not_applicable, deferred | LS1 §12 |
| **Grade** | How far a claim can be leaned on: C (a named tool ran), L (read or reasoned), S (suspected or model-written) | DEF, LEC 5 |
| **Synthetic** | A label for fixtures, seeded mutants and teaching data; not a grade | This consolidation |
| **Receipt (Loom Receipt v1)** | One JSON per accepted artifact (`loom.receipt/1`) binding candidate, witness records, tools, outputs, unrun witnesses, budget and the previous receipt. Unsigned | DEF, receipt.py |
| **x3dprov** | Hash-chained provenance steps inside the X3D head; lives in x3d.ML; 0.1 unsigned | DEF |
| **FACTS** | x3d.onto's graded rulebook of findings (sections A to Q) | DEF |
| **Trap** | A specific mistake already paid for once, usually one a validator passes | DEF, LEC 3 |
| **loom_gate.py** | x3d.onto's Traps witness (11 rules plus `--fork`) | DEF |
| **loomkit** | This repository's portable kit: acceptance, traps subset, fold-back check, picture protocol, receipts | kit/ |
| **Fork, the** | hagopjay/x3d_mcp, the family's Grammar and Meaning validator | MC |
| **Family pin** | The single fork tag every consumer validates against: `loom-pin-2026-11-01` (decided 1 Nov) | DEF decision 5 |
| **Lawful metric** | x3d.onto's 0-1 score: nodes in fields X3DUOM accepts, requested things exist and move, parts touch, escape hatches closed | LEC 8, MEAS |
| **Exact-fix hint** | A concrete edit (move, wrap, rename, set) attached to a validator error | MEAS, SITE |
| **Escape hatch** | A cheap way to satisfy a metric without doing the work (for example declaring profile Full) | LEC 8 |
| **Kickoff (PRE)** | What to paste before the first prompt: target, pins, traps, generator first, guardrails, witness plan, where outputs land | KICK |
| **Handoff (POST)** | The done-when the agent fills at the end; a missing item means not done | KICK |
| **First-reply check** | The agent restates target and "better", lists witnesses and first steps before starting | KICK |
| **Stop-and-show** | Points where the agent shows HagopJay before going on | KICK |
| **Send** | His explicit word before anything leaves (law 16) | DEF |
| **Stumping** | The Loom's attack step: writing prompts and rubrics whose triggers sit where models slip | STUMP; decision 3 Nov |
| **Trigger** | A criterion's "If …, this item fails" clause, with tolerance and sampling rule | STUMP |
| **Seam** | A place a model slips that a grader can measure (numbers in creative work, version traps, image specs, cross-checked outputs) | STUMP |
| **Shortcut-killer** | A derived variant that rules out a cheap route (a relit night, not a darkened day) | STUMP |
| **Mutant / repaired control** | A single-fault specimen and its fixed twin; the witness must reject one with its exact diagnostic and pass the other | BREAK |
| **Negative control** | A deliberately wrong input a gate must reject, for the intended reason | LS1 §7 |
| **Surviving control** | A negative control that passed: a broken gate | LS4 |
| **Coverage candidate** | A "clear" matrix cell: a question about who should own catching it | BREAK |
| **Debrief** | The after-action account: scope, witness inventory with boundaries, gates, receipts, incidents, lessons, what stays local | LS1-LS4 |
| **Fold-back** | What the Loom learned in a project, returned as an additions-only `tools/<name>/` patch with its counterexamples | GEAR, BREAK, CITY, LS4, IFC |
| **Fold-back kit** | A zip carrying a fold-back patch and its smoke test outside the project | LS4, IFC kits |
| **Gate kit** | Same, for a project's reusable gates (Gear, Break, Data City) | Gate-Kits |
| **Learning maturity** | How far a lesson has got: implemented locally, reproduced, proposed, inconclusive | LS1 §10 |
| **Picture review** | A model judge's output: located, image-bound, `suspected` flags; never a score | LS4 picture.py |
| **Judge of record** | HagopJay's eye and ear; model judges only flag | DEF, SPEC |
| **Gobbler** | The agent that operates the Loom (simulated today) | DEF |
| **Village Voice** | The smaller conversational model inside the Gobbler that turns villagers' wishes into petitions (planned) | DEF |
| **Petition** | A schema-checked, S-graded request from a villager; answered weave, defer or decline | DEF |
| **Gobblering** | The improvement loop: champion vs variants, witness veto, blind pairwise votes, his pick overrides | SPEC |
| **Village** | The people the Gobbler works for | DEF |
| **Demiurge** | The Gobbler demiurge page in x3d.onto, where the agent roles are simulated | DEF |
| **Valid is not visible** | Passing grammar starts inspection, never ends it (law 2) | DEF, LEC 1 |
| **Unknown is not zero** | A missing measurement stays null, never 0 (law 13) | DEF, CITY |
| **Host copy** | A test server enforcing an exact copy of the hosted-page Artifact security policy | DEF, LEC 3 |
| **SwiftShader** | Chromium's software renderer: proves the browser path runs, never GPU performance | LS1-LS4 |
| **SOURCE_DATE_EPOCH** | The standard way to declare the build date as an input | LEC 4 |
| **Spine (x3d_spine)** | The planned BigQuery dataset of runs, calls and checks | KICK |
| **MemoryRecord** | The planned single record format for the graph (claim, session, tie, artifact, coverage, note, petition, answer) | BLUE §3.2 |
