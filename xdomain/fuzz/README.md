# Differential fuzzer for the X3D validation stack (built 2026-10-29)

Private. Nothing here has been sent to the Web3D Consortium or any outside repo.

The thesis this tests: X3D's XML definitions (XSD, X3DUOM, the ontology) make the generate, validate, repair loop trustworthy. That holds only if the validators agree with each other and with a runtime. This tool generates scenes, gives each one to every oracle available here, and keeps the cases where they disagree.

Grades: **C** = measured by the tools here (one machine, the versions below); **L** = my reading of code or schema text; **S** = a guess. Whether a disagreement is a specification error or a validator bug is **S** unless schema or spec text says so; where I quote text it is from the files named, not from the ISO specification (not available here).

## What runs

| | |
|---|---|
| generator `gen.py` | scenes sampled top-down from X3DUOM 4.1 `acceptableNodeTypes` (`uom` mode, 4,907 containment pairs) or from the verified matrix in `data/` (`verified` mode, 3,661 pairs the XSD accepted one at a time); depth 1 to 5; 0 to 2 non-node fields per node filled with values inside UOM bounds and enumerations; DEF (35%), USE (8%), type- and direction-matched ROUTEs placed after the nodes; profile Full 80% of the time, otherwise a smaller profile with or without some component statements. Deterministic in (seed, index). |
| mutation mode | an excerpt (at most 60 elements, path from `<Scene>` kept, url fields, protos and scripts stripped) of five real scenes in this repo (constellation, Dyson demo, tender, feather, villager), then 1 to 3 of: swap a child for another UOM-allowed type, move a child to another UOM-allowed field, ROUTE first, add a ROUTE, set a legal value, set a value just outside a UOM bound, swap the profile, grow a subtree |
| oracles `oracles.py` | the fork's XSD (`validate_xml`, XSD 4.1), semantic check (`semantic_diagnostics`), profile check (`check_profile`); my X3DUOM reader (containment, SFNode cardinality, containerField choice types, bounds, enumerations, unknown attributes); **X_ITE 16.5.1** in headless Chromium (`xite_worker.js`: one page, 25 scenes per call, `createX3DFromString`, console warnings and errors captured in the page, nodes counted by walking the built scene, ROUTEs counted, a 20 s cap per scene) |
| buckets `classify.py` | uom_allows_xsd_rejects, uom_denies_xsd_accepts, xsd_valid_xite_drops, xsd_valid_xite_warns, semantic_false_alarm (an error from the fork's semantic check on a scene XSD, UOM and X_ITE take cleanly), semantic_silent_drop (X_ITE drops part of an XSD-valid scene and the semantic check says nothing about it), profile_mismatch |
| minimiser `minimize.py` | ddmin over elements, then single deletions and hoists (a wrapper replaced by its children), then the profile set to Full, then ddmin over attributes; each round's candidates go to X_ITE in one call. The predicate is "the same bucket and signature still appear". |
| residue `residue.py` | the 441 pairs of DIRECTIONS A3, one by one, rebuilt in a context the XSD has verified |

Versions: fork `/home/user/x3d_mcp` at `2b696f5`, lxml 6.1.3, X3DUOM 4.1 as bundled there, X_ITE 16.5.1 (`gobbler-v4/vendor/x_ite`, fetched and hash-checked by `make v4-data`; `x_ite.min.js` sha256 66ce4165…), Chromium 1243 with SwiftShader. **X3DOM was not run**: the CDN (cdn.jsdelivr.net) is refused by this session's proxy; the npm registry answers, but I did not fetch it.

```
make fuzz           # 2,000 scenes, seed 1 -> findings/TABLE.md, findings.json, one .x3d per signature
make fuzz-residue   # the 441 pairs -> findings/residue.json, findings/residue/*.x3d
make test-fuzz      # 30 checks
```

## Results, 2,000 scenes, seed 1 (C)

Run time **4 min 12 s** wall clock here (X_ITE 229 s of it, minimising 55 s, generation 7 s). 1,636 scenes are XSD-valid with nothing from UOM; 268 are XSD-invalid with nothing from UOM; 72 are flagged by both; 24 are XSD-valid and flagged by UOM.

| bucket | scenes | signatures | reproducers that re-check |
|---|---:|---:|---:|
| uom_allows_xsd_rejects | 288 | 61 | 61 |
| uom_denies_xsd_accepts | 24 | 7 | 7 |
| xsd_valid_xite_drops | 81 | 10 | 9 |
| xsd_valid_xite_warns | 12 | 4 | 4 |
| semantic_false_alarm | 27 | 3 | 3 |
| semantic_silent_drop | 80 | 9 | 8 |
| profile_mismatch | 33 | 21 | 21 |

A scene can fall in more than one bucket. 113 of 115 minimised reproducers re-check when run again; the 2 that do not are the "scene load did not settle in 20 s" signature, which depends on what ran before it in the page (below). Full table: `findings/TABLE.md`.

### The reproducers that matter most

1. **ROUTE before its node** (`xsd_valid_xite_drops/route-XML_Parser_Unknown_named_or_imported_node___.-sem-silent-*.x3d`, 3 elements; **67 scenes**). XSD-valid, 0 semantic errors, profile OK; X_ITE warns "XML Parser: Unknown named or imported node" and drops the ROUTE. This is the gobbler-demiurge validator gap, found and shrunk by the fuzzer without being told about it. **C**. Whether the specification makes it an error: **S**.
2. **X_ITE throws on a scene UOM and XSD accept.** `TextureBackground` with `MultiTexture` as `frontTexture`: X_ITE fails the whole load with "t?.checkLoadState is not a function" (3 scenes). The UOM field says `acceptableNodeTypes="X3DTexture2DNode|MultiTexture"` and its description says "Parent TextureBackground element can contain up to six image nodes (ImageTexture PixelTexture MovieTexture MultiTexture)". **C** that it throws; **L** that it is an X_ITE bug.
3. **Analyser minDecibels / maxDecibels.** `<Analyser minDecibels="-4.266"/>` (default maxDecibels -30): X_ITE fails the load ("The minDecibels provided … is greater than or equal to the maximum bound", from Web Audio). UOM gives no bound or ordering for either field; XSD and the semantic check accept (3 scenes). **C**; whether the spec requires min < max: **S**.
4. **Field access differs between UOM and X_ITE.** A ROUTE into `AudioDestination.maxChannelCount` is dropped ("destination field … must be an input"); ROUTEs naming `ListenerPointSource.gain` and a Script field are dropped as unknown fields. UOM lists these fields with the access the generator used; the semantic check (which reads UOM) is silent. **C**.
5. **XSD content models written as `xs:sequence` where the field is a set.** `NurbsSet` (7 scenes), `ParticleSystem.physics` (7), `ComposedTexture3D.texture`: the XSD lists the allowed children inside `<xs:sequence minOccurs="0" maxOccurs="unbounded">` (read in `x3d-4.1.xsd`), so one `ForcePhysicsModel` alone, or one `ImageTexture` alone ("Missing child element(s). Expected is ( MovieTexture )"), is rejected; a full run of every listed type in order is required. UOM types these fields MFNode with an abstract range. **C** that the XSD says this; **L** that it is a schema error.
6. **bboxSize** (148 scenes, the largest signature): a negative component other than the default `-1 -1 -1` fails the XSD pattern. The XSD says "bboxSizeType dimensions are non-negative values, default value (-1 -1 -1) indicates that no bounding box size has been computed." X3DUOM carries this only as `baseType="bboxSizeType"`, a reference to the XSD type, not as a bound; my UOM reader does not resolve it, so this bucket counts it. **C** for both texts; the disagreement is in how much of the rule UOM states itself.
7. **Profiles.** All 21 signatures (33 scenes) go one way: the fork's profile check says a node is outside the declared profile and components, and X_ITE builds it with no warning. The commonest is `PhysicalMaterial` (component Shape) under Interchange, MedicalInterchange, Interactive and CADInterchange; others are Sound, Interpolation, Grouping, Navigation nodes under smaller profiles. Elsewhere X_ITE does warn "Node type … does not match component/profile statements" and still builds the node; those cases agree with the fork and are not counted. **C**.
8. **semantic_false_alarm is not what its name says.** All 27 scenes are the fork's rules catching what the XSD and X_ITE both ignore: `interpolator-key-length` (25: key and keyValue counts disagree, which my generator produces), two Gaussian-splat array checks. By my reading these are right (**L**). No semantic false alarm in the strict sense was found in 2,000 scenes.
9. **UOM bounds the XSD does not enforce** (uom_denies_xsd_accepts): `HAnimJoint.scale`, `HAnimHumanoid.scale`, `HAnimJoint.stiffness`, `NavigationInfo.avatarSize`, `ColorRGBA.color` out of UOM range pass the XSD; two placements UOM denies pass the XSD (`InlineGeometry` in `LayoutLayer.children`, a grouping node in `HAnimHumanoid.children`). **C**.

Signatures are coarse on purpose (DEF names, numbers and quoted values stripped from messages; containment keyed by parent, field and the child's base type), so one cause should give one file. Some causes still split, for example "sem-flags" vs "sem-silent" variants of the same X_ITE exception.

## The 441-pair residue (DIRECTIONS A3) (C unless marked)

`residue.py` recomputes the set from `data/` exactly as `harness/proposal_numbers.py` does and gets **441**; `model.py` gives the UOM universe as **4,907** pairs. Both match FACTS N.

Per-parent counts in DIRECTIONS A3 ("Layer 96, LayoutLayer 93, GeoLOD 52, Collision 50, pick sensors ~95") are the counts of the **643**-pair set (all fields, FACTS M), not of the 441: in the 441 they are Layer 10, LayoutLayer 9, GeoLOD 40, Collision 50, pick sensors 95 (Point 33, Line 32, Primitive 30).

Each pair rebuilt with its parent reached from `<Scene>` by the shortest chain of XSD-verified placements:

| cause | pairs | X_ITE 16.5.1 builds the child |
|---|---:|---:|
| X3DUOM's own containerField choice type for the child lacks the field (e.g. `containerFieldChoicesAudioGraph` = children, outputs, source; no `proxy`) | 70 | 70 |
| X3DUOM's own ContentModel for the parent (its group names resolved in the XSD) excludes the child | 337 | 336 |
| harness artifact: `ProtoInstance` without `name` or declaration; accepted once declared | 20 | 20 |
| harness artifact: accepted once placed by a verified chain (`BlendedVolumeStyle`, `ComposedVolumeStyle` nested in themselves) | 2 | 2 |
| parent not reachable through verified placements (`CollidableOffset`) | 1 | 0 |
| every UOM structure admits it and the XSD rejects (the `xs:sequence` cases above, `TextureProperties` alone in `ComposedCubeMapTexture`, `GeoLOD` as `rootNode`) | 11 | 11 |

What this says:
- **407 of the 441 (92%) are X3DUOM disagreeing with itself**: `acceptableNodeTypes` allows the pair; the same file's containerField choice types or ContentModel do not, and the XSD follows those. The 66 harness rejections that were containerField enumeration errors are all among the 70.
- **22 are harness artifacts**, so the residue of real UOM-allows/XSD-rejects pairs is at most 419.
- **X_ITE builds the child in 439 of 441**, with no warning naming it: the runtime follows `acceptableNodeTypes`, not the XSD.
- So for the generate, validate, repair loop, the XSD is stricter than the runtime on these pairs, and a model trained on the XSD's verdicts would be told "invalid" for scenes that render. Which side the specification intends is **S** for every row; each row is a concrete question for the Consortium (held, not sent).
- Random generation reached 49 of the 441 pairs on its own in 2,000 scenes, plus 100 other UOM-allowed placements the XSD rejects that the matrix (one child per document) never tests.

## Limits
- One seed, one machine, one runtime. X3DOM not run (above). X_ITE is asked to build each scene, not to render it: `--render` (replaceWorld plus two frames) exists and costs about 100 ms per scene against about 20 ms; it was timed on one scene repeated 50 times only.
- X_ITE state carries across scenes in one page. A few scenes did not finish loading within the cap only when they followed certain others; that signature does not reproduce alone and is marked so. The page is restarted after such a scene.
- My UOM reader is mine (L): it does not resolve `baseType` references to XSD types, ContentModel order, or inter-field constraints.
- Values are random inside UOM bounds, so inter-field faults (key/keyValue counts, min/max pairs) occur by chance, which is how items 3 and 8 were found.
- Signatures are heuristics; a bucket's signature count is a count of distinct messages and placements, not of distinct root causes.

## Files
`model.py` (UOM, verified matrix, residue), `gen.py`, `oracles.py`, `xite_worker.js`, `classify.py`, `minimize.py`, `run.py`, `residue.py`, `test_fuzz.py`; output in `findings/` (`TABLE.md`, `findings.json`, `<bucket>/*.x3d`, `residue.json`, `residue/*.x3d`).
