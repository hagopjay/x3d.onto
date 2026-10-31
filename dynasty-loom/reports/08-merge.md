# 08 · Merge: the genealogy ledger and the loom view

Grades: **Confirmed** = reproduced by the tool run named; **Likely** = read from code or files; **Suspected** = model recall. Generator: `proto/ingest/ingest.py` 0.2.0 (Python 3.13.17, jsonschema 4.26.0, PyLD 2.0.4).

## 1. Result

- 20 sources, 530 person records, **373 persons**. Matches: QID 121, enwiki title 19, folded name + birth year 17; 95 provisional `x:` ids; name alone never matches. 154 unions, 6,038 claims (Likely 4,941, Suspected 1,093, Illustrative 4). [Confirmed: receipt.json, G27]
- Builds are byte-identical (G22 and a second full run). Tests 18/18 (3 new); the original manifest still builds unchanged. [Confirmed: tests/test_proto.py]
- Verdict: *public candidate written; 71 records withheld by error gates*: 39 hidden anyway as possibly living, 32 otherwise public (section 3). [Confirmed]

## 2. Per family (`loom-view.json`)

| | Rothschild | Habsburg | Darwin–Wedgwood |
|---|---|---|---|
| people / core | 120 / 92 | 106 / 75 | 76 / 69 |
| unions / close / dated | 43 / 15 / 40 | 39 / 8 / 10 | 12 / 3 / 1 |
| people C / L / S | 39 / 76 / 5 | 3 / 102 / 1 | 23 / 48 / 5 |
| unions C / L | 21 / 22 | 2 / 37 | 7 / 5 |
| houses | 6 (London, Paris open) | 6 | 8 |
| generations | 0–7 | 0–20 | 0–4 |

- Confirmed needs two independent source families agreeing on birth, death and parents; only 4 Habsburg people appear in two, hence 3 Confirmed. [Confirmed: grade_basis in private/genealogy.graph.json]
- Undated marriages are undated in every source. Rothschild has 10 events (Likely), the others none. [Confirmed: harvest check]

## 3. Gates

- **Error gates, all pass:** G01, G02, G04, G05, G06, G09, G21 (GEDCOM 7 roundtrip), G22, G23 (leak scan), G31 (datagates on the view), G32 (contract). JSON-LD expands for both builds (71,641 and 63,733 triples, no bad IRIs). [Confirmed: gates.json, jsonld-check.json]
- **Cross-checks:** G28 consanguinity 35/35 equal to the fact-check (26 unions, 9 F values); G29 528 parent roles agree with stated sex; G30 172 source_diff values agree, every expected G13/G15/G16 hit found; G26 pass (46 listed children have no record). [Confirmed]
- **datagates via the FamilyMember adapter:** D00 54 errors (31 no birth year, 22 no generation, 1 coverage); D10 26 errors (presumed living, already hidden) and 5 warnings; D08 397 and D14 38 warnings. Also warnings: G07 90 dangling references, G11 111, G13 30. [Confirmed]

**Withheld from the public view (32), no fixes invented:**
- **No birth year in any source (18):** Amschel Moses Rothschild, Schönche Lechnich, Clarice Sebag-Montefiore, David Emmanuel Leonino, Sir Edward Albert Sassoon, Leon Lambert; Isabella of Burgundy, Catherine of Savoy, Elisabeth of Bohemia; Maud du Puy, Ellen Crofts, Jacques Raverat, Amy Ruck, Elinor Monsell, Richard Buckley Litchfield, Charles Langton, Elizabeth Pole, Frances Mosley.
- **No parent or union link, so no generation (13):** Arthur, Bethsabée, Elisabeth, Pauline, Marie-Hélène and Benjamin de Rothschild; Teresa and Elizabeth Charlotte Rothschild; Jacqueline Piatigorsky; Josiah Wedgwood (1st Baron), Josiah Wedgwood V, Sir John Wedgwood (2nd Bt), C. V. Wedgwood.
- **View round (1):** Annabelle Neilson, whose only partner is hidden as possibly living.

## 4. Close-marriage ledger (phi, exact, kinship.py)

**Rothschild** (Confirmed): Natty × Emma 1867 5/32; James × Betty 1824 (uncle–niece) 1/8; Albert × Bettina 1876 1/8; James Édouard × Laura Thérèse 1871 1/8; Edmond × Adelheid 1877 15/128; Ferdinand × Evelina 1865 7/64. At 3/32: Nathaniel × Charlotte 1842, Alphonse × Leonora 1857, Salomon James × Adèle 1862. At 1/16: Anselm × Charlotte 1826, Lionel × Charlotte 1836, Anthony × Louisa 1840, Mayer Carl × Louise 1842, Wilhelm Carl × Mathilde 1849, Adolph Carl × Julie 1850.

**Habsburg** (Likely, undated): Leopold I × Margaret Theresa 0.2610; Philip IV × Mariana 435/2048 (0.2124); Philip II × Anna 5/32; Charles II of Inner Austria × Maria Anna of Bavaria 1/8; Ferdinand III × Maria Anna 0.0986; Philip III × Margaret 21/256; Maximilian II × Maria 1/16; Francis II × Maria Theresa of Naples 1/16.

**Darwin–Wedgwood**, 1/16 each: Josiah III × Caroline Darwin and Charles × Emma (Confirmed); Henry Allen Wedgwood × Jessie (Likely).

phi sees only recorded ancestry, so it is a lower bound: eight documented kin marriages (e.g. Charles V × Isabella of Portugal, Franz Joseph × Elisabeth, Hensleigh × Fanny Mackintosh, the second half of Francis II × Maria Theresa) are not computable; `merge-ledger.json` lists them. The commonly cited F ≈ 0.25 for Charles II of Spain exceeds 0.2124 here. [Suspected: model recall]

## 5. Top conflicts (kept, never silently resolved)

1. Guy de Rothschild's father: Édouard accepted (decisions, fact-check); Alphonse (`family.ts`) and Edmond (HTML copies) kept. [Confirmed: G13]
2. The app's `james_edouard` joins two men (1844–1881 and 1878–1957). [Confirmed: G14]
3. 18 house-label disagreements, fact-check versus harvest, settled by precedence. [Confirmed: G13]
4. 9 enwiki titles differ under one QID (e.g. `Salomon_Rothschild` / `Salomon_Mayer_von_Rothschild`). [Confirmed: G27]
5. Caroline Sarah Darwin's household: Shrewsbury (dw-darwin) or Leith Hill Place (dw-wedgwood). [Confirmed: G13]

## 6. What is missing

- **Naples house:** no harvest partition; its 4 people come from the fact-check file.
- **In-laws ledger:** not harvested; undated in-laws are withheld with their marriages (10 of 30 Darwin–Wedgwood unions). [Confirmed]
- **Habsburgs:** `habs-spanish.json` is empty; Austrian (after 1520) and Lorraine lines not harvested; 13 Lorraine-era people have `family` null.
- **Armenian set:** not harvested.

## 7. Paths

`proto/merged/`: `loom-view.json`, `gates.json`, `receipt.json`, `jsonld-check.json` (+ receipt); `private/` and `public-candidate/` hold graph JSON, JSON-LD, GEDCOM 7, GEDCOM X; `private/` adds `merge-ledger.json`. Config: `proto/ingest/config/merge.json`, `proto/ingest/curated/houses.json`.
