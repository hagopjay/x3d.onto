# 02 · Data model and ingest (loom stage 1)

Analyst 2 of 7 · 2026-10-29 · Prototype and outputs: `scratchpad/proto/ingest/` (the paths below are relative to it).

Grades used here:
- **C** Confirmed: a tool here opened or ran it.
- **L** Likely: read, or a standard value from memory.
- **S** Suspected: unchecked, or model recall.
- **I** Illustrative: for display only.

Every finding names the tool behind it.

## Summary

- **The current record is for display, not genealogy (C, `jsobj.py` and the gates).** `FamilyMember` has one bare year per event and a single `spouse` that is stated from one side only. Its `generation` is typed in by hand, and it has no sources, places, sex or privacy flag. The Rothschild data exists in four overlapping versions that disagree on parents, dates and generations.
- **The canonical graph** has four node classes: Person, Union, Branch and Place.
  - Every fact is a claim with a source, a locator, a verbatim quote, a grade and a provenance.
  - Unions are nodes in their own right.
  - Generation and kinship are computed from the tree, never stored.
- **The generator (C):** `ingest.py` needs only the standard library plus `jsonschema` for one gate. It reads 7 pinned sources (7 byte-identical copies are also checked) in 0.36 s and builds:
  - 30 people, 14 unions and 607 claims;
  - 25 gates and a receipt;
  - graph JSON, JSON-LD, GEDCOM 7, GEDCOM X and a view in the shape the Cosmos app reads, each in a private and a public-candidate build.
- **Cousin marriages and a blocked build (C, G17 and G09).** It finds the two Rothschild cousin marriages in the data and computes their kinship coefficient φ: 1/8 and 1/16. It also refuses the public build on a real error: Guy (born 1909) is listed as a son of Alphonse (died 1905).
- **GEDCOM 7 (C, G21 and unit tests).** A GEDCOM 7 reader and writer round-trips both builds. A synthetic test file covers Julian dates, adoption, remarriage, a cousin marriage, `RESN` and living people.

## 1. Audit of the current shape

**What exists** (C: read as data with `jsobj.py` and `json`; md5 hashes and file times from the shell)

| Source | Records | Read by | Notes |
|---|---|---|---|
| `*/data/family.ts` (4 byte-identical copies) | 18 | roths3 app; `cline_docs` calls it the "source of truth" | `victor → charles` points to no one; Guy's parent is Alphonse |
| `roths/data/trees/rothschild.json` | 9 | roths app, through `datasets.ts` | placeholder picsum images for Mayer and Gutle |
| `habsburg_stub.json`, `darwin_wedgwood_stub.json` | 1, 2 | roths app | only Emma states the marriage |
| `rothschilds.html` (v1) | 26 | standalone page | no branch; Betty has no parents; James Édouard 1844–1881 |
| `rothsch2.html` (v2, plus an identical copy in collateral/) | 26 | standalone page | branch and notes; James Édouard 1878–1957; Guy's parent is Edmond |

**What each field cannot do**

| Field | Today | Problem | Canonical answer |
|---|---|---|---|
| `id` | local slug; the renderer builds `${ds}:${id}` | no outside identity | `person:{dataset}/{local}`, plus `ids.wikidata` and `ids.enwiki`, written as GEDCOM `EXID` |
| `name` | one string | spelled differently across files (Betty, Charlotte: G15) | `names[]`, each preferred or variant and backed by claims |
| `born` | a required `number` | forces an invented value; no precision, qualifier, calendar or place | `facts.birth.date` plus a `born_in` edge |
| `died` | an optional `number` | `died ?? 'Present'` and `m.died \|\| 2025` turn "unknown" into "alive" | `facts.death`, `DEAT Y`, and an explicit `living` rule |
| `generation` | a stored integer | contradicts the tree: Betty is stored as 2 but derives as 3, and three brothers are stored as 3, 3 and 4 (G11, G12) | derived as `{min, max, method}`; the layout value is graded I |
| `parents` | an array of ids | no kind of parentage, no way to contest it, references to missing people allowed | `child_of` edges from a Union with a `pedigree` value, plus `alt_parent` edges |
| `spouse` | a **single** string | stated from one side; no remarriage; dropped edges (see below) | Union nodes with `partner_in` edges |
| `branch` | a string | used both as lineage and as a longitude seat | `member_of` a Branch, plus `seated_at` a Place with coordinates |
| `note`, `wikipedia` | free text and a URL | no sources | claims, and `ids.enwiki` |
| `imageUrl` | picsum placeholders | looks like a portrait but is a random photo (G19) | `media.kind = placeholder`, dropped from views |
| `achievements` | declared but never filled | none | events and notes with claims |
| (missing) | sources, sex, places, events, privacy | `DatasetManager.validateGraph` checks only three keys | the schema below, checked by gate G05 |

