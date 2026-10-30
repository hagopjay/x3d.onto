# 03 - Historical accuracy and data expansion

This report asks two questions: are the people in the genealogy real, correctly dated and correctly linked, and who should be added? Every claim carries a Loom grade:
- **Confirmed**: matches a source fetched in this session.
- **Likely**: supported only indirectly (a catalogue-record title, a search-result label, or an inference from linked records).
- **Suspected**: unsupported or conflicting.

Abbreviations:
- **WP**: the English Wikipedia article on that person.
- **RA**: The Rothschild Archive genealogy (rothschildarchive.org/genealogy and family.rothschildarchive.org).
- **DCP**: the Darwin Correspondence Project name register.

## 1. Bottom line

- **What the upload holds.** There are four versions of the Rothschild tree, holding 9, 18, 26 and 26 people (26 distinct), plus two stubs with 3 people.
- **What is wrong.** I logged **33 findings** (table in section 4):
  - 10 structural errors that mis-draw the tree: wrong parent, generation or dates.
  - 16 wrong, overstated or unsourced claims in notes.
  - 3 dead links or fake portraits.
  - 4 issues of naming, linking, precision or omission.
- **What I built.** A corrected and expanded dataset of **140 deceased people**: Rothschild 71, Habsburg 38 and Darwin-Wedgwood 31.
  - It has the same shape as `rothschild.json`.
  - It adds `qid`, `qid_confidence`, `born_precision`, `died_precision`, `spouses[]`, `sources[]` and `confidence`.
- **Cousin marriages.**
  - **26 kin marriages are computed** from the parent links. Each has a named relationship and the inbreeding coefficient F of the couple's children.
  - **8 more are documented** where the shared ancestors fall outside the modelled pedigree.
  - Pedigree-collapse tables cover 9 showcase people.
- **Main caveat: Wikidata was unreachable from this sandbox,** so no QID was read from Wikidata itself.
  - 6 QIDs are Confirmed through DBpedia owl:sameAs.
  - 122 are Likely (a unique label match in search results).
  - 11 are Suspected, and 1 was not found.
  - A one-pass verification is needed before anything keys on QIDs (section 8).

## 2. Method and source access

**Parsing.** Source files were parsed as text (regex or JSON); nothing in the upload was executed. `diff_sources.py` produces the per-person diff in `source_diff.json`.

