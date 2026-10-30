# 09 · Tapestry loom: fix round on the critique

Input `proto/merged/loom-view.json` (sha256 `2aef8ce4…`) matches the data receipt (Confirmed, sha256). Changed: `build_loom_scene.py`, `page/index.html`, `tools/gate_loom.js`, `tools/write_receipt.py`. A second build is byte-identical (Confirmed, cmp). The critique was cut off inside fix 1's gate; fixes 2–6 follow its "Answers to the brief".

## Layout grammar
- Time runs up; houses stand west to east by longitude, latitude as shallow depth. A cloth narrower than 1.2 (width/height) is widened up to 3.5× (Habsburg 3.42×).
- A life is a warp thread; a marriage, a level weft pick, doubled and near-white when close, "?" without a year. Dye: ecru toward each house's dye in CIELAB at L* 54.
- Moves: a dated record first (the data's `moved`, else a report 07 seed), else the first pick into the adult house (one spouse moves if the other was born there, both if neither was). Only someone with no such pick gets birth + 21, dotted, its year never printed. In-laws follow their spouse; an open diamond marks the mover.
- Each stop has its own fell; its subject gets a ring, a silver line back to a founder and a label. Front stops use a long lens (fov 0.24) with a year rail at the subject's depth; Wide uses 0.72.

## What each stop shows
Rothschild (12): Cloth (founders); Judengasse 1740–84 (Mayer); No. 148 (Gutle); Five Arrows 1792–1831 (Nathan 1798 C, James 1811 S, Salomon 1820 S, Carl 1821 C); Doubles (James and Betty); Frankfurt 1836 (Lionel, Charlotte, Nathan); Close weave (12 brides, 4 grooms cross on close picks); Seats; Naturalists; Zikhron (Edmond); Ruptures (report 07's closings: Naples 1863, Frankfurt 1901, Vienna 1938, Paris 1982); Wide.

Habsburg and Darwin–Wedgwood (8 each): Cloth, The first threads, The founders' children, The houses part, Doubles, Close weave (Charles and Emma), Ruptures, Wide.

## Critique: asked and done
1. Moves, as specified: the `oth in done` birth-order test is gone; the four sons move on report 07's years. Moves by kind: Rothschild 4 dated, 22 wedding, 2 following, 2 estimated; Habsburg 14 wedding; Darwin–Wedgwood 8 wedding, 3 estimated. Scene gate `moves` fails the build on an unexplained move, an estimate where a marriage into that house exists, or a printed estimate. `moved` is requested in `out/data-issues.json`; the contract is unedited.
2. Closings: the data's "closed" is the last core death (Naples 1907, Frankfurt 1924), no longer called a closing; the cloth marks report 07's graded closings and lists the conflict.
3. Subjects: all labelled on desktop, with a leader where the row is full, including Nathan (Rothschild stop 7) and Charles (Darwin–Wedgwood stop 8).
4. Names: on their thread's row or dropped, in front of every house plane, clip lifted per stop; Wide no longer cuts them.
5. Dye: each quarter step now moves 19.1 dE76 (Rothschild), 14.5 (Habsburg), 12.8 (Darwin), 15.4 (Wedgwood); close picks are near-white, not orange-red; the page has a dye gauge.
6. Phone: per-stop viewpoints and labels, at least 12 px tall (were about 5).

Also: rail readings within 0.82 yr at every front stop (limit 1.0); Habsburg's cloth widened from about 270 to 730 px; light panels toned down.

## Gates (all pass)
- Generator (Confirmed): xmllint (libxml 20914) against the fork's x3d-4.0.xsd and the x3d_mcp validator `acdf5c4`: all three scenes CLEAN, 0 errors, 0 warnings. Scene gates `moves`, `dye_ramp`, `rail_reading`, `subjects_labelled`, `names_on_their_rows`: ok for all three.
- Live `tools/gate_loom.js --all-stops`: 54/54 (Confirmed) on X_ITE 16.5.1 (vendored), Chromium 153.0.8010.12 with SwiftShader, Playwright 1.63.0, node v22.22.0, Python 3.13.17: 28 desktop stops (labels bound and on-row by X_ITE text bounds, fell, subjects), 12 Rothschild phone stops at 390×844, pick, keys, clean console, local-only network.
- Frames (Confirmed): 41 in `frames/final/` (28 desktop, 1 pick, 12 phone), non-black by `lookgates.py` (numpy 2.5.4, Pillow 13.0.0).
- Artifact: `make_artifact.py` 67 files, 6,609,598 bytes, no secrets, 302 people, none possibly living. `artifact_csp_gate.js` PASS, 6/6 checks, desktop-light and phone-dark; harmless notes: CSP blocks X_ITE's PT Sans fonts and a WebAssembly compile (labels use the bundled TTF), local favicon 404. Likely on the real host, whose policy the gate only copies.

## Sizes
| family | x3d bytes (gz) | cards bytes |
|---|---|---|
| rothschild | 209,880 (24,760) | 192,475 |
| habsburg | 160,377 (20,044) | 138,700 |
| darwin_wedgwood | 161,449 (19,320) | 112,033 |

## What is left
- Five Arrows: the window still gets about 110 px of 700 (critique: 140), because the four moves span the cloth; it needs report 07's top-down view.
- Unnamed houses: Rothschild Cloth and Ruptures (Naples); Habsburg Cloth (Tyrol), Ruptures (Tyrol, Albertine), Wide (Styria); Darwin–Wedgwood Cloth (Etruria/Maer, Hensleigh, Cambridge), Wide (Down).
- Phone: a subject goes unlabelled at 4 stops: Rothschild Five Arrows (Carl), Habsburg founders' children (2 of 4), Darwin–Wedgwood Cloth (2 of 4) and first threads (Mary Howard). Habsburg and Darwin–Wedgwood phone labels: not measured live (Likely).
- Listed, not drawn (S, review 08): Charles and Emma's 1839 wedding year and 1842 move to Down; Robert at The Mount from 1786; Josiah III to Leith Hill in 1847.
- Data stage: define house opened/closed; add `moved`; fill null union years (3 of 43, 29 of 39, 11 of 12); resolve "James Édouard" (1878–1957, father Alphonse; James Armand's dates), drawn as filed (Suspected, duplicate check).

Receipts: `scene2/receipt.json`, `out/receipt.json`, `frames/final/receipt.json`, `artifact/receipt.json`.
