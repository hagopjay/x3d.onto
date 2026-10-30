# Ontology thread: source index (ingested 2026-10-20)

Grades as the sources use them: **C** Confirmed (read or run), **L** Likely (author's reading), **S** Suspected (unchecked / model paraphrase). `n/a` = source assigns no grade.
Read depth: **full** = read end to end; **skim** = grep/section reads only. Sizes in chars unless noted.
Drive connector (`search_files`/`read_file_content`) WAS available; read-only use. Nothing downloaded, no tars/zips, no claude.ai artifact URLs.

| # | Source (Drive id) | Size | Date | Trust | Read | What it is |
|---|---|---|---|---|---|---|
| 1 | README (27).md `17IYnj…` | ~15 KB | 17 Oct 2026 | C/L/S per item | full | Ontology thread index + key findings 1-18. Names doc of record and file map. |
| 2 | README (28).md `15-bNu…` | ~9 KB | 17 Oct | C (S where marked) | full | SPARQL dangling-USE / wrong-type-USE checks; 7-scene run + 200-scene scale run. |
| 3 | README (29).md `1VlKGr…` | ~5 KB | 17 Oct | C readings, L interpretation | full | 8 node/field claims of Carlson's Gemini review of X3D 4.1 tested against X3DUOM 4.1. |
| 4 | README (30).md `1t4aTE…` | ~19 KB | 17 Oct eve | C trials; L DSPy/parts; S reconstructions | full | Steps 2-4: use-type check, Polys 2024 rerun, DSPy arms, parts-and-contact. |
| 5 | DOC.md `12JR1T…` | 82,259 chars (task said 47 KB) | 17 Oct (rev 68) | C/L/S per row | sections 1-4, 6-8, App A, D read; **skim** 5, 8 (duplicates 4/references), App B, C, E | Doc of record: ladder, cross-check table, philosophy, 10 questions to Polys, next steps, heuristics, evidence ledger. |
| 6 | references.md `1qOM_2…` | ~9 KB | 17 Oct | L (page read, works NOT read) | full | Web3D ontology page's books/papers/specs/tools/8 open-work items + why they matter. |
| 7 | hitzler2021-notes.md `1stWdo…` | ~5 KB | 17 Oct | C quotes, L mapping | full | Notes on Hitzler CACM 2021 review. |
| 8 | polys2024-notes.md `1KFlyp…` | ~6 KB | 17 Oct | C quotes, L mapping | full | Notes on Polys, Mohammed, Sandbrook 2024 (1,200 trials). |
| 9 | web3d-search-summaries.md `1miSdF…` | ~4 KB | 17 Oct 18:50Z | **S** (model paraphrase of blocked pages) | full | April 2026 MCP thread, 17 Jul 2026 blog; nothing on ontology. |
| 10 | fetch-list.md `1I3oJ1…` | ~5 KB | 17 Oct 18:55Z | n/a | full | What is still blocked (web3d.org etc.), ranked 1-8, with URLs. |
| 11 | MANIFEST sheet `1PouuT…` | A1:D86 | 17 Oct | C (SHA-1s) | full (listing only) | 85-file SVN mirror manifest (X3dToTurtle.xslt, ontologies 4.0/4.1/t3dmo, queries, papers). Files themselves NOT read. |
| 12 | drive-text/INDEX.md (local) | 78,794 B | 18 Oct | C/L per drift row | grep + threads 68-70 artifact tables read; **skim** rest | 74-thread artifact index. "Artifact content was not read." |
| 13 | drive-text/EVIDENCE.md, REPORT.md (local) | 381,812 / 149,449 B | 16 Oct | Confirmed/Likely/Contested/Suspected/Question | **skim** (head + grep for ledger schema; 0 hits for "ontolog") | Shroud forensic ledger (136 rows) and report. Used only for ledger schema (see HOOKS.md). |
| 14 | x3d_mcp `src/tools/semantics.py`, `src/x3d_utils/ontology.py` (local, HEAD fa0b389) | – | – | C (code) | full | How the ontology is exposed today (see FACTS F-code). |
| 15 | flywheel REPORT.md (`work/trace-pipeline/out/flywheel/`) | 10,254 B | 19 Oct | C/R per line | full | Flywheel stations, F1-F7 toolchain findings. |

## INDEX.md thread entries (my note: only titles/dates, no artifact bodies)
- **68 DSPy prompt optimization agent** (created 17 Oct 16:46Z): artifacts "DSPy across x3d.io: standing note and future plans", "Picture judges: tuning the judge prompt (spec)", "Playground: learned prompt and repair ladder (spec)", "X3D Verifier Gap", "Playground architecture page". Drift row: "DSPy becomes a method for every thread" ● Confirmed (17 Oct 16:46Z-21:09Z).
- **69 X3D traceability for ML pipelines** (16:49Z): Tether Firehose 1-3, "Where X3D-style tethering pays: MLOps stages and other pipelines". Cornerstone status ◐ Likely.
- **70 Lentz and Polys on ontology and AI** (16:59Z): artifact "Ontology, Lentz and Polys: how their work meets ours" (= DOC.md's source).
- **71 Brutzman roadmap** (17:40Z): "Brutzman's roadmap for issue 31: what we have, measured". Not otherwise ingested.
Artifact bodies for 68, 69, 71 are **not available** (private claude.ai URLs). See GAPS.md.

## Added 2026-10-21
| 16 | `data/xslt/X3duomToX3dOntology.xslt` (SVN HEAD via SourceForge) | 67,046 B, 1,220 lines | 29 Sep 2026 header | C (code) | full | The stylesheet that builds the ontology from X3DUOM; basis of the proposal. Untrusted data, never executed. |
| 17 | `data/X3dOntology4.1.ttl` (same mirror) | 1,170,960 B | 29 Sep 2026 | C | parsed, all 18,121 triples | The 4.1 ontology; SHA-1 matches the doc's manifest. |
| 18 | `proposal/PROPOSAL-narrowed-ranges.md` | – | 21 Oct 2026 | draft, HELD | – | Cover note and note for Jakub Flotyński. Not sent. |
| 19 | `dynasty-loom/` (Dynasty Loom v3: hypersphere and loom views of three families, X3D 4.0 in X_ITE 16.5.1) | 9.8 MB, 132 files | 30 Oct 2026 | C (rebuilds byte-identical to the published v3; xmllint, fork validator, Loom gate, CSP gate) | full | Generators, data, ingest (GEDCOM 7 prototype), gates, reports 01-10 and the published release; see `dynasty-loom/README.md`. |
