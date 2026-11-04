# The X3D Loom, version 1

The single authoritative definition, consolidated on 3 November 2026 from the Drive folder, the other model's project zips and PR patches, and the notes on this Mac. It replaces no source: every source stays where it is, and this file says which one each statement comes from.

**How to read it.**
- **Citations** look like `[DEF §Laws]`: a source ID (defined in [SOURCES.md](SOURCES.md)) and a section. `[KIT …]` means this repository's own runs, under `runs/`.
- **Grades** stay C / L / S, as every source and the code use them (user decision, 3 Nov):

| Grade | Means | Who may give it | Brief's word |
|---|---|---|---|
| **C** | A named tool ran and showed it; the tool and version are named | A witness run | Measured |
| **L** | Read in code or a document, or reasoned, not run | Any agent, naming file and line | Established (read) or Estimate (reasoned number) |
| **S** | Suspected; a hunch; **anything a model wrote**; any creative judgment | Anyone; every model output starts here | Conjecture |

- **Synthetic** is a separate label, never a grade. It marks fixtures, seeded mutants and teaching data (for example Data City's 64 records, Break-the-Loom's 24 specimens, loomkit's test fixtures). A C result on a synthetic fixture is a fact about the instrument, not about the world.
- A number carried over from a source keeps that source's grade. Only a witness run raises a grade; anyone may lower one; grade changes are appended with a reason, never edited in place [DEF §Grades].
- **Status** is a second axis, orthogonal to grade: `pass`, `fail`, `error`, `not_run`, `not_applicable`, `deferred` [LS1 §12]. A C-graded fail is valuable evidence; an S-graded design choice cannot satisfy a required measured witness.

---

## 1. Purpose

**What the Loom is.** The Loom is how this project makes 3D worlds an AI can be held accountable to. A generator weaves each world from cards (data, spec, code); independent witnesses inspect it from every side; a receipt proves how it was made; and every failure becomes a rule, so no project pays for the same mistake twice [DEF §What the Loom is].

**The tether line** (grade L, proposed by the 29 Oct grand review): "X3D is the 3D format an AI can be held accountable to for structure and behaviour. For appearance, accountability takes a browser and an eye, and the Loom keeps all three in one loop" [DEF §What the Loom is].

**Why X3D: the loom heuristic.** X3D's rules are published as machine-readable XML (the XSD schema and the X3D Unified Object Model, X3DUOM), so software can check a scene an AI writes and say exactly what to fix. The generate, validate and repair loop is what makes X3D a natural spec for AI building in 3D [SITE thesis; MEAS §Headline].

**Three words, three jobs** (HagopJay's split, 30 Oct) [LEC 6; DEF §What the Loom is]:

| Word | Its one job | Scope |
|---|---|---|
| **Loom** | Make one thing right: generator, witnesses, receipt | One artifact |
| **Flywheel** | Turn a failure anywhere into a rule everywhere | All artifacts, over time |
| **Knowledge graph** | Store the flywheel's momentum so it turns when no agent is running | Everything ever learned |

Selection is what makes the graph evolve rather than hoard: grades decide how far a memory can be trusted, and two-sided tests decide whether a rule survives real files [LEC 6].

**The founding image.** Jacquard's 1804 loom wove from punched cards: to change the cloth you punched a new card, you never took scissors to the cloth. That is law 1 [LEC 2].

---

## 2. Roles

### 2.1 The human (HagopJay)

| Role | What only the human does | Source |
|---|---|---|
| Curator | Decides what is woven; models only propose | [DEF §Who does what] |
| Judge of record, eye and ear | His look and his listen decide taste. Picture judges and audio critics flag; he picks, and each pick is logged as a gold label | [DEF §Witnesses, Eyes; SPEC §Gobblering] |
| The "send" | Nothing leaves (upstream PRs, emails, public pushes, publication) without his explicit "send" | [DEF law 16; KICK §PRE 5] |
| The "yes" | Typed yes before any new cloud resource, quota or role, any delete, anything public, any paid model, going past the budget cap | [KICK §PRE 5; DEF §Decisions] |
| Decision maker | Answers the decision table; answers are quoted verbatim and dated | [DEF §Decisions for HagopJay] |

### 2.2 The models

| Role | Who has played it | Rule | Source |
|---|---|---|---|
| Builder agent: plans, writes generators, runs witnesses, repairs, debriefs | the builder model (Dynasty Loom, demiurge, a hosted model measurements); the other model, a second vendor's, by its own receipts (Loomsong Study 01 to v4, Gear, Break, Data City, IFC studio); a hosted model as writer in the measurements | Writes S; acts only through generators and witnesses; at most 3 agents at once | [DEF §Agent architecture; LS1 §16 "<vendor> session usage is excluded"; DEF law 12] |
| Judge (picture, audio, adjudication) | model F and model P; blinded model reviewers for labels | **Flags only**: located, image-bound, state `suspected`; never a number in a release (user decision, 3 Nov) | [MEAS; LS4 picture.py; IFC release_contract.py] |
| Optimiser | DSPy GEPA against the lawful metric | Runs offline, on his yes; the metric's escape hatches are closed first | [DEF §Toolchain; LEC 8] |

### 2.3 The tools (the Loom's organs)

| Tool | Organ | Accountability rule | State | Source |
|---|---|---|---|---|
| **x3d_mcp fork** (hagopjay) | Grammar and Meaning witnesses, repair, exact-fix hints | Every verdict names its commit | 103 commits ahead, 0 behind; 23 semantic checks (upstream 10); 48 tools (34); 1,047 test functions (284), C | [MC §1-2; DEF §Repo map] |
| **loom_gate.py** (x3d.onto) | Traps witness | Rules with tests on both sides, corpus re-run | 11 rules, 18 test functions, C (1 Nov) | [DEF §Witnesses] |
| **X_ITE 16.5.1** | Behaviour, Host, Eyes | Version and rig named with every render claim; shipped as the page's own files, never from a CDN | All Loom gates run on it | [DEF §Toolchain; KICK §PRE 2] |
| **Headless Chromium + Playwright** | Behaviour and Eyes instruments | Renderer named; SwiftShader is not a GPU | Chromium 131/153, Playwright 1.62/1.63 in use | [LS1 §16; DEF §Witnesses] |
| **Strict host-policy copy** | Host witness | C under the copy, L on the real host | Built | [DEF §Grades] |
| **Blender 5.2 + blenderizer** (x3d-blender-io) | The hand: generator for modelled, baked, rigged assets | Never mocked; every Blender scene also exports validated X3D; one receipt per asset | 194-case export suite | [DEF §Toolchain; MC §5] |
| **loom_receipt.py, x3dprov** (x3d.onto, x3d.ML) | Receipts | Refuses to overwrite; hash chain in the X3D head; unsigned in 0.1 | Built | [DEF §Receipts] |
| **DSPy** | Flywheel optimiser | Lawful metric, few-shot first | Measured on a hosted model | [DEF §Toolchain; MEAS] |
| **hosted model API** | Judges; cards (style, imagery, video, music) | Flags, never grades; cached by prompt hash; paid calls on his yes | Measured, [cost withheld] upper bound | [MEAS §Cost] |
| **loomkit** (this repo, `kit/`) | Portable acceptance, traps subset, fold-back and receipt tools for a machine without x3d.onto | Stdlib only; tested two-sided in normal and `-O` | C, this repo | [KIT tests/last-run.json] |

**Repo map** [DEF §Repo map; MC §5]: x3d_mcp (validator), x3d.onto (rulebook FACTS, Traps, receipts, lawful metric, Dynasty Loom, demiurge), x3d.ML (provenance: x3dprov, PROV-O, CI tether, verdict drift), x3d-blender-io (Blender weaver), x3d.xray (read path: memory compiled into a flyable scene), x3d.poc (public showcase), x3d_ai (private workbench). There never was a repo named x3d_prov: lineage lives in x3d.ML as `x3dprov` (decision 3, 1 Nov) [DEF §What happened to x3d_prov].

---

## 3. The laws

Sixteen laws bind every Loom project; each was paid for by a real failure [DEF §The laws]. Laws 17 to 20 are new in v1. Each one generalises incidents the other model hit and fixed in several projects, so their grade is L: reasoned from C incidents. They are in [LEARNINGS-from-patches.md](LEARNINGS-from-patches.md).

| # | Law | Forbids | Paid for by (grade, source) |
|---|---|---|---|
| 1 | **Generator, not file.** Fix the card or the generator, then weave again | Hand-editing generated output | Dynasty Loom v3: 87 of 87 files rebuilt byte for byte (C, [LEC 2]) |
| 2 | **Valid is not visible.** Grammar passing starts the inspection, never ends it | Shipping on "0 errors" | 3 of 3 pocket worlds valid and white (C, [LEC 1]); 13 of 16 wrong scenes pass strict validation (C) |
| 3 | **Many witnesses, blind spots that don't overlap** | One clever test for all | Labels vanished only under the host policy (C under the copy, [LEC 3]) |
| 4 | **If you can't make it again, you don't know what it is.** Declare every input, the date included | Undeclared clock, time zone, file order, seeds, versions | Clock moved 3 days, rebuild differed (C, [LEC 4]) |
| 5 | **Say how sure you are.** C, L or S on every claim, with its instrument | Upgrading a grade in translation | "Upstream is broken" split into C and L (C/L, [LEC 5]) |
| 6 | **Models speak in S.** Model output enters as S, labelled as generated; judges flag, never grade | A model's sentence entering the record as fact | HOOKS.md 7b [DEF] |
| 7 | **Every mistake pays rent once.** Incident, fact, rule with tests, fork check, upstream | Fixing a trap in one project only | shader-raw-source: white sphere to gate rule in a day (C, [LEC 6]) |
| 8 | **Gates are fixed like code**, tests on both sides and a corpus re-run | Silencing a noisy rule | glsl-int-literal: 62 findings over 859 files, all one false line (C, [DEF]) |
| 9 | **The metric will be attacked.** Close escape hatches before optimising | Rewarding "valid" alone | 67 of 67 optimised valid scenes declared Full (L, [LEC 8]) |
| 10 | **Truth gates when the world is real.** No invented person, face, date or note | Guessed likenesses, unlabelled AI images | 20 errors and 26 warnings in shipped family data (C, [DEF]) |
| 11 | **Ask once, cache forever.** Every paid call keyed by its prompt hash and capped | Re-requesting the same picture | Portrait cache: 2 calls per person, 60 total (C, [LEC 7]) |
| 12 | **Budget is a witness.** Two or three agents at a time; partial results on disk | Wide fan-outs | 22 agents emptied the usage window in ~25 min; 4 h stop (C, [LEC 10]) |
| 13 | **Unknown is not zero; no witness, no tie** | An edge or number nobody measured | x3d.xray ledger (L, [BLUE §2]); Data City null semantics (C, [CITY]) |
| 14 | **Add layers, never replace.** Version everything | Overwriting a demo or a receipt | loom_receipt.py refuses to overwrite (C, [DEF]); every Loomsong version kept its predecessor's receipt (C, [LS2 §5; LS3 §9]) |
| 15 | **Name the instrument behind every number** | Software-GL frame rates; unpinned verdicts | "7 to 10 of 10 repairs" holds only at upstream 74da0ec, 3 to 6 at 020221e (C, [DEF]) |
| 16 | **Nothing leaves without "send".** Public pages pass a leak sweep first | Outbound PRs, emails, pushes on assumption | 33 upstream PRs drafted, 0 sent (C, [MC §9]) |
| 17 | **Evidence is bound to the exact candidate.** A witness record names the sha256 of the full candidate inventory (runtime, generators, **test code**, data, docs, vendored runtime); any change makes it stale | Packaging changed code with an old pass | Study 01 packaged a changed shader against a stale browser pass, exit 0 (C, [LS1 §9 A01]); fixed in v2 and kept in v3, v4, Gear, Data City, IFC (C) |
| 18 | **A gate is code that cannot be switched off.** Explicit raising predicates, never `assert`; tested under `python -O`; refuse an environment you cannot gate | Gates that vanish under optimisation | Red Score packaged under `-O` (C, [LS1 §9 A02]); IfcOpenShell asserts forced the IFC studio to refuse `-O` (C, [IFC]) |
| 19 | **A control must fail for the intended reason.** Every negative control expects one stable diagnostic; an instrument crash is `error`, not a catch; a missing witness, unknown status or empty profile never passes | "Some failure happened" counted as a catch | IndexError mistaken for rejection (L, [LS1 §12]); Break-the-Loom requires the exact diagnostic (C, [BREAK]) |
| 20 | **Fold back small, with the counterexample.** A lesson returns as an additions-only patch carrying the minimal failing fixture, the repaired control, its scope and its blind spots; promote only after the target corpus re-runs | Grand universal rules; browser facts promoted to X3D prohibitions | All five project PR patches have this shape (C, [KIT runs/foldbacks-20261104]); "Turn observed misses into portable counterexamples before naming a grand universal rule" [LS4] |

---

## 4. The loop, step by step

Every Loom build runs three rows: **weave, inspect, remember** [DEF §Anatomy]. Version 1 spells the loop out as ten steps. A red witness at any step sends work back to the card or the generator, never to the artifact [DEF §Witnesses].

```
 0 Card ─► 1 Kickoff (PRE) ─► 2 Weave ─► 3 Witness ─► 4 Gate ─► 5 Stump ─► 6 Judge ─► 7 Receipt ─► 8 Debrief ─► 9 Fold-back ─► 10 Handoff (POST)
              ▲                  ▲           │fail        │reject     │survivor    │flag                                │
              │                  └───────────┴────────────┴───────────┴────────────┘ fix the card or generator, weave again
              └───────────── the knowledge graph (FACTS, rules, memories) feeds the next kickoff's trap list ◄──────────┘
```

### Step 0: the card
Name the idea, its **source of truth** (`repo/path @ commit`), and a measurable **better** (for example "wins a blind A/B against v1", "real-GPU fps ≥ 60", "0 errors on the new pin"), plus what must not change. Leaving "better" vague is how an agent polishes forever or reports "valid" while nothing shows [KICK §Why each part is there]. For music: the score is the card; visual and audio are woven from the same card [DEF §Before the music].

### Step 1: kickoff (what to paste **before**)
Paste **PRE** as the first message of a new Loom project, with this definition attached. Use [kit/templates/KICKOFF-PRE.md](kit/templates/KICKOFF-PRE.md), the kickoff doc's text updated for v1 [KICK §PRE]. Its seven blocks:
1. **Target**: idea, source of truth, better, must-not-change, visibility.
2. **Tool pins**: fork tag `loom-pin-2026-11-01` (until it exists, fork main at a named commit), loom_gate sha, X3D version and profile, X_ITE 16.5.1 as the page's own files, Blender and blenderizer sha, Chromium and Playwright, host-policy copy, model ids. Every receipt records these [KICK §PRE 2; DEF decision 5].
3. **Traps to read before coding**: FACTS sections, the lessons table, and the trap list in §8 of this file.
4. **Generator first**: never hand-edit; deterministic bytes (SOURCE_DATE_EPOCH, seeds, sorted keys); one data file holds every number the scene shows; a red witness stops the build.
5. **Guardrails**: budget cap and ledger; typed yes for cloud, delete, public, over-cap; C/L/S on every claim; AI-made media labelled; no real faces; stop-and-show points; at most 3 agents.
6. **Witness plan** with thresholds (§6), naming the **acceptance profile** (§6.2). New in v1.
7. **Where outputs land**: one PR per behaviour change; `runs/<run-id>/witness.json`; receipts beside the artifact; heavy evidence by sha256; spend ledger private [KICK §PRE 7].

**The first-reply check:** the agent restates target and "better" in its own words, lists the witnesses, and names its first three steps with cost estimates. Only then does it start [KICK §PRE]. This catches a wrong reading of "better" before work is spent on it.

### Step 2: weave
Write or extend the generator, never the output [DEF law 1]. Practices that every project proved:
- **One event model** feeds audio, geometry and UI, so they cannot drift apart [LS1 §2].
- **Declared inputs only**: seed (Loomsong 61429), SOURCE_DATE_EPOCH, pinned library versions; same-environment byte-equal regeneration (Loomsong 10, 12, 15, 22 outputs across v1 to v4, C) [LS1; LS2; LS3; LS4].
- **Bake what is spatially expensive and temporally stable; keep score time and camera live** [LS4 §Practical wisdom].
- **Bundle the full pinned runtime**: the loader alone was not enough; ship CSS and dynamically loaded components, and expect zero external requests [CITY lesson 1].
- **Build atomically, or refuse to serve while building**: a preview that mixed new JavaScript with the old scene failed; v4 added a build marker that makes the server refuse requests [LS3 §1; LS4].

### Step 3: witness
Run the witnesses, cheapest first: file-reading witnesses (Grammar, Meaning, Traps) before browser and human ones (Behaviour, Host, Eyes last) [DEF §Witnesses]. Each witness writes one **witness record** (`loom.witness/1`, §5) bound to the candidate's sha256. If the candidate changes while it runs, it refuses: `CANDIDATE_CHANGED_DURING_WITNESS` [LS3 §1]. The eleven witnesses are in §6.1, and each project adds domain witnesses to its profile.

### Step 4: gate
A witness observes; a **gate decides** [LS1 §7]. v1 has one acceptance function (`kit/loomkit/accept.py`). A named **profile** lists the required witnesses, and acceptance is "a closed set of current-candidate witnesses, not a score" [IFC release_contract.py]. Algorithm [LS1 §14, tightened in LS2-LS4 and IFC]:
1. Freeze the candidate inventory; compute its sha256 (evidence, caches, VCS and archives excluded, so the digest is never self-referential).
2. Resolve the profile's required set. An empty set rejects (`EMPTY_PROFILE`).
3. For each required witness, require one well-formed record: present (`MISSING_WITNESS`), right schema and name, bound to this candidate (`STALE_WITNESS`), not a development run (`DEVELOPMENT_WITNESS`), status `pass` (`WITNESS_NOT_PASS`) or an allowed `deferred` / `not_applicable` with a written reason (`STATUS_NEEDS_REASON`), grade C for a pass (`UNMEASURED_REQUIRED_WITNESS`), coverage fields present (`COVERAGE_REQUIRED`), evidence files unchanged (`EVIDENCE_DRIFT`).
4. Only then write the receipt.

All predicates raise explicit errors and are tested under normal Python and `-O` [law 18]. Exit codes: 0 accepted, 1 contract violation with a stable code, 2 instrument or input error [CITY README].

### Step 5: stump (attack the Loom)
Accepted evidence is only as strong as the controls that tried to break it. Stumping is the Loom's attack step (user decision, 3 Nov). It has two halves:
- **Attack the candidate (Break-the-Loom).** Generate single-fault mutants with a repaired control for each. Every mutant must be schema-valid ("valid syntax should stay valid"), and the assigned witness must reject it with its exact diagnostic while the control passes. Read the matrix cell by cell: Caught, Clear, XSD-valid, Outside scope, Error. A **clear** cell is a coverage question for a named owner before it is a request for a new rule [BREAK TECHNICAL].
- **Attack the model (stumping rubrics).** When the Loom is used to test a model, write criteria where models actually slip: numbers hidden inside creative work, version traps the grader runs, specs given as images, the solver's own outputs checked against each other, and shortcut-killers. Put 80% or more of the points on 20 to 30 criteria, each ending "If …, this item fails", and keep files and naming at 5% or less. Aim each trigger at the slip, not at a blunder; prove feasibility headless; rerun 2 to 4 times [STUMP §Bottom line, §Final insights, App. A, D]. The graded references showed partial credit is the default: with no trigger, 11 partial misses still scored 0.739; one well-placed trigger zeroed Boston's heaviest item (L, as reported in [STUMP §What the graded references proved]).
- **Test the observer as deliberately as the object.** Use a displaced marker, a 1% wrong-speed rotor, an induced stall that must appear in the recorded frame gaps, a corrupted asset that must stop startup [GEAR §5-6; LS4].

### Step 6: judge
Taste stays with the human; machines raise flags.
- **Eyes and Ear**: HagopJay's eye and ear are the judge of record [DEF §Witnesses; SPEC]. Nobody has yet heard the Gobbler's music (gap, [DEF §Known gaps 1]).
- **Model judges flag only**: a located, image-bound, `suspected` observation (view, normalised region, concern of more than 15 characters), bound to the candidate and to each frame's sha256. Any score, rating, "n/10" or `confirmed` state rejects (`PICTURE_GRADING`, `MODEL_TRUTH_PROMOTION`) [LS4 picture.py; IFC]. Implemented in `kit/loomkit/picture.py`.
- **Numeric judge scores only in labelled experiments** (user decision, 3 Nov), for example ranking variants in a Gobblering round (§9.3). They never gate a release. Why: re-judging the same frame moved the judge's score by sd 0.12 to 0.25 (C, [MEAS]); a black still once scored 2.33 (C, [DEF lesson 18]); the judge is not calibrated against people [MEAS §Vision judge].
- **Separate three questions** for every visual change: did the change reach the renderer; is the candidate still technically sound; is it artistically better? The first two are witnessed; the third is his [LS2 §The strongest lesson].

### Step 7: receipt
Write one **Loom Receipt v1** per accepted artifact (`loom.receipt/1`, §5), only after acceptance. It names the candidate sha256 (the subject; the receipt is never hashed into it), each required witness record's hash, the unrun witnesses (visible, never hidden), tool pins, outputs with bytes and sha256, model calls by prompt hash with a cached flag, budget, limitations, and `prev`, the receipt it replaces. It refuses to overwrite [DEF §Receipts; LS1 §14; LS4 package.py]. Receipts are unsigned: they make drift visible; they do not authenticate authorship [LS2 §2; IFC].

### Step 8: debrief
Fill [kit/templates/DEBRIEF-FORM.md](kit/templates/DEBRIEF-FORM.md). The shape is the one the other model's debriefs converged on [LS1; LS2; LS3; LS4; IFC; GEAR; BREAK; CITY]:
- outcome and scope (what was retained, reduced, deferred);
- a witness inventory with **actual status and its boundary** ("what a pass does not establish");
- the gates that actually controlled the work;
- the receipt lineage (candidate, previous receipt, archive);
- incidents, each with repair, evidence and **learning maturity**: implemented locally, reproduced, proposed, or inconclusive;
- lessons to fold back, with their destination;
- what should stay local (creative decisions become scoped art-direction memory, never universal rules, never promoted from S to C because tests passed) [LS3 §10];
- reproduction commands.

### Step 9: fold-back (what the Loom learned returns to the Loom)
Every lesson travels as a **PR-style fold-back patch**. Five of the project zips carry one (C, [KIT runs/foldbacks-20261104]):
- additions-only, under `tools/<name>/`;
- a README with `git apply --check`, `git apply`, then `python3 tools/<name>/smoke.py` and `python3 -O tools/<name>/smoke.py`;
- production predicates plus the minimal fixtures and negative controls;
- tested in an empty temporary git repository, with no compatibility claimed against an unseen checkout;
- a destinations table: x3d.onto for facts and traps, the fork for standard-level semantics, x3d.ML for lineage, shared acceptance code for release rules;
- no CI activated and nothing pushed.

Check one with `kit/loom foldback`. Fill [kit/templates/FOLDBACK-FORM.md](kit/templates/FOLDBACK-FORM.md).

The **flywheel** a fold-back feeds has five stages [DEF §The flywheel; LEC 6]: (1) incident, with a minimal reproducer saved; (2) fact, a graded FACTS entry; (3) rule, a gate rule with tests on both sides, re-run over the whole corpus (798 to 883 files so far); (4) fork check, when the lesson is about meaning rather than one browser; (5) upstream, a rebuilt, trailer-free PR to the Consortium, **only on "send"**. A rule that proves wrong goes back to stage 3. Four loops have been traced commit by commit; none has reached stage 5 (C, [MC §6]). Break-the-Loom writes the same wheel at a finer grain: observed incident, scoped fact, executable predicate, two-sided controls, wider corpus, reviewed promotion [BREAK].

### Step 10: handoff (what to paste **after**)
Paste **POST** in the same first message as PRE. It is the done-when; a missing item means not done [KICK §POST]. Use [kit/templates/HANDOFF-POST.md](kit/templates/HANDOFF-POST.md). It has eight items: receipts, witness table (red rows stay red, with reason and fix plan), numbers (each with witness, commit and grade), frames (fixed-time stills, a host-copy run, a contact sheet, before and after), lessons (FACTS entry with symptom, cause, fix, test; a proposed rule with one passing and one failing test; upstream yes or no, held for "send"), spend, versions, next. v1 adds a ninth: **the fold-back patch** and its `loom foldback` result.

An agent working elsewhere reports in with the 8-part shape in [kit/templates/REPORT-IN.md](kit/templates/REPORT-IN.md) [DEF §Brief for the agent still out].

---

## 5. Artefacts and their formats

| Artefact | Format (schema) | Written by | Lives | Source |
|---|---|---|---|---|
| Card | Data file(s): score, CSV, IFC, recipe JSON, style board | Human or agent, then frozen by hash | Project repo `sources/` or `cards/` | [DEF; LS1; GEAR; CITY] |
| Generator | Code that emits the X3D and a manifest | Agent | Project repo `gen/` | [DEF law 1] |
| Build manifest | `outputs: {path: {bytes, sha256}}`, seed, versions | Generator | `assets/build-manifest.json` | [LS1 §8] |
| Candidate inventory | `loom.candidate/1`: `{files: {path: sha256}, sha256}` | `loomkit candidate` | Recomputed, never stored inside itself | [LS2 §2; core.py] |
| Witness record | `loom.witness/1`: witness, status, grade, subject_sha256, instrument, measurements, coverage, limitations, evidence[{path, sha256}], development, reason, environment{python, optimized} | Each witness | `runs/<run-id>/evidence/<witness>.json` | [LS1 §14 proposal; LS2-LS4 contract.py; core.py] |
| Acceptance profile | `loom.profile/1`: name, required[{witness, allow, coverage}], visible_not_run, limitations | Kickoff | `kit/profiles/*.json` | [LS1 §11 required_witness_set; this repo] |
| Picture review | `loom.picture-review/1`: subject_sha256, reviewer, state=suspected, images{view: sha256}, flags[{id, view, region, concern, state}], scope | Model judge | Beside the frames | [LS4 picture.py] |
| Loom Receipt v1 | `loom.receipt/1`: kind=artifact, subject, candidate_sha256, profile, inputs, tools, outputs, witnesses[{witness, status, grade, record_sha256}], not_run, model_calls, budget, limitations, prev, signed=false, sha256 | `loomkit receipt`, after acceptance | `receipts/<artifact>.json` beside the artifact | [DEF §Receipts proposal; KICK §POST 1] |
| x3dprov chain | Hash-chained steps in the X3D `<head><meta>` | x3dprov 0.1 | Inside the scene | [DEF §Receipts] |
| FACTS entry | Symptom, cause, fix, test, grade, instrument, scope, reproducer path | Agent at incident time | x3d.onto `FACTS.md` (sections A to Q exist) | [KICK §POST 5; DEF §Flywheel] |
| Fold-back patch | Additions-only unified diff under `tools/<name>/` + README + smoke.py + fixtures | Agent | `integration/*.patch` in the project | [LEARNINGS §The PR shape] |
| Debrief | Form in `kit/templates/DEBRIEF-FORM.md` | Agent | Beside the release | [LS1-LS4] |
| Evidence manifest | `loom.evidence-manifest/1` (`kit/templates/evidence-manifest.schema.json`) | Release step | Beside the archive | [LS1 §8; LS4 check_release.py] |
| Spend ledger | One line per paid call: model, units, list price, prompt hash, cached | Every paid call | Private project files only | [KICK §PRE 5; MEAS §Cost] |
| MemoryRecord (planned) | One line per write: kind = claim, session, tie, artifact, coverage, note, petition, answer | Scribe | The knowledge graph | [BLUE §3.2; DEF §Knowledge graph] |

---

## 6. Quality gates and rubrics

### 6.1 The witnesses
Eleven Loom witnesses [DEF §The witnesses], with the domain witnesses projects added. "Blind to" is why there are many.

| # | Witness | Asks | Instrument today | Blind to | State |
|---|---|---|---|---|---|
| 1 | Grammar | Tags and attributes legal for the declared version? | X3D 4.0/4.1 XSD via the fork | Meaning, behaviour, looks | Built |
| 2 | Meaning | ROUTE types and order, DEF before USE, profile and components, containerField, colour range, H-Anim names | Fork: 23 semantic checks | One browser's quirks | Built |
| 3 | Traps | Has this exact trap already cost us once? | loom_gate.py (11 rules + `--fork`); loomkit.traps (11-rule portable subset) | Traps nobody has paid for | Built |
| 4 | Behaviour | Does the real browser load, compile and route it, console clean? | X_ITE 16.5.1 headless, Chromium, Playwright | Taste; real-GPU speed | Built |
| 5 | Eyes | Lit, framed, unclipped, beautiful? | Frames at every stop, luminance measures, flag-only judge, **his eye** | Off camera | Built |
| 6 | Host | Does it work where it will live? | Strict copy of the hosted-page Artifact policy | Real-host differences (L) | Built |
| 7 | Receipts | Can we make it again, byte for byte? | loom_receipt.py; rebuild and compare sha256 | Whether the thing is right | Built |
| 8 | Truth | Does content match the real world and the project's rules? | Per project (dynasty data gates, Data City truth gate, score fixture) | Anything not yet a rule | Built per project |
| 9 | Budget | Over the cap, or a repeated paid call? | Prompt-hash cache, caps, spend log | Quality | Partly built |
| 10 | Ear | Right sound, loudness, sync? | Loudness and peak; onsets vs score | Taste in sound | Partly built (Loomsong) |
| 11 | Score | Does every drawn event come from a note, and every note get drawn? | Event to geometry bijection | Interpretation | Built for one source (Loomsong) |

Domain witnesses that projects added and that v1 adopts as named, optional profile entries: **Sync**, **Flash**, **Fps**, **Pose**, **Fidelity** [SPEC]; **Optics**, **Motion** (camera cards), **Onsets**, **Picture protocol**, **Profiler** [LS3; LS4]; **Rendered pose** and **Observation window** [GEAR]; **Integration (fold-back)** [GEAR; IFC; LS4]; **Protocol** (revision CAS, idempotency) [IFC].

Why many: each "blind to" is covered by another row. Order matters: cheap file readers first, browser and person last, and only on files that passed [DEF §The witnesses].

### 6.2 Acceptance profiles
A profile names which witnesses must be present, current and green for one kind of delivery. It keeps deferred, not-applicable, blocked and failed distinct [LS1 §1 "acceptance profile"]. Profiles seen so far:

| Profile | Required set | Source |
|---|---|---|
| `x3d-static/v1` (this repo) | grammar, meaning, traps, truth, foldback; behaviour, eyes, host visible as not_run | [KIT kit/profiles/x3d-static.json] |
| Loomsong local interactive study (v2) | local (8 named checks), browser (full playback), loudness, rebuild, gates | [LS2 §2] |
| Loomsong v3 | + optics, motion, onsets | [LS3 §7] |
| Loomsong v4 | + fidelity, integration, profiler, picture-protocol; 9 browser coverage flags; 21 sampler probes | [LS4 contract.py] |
| IFC bridge studio | core, optimized-safety, static, protocol, rebuild, integration, browser, gates + picture observation | [IFC release_contract.py] |
| Data City | local, browser, rebuild, release_gates | [CITY TECHNICAL] |
| Loomsong full production (spec, not built) | 16 witnesses: the 11 + Sync, Flash, Fps, Pose, Fidelity | [SPEC §Witnesses and gates] |

### 6.3 Thresholds the sources set
Thresholds belong to a profile. Hard boundaries need just-inside and just-outside fixtures [LS1 §11].

| Measure | Threshold | Status | Source |
|---|---|---|---|
| Integrated loudness | −14 LUFS ±1 (spec, full production); −18 to −12 LUFS enforced in the local study profile | Spec vs enforced differ, see SOURCES §Disagreements | [SPEC; LS2 §3] |
| True peak | ≤ −1.0 dBTP | Enforced v2+ | [SPEC; LS2] |
| Onsets vs score | median ≤ 5 ms, p95 ≤ 15 ms (spec); max ≤ 25 ms on the isolated silver stem (v3, enforced) | Partly built | [SPEC; LS3 §5] |
| A/V sync | page clock within 16.7 ms of audio clock; broadcast window 45 ms ahead / 125 ms behind (L, check ITU-R BT.1359 before quoting) | Not built | [SPEC; DEF M3] |
| Rendered notes | precision and recall ≥ 0.99 at 50 random times (spec); 199 of 218 eligible IDs decoded at 35 s (v3) | Partial | [SPEC; LS3 §5] |
| Flash | 0 WCAG 2.3.1 violations (≤ 3 flashes/s, L) | Not run anywhere | [SPEC; DEF M8] |
| Fps | Real GPU, 1080p: median ≥ 60, 1% low ≥ 45 | Not measured anywhere | [SPEC] |
| Eyes nonblank | mean luminance > 2/255; > 2% of region > 5/255; < 15% > 250/255; region central 60% × 15-80% | Enforced v2+ | [LS2 §4] |
| Effect presence | unchanged-frame control < 0.001/255; changed > 0.005 or > 0.02 | Enforced v2+ | [LS2 §4] |
| Eyes (spec) | no black frame; 95th luminance percentile < 0.98 | Spec | [SPEC] |
| Camera motion | lens 0.25-1.25 rad; eye-target > 2 units; < 4 units/s; < 20°/s; endpoint < 0.01 | Enforced v3+ | [LS3 §4] |
| Gear clearance | strictly positive certified lower bound over a complete angular cover; unresolved at depth 18 fails | Enforced | [GEAR §4] |
| Gear motion | ≥ 30 frames over ≥ 2 s; slope error ≤ max(1e-5 rad/s, 0.02%); residual < 1e-4 rad | Enforced | [GEAR §5] |
| IFC geometry | one-to-one winding-sensitive triangle match within 20 µm | Enforced | [IFC] |
| Judge noise | re-judging moves a mean by 0.09; differences under 0.2 are noise | Measured | [DEF §Toolchain; lesson 18] |

### 6.4 Stumping rubric rules
For prompts that test models [STUMP; STUMPB; TIDE]:
- Every criterion uses the form `R## · points · class` / title / quoted brief words / check / "If …, this item fails." Trigger kinds: tolerance, counted sample, frame window, shortcut named as an outcome, direction or sign, run gate, repeatability, two outputs agree, stress at extreme inputs [STUMP App. A].
- 80% or more of the points go on criteria worth 14 to 25 points; files and naming at 5% or less [STUMP].
- Fairness, checked by script: every quote appears word for word in the brief; every expected number is recomputed; unstated norms total 5% or less; no requirement is impossible at the corners of its own ranges [STUMP App. D].
- Version traps bite only when code runs: name the version, never the new API [STUMP App. C].
- Template: [kit/templates/STUMP-CRITERION.md](kit/templates/STUMP-CRITERION.md).

---

## 7. Measurements so far

Grades as carried from the source; **synthetic** marks fixtures and teaching data. Nothing here has been replicated outside the project [SITE caveats].

### 7.1 X3D on a hosted model (30 Oct) [MEAS; SITE]
| Question | Result | Grade |
|---|---|---|
| Do XSD + X3DUOM excerpts make an AI judge better? | model P: 99 vs 87 of 115 fuzzer findings right (p 0.017); invented evidence 9 vs 29. model F: 86 vs 75 (p 0.027). Grounded Flash matched bare model P at under half the cost ([cost withheld] vs [cost withheld]) | C |
| Does the lawful metric give DSPy something to optimise? | GEPA on model L, 50 unseen prompts: 31.3 → 58.3 and 32.6 → 60.2 (two runs, p < 0.001); with 3 repair rounds 39.6 → 70.3 (perfect scenes 2 → 13); no help on model L2 (92.6 → 93.6, ns); model F had nothing to tune (99.6) | C |
| Do exact-fix hints beat plain errors? | model L, 540 broken scenes (**synthetic** mutants): first repair valid 507 vs 489 (31 gained, 13 lost, p 0.0096); round 2: 530 vs 524 (ns). Gains concentrated on ROUTE-before-node (32 → 45 of 45). Hints alone, no model: 522 of 540, of which 12 only by deleting a node; the original restored in 257 | C |
| Is a vision judge usable on X_ITE frames? | model F on 35 frames, judged twice: re-judging sd 0.12-0.25 while frames span 4.7-6.7; Flash and Pro agree in rank (Spearman 0.66); not calibrated against people | C |
| Spend | [cost withheld] of [cost withheld] approved, upper bound from token counts at assumed prices, 4,180 calls | C (ledger), price basis L |
| Labels | 7 blinded model reviewers; 2 adversarial reviewers re-checked 47 contested findings and upheld 46; reviewers saw the same files as the grounded arm | C, with that bias |
| Stack findings from the labels | 55 XSD content-model errors; 28 X_ITE bugs (profile check ignores component levels, x_ite.js:52514); 16 X3DUOM errors (PhysicalMaterial missing from profile lists); 5 fork/fuzzer bugs; none reported upstream | C (as labelled) |

### 7.2 Metrics and gates (x3d.onto) [LEC 1, 8; DEF]
| Measure | Result | Grade |
|---|---|---|
| Lawful metric vs strict validity | AUC 0.997 on 383 recorded scenes, model-free | C |
| Wrong-but-valid scenes | 13 of 16 (**synthetic**) pass strict validation; lawful catches 16 | C |
| DSPy with Full open | 67 of 67 valid scenes declared profile Full | L |
| Hard-prompt failure | plain 84%, DSPy Full open 64%, Full barred 30%, five plain examples 6% (100 trials per arm) | L |
| Valid scenes that draw nothing | 203 of 1,058 | C [DEF lesson 1] |
| Gate false positives | glsl-int-literal: 62 findings over 859 files, all one false line; fixed and re-run | C |

### 7.3 Projects (the other model's runs, local renderer = SwiftShader unless stated)
| Project | Key measured results | Grade | Source |
|---|---|---|---|
| Dynasty Loom v3 | 87 of 87 files rebuilt byte for byte; 1 hidden input (the date) found; 302 people pass the publish gate; 20 errors and 26 warnings in shipped data; portrait cache ≤ 2 per person, 60 total | C | [LEC 2, 4, 7; DEF] |
| Loomsong Study 01 v1 | 60.931 s, 450 events (94 composer, 356 arrangement), 58,500 ribbon vertices; 10 outputs byte-identical on rebuild; master −14.92 LUFS, −1.97 dBTP; audit: 156 member hashes verified; A01 and A02 reproduced | C | [LS1] |
| Cinematic v2 | 14 release controls (7 cases × normal/-O); 12 outputs byte-identical; full 62.94 s playback; 8 shots | C | [LS2] |
| Cinematic v3 | 22 gate executions; 15 outputs; 95/95 silver attacks, max 11.17 ms; 199 rendered IDs at 35 s; 9 interruption paths | C | [LS3] |
| Cinematic v4 | 40 gate executions (20 cases × 2); 22 outputs; 21 GPU texel probes; 25 BRDF reference probes within 0.0021 | C | [LS4] |
| Gear Loom | min certified clearance 0.0448 mm (six recipe) vs sampled 0.150 mm; 64 intervals per tooth pitch; 1% speed mutant and 180 ms stall caught | C (floating-point certificate, not exact arithmetic) | [GEAR] |
| Break the Loom | 12 mutants rejected with their exact diagnostic, 12 controls accepted, all XSD-valid (**synthetic** corpus) | C | [BREAK] |
| Data City | 64 records (**synthetic** teaching data); null/zero/negative semantics; checksum-ID pixels; 19 diagnostics | C | [CITY] |
| Confluence IFC studio | 111 IFC products; 31 core defect controls; 20 GPU texel probes; 14 browser checks; max extent error 5.3e-9 m | C | [IFC] |
| Every project | Dedicated-GPU frame rate, physical A/V latency, formal flash analysis, human approval | **not measured** | [LS1-LS4; SPEC] |

### 7.4 This repository's own runs (3-4 Nov UTC, Python 3.13.2, macOS arm64)
| Run | Result | Grade |
|---|---|---|
| loomkit self-test, normal and `-O` | 29 negative controls rejected with the intended code; 11 trap rules pass their clean fixture and catch their failing one (**synthetic** fixtures). A deliberately weakened copy (stale check removed) fails the suite with SURVIVING_CONTROL | C [KIT tests/last-run.json] |
| Fold-back survey, 5 distinct patches (10 copies) | 4 pass (Break, Data City, Gear, Loomsong v4: clean apply, additions-only, smoke green normal and `-O`). IFC bridge, rerun with the studio's own venv (IfcOpenShell 0.8.5, arm64): node protocol check passes (3 positive, 6 negative), but the Python smoke **fails its positive control** with WORLD_TRIANGLE_MISMATCH: 2 of 111 products (boxes, 12 triangles each, same count) have 4 triangles whose centroids sit 11.7 mm off, consistent with the other diagonal of each quad face. Same surface, different triangulation; the author's receipt shows a pass on its own platform | C counts; L diagonal explanation [KIT runs/foldbacks-20261104/report.json, interpreter = the studio venv] |
| Patch reproduction (projects agent) | `Loomsong-v3-to-v4.patch` on v3: every source file equals v4; after `gen/build.py` (40 s, 22 outputs) X3D, JSON and WAVs are byte-identical, all 9 PNGs pixel-identical but not byte-identical, two floats differ in the last bit (≤ 3.6e-15). `IFC-X3D-Bridge-upgrade.patch` reverse/forward-applies to exactly the Studio zip | C [CAT §Patch results] |
| Data City through `x3d-static/v1` | Accepted: grammar and meaning pass on 2 scenes (fork fa0b389, branch fix/physics-findings, not the family pin); traps 0 errors; project truth gate exit 0; fold-back pass; behaviour, eyes, host visibly not_run. Controls on the real project: a hand edit gave STALE_WITNESS; a planted colour gave 73 trap errors | C [KIT runs/data-city-20261104] |
| Traps over 48 unique real X3D files | Error rules hit only Break-the-Loom mutants (route-before-def on 01-route/mutant, shader-raw-source on 02-raw-shader/mutant); 0 error hits on any control or project scene. Warning rule metadata-containerfield fires 23 times on Break 09 and 12 (controls and mutants): the pattern Gear and IFC saw X_ITE warn on, unconfirmed in a browser here (L) | C counts, L meaning [KIT runs/traps-corpus-20261103] |

---

## 8. Known failure modes and their fixes

Each row is a trap someone paid for. The fix is the v1 rule; LEARNINGS-from-patches.md has the longer account.

| # | Failure | Fix (rule) | Source |
|---|---|---|---|
| 1 | Valid X3D draws white: raw GLSL in a ShaderPart is read as a URL | `data:x-shader/x-fragment,` prefix; trap shader-raw-source | [LEC 1; FACTS P via DEF] |
| 2 | Valid X3D, invalid GLSL (`active` reserved) | Runtime `isValid` check + compile witness; lexical guard | [LS1 F01] |
| 3 | ROUTE before its node: fork passes, X_ITE drops | trap route-before-def; fork 788041c | [DEF; MC FW2] |
| 4 | Colour above 1: XSD error blames something else | trap color-range | [KICK] |
| 5 | White emissive washes out coloured faces | trap color-emissive-white | [FACTS Q via DEF] |
| 6 | WOFF2 fonts need eval: labels vanish under host policy | Ship TTF; Host witness | [LEC 3] |
| 7 | X_ITE has no public scene clock | The page (audio clock) owns time | [DEF lesson 9; KICK] |
| 8 | Still PNG in MovieTexture hangs the world | trap movie-not-still | [KICK] |
| 9 | GaussianSplats culled never sorts, loading never ends | bboxSize/bboxCenter on every node; trap splat-bbox | [DEF §Video to world] |
| 10 | Build date leaked into output | SOURCE_DATE_EPOCH; rebuild with the clock moved | [LEC 4; BREAK] |
| 11 | Optimiser declares profile Full | Lawful metric charges for every step above the smallest profile | [LEC 8] |
| 12 | Old browser pass authorises changed code | Witness records bound to the candidate digest, test code included | [LS1 A01; LS2] |
| 13 | `python -O` strips asserts; red gate packages | Explicit raising predicates; tests in both modes; refuse `-O` if a dependency asserts | [LS1 A02; IFC] |
| 14 | Packager checks values present, not a required set | Named required set; empty set rejects | [LS1 §9] |
| 15 | "pass" without a threshold | Numeric predicates with units, window and just-inside/outside fixtures | [LS1 §6, §11] |
| 16 | Preview mixed new code with an old scene | Sequence build before witnesses; refuse to serve while building | [LS3; LS4] |
| 17 | Shader assumed local position was world | Declare coordinate spaces; use the runtime's matrices | [LS3 §2] |
| 18 | Smoothing failed: unshared vertices | Weld, orient; topology witness with a reversed-face control | [LS3 §2] |
| 19 | Diagnostic colours contaminated by overlays | Overlay-free path, flat attributes, checksum, corrupted-ID control | [LS3 §5] |
| 20 | Image difference came from UI, not the scene | Hide UI, freeze CSS animation, unchanged-twice control first | [LS2 §4] |
| 21 | Shaders compiled while bakes 404'd | Asset preflight: verify bytes and sha256 before scene creation; corrupted-asset control | [LS4] |
| 22 | Atlas V convention swapped materials | GPU texel probes at declared coordinates | [LS4] |
| 23 | One ImageTexture per binding | One DEF owner, USE references, no mips on data maps | [LS4] |
| 24 | CPU time renamed GPU time; idle frames called fps | Four clocks kept apart; forced-redraw workload; nulls for unavailable | [LS4; IFC] |
| 25 | Interrupted benchmark exported as complete | Condition change cancels and erases the export | [LS2 §4; LS3 §8] |
| 26 | "No camera jumps" rejects intended cuts | Director card declares cuts; motion checked within shots | [LS2 §4] |
| 27 | Metadata valid but unattached | Explicit containerField; runtime warnings reject; read the live node | [GEAR §8; IFC] |
| 28 | Correct rate, wrong phase (half-pitch collision) | Check state, not only derivatives | [GEAR §5, §9] |
| 29 | Sampled gap reported as guaranteed | Certified lower bound; unresolved fails | [GEAR §4] |
| 30 | Loading overlay made an empty frame look full | Disable splash, exclude status strip; camera-negative control | [BREAK] |
| 31 | Duplicate paid call hid under the cap | Separate duplicate-key and over-cap fixtures | [BREAK] |
| 32 | Count passed while identity was wrong | Match identities, not counts | [BREAK] |
| 33 | Missing value became zero | Null semantics end to end; never COALESCE to 0 | [CITY] |
| 34 | Default Decimal context rounded > 28 digits | Explicit local context; long-tail fixture | [CITY] |
| 35 | Rejection caught but its insertion kept | Savepoint rollback; inject failure after insertion | [IFC] |
| 36 | Stable GUIDs but bytes changed (set order) | Sort; compare bytes on regeneration | [IFC] |
| 37 | Quantisation used as tolerance | Spatial search + one-to-one match within a tolerance | [IFC] |
| 38 | Load "ended cleanly" at 88.6% of a table | Rename output only after the whole pipeline succeeds and counts reconcile | [WD] |
| 39 | Expected total double-counted | Two-route rule: show the derivation and a second route | [WD] |
| 40 | "Byte for byte" claimed after comparing sizes only | Say what was compared | [WD] |
| 41 | 22 agents emptied the usage window | ≤ 3 agents; partial results on disk | [LEC 10] |
| 42 | Validator pins spread over five fork commits | One tagged pin for the family | [MC §1; DEF decision 5] |
| 43 | A smoke test run with `-I` could not import its own package | Run patch smoke tests as their README says (`-E -s`); the result was `error`, correctly not `fail` | [KIT, 3 Nov] |
| 44 | Rebuild on another platform: PNG bytes and last-bit floats differ while content is identical | Cross-platform reproduction compares decoded pixels and tolerance-checked floats; byte identity is claimed only on the original platform | [CAT §Patch results] |
| 45 | A geometry witness's own positive control fails on another platform: the kernel split quads along the other diagonal | Compare surfaces (or canonicalise triangulation), not triangle lists; run every fold-back's smoke on a second platform before promotion | [KIT runs/foldbacks-20261104/report.json] |

---

## 9. Planned, not yet run (roadmap)

Scope decision, 3 Nov: v1 defines what has run. Everything below is defined in the sources but has not run, and is S or L until witnessed.

### 9.1 The Gobbler and the Village Voice [DEF §Agent architecture]
The Gobbler is the agent that operates the Loom: it plans, weaves, calls the witnesses and answers the village. It is simulated today as the ten demiurge wing roles. Inside it the Village Voice talks with villagers and writes structured, schema-checked **petitions** (graded S). The Gobbler answers (weave, defer, decline), and a woven petition adds one layer, never a replacement. The validator role is always code, never a model; the curator is always HagopJay. Decided 1 Nov: the Voice runs on a strong hosted model behind a response cache keyed by prompt hash, plays from a recorded tape inside a published page, and goes live later.

### 9.2 Before the music (M1 to M12) and Loomsong full production [DEF §Before the music; SPEC]
Score card loader; audio synthesised from the score; Ear, Score and Sync witnesses; a sound probe in X_ITE under the host copy; one clock; camera grammar as rules; motion and flash safety; a real-GPU lane (yes given, the existing spot L4, [cost withheld] total cap for API and GPU); Loom Receipt v1 for music; one fork pin; style and budget cards. Loomsong Study 01 to v4 implemented a local subset (C, §7.3). Full production remains: two pieces, splat worlds, animated stills, a Blender film.

### 9.3 Gobblering [SPEC §Gobblering]
The improvement loop on a project: a champion, four variants changing one to three knobs, a witness veto, blind pairwise model votes in both orders (a win needs 2 of 3 judges in both orders), and **his pick overrides and is a gold label**. Stop after three rounds without a win or five since he last looked. Numeric judge votes are allowed here only as a labelled experiment, never as a release gate (decision, 3 Nov).

### 9.4 Video to world: the 8-second stage [DEF §Video to world]
A generated video as a card, then frames, masks and depth, poses, Gaussian splats (gsplat), clean-up, X3D 4.1 GaussianSplats. New witnesses: Pose (reject a video before any GPU time) and Fidelity (PSNR/SSIM/LPIPS on held-out frames only, GPU named). Each video generation and any GPU needs his yes.

### 9.5 Infrastructure
- Loom Receipt v1 as a MemoryRecord; one way into the graph (overview, query, traverse, how_built, 32 KB caps) [DEF §Knowledge graph; BLUE §3].
- x3dprov 0.2 with C2PA-shaped signing [DEF gap 11].
- LangGraph runs of the Gobbler's roles and a BigQuery spine [DEF §Toolchain].
- Dependency-aware witness invalidation, replacing today's conservative "any change invalidates all" [LS1 §12; LS2 §2].
- A PROV-O / OpenLineage adapter with conformance tests before claiming conformance [CITY].

---

## 10. Open questions (for HagopJay)

1. **Promote the five fold-back patches?** Four pass `loom foldback` here. Applying them to x3d.onto, the fork or x3d.ML is a PR into your repos, so it waits for your word, and those repos are not checked out on this Mac. Which first? Break-the-Loom's own table suggests Traps and shared acceptance code [BREAK].
2. **The IFC bridge fold-back fails its positive control on this Mac** (triangulation differs by platform, §7.4). Fix the witness upstream of promotion (surface comparison), or pin the platform in its profile?
3. **The family pin.** Local x3d_mcp is at fa0b389 on `fix/physics-findings` (17 Oct), not `loom-pin-2026-11-01` (decision 5, 1 Nov). Has the tag been created, and should every receipt be re-scored on it [DEF M11]?
4. **The metadata-containerfield warning** fires on Break-the-Loom controls 09 and 12. Should the projects agent confirm it in X_ITE (is a `MetadataSet` directly under `Shape` attached), and if so raise it to an error rule?
5. **Ear thresholds.** −14 ±1 LUFS (spec) or −18 to −12 (local study, enforced)? v1 keeps both, tied to their profiles, until you choose a production profile.
6. **The C/L/S scale has no "Contested" and no "Question".** Only the Shroud ledger uses those [DEF §Grades]. Add them to the Loom?
7. **Where does stumping's golden-examples log live**, and should stump runs write Loom receipts [STUMP §Practical playbook]?
8. **Two FACTS sections named P** will collide on merge; rename one to P2 [DEF gap 12].
9. **x3d.ML main still serves a private build graph** with internal identifiers: remove, or leave [DEF gap 13]?
10. **The 33 drafted upstream PRs**: when to "send" the first three (304 tests passing together) [MC §9]?

## 11. Decisions

| Date | Decision | His words or choice | Source |
|---|---|---|---|
| 1 Nov 22:17Z | Village Voice model | "use a good gemini for the voice and make sure to cache a lot and to re-use instead of fresh calls" | [DEF §Decisions 1] |
| 1 Nov | Where the Voice runs | "default whichever is easiest" → recorded tape in the page | [DEF 2] |
| 1 Nov | Home of lineage | "i guess it was in ML the whole time" → x3dprov stays in x3d.ML | [DEF 3] |
| 1 Nov | Music audio | Synthesise both from the score at a *Thriller*-grade master | [DEF 4] |
| 1 Nov | One fork pin | "yes fork" → tag loom-pin-2026-11-01 on fork main | [DEF 5] |
| 1 Nov | Real GPU | Yes: the existing spot L4, [cost withheld] total cap for API and GPU together | [DEF 6] |
| 1 Nov | DSPy in the music build | Longer-term; log judge calls DSPy-ready | [DEF 7] |
| 3 Nov | Grade scale | Keep C/L/S, with a mapping to Measured / Established / Estimate / Conjecture | This consolidation |
| 3 Nov | Model judges | Flags only in a release; numbers only in labelled experiments | This consolidation |
| 3 Nov | Scope of v1 | Method core plus a "Planned, not yet run" roadmap | This consolidation |
| 3 Nov | Stumping | A Loom stage (the attack step); the Wikipedia and MuJoCo docs are context only | This consolidation |
| 3 Nov | PR patches | Every project zip's PR patch is the record of what the Loom taught it (user's note); verified for 5 projects | This consolidation |
