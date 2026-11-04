# LOOM KICKOFF (PRE): paste before the first prompt

Paste as the first message of a new Loom project. Attach `LOOM-v1.md` (an LLM outside the hosting app gets it as Markdown). Paste `HANDOFF-POST.md` under it, in the same message. Fill every angle bracket. Sections 1, 2 and 6 change per project; the rest stay almost the same. Based on the 1 Nov kickoff doc [KICK], updated for Loom v1.

```
LOOM KICKOFF (PRE). Read all of this and the attached LOOM-v1.md before writing any code.
From LOOM-v1 read at least: 3 The laws, 4 The loop, 6 Quality gates, 8 Known failure modes.

You are applying the Loom to <an existing 3D idea | a new one>. The Loom is a generator plus witnesses:
you write code that emits the X3D, independent witnesses check it, a named acceptance profile decides,
you repair the generator until they agree, and every claim carries a grade and a receipt.

1. TARGET
- Idea: <name>. Today it is: <one line>.
- Source of truth: <repo>/<path> @ <commit>. Live copy: <link | none>.
- Better means (measurable): <e.g. wins a blind A/B against v<N>; real-GPU fps >= 60; 0 errors on the pin>.
- Must not change: <e.g. the v<N> page and its files>. Build v<N+1> beside it. Never overwrite a demo.
- Visibility: <private | public>. If public: no keys, cloud project id, run-as identity, costs, vendor
  names or private links; a leak sweep runs before anything is published.

2. TOOL PINS (use exactly these; every witness record and receipt names them)
- Validator: hagopjay/x3d_mcp tag <loom-pin-2026-11-01> (<sha>); until the tag exists, fork main @ <sha>.
- Trap gate: loom_gate.py from x3d.onto @ <sha>, all rules plus --fork. Where x3d.onto is absent,
  loomkit traps (LOOM-v1 kit) as the portable subset, named as such.
- X3D <4.0 | 4.1>, profile <Interchange | Immersive | Full: the smallest that fits>, every component declared.
- X_ITE <16.5.1>, shipped as the page's own files, never fetched from a CDN at runtime.
- Blender <5.2.x> with blenderizer (x3d-blender-io) @ <sha>, if the idea touches Blender.
- Headless Chromium <ver> + Playwright <ver> for Behaviour and Eyes; name the renderer (SwiftShader is not a GPU).
- Strict host-policy copy server for Host.
- Models: builder <id>; judges <ids> (flags only); image / video / audio <ids>. Cache by prompt hash.

3. TRAPS TO READ BEFORE CODING
- LOOM-v1 section 8 (45 known failure modes) and FACTS <sections>.
- Host: the policy blocks other hosts and eval. No Script nodes: drive the scene from page JS through SAI.
  Fonts as TTF. Strip the DOCTYPE from page copies; serve .x3d as application/xml.
- X_ITE: browser.currentTime is undefined, so the page owns the clock. A 4.0 file rejects GaussianSplats,
  FontLibrary, HAnimPose, InlineGeometry and RenderedTexture. Inline shader source needs a data: prefix.
  A ROUTE written before its node is dropped. A still PNG in MovieTexture hangs the world. Give metadata
  an explicit containerField. Valid X3D can still be invalid GLSL: check isValid at runtime.
- Colour values above 1 fail the XSD with a message that blames something else.
- Splats: give every GaussianSplats node bboxSize and bboxCenter.
- Build in scratch, never in a shared folder that stamps files; never serve while building.
- <traps specific to this idea>

4. GENERATOR FIRST
- Never hand-edit an output. A generator (<path>) emits the X3D and a build manifest.
- Same inputs and seed give the same bytes: SOURCE_DATE_EPOCH, seeds, sorted keys, pinned libraries.
- One data file holds every number the scene shows; page, film and report all read it.
- A red witness stops the build: fix the card or generator, never explain it away.

5. GUARDRAILS
- Budget: $<cap> for API and GPU together. Log every paid call (model, units, list price, prompt hash,
  cached) in <ledger path>. Stop at the cap and ask.
- Wait for my typed yes before: any new cloud resource, quota or role; any delete; any download or
  install; anything public or sent outside; any new paid model; going past the cap.
- Grade every claim C / L / S. Model output is S. Label anything synthetic.
- Model judges give located "suspected" flags, never scores, in anything that gates. My eye and ear decide.
- Label AI-made images, video and voices where they appear. No real faces.
- Stop-and-show points: <list>. Keep working on the recommended path while I look.
- At most <3> agents at once; write partial results to disk.

6. WITNESS PLAN AND ACCEPTANCE PROFILE
- Profile: <name>, required witnesses: <list>; allowed deferrals, each with its reason: <list>.
| Witness   | Tool and version              | Pass when                                        |
| Grammar   | XSD via the pinned fork       | 0 errors                                         |
| Meaning   | fork semantic checks          | 0 errors; every warning listed                   |
| Traps     | loom_gate.py | loomkit traps  | 0 error hits                                     |
| Behaviour | X_ITE headless                | loads, shaders valid, console clean, ROUTEs fire |
| Eyes      | fixed-time frames, flag-only judge, me | <criteria>                              |
| Host      | strict policy copy            | works under the policy, 0 external requests      |
| Receipts  | rebuild and compare sha256    | byte-identical rebuild                           |
| Truth     | <this idea's real-world rule> | <criteria>                                       |
| Budget    | spend ledger                  | under the cap; no repeated paid call             |
| Foldback  | loom foldback on your patch   | clean apply, additions-only, smoke green normal and -O |
| <Ear / Score / Sync / Flash / Fps / Pose / Fidelity> | <tool> | <criteria with units and tolerance> |
- Every gate is a raising predicate (never assert), tested under python -O, with one passing and one
  failing fixture whose failure names the intended diagnostic.

7. WHERE OUTPUTS LAND
- Generator, scene and gate changes: one PR per change in <repo>; CI re-runs the witnesses.
- Witness records: runs/<run-id>/evidence/<witness>.json, each naming the candidate sha256.
- Receipts: receipts/<artifact>.json beside the artifact, chained by prev, never overwritten.
- Heavy evidence: named by sha256; the records store hash and path.
- Lessons: a FACTS entry plus a fold-back patch (additions-only tools/<name>/ with smoke.py).
  Upstream only after I say "send".
- Spend ledger: private project files only.

Your first reply: restate the target and "better" in your own words, name the acceptance profile and
the witnesses you will run, and list your first three steps with their cost estimate. Then start.
```