**Sources checked against:**
- WP article pages and RA person pages.
- DCP name registers and Cambridge and Trinity archive catalogue records.
- Royal Collection Trust and Royal Museums Greenwich object records, for two Habsburgs.
- Alvarez, Ceballos and Quinteiro (2009), PLoS ONE 4(4): e5174 (https://doi.org/10.1371/journal.pone.0005174), for the Spanish Habsburg inbreeding benchmark.

**What was blocked:**
- The fetch tool refused wikidata.org, Wikimedia Commons, the Wikipedia API and any URL with a query string.
- DBpedia SPARQL failed (URL too long), and parallel DBpedia page fetches were rate-limited.
- **The shared web-fetch budget ran out late in the session.** After that, the last Darwin descendants were checked only through search-result titles. Charles Galton Darwin, Frances Cornford and Nora Barlow were left out rather than added unverified.

**Generations are recomputed, not copied:**
- Founders are generation 1.
- A child is 1 plus the lower of its parents' generations.
- A spouse who married in takes their spouse's generation.

This rule exposes the generation errors below.

**Kinship uses Wright's path method** over the parent links:
- Path pairs are grouped into named relationships, such as "double first cousins once removed".
- Each total is asserted equal to an independently computed recursive kinship coefficient. The assertion passes for all 26 couples.
- **Every pedigree is truncated, so every computed F is a lower bound.**

## 3. What the sources contain (diff)

| Ver. | File (identical copies) | People |
|---|---|---|
| A | roths/data/trees/rothschild.json (also "roths - Copy" and the roths/dist bundle) | 9 |
| B | roths/data/family.ts (also roths2, roths3, "roths - Copy" and the roths2/dist bundle) | 18 |
| C | rothschilds.html (embedded data) | 26 |
| D | rothsch2.html (also roths/collateral/rothsch2.html) | 26 |
| S1, S2 | habsburg_stub.json; darwin_wedgwood_stub.json | 1; 2 |

By id, the versions nest: A is inside B, B is inside C, and C equals D. Apart from note wording, they differ only in these ways:
- **Dates:** only `james_edouard` differs (C has 1844-1881; D has 1878-1957).
- **Parents:** only `betty` differs (C gives none) and `guy` (B says alphonse; C and D say edmond; all are wrong).
- **Fields and names:** C has no `branch` field. C also renames Betty "Betty Salomon Rothschild" and calls the 1819 Charlotte "Charlotte de Rothschild", which is the name of her 1825 cousin.
- **Generations:** `generation` is identical in every version, so the generation errors are shared by all of them.
- **Broken links:**
  - In B, `victor` points to a parent `charles` that B does not define.
  - In S2, Emma has `spouse: charles_darwin`, but Charles has no spouse.
- **Id changes in the new data:**
  - `hannah` becomes `hannah_cohen`.
  - `charlotte` becomes `charlotte_1819`.
  - `nathaniel` becomes `natty`, to separate him from Nathaniel (1812-70).
  - `emma_wedgwood` becomes `emma_darwin`.
  - Every other source id is kept.

## 4. Error table

"Grade" is the confidence in the correction.

| # | Person | Field | Files | Source value | Correct value | Grade | Source |
|---|---|---|---|---|---|---|---|
| 1 | Mayer Amschel | born | A B C D | 1744 | 23 Feb 1743 or 1744 (sources differ). Kept 1744 with born_precision "uncertain". A precision flag, not an error | Confirmed | WP; RA |
| 2 | Gutle Schnapper | wikipedia | A B | en.wikipedia link | The linked page does not exist; set to null | Confirmed | Fetch of the link |
| 3 | Gutle Schnapper | note | A B D | "remained in Frankfurt all her life" | Not found in any source; removed | Suspected | WP Mayer; RA |
| 4 | Hannah Barent Cohen | wikipedia | A B | en.wikipedia link | The linked page does not exist; set to null | Confirmed | Fetch of the link |
| 5 | Hannah Barent Cohen | note | A B | "key advisor" | Not found; removed | Suspected | WP Nathan; RA |
| 6 | Nathan | note | A B D | "Financed Wellington's armies..." | Overstated. From 1811, working with J. C. Herries, he arranged transfers of government money to pay Wellington's troops | Likely | WP Nathan |
| 7 | Carl | note | A B D | "later moved to Frankfurt" | Wrong. He founded the Naples house in 1821 and died in Naples on 10 Mar 1855; his sons took over Frankfurt | Confirmed | WP Carl |
| 8 | James | note | A B D | "King of Bankers" | No source found for the epithet; dropped | Suspected | WP James |
| 9 | James | tour title | roths/constants.tsx | "Railway King" | No source found for the epithet; attribute or drop | Suspected | WP James |
| 10 | Betty | note | A B D | "art collector" | A salon hostess and patron of the arts; Ingres painted her portrait (1841-48) | Likely | WP Betty |
| 11 | Betty | generation | A B C D | 2 | 3 by descent (she is Salomon's daughter). Draw her marriage to her uncle James as an edge that crosses generations | Confirmed | Parent links |
| 12 | Betty | parents, name | C | [] ; "Betty Salomon Rothschild" | [salomon, caroline_stern] ; "Betty von Rothschild" | Confirmed | WP; RA |
| 13 | Charlotte (1819-84) | note | B D | "Artist and pianist" | Confused with her cousin Charlotte (1825-99). This Charlotte was a London hostess and an education philanthropist | Confirmed | RA person 41; WP |
| 14 | Charlotte (1819-84) | name | C | "Charlotte de Rothschild" | "Charlotte von Rothschild", to avoid confusion with her 1825 namesake | Confirmed | RA |
| 15 | Anselm | note | B D | "Rebuilt the Vienna branch after 1848" | Vague. He headed the Vienna house after Salomon and founded the Creditanstalt (1855) | Likely | WP Anselm |
| 16 | Natty (source id `nathaniel`) | note | B D | "First Jewish peer in Britain" | First Jewish member of the House of Lords who had not converted (made Baron Rothschild in 1885) | Likely | WP Natty |
| 17 | Edmond James | generation | B C D | 4 | 3 (son of James) | Confirmed | Parent links |
| 18 | Victor | parents | B | `charles` (no such record) | Add Charles Rothschild (1877-1923) and Rozsika | Confirmed | WP Charles |
| 19 | Guy | parents | B; C D | alphonse; edmond | Edouard Alphonse James de Rothschild (1868-1949) | Confirmed | WP Guy |
| 20 | Guy | generation | B C D | 6 | 5 | Confirmed | Parent links |
| 21 | Guy | note | B C D | "Nationalised 1981" | Nationalised in 1982 by the Mitterrand government | Likely | WP Guy |
| 22 | James Edouard | parents, generation | C D | alphonse; 5 | Nathaniel (1812-70) and Charlotte (1825-99); 4 | Confirmed | WP; RA |
| 23 | James Edouard | born, died | D | 1878-1957 | 1844-1881 (D used James Armand's dates) | Confirmed | WP |
| 24 | Maurice | generation | C D | 5 | 4 (son of Edmond) | Confirmed | Parent links |
| 25 | Maurice | note | D | "...Lafite." | No source links him to Lafite. His documented career: deputy 1919-29, then senator for Hautes-Alpes 1929-45 | Suspected (claim) | WP Maurice |
| 26 | Edmond Adolphe | generation | C D | 6 | 5 | Confirmed | Parent links |
| 27 | Edmond Adolphe | note | D | "LCF Rothschild Group" | He founded La Compagnie Financiere Edmond de Rothschild (1953), the root of the Edmond de Rothschild Group | Likely | WP |
| 28 | Ferdinand | note | D | Left Waddesdon to the National Trust | Wrong. He left Waddesdon to his sister Alice and bequeathed the Waddesdon Bequest to the British Museum (1898) | Confirmed | WP Ferdinand |
| 29 | Miriam | note | D | "30,000 specimens" | Figure not found; dropped. Documented: co-author of the six-volume Rothschild flea catalogue (1953-81) | Suspected (figure) | WP Miriam |
| 30 | Victor | note | D | "Soviet spy (never proven)" | Misleading framing. In 1986 the government said it had no evidence he had ever been a Soviet agent | Likely | WP Victor |
| 31 | Mayer, Gutle | imageUrl | A B | picsum.photos URLs | Random stock photos posing as portraits; dropped | Confirmed | picsum is a random-image service |
| 32 | Emma Darwin | spouse | S2 | One-way link | Reciprocal `spouses` on both records | Confirmed | S2 itself |
| 33 | Founders' wives and others | omissions | all | The brothers' and Anselm's marriages are missing | Added Eva Hanau, Caroline Stern, Adelheid Herz, Charlotte (1807) and others | Confirmed | RA; WP |

**Correct as given** (Confirmed against WP):
- All other dates in the sources.
- Lionel as "first Jewish MP (1858)".
- Alfred's Bank of England directorship.
- Charles founding the SPNR (1912).
- The stubs' dates for Maximilian I, Charles Darwin and Emma.

Where WP prose uses looser kinship terms, the dataset uses the computed relationship instead. Examples are "niece" for Alphonse's wife Leonora, and "second cousin" for the Ferdinand-Evelina and Albert-Bettina marriages.

## 5. Expansion

Each record carries a rewritten, sourced note.

**Rothschild: 71 people, generations 1-7.** It covers all five brothers' houses:
- **Frankfurt:** Amschel and Eva Hanau, plus Carl's sons Mayer Carl and Wilhelm Carl.
- **Vienna:** Salomon, then Anselm, then Ferdinand, Albert Salomon and Alice, then Louis Nathaniel.
- **London:**
  - Nathan's children: Lionel, Anthony, Mayer Amschel, Hannah Mayer and Louise.
  - Lionel's children: Natty, Leopold, Alfred, Leonora and Evelina; Mayer Amschel's daughter Hannah Primrose.
  - Natty's sons Walter and Charles; Charles's children Victor, Miriam and Nica; Victor's son Jacob.
  - Also Evelyn and Edmund.
- **Naples:** Carl and his son Adolph Carl.
- **Paris:**
  - James's children: Alphonse, Gustave, Salomon James, Edmond and Charlotte.
  - Later generations: Alphonse's son Edouard and grandson Guy; Robert and his son Elie; Edmond's son Maurice and grandson Edmond Adolphe.
  - The Mouton line runs Nathaniel, James Edouard, Henri, Philippe and Philippine.
- **Branch** keeps the original convention: the house where the person lived or worked.

**Habsburg: 38 people, generations 1-14,** descending from Maximilian I and Mary of Burgundy:
- **Spanish line:** Charles V and Philips II to IV, down to Charles II. It includes every bride whose marriage feeds Charles II's pedigree, so his pedigree collapse can be computed.
- **Austrian line:** Ferdinand I down to Franz Joseph, Elisabeth and Rudolf. It includes Maria Theresa's children Joseph II, Leopold II, Marie Antoinette and Maria Carolina.
- **Branch** is "Spain" or "Austria".

**Darwin-Wedgwood: 31 people, generations 1-5.** This is the showcase:
- **Founders:** two couples, Josiah Wedgwood I and Sarah, and Erasmus Darwin and Mary Howard.
- **The three Darwin-Wedgwood marriages:** Robert and Susannah (1796), Caroline Darwin and Josiah III, and Charles and Emma.
- **Others included:** the Allen-sister cousin marriages; Francis Galton, Charles's half first cousin through Violetta; Charles's children; Ralph Vaughan Williams; and Gwen Raverat.
- **Branch** is the birth family. In-laws take their spouse's family.

**Living people are excluded:**
- Every record has a death year, and the build fails if a death year is missing or later than 2025.
- The latest deaths are Jacob, 4th Baron Rothschild (2024), and Evelyn de Rothschild (2022).
- No living spouse or child is recorded.

## 6. Cousin marriages and pedigree collapse

**Computed from the dataset's parent links.** Each entry gives the couple, the relationship and the F of their children; F is a lower bound. The full path lists are in `consanguinity.json`.

**Rothschild (15):**

| Couple | Relationship | F |
|---|---|---|
| Betty x James | uncle-niece | 0.125 |
| Anselm x Charlotte (1807) | first cousins | 0.0625 |
| Lionel x Charlotte (1819) | first cousins | 0.0625 |
| Anthony x Louisa Montefiore | first cousins | 0.0625 |
| Mayer Carl x Louise | first cousins | 0.0625 |
| Nathaniel x Charlotte (1825) | first cousins; also first cousins once removed | 0.094 |
| Adolph Carl x Julie | double first cousins once removed | 0.0625 |
| Wilhelm Carl x Mathilde | double first cousins once removed | 0.0625 |
| Alphonse x Leonora | double first cousins once removed; also double second cousins | 0.094 |
| Salomon James x Adele | double first cousins once removed; also double second cousins | 0.094 |
| Edmond x Adelheid | double first cousins once removed; also second cousins (+3 more distant links) | 0.117 |
| Ferdinand x Evelina | first cousins; also 3-fold second cousins | 0.109 |
| Albert x Bettina | double first cousins once removed; also double second cousins (+4) | 0.125 |
| Natty x Emma | double first cousins; also double second cousins | 0.156 |
| James Edouard x Therese | first cousins; also 3-fold second cousins (+2) | 0.125 |

**Habsburg (8):**

| Couple | Relationship | F |
|---|---|---|
| Philip II x Anna | uncle-niece; also first cousins once removed | 0.156 |
| Maximilian II x Maria | first cousins | 0.0625 |
| Charles II of Inner Austria x Maria Anna of Bavaria | uncle-niece | 0.125 |
| Philip III x Margaret | first cousins once removed; also double second cousins (+3) | 0.082 |
| Philip IV x Mariana | uncle-niece; also first cousins once removed (+20) | 0.212 |
| Ferdinand III x Maria Anna of Spain | first cousins; also 3-fold second cousins once removed (+5) | 0.099 |
| Leopold I x Margaret Theresa | uncle-niece; also first cousins (+39) | 0.261 |
| Francis II x Maria Theresa of Naples | first cousins (only half modelled; they were double first cousins) | 0.0625 |

**Darwin-Wedgwood (3):** Caroline Darwin x Josiah III, Charles x Emma, and Henry Allen x Jessie are all first cousins (F 0.0625).

**Documented but not computable (8).** The common ancestors are not in the data, so these should be drawn as annotated edges rather than inferred:
- Charles V x Isabella of Portugal: first cousins.
- Ferdinand II x Maria Anna of Bavaria (b. 1574): first cousins.
- Maria Theresa x Francis Stephen: half second cousins.
- Francis II x Maria Theresa of Naples: double first cousins.
- Franz Joseph x Elisabeth: first cousins.
- Josiah I x Sarah Wedgwood: distant cousins.
- Henry Allen x Jessie: double first cousins (their fathers were brothers and their mothers were sisters).
- Hensleigh Wedgwood x Fanny Mackintosh: first cousins through the Allen sisters.

**Pedigree collapse.** Each figure is slots / recorded / distinct ancestors at that generation back.
- **Walter Rothschild (F 0.156):**
  - Great-grandparents: 8 / 8 / 4.
  - Great-great-grandparents: 16 / 8 / 2. All 8 recorded slots are Mayer Amschel and Gutle. This is the clearest single picture of the family's marriage strategy.
- **Charles II of Spain:**
  - Generations 3 to 6 back: 8/7/7, 16/13/11, 32/20/9 and 64/24/8.
  - **The dataset gives F 0.212, against the published 0.254** (Alvarez et al. 2009). The gap is expected, because the published figure uses a 16-generation pedigree of about 3,000 people. Show 0.254 as the cited value and 0.212 as "computed from this tree".
- **Philip IV:** F 0.082; 64 / 6 / 2 at six generations back.
- **Louis Nathaniel (Vienna):** F 0.125; 32 / 6 / 2 at five generations back.
- **William Erasmus Darwin:** F 0.0625. Of 8 great-grandparent slots, 6 are recorded and only 4 people are distinct, because Josiah I and Sarah fill four slots.
- **Ralph Vaughan Williams and Gwen Raverat:** F 0, because only one parent of each is in the data. Even so, Josiah I and Sarah each appear twice among their recorded great-great-grandparents.

## 7. Confidence policy as implemented

- **`confidence`** grades a person's core facts: dates, parents and spouses.
  - Confirmed: matches a source fetched in this session.
  - Likely: inferred, or supported only by a catalogue-record title.
  - Suspected: conflicting or unverifiable.
- **Record confidence by family:**
  - Rothschild: all 71 Confirmed.
  - Habsburg: 37 Confirmed and 1 Likely (Maria Carolina, from an RMG record).
  - Darwin-Wedgwood: 29 Confirmed and 2 Likely. Margaret Wedgwood's parentage is inferred, and Gwen Raverat's parentage was not fetched.
- **Unverifiable claims in notes** were removed rather than kept as Suspected text.
- **`qid_confidence`** has three levels:
  - Confirmed: via DBpedia sameAs.
  - Likely: a unique label match.
  - Suspected: ambiguous. For example, Charlotte (1807) has a possible duplicate item, Q107358812.
- **`wikipedia`** is null wherever no article was verified: Gutle, Hannah Cohen and Alice.
- **`imageUrl`** is dropped. Real portraits should come from Commons through verified QIDs, with licence metadata.
- **`spouse`** is kept as the first entry of `spouses[]` for backward compatibility. Consumers should read `spouses`.

## 8. Recommendations to the other workstreams

1. **Verify the QIDs** before relying on them. Run one mechanical pass over Wikidata `Special:EntityData/<QID>.json`, comparing the label, birth and death (P569/P570) and father and mother (P22/P25) against each record. Promote the matches to Confirmed and list the mismatches.
2. **Use the recomputed `generation`.** Draw marriages across generations, such as Betty x James and Philip IV x Mariana, as edges spanning generation rows. That is the visual signature of pedigree collapse.
3. **Take relationship labels and F from `consanguinity.json`,** not from note prose. Label F as a lower bound unless a published value is cited.
4. **Next additions,** budget permitting:
   - Darwin: Charles Galton Darwin, Frances Cornford, Nora Barlow and Bernard Darwin.
   - Rothschild: the remaining in-law spouses of the London line and the Rosebery grandchildren.
   - Habsburg: the Wittelsbach parents, so that the Ferdinand II and Franz Joseph marriages become computable.

## Files

- scratchpad/proto/facts/rothschild.json
- scratchpad/proto/facts/habsburg.json
- scratchpad/proto/facts/darwin_wedgwood.json
- scratchpad/proto/facts/consanguinity.json (computed and documented kin marriages, path lists, pedigree collapse)
- scratchpad/proto/facts/source_diff.json (per-person diff of versions A-D, S1, S2)
- scratchpad/proto/facts_build/build_facts.py (data, integrity checks and kinship engine). Rebuild with: `python3 -I build_facts.py <out_dir>`
- scratchpad/proto/facts_build/diff_sources.py (text-only parser of the source files)