**Spouse edges the renderers drop or duplicate (G18).** The React renderer draws a spouse edge only when `id < spouse`, so the Darwin–Wedgwood marriage is never drawn. The v1 page draws four couples twice.

**Errors in the data.** The gates confirm that each conflict exists (C). The historical reading is S, from model recall, because wikidata.org returned 403 here.

1. **Guy's father.** Guy (born 1909) has Alphonse (died 1905) as parent in all four family.ts copies, and Edmond in both HTML pages. Historically his father was Édouard (1868–1949), Alphonse's son (S).
   - The prototype records this in `curated/decisions.json` with prov `model_recall`.
   - Leaving the decision out reproduces the blocked build.
2. **"James Édouard" is two people under one id (G13, G14).** He is 1844–1881 in v1 and 1878–1957 in v2. The first matches James Édouard, Nathaniel's son; the second matches James Armand, Edmond's son (S).
3. **Betty is a generation too high.** v1 also gives her no parents (G11, G16).
4. **Cousin marriages the data leaves out (S):**
   - Natty (Lionel's son) × Emma Louise von Rothschild;
   - Anselm × Charlotte, Nathan's daughter.

   Charles Darwin and Emma Wedgwood were first cousins (L), which a two-person stub cannot show.

## 2. Canonical schema

The schema is `schema/genealogy-graph.schema.json`, written to JSON Schema 2020-12. Gate G05 validates both builds against it (C, jsonschema 4.26.0).

**Principles**
- **Claims, not fields.** A claim is `{id, source, kind, subject, predicate, value, locator, quote, grade, prov}`. Its id is the first 12 hex digits of the sha256 of `[source, locator, predicate, value]`. Every quote must appear verbatim in the pinned file (G04: 607 of 607, C).
- **Open world.** An empty `parents` list means "not stated", not "no parents".
- **Precedence and alternatives.** Manifest order decides which value wins. Every other value is kept on the fact as `status: contested` with `alternatives[]`.
- **Independent agreement only.** Agreement raises a grade only when the sources come from independent families. Five app files that copy each other count as one source.
- **Derived values** carry `prov: computed` and are never written back as data.

**Nodes and edges**
- **Person** has:
  - `names[]`;
  - `facts.birth` and `facts.death`, each `{date, place, claims, status, grade, alternatives}`;
  - `generation`, `ids`, `notes`, `media`;
  - `living {value, rule, grade}`, `vis` and `metrics`.
- **Union** is GEDCOM's `FAM` record. It has:
  - `partners`: at most two, ordered, written as a JSON-LD `@list`;
  - `partner_unknown`: open unions are written `+?`;
  - `children`;
  - `type`: marriage, unknown or open;
  - `consanguinity {related, phi, relationship, paths}`.
- **Branch** and **Place.** A Place has `geo {lat, lon, grade, prov}` plus Wikidata and GeoNames ids. The five branch seats are in `curated/places.json`; their coordinates are graded L and their ids S.
- **Edges** are `partner_in`, `child_of` (with `pedigree` BIRTH, ADOPTED or FOSTER), `alt_parent` (contested parentage), `member_of`, `seated_at`, `born_in` and `died_in`. Each edge has its own grade, prov and claims.

**Dates** (`gdates.py`) are a single object with `kind`, `qualifier`, `calendar`, `precision`, `phrase`, an `earliest`/`latest` window, and three spellings: `gedcom`, `edtf` and `gedcomx`.

| GEDCOM | EDTF | GEDCOM X | Window or handling |
|---|---|---|---|
| `ABT 1850` | `1850~` | `A+1850` | 1845–1855 (a policy setting) |
| `BET a AND b` | `[a..b]` | | |
| `JULIAN 22 MAR 1459` | | | converted through Julian day numbers |
| bare year | | | precision `year`; before 1582 it raises a calendar notice (G20) |

**Generation** is computed from the tree as `{min, max, method}`. The method is founder, descent, partner-aligned or isolated.
- Marriage inside the family gives a range. Alphonse, Gustave and Edmond are [3,4]: generation 3 through their father James, 4 through their mother Betty.
- The layout uses `max`, graded I.
- Stored values are kept per source only to diff against.

**Kinship** (`kinship.py`):
- φ is Malécot's kinship coefficient, computed with Karigl's recursion in exact fractions. A child's inbreeding coefficient is F = φ of the two parents.
- Relationship names come from the lengths of the paths to the common ancestors, and say whether the relationship is full or half.
- Pedigree collapse = 1 − distinct ancestors ÷ filled ancestor slots.
- F is flagged as a lower bound whenever a pedigree is missing a parent.

**Privacy rule** (separates the public and private builds):
- A person is dead if a death is recorded or asserted (`DEAT Y`).
- A person is presumed dead if the latest possible birth (or a bound set by a child's birth) is more than 110 years before `as_of`.
- Everyone else is presumed living. `RESN CONFIDENTIAL` or `RESN PRIVACY` always hides the person.

The public candidate turns each hidden person into an opaque "Living or private person" node, and drops:
- their claims and conflicts;
- their branch and place edges;
- the kinship values on unions they belong to;
- any metric computed through them. Otherwise a child's F of 1/16 would reveal a hidden parent's cousin marriage.

G23 checks all of this. The public files are written only when every error gate passes.

**Alignment with gobbler-v3.** The graph keeps gobbler's conventions:
- `grade`, `prov` and `vis` on nodes and edges;
- `filter_public` on `vis`;
- the JSON-LD context: `@vocab https://polyxandria.example/kg#`, `name → schema:name`, `prov → px:provenance`, `grade → px:grade`;
- sha256 receipts.

It departs from gobbler in three ways, on purpose:
- Ids are strings prefixed by class.
- Evidence sits in one top-level `claims` array that facts and edges reference; gobbler puts `px:evidence` on each `px:Statement`. Claim values are typed `@json` literals.
- There is a fifth provenance, `computed`, used alongside the `Illustrative` grade from x3d.onto v2.

**Mappings** (L for the specs, from memory; C only for the prototype's own export and import agreeing with each other, gate G21)

| Canonical | GEDCOM 7 | GEDCOM X | Wikidata | schema.org |
|---|---|---|---|---|
| Person | `INDI` | `Person` | item | `Person` |
| birth, death | `BIRT`/`DEAT` with `DATE`, `PHRASE`, `PLAC` + `MAP`; `DEAT Y` | `Fact` Birth or Death with a formal date | P569/P570 (with calendar model), P19/P20 | `birthDate`, `deathDate` |
| Union | `FAM` with `HUSB`/`WIFE` as partner slots of any sex, and `MARR` | `Couple` relationship | P26 with qualifiers | `spouse` (loses detail) |
| child_of | `CHIL`, plus `INDI.FAMC` with `PEDI` | `ParentChild` | P22, P25, P40 | `parent`, `children` |
| alt_parent | `FAMC` with `STAT CHALLENGED` | an extra `ParentChild`, confidence Low | none | none |
| ids | `EXID` with a `TYPE` URI | `identifiers` | QID | `sameAs` |
| claim | `SOUR`, `PAGE`, `QUAY`, plus `_GRADE` | `SourceReference`, confidence | references | `citation` |
| privacy | `RESN` | not modelled (listed in `x-loom-losses`) | none | none |
| loom extras | `_LOOMID`, `_GRADE`, `_SHA256`, `_BRANCH`, declared in `SCHMA` | listed in `x-loom-losses` | none | none |

## 3. The prototype and what ran

About 2,400 lines of Python:

| Module | Role |
|---|---|
| `jsobj.py` | reads JS and TS literals as data only; refuses identifiers, function calls, spreads and `${}`, so no app code is ever run |
| `loaders.py` | turns the Cosmos JSON trees, the TS and HTML literals, and GEDCOM 7 into claims |
| `build.py` | merges sources and derives unions, generations and issues |
| `gdates.py`, `kinship.py`, `gedcom7.py` | dates; φ and F; GEDCOM 7 parsing, import and export |
| `exports.py`, `gates.py`, `ingest.py` | output views and the public filter; the 25 gates; the command line and receipt |
| `resolve_wikidata.py` | adds QIDs and dates from Wikidata's `wbgetentities` API. Tested offline only; the live call was refused (403) |
| `check_jsonld.py` | expands the JSON-LD with PyLD. Run separately, so the generator itself needs no PyLD |

**How to run** (from `proto/ingest/`):
- Main build: `python3 -I ingest.py --manifest config/sources.json --src <unzipped geneology dir> --out out`
- Blocked build: add `--without-decisions`.
- Fixture: use `--manifest config/fixture.json`; its single source sits inside the prototype folder.
- Tests: `python3 -I tests/test_proto.py`

**Results** (C: `out/receipt.json`, `out/gates.json`, `out/derived-tables.json`)

| Build | People | Unions | Edges | Claims | Verdict |
|---|---|---|---|---|---|
| main | 30 (Rothschild 27, Darwin–Wedgwood 2, Habsburg 1) | 14 (5 marriages, 9 open) | 80 | 607 (603 S, 4 I) | public candidate written; every error gate passes |
| without decisions | | | | | **blocked by G09** (exit 1); old public files removed |
| fixture (synthetic GEDCOM 7 file) | 14 | 7 | 22 | 110 | written; 3 people hidden (Ida by `RESN`; Kit and Lee presumed living) |

**Gate findings on the real data**

| Gate | Finding |
|---|---|
| G07 | `victor → charles` points to no one inside family.ts; the merge with the other sources supplies Charles |
| G08 | the Darwin–Wedgwood marriage is stated from one side only |
| G11, G12 | Betty's generation; 6 groups of siblings stored at different generations |
| G13, G14 | Guy's parents contested three ways (2 `alt_parent` edges); James Édouard is two people merged |
| G17 | James × Betty: uncle and niece, φ = 1/8, so F = 1/8 for Alphonse, Gustave and Edmond (pedigree collapse 2/7). Lionel × Charlotte: first cousins, φ = 1/16, so F = 1/16 for Natty and Alfred (collapse 2/9). All are lower bounds. |
| G18 | the renderer edge problems from section 1 |
| G19, G20, G25 | 4 placeholder images; Maximilian I's dates have no calendar; 21 Wikipedia titles still need QIDs |

**Generation ranges.** Guy is [5,6] with the decision and [4,5] without it, against a stored 6. Hannah is [2,2], aligned to her partner.

**The blocked build** fails G09: Guy is born more than a year after his listed parent died. It also warns that the parent would have been 82 at the birth (G10).

**The fixture** checks the privacy rule:
- the first-cousin union gets φ = 1/16;
- Jo's F of 1/16 is withheld from the public build because it passes through the hidden Ida;
- the adopted Max has F = 0.

**Other checks (all C):**
- 15 unit tests pass.
- PyLD 2.0.4 expands the JSON-LD with 0 bad IRIs: 7,220 triples for the main build, private and public, and 1,484 (private) and 1,267 (public) for the fixture.
- The GEDCOM round trip (G21) re-imports all 53 records unchanged.
- Two builds produce byte-identical files (G22).
- The receipt pins Python 3.13.17, the jsonschema version, and the sha256 of the manifest, every script, every input and every output. It also records the 0.357 s build time.

## 4. Path to a GEDCOM 7 importer

`gedcom7.py` is a working start, not a complete reader (C for what the code does, L for statements about the spec).

**Parsing**
- Reads the line grammar `level [xref] TAG [payload]`, including `_` extension tags.
- Unescapes `@@` and joins `CONT` lines.
- Refuses `CONC`, which exists only in 5.5.1, and any `HEAD.GEDC.VERS` other than 7.x.

**Import** feeds the same claim stream as the app loaders, with the line number as the locator and the lines themselves as the quote. It reads:
- `INDI` with `NAME`, `SEX` and `RESN`;
- `BIRT` and `DEAT` with `DATE` and `PHRASE`, `PLAC` and `MAP`, and `SOUR`/`PAGE`/`QUAY`;
- `EXID` with `TYPE`, `NOTE`, and `FAMC` with `PEDI` and `STAT`;
- `FAM` with `HUSB`, `WIFE`, `CHIL` and `MARR`;
- the loom extension tags.

`QUAY 3` maps to Likely, not Confirmed, because a file's `QUAY` is someone else's assessment.

**Export**
- Declares the extension tags in `SCHMA`.
- Writes contested parents as `FAMC` with `STAT CHALLENGED`, and alternative dates as repeated events.
- Writes `MARR Y` or `DEAT Y` when an event happened but has no date.

**Next steps, in order**
1. Run it against the published GEDCOM 7 test files. That was not possible here, with no network.
2. Read the remaining events (`BAPM`, `BURI`, `RESI`, `OCCU`, `TITL`), name parts, `SNOTE`, `OBJE`, `ASSO` and full `SOUR` records.
3. Add a 5.5.1 front end that joins `CONC` lines, converts dual years and `INT` dates, and maps the common `_` tags, then hands the result to the 7.0 reader.

## 5. Reading the harvest and fact-check files (not built yet)

**The fact-check files** `proto/facts/{rothschild,habsburg,darwin_wedgwood}.json` already use the Cosmos tree shape, `{id, name, members[]}`. `load_json_tree` reads them as they are; only the new member keys need mapping into claims:
- `spouses[]` becomes one Union claim per spouse, replacing the single `spouse`.
- `qid` becomes an `EXID` claim, graded by `qid_confidence`.
- `born_precision` and `died_precision` set the date precision in `gdates`.
- `sources[]` become the cited source on each claim.
- `confidence` can lower a grade but never raise it above what the provenance allows. Facts a model wrote stay `model_recall` and Suspected unless a tool fetched and hashed the cited page.

These files enter the manifest as an overlay family, `fact-check`, placed after `decisions`.

`facts/consanguinity.json` and `facts/source_diff.json` are not sources of facts. They become cross-check gates: their φ and F values must match `kinship.py`, and their diffs must match G13, G15 and G16. Any mismatch is reported.

**The harvest files** `proto/harvest/*.json` have the shape `{partition, group, persons[]}` and need a new `load_harvest`:
- **Matching people.** Each record is matched to an existing person by QID first, then by Wikipedia title, then by name plus a birth year within `identity_conflict_years`. Name alone never matches. Provisional `x:` ids stay local and are flagged.
- **Dates.** The `born` and `died` objects map straight to `gdates` (`date` plus `precision`). A missing calendar raises G20 for dates before 1582.
- **Places.** `place` and `place_qid` become Place nodes with `born_in` and `died_in` edges.
- **Parents and spouses.** `father` and `mother` become ordered `child_of` claims. `spouses[{id, married, ended}]` become Unions with a dated `MARR` and an end date. `children[]` is checked against the parent links in reverse, the way G08 checks spouses.
- **Other fields.**
  - `sex` becomes a claim.
  - `living_possible` forces "presumed living" unless a death is recorded.
  - `core` is a view filter, not a fact.
  - `titles` and `occupations` need the `OCCU` and `TITL` fact kinds from section 4.
- **Grading.** `sources` and `confidence` follow the rule above. A record whose Wikidata response was saved and hashed is prov `data`, graded Likely.

Both sets of files must be pinned in the manifest (G01), and both may be partial. Under the open-world rule, a missing record takes nothing away. A later, complete file simply becomes a new pinned version of the source.

## 6. Recommendations

1. **Make the generator the app's input.** The roths3 app should load the generated `cosmos-datasets.json` instead of the hand-edited `family.ts`. That file already adds `spouses`, `unions`, `generationRange`, `living`, `grade`, `contested` and `inbreedingF`. The app should draw Union nodes rather than spouse fields, which removes the G18 problems by design.
2. **Correct data through overlays,** such as `curated/decisions.json` with its `why` field, never by editing the app files. That way the receipt shows every correction.
3. **Run `resolve_wikidata.py` somewhere wikidata.org is reachable.** Today 603 of the 607 claims are S because every input is an unsourced app file. Independent sources with references are the only way to reach L or C.
4. **Add the missing cousin marriages and the Darwin and Wedgwood parents.** Pedigree collapse is the story this data can tell visually: a φ ring on Union nodes, and an F halo on each person, shaded to show it is a lower bound.
